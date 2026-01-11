"""Customer portal URL patterns - re-export from parent module."""

from diveops.operations.customer_urls import urlpatterns

app_name = "portal"

__all__ = ["urlpatterns", "app_name"]
