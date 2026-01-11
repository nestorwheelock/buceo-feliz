"""Context processors for DiveOps core."""


def impersonation_context(request):
    """Add impersonation context to templates."""
    return {
        "is_impersonating": getattr(request, "impersonating", None) is not None,
        "impersonating_user": getattr(request, "impersonating", None),
        "real_user": getattr(request, "real_user", request.user),
    }
