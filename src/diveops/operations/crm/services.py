"""CRM service layer for lead management.

Clean domain logic for lead pipeline operations.
Views should call these functions instead of manipulating models directly.
"""

from django.db import transaction
from django.utils import timezone

from django_parties.models import Person, LeadStatusEvent

from ..models import DiverProfile


def is_lead(person: Person) -> bool:
    """Check if a Person is a lead (has lead_status set)."""
    return person.lead_status is not None


@transaction.atomic
def set_lead_status(
    person: Person,
    new_status: str,
    actor=None,
    note: str = None,
    lost_reason: str = None,
) -> LeadStatusEvent:
    """Change a lead's pipeline status.

    Args:
        person: The Person record to update
        new_status: Target status (new, contacted, qualified, converted, lost)
        actor: User making the change (optional)
        note: Optional note about the status change
        lost_reason: Reason for loss (only used when new_status='lost')

    Returns:
        The created LeadStatusEvent

    Raises:
        ValueError: If new_status is invalid
    """
    valid_statuses = dict(Person.LEAD_STATUS_CHOICES).keys()
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {list(valid_statuses)}")

    old_status = person.lead_status

    # Update person
    person.lead_status = new_status
    update_fields = ["lead_status", "updated_at"]

    if new_status == "lost" and lost_reason:
        person.lead_lost_reason = lost_reason
        update_fields.append("lead_lost_reason")

    person.save(update_fields=update_fields)

    # Create audit event
    event = LeadStatusEvent.objects.create(
        person=person,
        from_status=old_status or "",
        to_status=new_status,
        actor=actor,
        note=note or "",
    )

    return event


@transaction.atomic
def convert_to_diver(person: Person, actor=None) -> DiverProfile:
    """Convert a lead to a diver.

    Creates a DiverProfile if one doesn't exist, sets lead_status to 'converted',
    and records the conversion timestamp.

    Args:
        person: The Person record to convert
        actor: User performing the conversion (optional)

    Returns:
        The DiverProfile (created or existing)

    Raises:
        ValueError: If person is not a lead
    """
    if not is_lead(person):
        raise ValueError("Person is not a lead (lead_status is null)")

    old_status = person.lead_status

    # Create or get DiverProfile
    # Parse experience from notes if available
    total_dives = 0
    notes = person.notes or ""
    if "Never dived" in notes:
        total_dives = 0
    elif "1-10" in notes:
        total_dives = 5
    elif "10-50" in notes:
        total_dives = 30
    elif "50+" in notes:
        total_dives = 75

    diver_profile, created = DiverProfile.objects.get_or_create(
        person=person,
        defaults={"total_dives": total_dives},
    )

    # Update lead status
    person.lead_status = "converted"
    person.lead_converted_at = timezone.now()
    person.save(update_fields=["lead_status", "lead_converted_at", "updated_at"])

    # Record status event
    LeadStatusEvent.objects.create(
        person=person,
        from_status=old_status or "",
        to_status="converted",
        actor=actor,
        note=f"Converted to diver. DiverProfile {'created' if created else 'already existed'}.",
    )

    return diver_profile


def add_lead_note(person: Person, body: str, author=None):
    """Add a note to a lead.

    Args:
        person: The Person record
        body: Note text
        author: User creating the note (optional)

    Returns:
        The created LeadNote
    """
    from django_parties.models import LeadNote

    return LeadNote.objects.create(
        person=person,
        body=body,
        author=author,
    )


def get_lead_notes(person: Person):
    """Get all notes for a lead, newest first.

    Args:
        person: The Person record

    Returns:
        QuerySet of LeadNote objects
    """
    from django_parties.models import LeadNote

    return LeadNote.objects.filter(person=person).select_related("author").order_by("-created_at")


def get_lead_timeline(person: Person):
    """Get combined timeline of status events and notes for a lead.

    Args:
        person: The Person record

    Returns:
        List of events/notes sorted by created_at descending
    """
    from django_parties.models import LeadNote

    events = list(
        LeadStatusEvent.objects.filter(person=person)
        .select_related("actor")
        .order_by("-created_at")
    )
    notes = list(
        LeadNote.objects.filter(person=person)
        .select_related("author")
        .order_by("-created_at")
    )

    # Combine and sort
    timeline = []
    for event in events:
        timeline.append({
            "type": "status_change",
            "created_at": event.created_at,
            "actor": event.actor,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "note": event.note,
            "obj": event,
        })
    for note in notes:
        timeline.append({
            "type": "note",
            "created_at": note.created_at,
            "actor": note.author,
            "body": note.body,
            "obj": note,
        })

    timeline.sort(key=lambda x: x["created_at"], reverse=True)
    return timeline


def get_or_create_lead_conversation(person: Person):
    """Get or create the single conversation for a person.

    Thread-safe via unique constraint + get_or_create.
    Returns the same conversation across lead→account→diver lifecycle.

    Args:
        person: The Person record (lead, account, or diver)

    Returns:
        Conversation instance
    """
    from django.contrib.contenttypes.models import ContentType
    from django_communication.models import Conversation

    person_ct = ContentType.objects.get_for_model(Person)

    conversation, created = Conversation.objects.get_or_create(
        related_content_type=person_ct,
        related_object_id=str(person.pk),
        defaults={
            "subject": f"Chat with {person.first_name} {person.last_name}".strip() or "Chat",
            "status": "active",
        },
    )
    return conversation


def get_lead_conversation(person: Person):
    """Get the conversation for a person if it exists.

    Args:
        person: The Person record

    Returns:
        Conversation instance or None
    """
    from django.contrib.contenttypes.models import ContentType
    from django_communication.models import Conversation

    person_ct = ContentType.objects.get_for_model(Person)

    return Conversation.objects.filter(
        related_content_type=person_ct,
        related_object_id=str(person.pk),
    ).prefetch_related("messages").first()


def send_lead_notification_email(
    person: Person,
    message: str,
    staff_user=None,
    message_obj=None,
) -> bool:
    """Send email notification to lead when staff replies.

    Returns True if email was sent successfully, False otherwise.
    Never raises - logs failures and returns False.
    """
    import logging
    from django.core.mail import EmailMessage
    from django.conf import settings

    logger = logging.getLogger(__name__)

    if not person.email:
        logger.warning(
            "Cannot send email: lead has no email",
            extra={"lead_id": str(person.pk)},
        )
        return False

    try:
        subject = "New message from Happy Diving"

        body = f"""Hi {person.first_name or "there"},

You have a new message from our team:

---
{message}
---

To continue the conversation, visit our website chat or reply to this email.

Happy Diving Team
Puerto Morelos, Mexico
"""

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[person.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        email.send(fail_silently=False)

        if message_obj:
            message_obj.status = "sent"
            message_obj.sent_at = timezone.now()
            message_obj.save(update_fields=["status", "sent_at", "updated_at"])

        logger.info(
            "Email sent to lead",
            extra={
                "lead_id": str(person.pk),
                "lead_email": person.email,
                "message_id": str(message_obj.pk) if message_obj else None,
                "staff_user": staff_user.email if staff_user else None,
            },
        )
        return True

    except Exception as e:
        logger.exception(
            "Failed to send email to lead",
            extra={
                "lead_id": str(person.pk),
                "lead_email": person.email,
                "error": str(e),
            },
        )

        if message_obj:
            message_obj.status = "failed"
            message_obj.save(update_fields=["status", "updated_at"])

        return False


def broadcast_conversation_message(
    conversation_id: str,
    message_id: str = None,
    message_text: str = "",
    sender_person_id: str = None,
    sender_name: str = "",
    created_at: str = None,
):
    """Broadcast a conversation message via WebSocket.

    Sends to the conversation room so all participants see the message.

    Args:
        conversation_id: UUID of the Conversation
        message_id: UUID of the Message
        message_text: The message body
        sender_person_id: UUID of the sender Person
        sender_name: Display name of sender
        created_at: ISO timestamp of when message was created
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer configured, skipping WebSocket broadcast")
            return

        message_data = {
            "type": "new_message",
            "message_id": message_id,
            "message": message_text,
            "body": message_text,
            "sender_person_id": sender_person_id,
            "sender_name": sender_name,
            "created_at": created_at or timezone.now().isoformat(),
        }

        # Broadcast to conversation room
        conversation_room = f"chat_conversation_{conversation_id}"
        async_to_sync(channel_layer.group_send)(conversation_room, message_data)

        logger.debug(
            "Broadcast conversation message via WebSocket",
            extra={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "sender_person_id": sender_person_id,
            },
        )
    except Exception as e:
        logger.exception(f"Failed to broadcast conversation message: {e}")


def broadcast_chat_message(
    person_id: str,
    visitor_id: str = None,
    message_id: str = None,
    message_text: str = "",
    direction: str = "inbound",
    created_at: str = None,
):
    """Broadcast a chat message via WebSocket.

    Sends to both visitor and lead room groups so both parties see the message.

    Args:
        person_id: UUID of the Person (lead)
        visitor_id: Visitor ID cookie value (for visitor's room)
        message_id: UUID of the Message
        message_text: The message body
        direction: 'inbound' (from visitor) or 'outbound' (from staff)
        created_at: ISO timestamp of when message was created
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer configured, skipping WebSocket broadcast")
            return

        message_data = {
            "type": "new_message",
            "message_id": message_id,
            "message": message_text,
            "direction": direction,
            "created_at": created_at or timezone.now().isoformat(),
        }

        # Broadcast to lead room (for staff viewing this lead)
        lead_room = f"chat_lead_{person_id}"
        async_to_sync(channel_layer.group_send)(lead_room, message_data)

        # Broadcast to visitor room (for the visitor's chat widget)
        if visitor_id:
            visitor_room = f"chat_visitor_{visitor_id}"
            async_to_sync(channel_layer.group_send)(visitor_room, message_data)

        logger.debug(
            "Broadcast chat message via WebSocket",
            extra={
                "person_id": person_id,
                "visitor_id": visitor_id,
                "message_id": message_id,
                "direction": direction,
            },
        )
    except Exception as e:
        # Don't fail the main operation if WebSocket broadcast fails
        logger.exception(f"Failed to broadcast chat message: {e}")
