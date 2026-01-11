"""Django app configuration for diveops."""

from django.apps import AppConfig


class OperationsConfig(AppConfig):
    """App configuration for dive operations."""

    name = "diveops.operations"
    verbose_name = "Dive Operations"
    default_auto_field = "django.db.models.BigAutoField"
