"""Mobile API URL patterns for the staff chat Android app."""

from django.urls import path

from . import mobile_api_views

app_name = "mobile"

urlpatterns = [
    # Authentication
    path("login/", mobile_api_views.MobileLoginView.as_view(), name="login"),

    # FCM Device Registration
    path("fcm/register/", mobile_api_views.FCMRegisterView.as_view(), name="fcm-register"),
    path("fcm/unregister/", mobile_api_views.FCMUnregisterView.as_view(), name="fcm-unregister"),

    # Conversations
    path("conversations/", mobile_api_views.MobileConversationsView.as_view(), name="conversations"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        mobile_api_views.MobileMessagesView.as_view(),
        name="messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/send/",
        mobile_api_views.MobileSendMessageView.as_view(),
        name="send-message",
    ),
]
