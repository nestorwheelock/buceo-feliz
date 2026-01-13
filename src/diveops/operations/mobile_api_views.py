"""Mobile API views for the staff chat Android app.

These endpoints power the mobile app with:
- Authentication via token
- FCM device registration
- Conversations list
- Chat messages
- Send message functionality
"""

import json
import logging

from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django_parties.models import Person
from django_communication.models import (
    Conversation,
    ConversationStatus,
    FCMDevice,
    Message,
)

logger = logging.getLogger(__name__)


def require_auth_token(view_func):
    """Decorator to require Bearer token authentication."""
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization required"}, status=401)

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Look up the token
        from rest_framework.authtoken.models import Token
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            if not token_obj.user.is_active or not token_obj.user.is_staff:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            request.user = token_obj.user
        except Token.DoesNotExist:
            return JsonResponse({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper


@method_decorator(csrf_exempt, name="dispatch")
class MobileLoginView(View):
    """Login endpoint for mobile app.

    POST /api/mobile/login/
    {
        "email": "user@example.com",
        "password": "secret"
    }

    Returns auth token for subsequent requests.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)

        # Authenticate
        user = authenticate(request, username=email, password=password)

        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not user.is_staff:
            return JsonResponse({"error": "Staff access required"}, status=403)

        # Get or create auth token
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        return JsonResponse({
            "token": token.key,
            "user": {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        })


@method_decorator(csrf_exempt, name="dispatch")
class FCMRegisterView(View):
    """Register FCM device token.

    POST /api/mobile/fcm/register/
    Headers: Authorization: Bearer <token>
    {
        "registration_id": "fcm-device-token",
        "platform": "android",
        "device_id": "unique-device-id",
        "device_name": "Pixel 7 Pro",
        "app_version": "1.0.0"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        registration_id = data.get("registration_id", "").strip()
        if not registration_id:
            return JsonResponse({"error": "registration_id required"}, status=400)

        # Create or update device
        device, created = FCMDevice.objects.update_or_create(
            user=request.user,
            registration_id=registration_id,
            defaults={
                "platform": data.get("platform", "android"),
                "device_id": data.get("device_id", ""),
                "device_name": data.get("device_name", ""),
                "app_version": data.get("app_version", ""),
                "is_active": True,
                "failure_count": 0,
                "deleted_at": None,
            },
        )

        return JsonResponse({
            "status": "registered" if created else "updated",
            "device_id": str(device.pk),
        })


@method_decorator(csrf_exempt, name="dispatch")
class FCMUnregisterView(View):
    """Unregister FCM device token.

    POST /api/mobile/fcm/unregister/
    Headers: Authorization: Bearer <token>
    {
        "registration_id": "fcm-device-token"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        registration_id = data.get("registration_id", "").strip()
        if not registration_id:
            return JsonResponse({"error": "registration_id required"}, status=400)

        # Deactivate device
        updated = FCMDevice.objects.filter(
            user=request.user,
            registration_id=registration_id,
        ).update(is_active=False)

        return JsonResponse({
            "status": "unregistered" if updated else "not_found",
        })


@method_decorator(csrf_exempt, name="dispatch")
class MobileConversationsView(View):
    """List conversations for mobile app.

    GET /api/mobile/conversations/
    Headers: Authorization: Bearer <token>

    Returns list of conversations with last message and unread count.
    """

    @method_decorator(require_auth_token)
    def get(self, request):
        person_ct = ContentType.objects.get_for_model(Person)

        # Get conversations linked to Person records
        conversations = (
            Conversation.objects.filter(
                related_content_type=person_ct,
                deleted_at__isnull=True,
            )
            .exclude(status=ConversationStatus.CLOSED)
            .select_related("related_content_type")
            .order_by("-updated_at")[:100]
        )

        # Batch fetch persons
        person_ids = [conv.related_object_id for conv in conversations]
        persons_by_id = {
            str(p.pk): p
            for p in Person.objects.filter(
                pk__in=person_ids,
                deleted_at__isnull=True,
            )
        }

        result = []
        for conv in conversations:
            person = persons_by_id.get(conv.related_object_id)
            if not person:
                continue

            # Get last message
            last_msg = (
                Message.objects.filter(conversation=conv)
                .order_by("-created_at")
                .first()
            )

            # Count unread (inbound messages not marked as read)
            unread_count = Message.objects.filter(
                conversation=conv,
                direction="inbound",
            ).exclude(status="read").count()

            # Needs reply if last message was inbound
            needs_reply = last_msg and last_msg.direction == "inbound"

            result.append({
                "id": str(conv.pk),
                "person_id": str(person.pk),
                "name": f"{person.first_name} {person.last_name}".strip() or person.email or "Unknown",
                "email": person.email or "",
                "initials": _get_initials(person),
                "last_message": last_msg.body_text[:100] if last_msg else "",
                "last_message_time": last_msg.created_at.isoformat() if last_msg else None,
                "needs_reply": needs_reply,
                "unread_count": unread_count,
                "status": conv.status,
            })

        return JsonResponse({"conversations": result})


@method_decorator(csrf_exempt, name="dispatch")
class MobileMessagesView(View):
    """Get messages for a conversation.

    GET /api/mobile/conversations/<conversation_id>/messages/
    Headers: Authorization: Bearer <token>

    Returns messages in chronological order.
    """

    @method_decorator(require_auth_token)
    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(
                pk=conversation_id,
                deleted_at__isnull=True,
            )
        except Conversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        messages = (
            Message.objects.filter(conversation=conversation)
            .order_by("created_at")[:200]
        )

        # Mark inbound messages as read
        from django.utils import timezone
        Message.objects.filter(
            conversation=conversation,
            direction="inbound",
        ).exclude(status="read").update(
            status="read",
            read_at=timezone.now(),
        )

        result = []
        for msg in messages:
            result.append({
                "id": str(msg.pk),
                "body": msg.body_text,
                "direction": msg.direction,
                "status": msg.status,
                "created_at": msg.created_at.isoformat(),
                "sender_name": _get_sender_name(msg),
            })

        return JsonResponse({"messages": result})


@method_decorator(csrf_exempt, name="dispatch")
class MobileSendMessageView(View):
    """Send a message in a conversation.

    POST /api/mobile/conversations/<conversation_id>/send/
    Headers: Authorization: Bearer <token>
    {
        "message": "Hello, how can I help?"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request, conversation_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message_text = data.get("message", "").strip()
        if not message_text:
            return JsonResponse({"error": "Message required"}, status=400)

        try:
            conversation = Conversation.objects.get(
                pk=conversation_id,
                deleted_at__isnull=True,
            )
        except Conversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        # Get the person for this conversation
        person_ct = ContentType.objects.get_for_model(Person)
        if conversation.related_content_type != person_ct:
            return JsonResponse({"error": "Invalid conversation type"}, status=400)

        try:
            person = Person.objects.get(pk=conversation.related_object_id)
        except Person.DoesNotExist:
            return JsonResponse({"error": "Person not found"}, status=404)

        # Create the message
        from django.utils import timezone

        msg = Message.objects.create(
            conversation=conversation,
            sender_person=None,  # Staff message, no Person sender
            direction="outbound",
            channel="in_app",
            from_address=request.user.email,
            to_address=person.email or "",
            body_text=message_text,
            status="sent",
            sent_at=timezone.now(),
        )

        # Update conversation timestamp
        conversation.last_outbound_at = timezone.now()
        conversation.save(update_fields=["last_outbound_at", "updated_at"])

        # Broadcast via WebSocket
        from .crm.services import broadcast_chat_message
        broadcast_chat_message(
            person_id=str(person.pk),
            visitor_id=person.visitor_id,
            conversation_id=str(conversation.pk),
            message_id=str(msg.pk),
            message_text=message_text,
            direction="outbound",
            status=msg.status,
            created_at=msg.created_at.isoformat(),
        )

        # Send email notification
        from .crm.services import send_lead_notification_email
        send_lead_notification_email(
            person=person,
            message=message_text,
            staff_user=request.user,
            message_obj=msg,
        )

        return JsonResponse({
            "status": "sent",
            "message_id": str(msg.pk),
        })


def _get_initials(person):
    """Get initials from person name."""
    initials = ""
    if person.first_name:
        initials += person.first_name[0].upper()
    if person.last_name:
        initials += person.last_name[0].upper()
    return initials or "?"


def _get_sender_name(msg):
    """Get sender name for a message."""
    if msg.direction == "inbound":
        if msg.sender_person:
            name = f"{msg.sender_person.first_name} {msg.sender_person.last_name}".strip()
            return name or msg.sender_person.email or "Visitor"
        return "Visitor"
    else:
        # Outbound - from staff
        return "Staff"
