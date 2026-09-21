import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestViews:
    """Tests for core views."""

    def test_dashboard_redirect_anonymous(self, client):
        """Anonymous request to dashboard redirects to login."""
        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_dashboard_authenticated(self, auth_client):
        """Authenticated request to dashboard returns 200."""
        response = auth_client.get(reverse("core:dashboard"))
        assert response.status_code == 200

    def test_styleguide_404_anonymous(self, client):
        """Anonymous request to styleguide returns 404."""
        response = client.get(reverse("core:styleguide"))
        assert response.status_code == 404

    def test_styleguide_404_non_staff(self, auth_client):
        """Non-staff user request to styleguide returns 404."""
        response = auth_client.get(reverse("core:styleguide"))
        assert response.status_code == 404

    def test_styleguide_200_staff(self, studio):
        """Staff user request to styleguide returns 200."""
        from django.test import Client

        staff_user = studio.owner
        staff_user.is_staff = True
        staff_user.save()
        client = Client()
        client.force_login(staff_user)
        response = client.get(reverse("core:styleguide"))
        assert response.status_code == 200
