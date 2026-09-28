from datetime import date

import pytest
from django.urls import reverse

from apps.clients.tests.factories import ClientFactory
from apps.finance.tests.factories import IncomeFactory

pytestmark = pytest.mark.django_db


def test_profile_updates_only_self(auth_client, studio, other_studio):
    assert (
        auth_client.post(
            reverse("core:profile_settings"), {"first_name": "Luka", "last_name": "Vision"}
        ).status_code
        == 302
    )
    studio.owner.refresh_from_db()
    other_studio.owner.refresh_from_db()
    assert studio.owner.first_name == "Luka"
    assert other_studio.owner.first_name != "Luka"


def test_branding_rejects_css_injection(auth_client, studio):
    response = auth_client.post(
        reverse("core:studio_settings"),
        {
            "name": studio.name,
            "slug": studio.slug,
            "accent_colour": "red;{}",
            "default_vat_rate": "22",
        },
    )
    assert response.status_code == 200
    studio.refresh_from_db()
    assert studio.accent_colour == "#c7955a"


def test_client_revenue_is_scoped(auth_client, studio, other_studio):
    person = ClientFactory(studio=studio)
    IncomeFactory(studio=studio, client=person, amount=350)
    IncomeFactory(studio=other_studio, amount=9999)
    response = auth_client.get(person.get_absolute_url())
    assert response.context["revenue"] == 350


def test_finance_invalid_period_falls_back(auth_client):
    response = auth_client.get(reverse("finance:dashboard"), {"leto": "bad", "mesec": "99"})
    assert response.status_code == 200
    assert response.context["year"] == date.today().year
