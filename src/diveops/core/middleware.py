"""Core middleware for DiveOps."""

from django.contrib.auth import get_user_model

IMPERSONATE_SESSION_KEY = "_impersonate_user_id"
IMPERSONATE_ORIGINAL_USER_KEY = "_impersonate_original_user_id"


class ImpersonationMiddleware:
    """Middleware to handle staff impersonation of customers.

    Sets request.is_impersonating and request.original_user for templates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        User = get_user_model()

        # Check if impersonation is active
        impersonated_user_id = request.session.get(IMPERSONATE_SESSION_KEY)
        original_user_id = request.session.get(IMPERSONATE_ORIGINAL_USER_KEY)

        if impersonated_user_id and request.user.is_authenticated:
            try:
                impersonated_user = User.objects.get(pk=impersonated_user_id)
                original_user = User.objects.get(pk=original_user_id) if original_user_id else request.user

                # Store original user for reference
                request.original_user = original_user
                request.real_user = original_user  # Alias for compatibility
                request.is_impersonating = True

                # Swap the user
                request.user = impersonated_user
            except User.DoesNotExist:
                # Clear invalid impersonation
                if IMPERSONATE_SESSION_KEY in request.session:
                    del request.session[IMPERSONATE_SESSION_KEY]
                if IMPERSONATE_ORIGINAL_USER_KEY in request.session:
                    del request.session[IMPERSONATE_ORIGINAL_USER_KEY]
                request.is_impersonating = False
                request.original_user = None
                request.real_user = request.user
        else:
            request.is_impersonating = False
            request.original_user = None
            request.real_user = request.user

        response = self.get_response(request)
        return response


def start_impersonation(request, user_id):
    """Start impersonating a user."""
    if not request.user.is_staff:
        raise PermissionError("Only staff can impersonate users")

    request.session[IMPERSONATE_SESSION_KEY] = str(user_id)
    request.session[IMPERSONATE_ORIGINAL_USER_KEY] = str(request.user.pk)


def stop_impersonation(request):
    """Stop impersonating a user."""
    if IMPERSONATE_SESSION_KEY in request.session:
        del request.session[IMPERSONATE_SESSION_KEY]
    if IMPERSONATE_ORIGINAL_USER_KEY in request.session:
        del request.session[IMPERSONATE_ORIGINAL_USER_KEY]
