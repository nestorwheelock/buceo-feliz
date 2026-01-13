"""Tests for Staff Portal Shared Locations views.

TDD tests for:
- SharedLocationsListView: Staff can view map of all shared locations
- Location data API endpoint for map markers
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django_parties.models import Person

from diveops.operations.models import LocationSharingPreference, LocationUpdate

User = get_user_model()


@pytest.fixture
def client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    user = User.objects.create_user(
        username="staffuser",
        email="staff@happydiving.mx",
        password="testpass123",
        first_name="Staff",
        last_name="User",
        is_staff=True,
    )
    return user


@pytest.fixture
def non_staff_user(db):
    """Create a non-staff user."""
    user = User.objects.create_user(
        username="customer",
        email="customer@example.com",
        password="testpass123",
        first_name="Customer",
        last_name="User",
        is_staff=False,
    )
    return user


@pytest.fixture
def person_sharing_location(db):
    """Create a Person who is sharing their location."""
    user = User.objects.create_user(
        username="activediver",
        email="diver@example.com",
        password="testpass123",
        first_name="Active",
        last_name="Diver",
        is_staff=False,
    )
    person = Person.objects.create(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    # Enable location sharing for staff
    LocationSharingPreference.objects.create(
        person=person,
        visibility=LocationSharingPreference.Visibility.STAFF,
        is_tracking_enabled=True,
    )
    return person


@pytest.fixture
def person_private_location(db):
    """Create a Person with private location settings."""
    user = User.objects.create_user(
        username="privatediver",
        email="private@example.com",
        password="testpass123",
        first_name="Private",
        last_name="Diver",
        is_staff=False,
    )
    person = Person.objects.create(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    # Location is private
    LocationSharingPreference.objects.create(
        person=person,
        visibility=LocationSharingPreference.Visibility.PRIVATE,
        is_tracking_enabled=True,
    )
    return person


@pytest.fixture
def location_updates(db, person_sharing_location, person_private_location):
    """Create location updates for both persons."""
    now = timezone.now()

    # Shared location - should be visible to staff
    shared_location = LocationUpdate.objects.create(
        person=person_sharing_location,
        latitude=Decimal("21.161908"),
        longitude=Decimal("-86.851528"),
        accuracy_meters=Decimal("10.5"),
        source=LocationUpdate.Source.FUSED,
        recorded_at=now,
    )

    # Private location - should NOT be visible to staff
    private_location = LocationUpdate.objects.create(
        person=person_private_location,
        latitude=Decimal("21.170000"),
        longitude=Decimal("-86.860000"),
        accuracy_meters=Decimal("15.0"),
        source=LocationUpdate.Source.GPS,
        recorded_at=now,
    )

    return [shared_location, private_location]


# =============================================================================
# Shared Locations List View Tests
# =============================================================================


class TestSharedLocationsListView:
    """Tests for GET /staff/shared-locations/"""

    def test_staff_can_access_shared_locations_page(self, client, staff_user):
        """Staff user can access the shared locations page."""
        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-list")

        response = client.get(url)

        assert response.status_code == 200
        # Page title should be in context
        assert response.context.get("page_title") == "Shared Locations"

    def test_non_staff_cannot_access_shared_locations(self, client, non_staff_user):
        """Non-staff users are redirected away from shared locations."""
        client.login(username="customer@example.com", password="testpass123")
        url = reverse("diveops:shared-locations-list")

        response = client.get(url)

        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    def test_anonymous_cannot_access_shared_locations(self, client):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:shared-locations-list")

        response = client.get(url)

        assert response.status_code == 302
        assert "login" in response.url.lower() or "accounts" in response.url.lower()

    def test_shared_locations_page_contains_map_element(self, client, staff_user):
        """The page should contain a map element for displaying locations."""
        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-list")

        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        # Should have a map container
        assert 'id="map"' in content or 'id="locations-map"' in content


# =============================================================================
# Location Data API Tests (for map markers)
# =============================================================================


class TestSharedLocationsAPIView:
    """Tests for GET /staff/shared-locations/api/"""

    def test_staff_can_get_location_data(
        self, client, staff_user, location_updates, person_sharing_location
    ):
        """Staff can retrieve location data as JSON for map markers."""
        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-api")

        response = client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        data = response.json()
        assert "locations" in data
        assert isinstance(data["locations"], list)

    def test_api_returns_only_visible_locations(
        self, client, staff_user, location_updates, person_sharing_location, person_private_location
    ):
        """API only returns locations from users sharing with staff."""
        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-api")

        response = client.get(url)

        data = response.json()
        locations = data["locations"]

        # Should only have the shared location, not the private one
        assert len(locations) == 1
        assert locations[0]["person_name"] == "Active Diver"

    def test_api_returns_location_with_required_fields(
        self, client, staff_user, location_updates, person_sharing_location
    ):
        """Each location has required fields for map markers."""
        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-api")

        response = client.get(url)
        data = response.json()

        assert len(data["locations"]) >= 1
        location = data["locations"][0]

        # Required fields for map marker
        assert "id" in location
        assert "latitude" in location
        assert "longitude" in location
        assert "person_name" in location
        assert "recorded_at" in location

    def test_non_staff_cannot_access_api(self, client, non_staff_user, location_updates):
        """Non-staff users cannot access location API."""
        client.login(username="customer@example.com", password="testpass123")
        url = reverse("diveops:shared-locations-api")

        response = client.get(url)

        assert response.status_code in [302, 403]

    def test_api_returns_most_recent_location_per_person(
        self, client, staff_user, person_sharing_location
    ):
        """API returns only the most recent location for each person."""
        now = timezone.now()

        # Create older location
        LocationUpdate.objects.create(
            person=person_sharing_location,
            latitude=Decimal("21.100000"),
            longitude=Decimal("-86.800000"),
            source=LocationUpdate.Source.GPS,
            recorded_at=now - timedelta(hours=2),
        )

        # Create newer location
        newer = LocationUpdate.objects.create(
            person=person_sharing_location,
            latitude=Decimal("21.200000"),
            longitude=Decimal("-86.900000"),
            source=LocationUpdate.Source.FUSED,
            recorded_at=now,
        )

        client.login(username="staff@happydiving.mx", password="testpass123")
        url = reverse("diveops:shared-locations-api")

        response = client.get(url)
        data = response.json()

        # Should only return the most recent location
        assert len(data["locations"]) == 1
        assert float(data["locations"][0]["latitude"]) == float(newer.latitude)
