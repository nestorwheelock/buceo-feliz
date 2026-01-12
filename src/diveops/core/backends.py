"""Custom authentication backends."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authentication backend that allows login with email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()

        # Try to find user by email (username field contains email input)
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Try username as fallback
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
