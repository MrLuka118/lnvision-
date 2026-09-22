import pytest
from django.test import Client

from apps.clients.tests.factories import ClientFactory
from apps.core.tests.factories import StudioFactory, UserFactory
from apps.finance.tests import factories as _finance_factories  # noqa: F401  (registers)
from apps.galleries.tests import factories as _gallery_factories  # noqa: F401  (registers)
from apps.portfolio.tests import factories as _portfolio_factories  # noqa: F401  (registers)
from apps.scheduling.tests import factories as _event_factories  # noqa: F401  (registers)
from apps.shoots.tests.factories import ShootFactory


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


@pytest.fixture
def client_obj(studio):
    """A client of the signed-in studio (named to avoid clashing with Django's `client`)."""
    return ClientFactory(studio=studio)


@pytest.fixture
def shoot(studio):
    return ShootFactory(studio=studio)
