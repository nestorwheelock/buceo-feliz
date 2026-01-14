"""WebSocket broadcast services.

This module provides a unified interface for broadcasting messages via WebSocket.
All broadcast calls should use this service to ensure:

1. Consistent message payload structure
2. Broadcasts happen AFTER transaction commit (prevents ghost messages)
3. Proper error handling without failing the main operation
4. Logging for debugging

Usage:
    from diveops.operations.services.broadcast import BroadcastService

    # Simple conversation broadcast
    BroadcastService.broadcast_message(
        message=message_obj,
        rooms=["conversation"],  # Sends to chat_conversation_{id}
    )

    # Lead chat broadcast (sends to multiple rooms)
    BroadcastService.broadcast_message(
        message=message_obj,
        rooms=["lead", "conversation", "visitor"],
        person_id=person.pk,
        visitor_id=visitor_cookie,
    )

    # With transaction.on_commit for safety
    BroadcastService.broadcast_on_commit(
        message=message_obj,
        rooms=["conversation"],
    )
"""

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from django_communication.models import Message

logger = logging.getLogger(__name__)


class BroadcastService:
    """Unified WebSocket broadcast service.

    Consolidates broadcast_conversation_message and broadcast_chat_message
    into a single, consistent interface.
    """

    @staticmethod
    def broadcast_message(
        message: Optional[Message] = None,
        *,
        rooms: list[str] = None,
        conversation_id: str = None,
        person_id: str = None,
        visitor_id: str = None,
        message_id: str = None,
        message_text: str = "",
        sender_person_id: str = None,
        sender_name: str = "",
        direction: str = None,
        status: str = None,
        created_at: str = None,
    ):
        """Broadcast a message via WebSocket to specified rooms.

        Can be called with either a Message object (preferred) or explicit fields.

        Args:
            message: Message object to broadcast (extracts fields automatically)
            rooms: List of room types to broadcast to. Valid values:
                   - "conversation": chat_conversation_{conversation_id}
                   - "lead": chat_lead_{person_id}
                   - "visitor": chat_visitor_{visitor_id}
            conversation_id: Conversation UUID (required for "conversation" room)
            person_id: Person UUID (required for "lead" room)
            visitor_id: Visitor cookie ID (required for "visitor" room)
            message_id: Message UUID (optional, extracted from message if provided)
            message_text: Message body (optional, extracted from message if provided)
            sender_person_id: Sender Person UUID (optional)
            sender_name: Display name of sender (optional)
            direction: Message direction: "inbound" or "outbound" (optional)
            status: Message status (optional)
            created_at: ISO timestamp (optional, defaults to now)
        """
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning("No channel layer configured, skipping WebSocket broadcast")
                return

            # Extract fields from Message object if provided
            if message:
                message_id = message_id or str(message.pk)
                message_text = message_text or message.body_text or ""
                conversation_id = conversation_id or (str(message.conversation_id) if message.conversation_id else None)
                sender_person_id = sender_person_id or (str(message.sender_person_id) if message.sender_person_id else None)
                direction = direction or message.direction
                status = status or message.status
                created_at = created_at or (message.created_at.isoformat() if message.created_at else None)

                # Try to get sender name from sender_person
                if not sender_name and message.sender_person:
                    sender_name = f"{message.sender_person.first_name} {message.sender_person.last_name}".strip()

            # Build message payload
            payload = {
                "type": "new_message",
                "message_id": message_id,
                "message": message_text,
                "body": message_text,  # Alias for compatibility
                "direction": direction,
                "status": status,
                "sender_person_id": sender_person_id,
                "sender_name": sender_name,
                "created_at": created_at or timezone.now().isoformat(),
            }

            # Default to conversation room if no rooms specified
            if not rooms:
                rooms = ["conversation"]

            # Build room names and broadcast
            room_names = []
            for room_type in rooms:
                if room_type == "conversation" and conversation_id:
                    room_names.append(f"chat_conversation_{conversation_id}")
                elif room_type == "lead" and person_id:
                    room_names.append(f"chat_lead_{person_id}")
                elif room_type == "visitor" and visitor_id:
                    room_names.append(f"chat_visitor_{visitor_id}")

            # Send to all rooms
            for room_name in room_names:
                async_to_sync(channel_layer.group_send)(room_name, payload)

            logger.debug(
                "Broadcast message via WebSocket",
                extra={
                    "rooms": room_names,
                    "message_id": message_id,
                    "direction": direction,
                },
            )

        except Exception as e:
            # Never fail the main operation if broadcast fails
            logger.exception(f"Failed to broadcast message: {e}")

    @staticmethod
    def broadcast_on_commit(
        message: Optional[Message] = None,
        **kwargs,
    ):
        """Broadcast message after the current transaction commits.

        This prevents "ghost messages" where a broadcast is sent but the
        database transaction rolls back. The WebSocket client would show
        a message that doesn't exist in the database.

        Usage:
            with transaction.atomic():
                message = Message.objects.create(...)
                BroadcastService.broadcast_on_commit(
                    message=message,
                    rooms=["conversation", "lead"],
                    person_id=person.pk,
                )
            # Broadcast happens here, after commit

        Args:
            Same as broadcast_message()
        """
        # Capture the message ID now (before commit) since the message object
        # might not be accessible after commit in some edge cases
        if message:
            kwargs.setdefault("message_id", str(message.pk))
            kwargs.setdefault("message_text", message.body_text or "")
            kwargs.setdefault("conversation_id", str(message.conversation_id) if message.conversation_id else None)
            kwargs.setdefault("sender_person_id", str(message.sender_person_id) if message.sender_person_id else None)
            kwargs.setdefault("direction", message.direction)
            kwargs.setdefault("status", message.status)
            kwargs.setdefault("created_at", message.created_at.isoformat() if message.created_at else None)

            if message.sender_person and not kwargs.get("sender_name"):
                kwargs["sender_name"] = f"{message.sender_person.first_name} {message.sender_person.last_name}".strip()

        def do_broadcast():
            BroadcastService.broadcast_message(**kwargs)

        transaction.on_commit(do_broadcast)

    # Compatibility aliases for existing code
    @staticmethod
    def broadcast_conversation_message(
        conversation_id: str,
        message_id: str = None,
        message_text: str = "",
        sender_person_id: str = None,
        sender_name: str = "",
        created_at: str = None,
    ):
        """Legacy compatibility wrapper for broadcast_conversation_message.

        Deprecated: Use broadcast_message() or broadcast_on_commit() instead.
        """
        BroadcastService.broadcast_message(
            rooms=["conversation"],
            conversation_id=conversation_id,
            message_id=message_id,
            message_text=message_text,
            sender_person_id=sender_person_id,
            sender_name=sender_name,
            created_at=created_at,
        )

    @staticmethod
    def broadcast_chat_message(
        person_id: str,
        visitor_id: str = None,
        conversation_id: str = None,
        message_id: str = None,
        message_text: str = "",
        direction: str = "inbound",
        status: str = "sent",
        created_at: str = None,
    ):
        """Legacy compatibility wrapper for broadcast_chat_message.

        Deprecated: Use broadcast_message() or broadcast_on_commit() instead.
        """
        rooms = ["lead"]
        if conversation_id:
            rooms.append("conversation")
        if visitor_id:
            rooms.append("visitor")

        BroadcastService.broadcast_message(
            rooms=rooms,
            conversation_id=conversation_id,
            person_id=person_id,
            visitor_id=visitor_id,
            message_id=message_id,
            message_text=message_text,
            direction=direction,
            status=status,
            created_at=created_at,
        )


# Module-level compatibility exports
def broadcast_conversation_message(*args, **kwargs):
    """Deprecated: Use BroadcastService.broadcast_message() instead."""
    return BroadcastService.broadcast_conversation_message(*args, **kwargs)


def broadcast_chat_message(*args, **kwargs):
    """Deprecated: Use BroadcastService.broadcast_message() instead."""
    return BroadcastService.broadcast_chat_message(*args, **kwargs)
