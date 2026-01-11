"""Core app configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core application."""

    name = "diveops.core"
    verbose_name = "DiveOps Core"
    default_auto_field = "django.db.models.BigAutoField"
