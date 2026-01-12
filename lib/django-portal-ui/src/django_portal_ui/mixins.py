"""
View mixins for portal access control.

Provides four levels of access:
- PublicViewMixin: No authentication required
- CustomerPortalMixin: Authenticated users (customers)
- StaffPortalMixin: Staff with module permissions
- SuperadminMixin: Superusers only
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class PublicViewMixin:
    """
    No authentication required.

    Use for public-facing pages like homepage, about, contact, etc.
    Templates should extend 'portal_ui/base_public.html'.
    """
    portal_context = 'public'


class CustomerPortalMixin(LoginRequiredMixin):
    """
    Authenticated customer access.

    Use for customer portal pages like my pets, my appointments, my orders.
    Templates should extend 'portal_ui/base_portal.html'.
    """
    portal_context = 'portal'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class StaffPortalMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Staff with module permission.

    Use for staff portal pages. Set required_module and required_action
    to enforce specific permissions.
    Templates should extend 'portal_ui/base_staff.html'.

    Example:
        class AppointmentListView(StaffPortalMixin, ListView):
            required_module = 'appointments'
            required_action = 'view'
    """
    portal_context = 'staff'
    login_url = '/accounts/login/'
    required_module = None
    required_action = 'view'
    raise_exception = True

    def test_func(self):
        user = self.request.user

        # Superusers always have access
        if user.is_superuser:
            return True

        # Must be staff
        if not user.is_staff:
            return False

        # Check module permission if specified
        if self.required_module:
            # Check if user has has_module_permission method (from django-accounts)
            if hasattr(user, 'has_module_permission'):
                return user.has_module_permission(
                    self.required_module,
                    self.required_action
                )
            # Fallback: check Django permission with codename format
            codename = f'{self.required_module}.{self.required_action}'
            return user.has_perm(codename)

        return True

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You don't have permission to access this page.")
        # Redirect unauthenticated users to login
        return redirect_to_login(
            self.request.get_full_path(),
            self.get_login_url(),
            self.redirect_field_name
        )


class SuperadminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Superuser only access.

    Use for superadmin pages like user management, system settings.
    Templates should extend 'portal_ui/base_superadmin.html'.
    """
    portal_context = 'superadmin'
    login_url = '/accounts/login/'
    raise_exception = True

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Superuser access required.")
        # Redirect unauthenticated users to login
        return redirect_to_login(
            self.request.get_full_path(),
            self.get_login_url(),
            self.redirect_field_name
        )


class ModulePermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Check specific module and action permission.

    More flexible than StaffPortalMixin - can be used in any context.

    Example:
        class ApproveOrderView(ModulePermissionMixin, UpdateView):
            required_module = 'orders'
            required_action = 'approve'
    """
    required_module = None
    required_action = 'view'
    raise_exception = True

    def test_func(self):
        user = self.request.user

        if user.is_superuser:
            return True

        if not self.required_module:
            return True

        if hasattr(user, 'has_module_permission'):
            return user.has_module_permission(
                self.required_module,
                self.required_action
            )

        codename = f'{self.required_module}.{self.required_action}'
        return user.has_perm(codename)


class HierarchyPermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Check if user can manage another user based on hierarchy level.

    Use for user management views where a user can only manage
    users with lower hierarchy levels.

    Example:
        class EditUserView(HierarchyPermissionMixin, UpdateView):
            def get_target_user(self):
                return self.get_object()
    """
    raise_exception = True

    def get_target_user(self):
        """Override to return the user being managed."""
        raise NotImplementedError("Subclasses must implement get_target_user()")

    def test_func(self):
        user = self.request.user

        if user.is_superuser:
            return True

        target = self.get_target_user()
        if target is None:
            return True

        if hasattr(user, 'can_manage_user'):
            return user.can_manage_user(target)

        # Fallback: compare hierarchy_level if available
        if hasattr(user, 'hierarchy_level') and hasattr(target, 'hierarchy_level'):
            return user.hierarchy_level > target.hierarchy_level

        return False
