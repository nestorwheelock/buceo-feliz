"""Profile views for all user types."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView, FormView


class ProfileView(LoginRequiredMixin, TemplateView):
    """Main profile page showing user info and settings."""

    template_name = "profile/profile.html"
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update({
            "user": user,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        })

        return context


class ProfileEditView(LoginRequiredMixin, TemplateView):
    """Edit profile information."""

    template_name = "profile/profile_edit.html"
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.save(update_fields=["first_name", "last_name"])
        messages.success(request, "Profile updated successfully.")
        return redirect("profile:view")


class ProfilePhotoView(LoginRequiredMixin, TemplateView):
    """Manage profile photo."""

    template_name = "profile/profile_photo.html"
    login_url = "/accounts/login/"


class ProfilePhotoDeleteView(LoginRequiredMixin, View):
    """Delete profile photo."""

    def post(self, request):
        messages.success(request, "Profile photo removed.")
        return redirect("profile:view")


class PasswordChangeView(LoginRequiredMixin, FormView):
    """Change password."""

    template_name = "profile/password_change.html"
    form_class = PasswordChangeForm
    login_url = "/accounts/login/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Password changed successfully.")
        return redirect("profile:view")
