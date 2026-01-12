"""Core models for DiveOps."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with email as primary identifier.

    Uses BigAutoField for compatibility with testbed data import.
    """

    email = models.EmailField(unique=True)

    # Link to Person from django-parties (optional)
    person = models.OneToOneField(
        "django_parties.Person",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_account",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def get_display_name(self):
        """Get display name for the user."""
        if self.person:
            return self.person.display_name
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email.split("@")[0]
