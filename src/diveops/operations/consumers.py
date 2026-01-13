"""WebSocket consumers for real-time chat."""

import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class ChatConsumer(WebsocketConsumer):
    """WebSocket consumer for lead chat conversations.

    Supports two connection types:
    1. Visitor (public): /ws/chat/visitor/<visitor_id>/
    2. Staff (authenticated): /ws/chat/lead/<lead_id>/

    Messages are broadcast to all participants in the conversation.
    """

    def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = None
        self.room_group_name = None

        # Determine connection type from URL route
        route_name = self.scope.get("url_route", {}).get("kwargs", {})

        if "visitor_id" in route_name:
            # Public visitor connection
            self.visitor_id = route_name["visitor_id"]
            self.is_staff = False
            self.room_group_name = f"chat_visitor_{self.visitor_id}"
        elif "lead_id" in route_name:
            # Staff connection - requires authentication and staff status
            user = self.scope.get("user")
            if not user or not user.is_authenticated or not user.is_staff:
                logger.warning("Unauthorized WebSocket connection attempt")
                self.close()
                return
            self.lead_id = route_name["lead_id"]
            self.is_staff = True
            self.room_group_name = f"chat_lead_{self.lead_id}"
        elif "conversation_id" in route_name:
            # Conversation connection - authenticated users OR visitors with valid conversation
            self.conversation_id = route_name["conversation_id"]
            user = self.scope.get("user")

            if user and user.is_authenticated:
                # Authenticated user (staff or portal user)
                self.is_staff = user.is_staff
            else:
                # Anonymous visitor - verify they have access to this conversation via cookie
                # For now, allow connection (the visitor would need to know the conversation ID)
                self.is_staff = False

            self.room_group_name = f"chat_conversation_{self.conversation_id}"
        else:
            logger.warning("Invalid WebSocket route")
            self.close()
            return

        # Join room group
        try:
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            logger.exception(f"Failed to join channel group: {e}")
            self.close()
            return

        self.accept()
        logger.info(f"WebSocket connected: {self.room_group_name}")

        # Send connection confirmation to client
        self.send(text_data=json.dumps({
            "type": "connection_established",
            "room": self.room_group_name,
        }))

    def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.room_group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected: {self.room_group_name}")

    def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")

            if message_type == "message":
                self.handle_message(data)
            elif message_type == "typing":
                self.handle_typing(data)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in WebSocket message")
        except Exception as e:
            logger.exception(f"Error handling WebSocket message: {e}")

    def handle_message(self, data):
        """Handle a chat message."""
        message_text = data.get("message", "").strip()
        if not message_text:
            return

        # The actual message saving is done via the HTTP API
        # This just broadcasts to the room that a new message exists
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_text,
                "direction": "outbound" if self.is_staff else "inbound",
                "sender": "staff" if self.is_staff else "visitor",
            }
        )

    def handle_typing(self, data):
        """Handle typing indicator."""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "is_typing": data.get("is_typing", False),
                "sender": "staff" if self.is_staff else "visitor",
            }
        )

    def chat_message(self, event):
        """Send chat message to WebSocket."""
        self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"],
            "direction": event["direction"],
            "sender": event["sender"],
        }))

    def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        self.send(text_data=json.dumps({
            "type": "typing",
            "is_typing": event["is_typing"],
            "sender": event["sender"],
        }))

    def new_message(self, event):
        """Notify about a new message (sent from HTTP API)."""
        self.send(text_data=json.dumps({
            "type": "new_message",
            "message_id": event.get("message_id"),
            "message": event.get("message"),
            "direction": event.get("direction"),
            "created_at": event.get("created_at"),
        }))
