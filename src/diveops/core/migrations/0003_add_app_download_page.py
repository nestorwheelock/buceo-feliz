"""Create the Android app download CMS page."""

from django.db import migrations
from django.utils import timezone


def create_app_download_page(apps, schema_editor):
    """Create the app download page in CMS."""
    ContentPage = apps.get_model("django_cms_core", "ContentPage")

    # Create published snapshot with minimal data
    published_snapshot = {
        "meta": {
            "title": "Download DiveOps Chat App",
            "description": "Staff messaging app with push notifications",
        },
        "blocks": [],  # Template handles all content
    }

    ContentPage.objects.create(
        slug="app",
        title="Download DiveOps Chat App",
        status="published",
        access_level="public",
        template_key="app-download",
        seo_title="Download DiveOps Chat App",
        seo_description="Staff messaging app with push notifications for dive operations",
        published_snapshot=published_snapshot,
        published_at=timezone.now(),
        is_indexable=False,  # Don't show in sitemap
        sort_order=100,
    )


def remove_app_download_page(apps, schema_editor):
    """Remove the app download page."""
    ContentPage = apps.get_model("django_cms_core", "ContentPage")
    ContentPage.objects.filter(slug="app").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_add_person_link"),
        ("django_cms_core", "0002_add_blog_functionality"),
    ]

    operations = [
        migrations.RunPython(create_app_download_page, remove_app_download_page),
    ]
