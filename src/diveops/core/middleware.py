"""Core middleware for DiveOps."""

from django.conf import settings


class ImpersonationMiddleware:
    """Middleware to handle staff impersonation of customers."""

    IMPERSONATION_SESSION_KEY = "_impersonate_user_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is impersonating someone
        request.impersonating = None
        request.real_user = request.user

        if request.user.is_authenticated and request.user.is_staff:
            impersonate_id = request.session.get(self.IMPERSONATION_SESSION_KEY)
            if impersonate_id:
                from diveops.core.models import User

                try:
                    impersonated_user = User.objects.get(pk=impersonate_id)
                    request.impersonating = impersonated_user
                except User.DoesNotExist:
                    # Clear invalid impersonation
                    del request.session[self.IMPERSONATION_SESSION_KEY]

        response = self.get_response(request)
        return response


def start_impersonation(request, user_id):
    """Start impersonating a user."""
    if not request.user.is_staff:
        raise PermissionError("Only staff can impersonate users")

    request.session[ImpersonationMiddleware.IMPERSONATION_SESSION_KEY] = str(user_id)


def stop_impersonation(request):
    """Stop impersonating a user."""
    if ImpersonationMiddleware.IMPERSONATION_SESSION_KEY in request.session:
        del request.session[ImpersonationMiddleware.IMPERSONATION_SESSION_KEY]
