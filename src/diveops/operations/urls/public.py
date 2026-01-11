"""Public URL patterns - re-export from parent module."""

from diveops.operations.public_urls import urlpatterns

app_name = "sign"

__all__ = ["urlpatterns", "app_name"]
