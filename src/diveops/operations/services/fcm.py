"""Firebase Cloud Messaging (FCM) service for push notifications."""

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Firebase Admin SDK (lazy loaded)
_firebase_app = None


def _get_firebase_app():
    """Get or initialize Firebase Admin app."""
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass

        # Initialize from service account file or environment
        cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
        if cred_path:
            cred = credentials.Certificate(cred_path)
        else:
            # Use Application Default Credentials
            cred = credentials.ApplicationDefault()

        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
        return _firebase_app

    except ImportError:
        logger.warning("firebase-admin not installed. FCM push disabled.")
        return None
    except Exception as e:
        logger.exception(f"Failed to initialize Firebase: {e}")
        return None


def send_push_notification(
    registration_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    sound: str = "default",
    badge: Optional[int] = None,
    click_action: Optional[str] = None,
) -> bool:
    """Send a push notification to a single device.

    Args:
        registration_id: FCM device token
        title: Notification title
        body: Notification body text
        data: Optional data payload (key-value pairs)
        sound: Notification sound ("default" or custom sound file)
        badge: Badge number (iOS only)
        click_action: Activity to open on click (Android)

    Returns:
        True if sent successfully, False otherwise
    """
    app = _get_firebase_app()
    if not app:
        logger.warning("Firebase not initialized, skipping push notification")
        return False

    try:
        from firebase_admin import messaging

        # Build Android-specific config
        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                sound=sound,
                click_action=click_action,
                # Make notification appear even when app is in foreground
                default_sound=True,
                default_vibrate_timings=True,
                notification_priority="PRIORITY_HIGH",
            ),
        )

        # Build iOS-specific config (APNS)
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound=sound,
                    badge=badge,
                    content_available=True,
                ),
            ),
        )

        # Build the message
        message = messaging.Message(
            token=registration_id,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            android=android_config,
            apns=apns_config,
        )

        # Send the message
        response = messaging.send(message)
        logger.info(f"FCM push sent successfully: {response}")
        return True

    except Exception as e:
        error_str = str(e)
        logger.exception(f"Failed to send FCM push: {e}")

        # Check for token errors that indicate device should be deactivated
        if "Requested entity was not found" in error_str or "not a valid FCM registration token" in error_str:
            logger.warning(f"Invalid FCM token, should be deactivated: {registration_id[:20]}...")

        return False


def send_push_to_user(
    user,
    title: str,
    body: str,
    data: Optional[dict] = None,
    sound: str = "default",
) -> int:
    """Send push notification to all of a user's active devices.

    Args:
        user: Django User instance
        title: Notification title
        body: Notification body text
        data: Optional data payload
        sound: Notification sound

    Returns:
        Number of successful deliveries
    """
    from django_communication.models import FCMDevice

    devices = FCMDevice.objects.filter(
        user=user,
        is_active=True,
        deleted_at__isnull=True,
    )

    success_count = 0
    for device in devices:
        if send_push_notification(
            registration_id=device.registration_id,
            title=title,
            body=body,
            data=data,
            sound=sound,
        ):
            device.mark_success()
            success_count += 1
        else:
            device.mark_failure()

    return success_count


def send_chat_notification(
    user,
    sender_name: str,
    message_preview: str,
    conversation_id: str,
    person_id: str,
) -> int:
    """Send chat message notification to staff user.

    Args:
        user: Staff User who should receive notification
        sender_name: Name of the person who sent the message
        message_preview: First part of message text
        conversation_id: Conversation UUID for deep linking
        person_id: Person UUID for deep linking

    Returns:
        Number of devices notified
    """
    # Truncate message preview
    if len(message_preview) > 100:
        message_preview = message_preview[:97] + "..."

    return send_push_to_user(
        user=user,
        title=f"New message from {sender_name}",
        body=message_preview,
        data={
            "type": "chat_message",
            "conversation_id": conversation_id,
            "person_id": person_id,
            "click_action": "OPEN_CHAT",
        },
        sound="default",
    )


def notify_staff_of_new_message(
    person,
    message_text: str,
    conversation_id: str,
):
    """Notify all staff users when a visitor sends a message.

    Args:
        person: Person (lead/visitor) who sent the message
        message_text: The message content
        conversation_id: Conversation UUID
    """
    from django.contrib.auth import get_user_model
    from django_communication.models import FCMDevice

    User = get_user_model()

    # Get all staff users with active FCM devices
    staff_with_devices = User.objects.filter(
        is_staff=True,
        is_active=True,
        fcm_devices__is_active=True,
        fcm_devices__deleted_at__isnull=True,
    ).distinct()

    sender_name = f"{person.first_name} {person.last_name}".strip() or person.email or "Visitor"

    total_sent = 0
    for staff_user in staff_with_devices:
        count = send_chat_notification(
            user=staff_user,
            sender_name=sender_name,
            message_preview=message_text,
            conversation_id=conversation_id,
            person_id=str(person.pk),
        )
        total_sent += count

    logger.info(f"Sent {total_sent} FCM notifications for new message from {sender_name}")
    return total_sent
