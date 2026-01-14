"""Shared pytest fixtures for diveops.operations tests."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone


User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def dive_shop(db):
    """Create a dive shop organization."""
    from django_parties.models import Organization

    return Organization.objects.create(
        name="Test Dive Shop",
        org_type="dive_shop",
    )


@pytest.fixture
def excursion_type(db, dive_shop):
    """Create an excursion type."""
    from diveops.operations.models import ExcursionType

    return ExcursionType.objects.create(
        name="Test Dive",
        slug="test-dive",
        dive_mode="boat",
        time_of_day="day",
        base_price=Decimal("150.00"),
    )


@pytest.fixture
def excursion(db, dive_shop, excursion_type, user):
    """Create a test excursion with all required fields."""
    from diveops.operations.models import Excursion

    departure = timezone.now() + timedelta(days=1)
    return Excursion.objects.create(
        dive_shop=dive_shop,
        excursion_type=excursion_type,
        departure_time=departure,
        return_time=departure + timedelta(hours=4),
        max_divers=12,
        price_per_diver=Decimal("150.00"),
        status="scheduled",
        created_by=user,
    )


@pytest.fixture
def diver(db, user):
    """Create a diver profile."""
    from django_parties.models import Person
    from diveops.operations.models import DiverProfile

    person = Person.objects.create(
        first_name="Test",
        last_name="Diver",
        email="diver@example.com",
    )
    return DiverProfile.objects.create(
        person=person,
        experience_level="certified",
    )


@pytest.fixture
def person(db):
    """Create a test person."""
    from django_parties.models import Person

    return Person.objects.create(
        first_name="Test",
        last_name="Person",
        email="testperson@example.com",
    )
