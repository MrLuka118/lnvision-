import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import Studio
from apps.core.services import ensure_studio
from apps.core.tests.factories import UserFactory


@pytest.mark.django_db
class TestSignup:
    """Tests for user sign-up and studio creation."""

    def test_signup_creates_user_and_studio(self, client):
        """POST to signup creates User and Studio with specified name."""
        client.post(
            reverse("account_signup"),
            {
                "studio_name": "Studio Svetloba",
                "email": "ana@example.com",
                "password1": "dolgo-varno-geslo-42",
                "password2": "dolgo-varno-geslo-42",
            },
        )
        user = User.objects.get(email="ana@example.com")
        assert user.studio.name == "Studio Svetloba"
        assert user.studio.slug == "studio-svetloba"
        assert user.studio.email == "ana@example.com"

    def test_signup_unique_studio_slug(self, client):
        """Signup with duplicate studio name generates unique slug."""
        client.post(
            reverse("account_signup"),
            {
                "studio_name": "Studio Svetloba",
                "email": "ana@example.com",
                "password1": "dolgo-varno-geslo-42",
                "password2": "dolgo-varno-geslo-42",
            },
        )
        client.post(
            reverse("account_signup"),
            {
                "studio_name": "Studio Svetloba",
                "email": "bob@example.com",
                "password1": "dolgo-varno-geslo-42",
                "password2": "dolgo-varno-geslo-42",
            },
        )
        second_user = User.objects.get(email="bob@example.com")
        assert second_user.studio.slug == "studio-svetloba-2"

    @override_settings(ACCOUNT_ALLOW_SIGNUPS=False)
    def test_signup_closed_shows_closed_template(self, client):
        """Signup closed: GET shows signup_closed.html."""
        response = client.get(reverse("account_signup"))
        assert response.status_code == 200
        assert "account/signup_closed.html" in [t.name for t in response.templates]

    @override_settings(ACCOUNT_ALLOW_SIGNUPS=False)
    def test_signup_closed_prevents_registration(self, client):
        """Signup closed: POST does not create user."""
        client.post(
            reverse("account_signup"),
            {
                "studio_name": "Studio Test",
                "email": "test@example.com",
                "password1": "dolgo-varno-geslo-42",
                "password2": "dolgo-varno-geslo-42",
            },
        )
        assert not User.objects.filter(email="test@example.com").exists()

    def test_ensure_studio_idempotent(self):
        """ensure_studio(user) returns same studio on multiple calls."""
        user = UserFactory()
        studio1 = ensure_studio(user)
        studio2 = ensure_studio(user)
        assert studio1.id == studio2.id
        assert Studio.objects.filter(owner=user).count() == 1

    def test_ensure_studio_full_name(self):
        """ensure_studio creates studio from user's full name."""
        user = UserFactory(first_name="Maja", last_name="Kovač")
        studio = ensure_studio(user)
        assert studio.name == "Maja Kovač"

    def test_ensure_studio_email_prefix(self):
        """ensure_studio falls back to email prefix if no name."""
        user = UserFactory(first_name="", last_name="", email="foto.bled@example.com")
        studio = ensure_studio(user)
        assert studio.name == "foto.bled"

    def test_middleware_creates_studio_on_dashboard_access(self):
        """Accessing dashboard without studio triggers middleware to create it."""
        from django.test import Client

        user = UserFactory()
        client = Client()
        client.force_login(user)
        client.get(reverse("core:dashboard"))
        user.refresh_from_db()
        assert hasattr(user, "studio")
        assert user.studio is not None
