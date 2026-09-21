import pytest
from django.test import Client

from apps.core.tests.factories import StudioFactory, UserFactory


@pytest.fixture
def user():
    """Return a test user."""
    return UserFactory()


@pytest.fixture
def studio(user):
    """Return a test studio with the user as owner."""
    return StudioFactory(owner=user)


@pytest.fixture
def other_studio():
    """Return a test studio with a different owner."""
    return StudioFactory()


@pytest.fixture
def auth_client(studio):
    """Return an authenticated Django test client."""
    client = Client()
    client.force_login(studio.owner)
    return client
