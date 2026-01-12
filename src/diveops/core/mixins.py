"""Core mixins for view access control."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class ImpersonationAwareStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for staff portal views with impersonation awareness."""

    required_module = None
    required_action = "view"

    def test_func(self):
        user = self.request.user

        # Superusers always have access
        if user.is_superuser:
            return True

        # Must be staff
        if not user.is_staff:
            return False

        # If no module required, staff is enough
        if not self.required_module:
            return True

        # Check module permission via django-modules if available
        if hasattr(user, "has_module_permission"):
            return user.has_module_permission(self.required_module, self.required_action)

        return True

    def get_real_user(self):
        """Get the real user, even if impersonating."""
        if hasattr(self.request, "real_user"):
            return self.request.real_user
        return self.request.user

    def is_impersonating(self):
        """Check if the current session is an impersonation."""
        return hasattr(self.request, "real_user") and self.request.real_user != self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_staff_portal"] = True
        context["is_impersonating"] = self.is_impersonating()
        if self.is_impersonating():
            context["real_user"] = self.get_real_user()
        return context
