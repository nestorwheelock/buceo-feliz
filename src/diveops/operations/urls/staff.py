"""Staff portal URL patterns - re-export from parent module."""

from diveops.operations.staff_urls import urlpatterns

app_name = "staff"

__all__ = ["urlpatterns", "app_name"]
