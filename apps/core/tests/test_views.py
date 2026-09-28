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

    def test_dashboard_greets_the_signed_in_user_or_their_studio(self, auth_client, studio):
        """The greeting names the signed-in user, or the studio when the user has no name."""
        studio.owner.first_name = "Ana"
        studio.owner.save()
        assert "Ana." in auth_client.get(reverse("core:dashboard")).content.decode()
        studio.owner.first_name = ""
        studio.owner.save()
        assert f"{studio.name}." in auth_client.get(reverse("core:dashboard")).content.decode()

    def test_dashboard_lists_inquiries_waiting_for_a_reply(self, auth_client, studio, other_studio):
        from apps.shoots.models import Shoot
        from apps.shoots.tests.factories import ShootFactory

        waiting = ShootFactory(studio=studio, status=Shoot.Status.INQUIRY)
        ShootFactory(studio=studio, status=Shoot.Status.CONFIRMED)
        ShootFactory(studio=other_studio, status=Shoot.Status.INQUIRY)
        response = auth_client.get(reverse("core:dashboard"))
        assert list(response.context["inquiries"]) == [waiting]
        assert response.context["inquiry_count"] == 1

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


@pytest.mark.django_db
def test_missing_page_uses_the_styled_404(client):
    response = client.get("/ta-stran-ne-obstaja/")
    assert response.status_code == 404
    assert "404.html" in [t.name for t in response.templates]


def test_500_page_renders_without_request_context():
    from django.template import loader

    html = loader.get_template("500.html").render()
    assert 'href="/"' in html
