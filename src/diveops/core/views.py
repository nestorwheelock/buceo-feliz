"""Core views for DiveOps."""

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import ListView, DetailView

from django_cms_core.models import ContentPage, PageType, PageStatus, BlogCategory


def health_check(request):
    """Health check endpoint for container orchestration."""
    from django.db import connection

    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({"status": "healthy", "database": "connected"})
    except Exception as e:
        return JsonResponse(
            {"status": "unhealthy", "error": str(e)},
            status=503,
        )


def index(request):
    """Homepage view."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("diveops:excursion-list")
        return redirect("portal:dashboard")

    return render(request, "index.html")


class BlogListView(ListView):
    """Blog listing view showing all published posts."""

    model = ContentPage
    template_name = "cms/blog_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        queryset = ContentPage.objects.filter(
            page_type=PageType.POST,
            status=PageStatus.PUBLISHED,
            deleted_at__isnull=True,
        ).select_related("category").order_by("-published_at")

        # Filter by category if provided
        category_slug = self.kwargs.get("category_slug")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = BlogCategory.objects.filter(
            deleted_at__isnull=True
        ).order_by("sort_order", "name")
        context["current_category"] = self.kwargs.get("category_slug")
        return context


class BlogDetailView(DetailView):
    """Blog post detail view."""

    model = ContentPage
    template_name = "cms/blog_detail.html"
    context_object_name = "post"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return ContentPage.objects.filter(
            page_type=PageType.POST,
            status=PageStatus.PUBLISHED,
            deleted_at__isnull=True,
        ).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        snapshot = post.published_snapshot or {}
        context["snapshot"] = snapshot
        context["meta"] = snapshot.get("meta", {})
        context["blocks"] = snapshot.get("blocks", [])

        # Related posts (same category, excluding current)
        if post.category:
            context["related_posts"] = ContentPage.objects.filter(
                page_type=PageType.POST,
                status=PageStatus.PUBLISHED,
                deleted_at__isnull=True,
                category=post.category,
            ).exclude(pk=post.pk).order_by("-published_at")[:3]
        else:
            context["related_posts"] = []

        return context
