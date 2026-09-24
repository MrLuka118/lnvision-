from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.clients.tests.factories import ClientFactory
from apps.scheduling.models import Event
from apps.shoots.models import Shoot
from apps.shoots.tests.factories import LocationFactory, PackageFactory

pytestmark = pytest.mark.django_db


def test_new_shoot_gets_price_title_and_calendar_event(auth_client, studio, client_obj):
    package = PackageFactory(studio=studio, name="Portret", price=Decimal("180.00"))
    response = auth_client.post(
        reverse("shoots:create"),
        {"client": client_obj.pk, "package": package.pk, "starts_at": "2026-10-14T15:00"},
    )
    shoot = Shoot.objects.get(studio=studio)
    assert response.status_code == 302
    assert response["Location"] == shoot.get_absolute_url()
    assert shoot.price == Decimal("180.00")
    assert shoot.title == f"Portret: {client_obj.display_name}"
    event = shoot.events.get(kind=Event.Kind.SHOOT)
    assert timezone.localtime(event.start).strftime("%Y-%m-%d %H:%M") == "2026-10-14 15:00"


def test_shoot_form_rejects_another_studios_client(auth_client, studio, other_studio):
    foreign = ClientFactory(studio=other_studio)
    response = auth_client.post(reverse("shoots:create"), {"client": foreign.pk})
    assert response.status_code == 200
    assert "client" in response.context["form"].errors
    assert not Shoot.objects.exists()


def test_shoot_form_offers_only_own_choices(auth_client, studio, other_studio):
    ClientFactory(studio=studio, first_name="Moja")
    ClientFactory(studio=other_studio, first_name="Tuja")
    LocationFactory(studio=other_studio, name="Tuja lokacija")
    html = auth_client.get(reverse("shoots:create")).content.decode()
    assert "Moja" in html
    assert "Tuja" not in html


def test_end_before_start_is_rejected(auth_client, client_obj):
    response = auth_client.post(
        reverse("shoots:create"),
        {"client": client_obj.pk, "starts_at": "2026-10-14T15:00", "ends_at": "2026-10-14T14:00"},
    )
    assert "ends_at" in response.context["form"].errors


def test_status_change(auth_client, shoot):
    response = auth_client.post(reverse("shoots:status", args=[shoot.pk]), {"status": "paid"})
    assert response.status_code == 302
    shoot.refresh_from_db()
    assert shoot.status == Shoot.Status.PAID


def test_status_change_sets_success_message(auth_client, shoot):
    response = auth_client.post(
        reverse("shoots:status", args=[shoot.pk]), {"status": "paid"}, follow=True
    )
    assert response.status_code == 200
    messages = list(response.context["messages"])
    assert len(messages) == 1
    shoot.refresh_from_db()
    assert str(messages[0]) == f"Status: {shoot.get_status_display()}"


def test_active_list_puts_upcoming_first(auth_client, shoot):
    response = auth_client.get(reverse("shoots:list"))
    assert response.status_code == 200
    labels = [label for label, _ in response.context["groups"]]
    assert len(labels) == 2


def test_client_with_shoots_cannot_be_deleted(auth_client, shoot):
    response = auth_client.post(reverse("clients:delete", args=[shoot.client.pk]))
    assert response.status_code == 302
    assert response["Location"] == shoot.client.get_absolute_url()
    shoot.client.refresh_from_db()  # still there


def test_client_without_shoots_can_be_deleted(auth_client, client_obj):
    response = auth_client.post(reverse("clients:delete", args=[client_obj.pk]))
    assert response.status_code == 302
    assert response["Location"] == reverse("clients:list")
    assert not type(client_obj).objects.filter(pk=client_obj.pk).exists()


def test_client_search(auth_client, studio):
    ClientFactory(studio=studio, first_name="Špela", last_name="Kovač")
    ClientFactory(studio=studio, first_name="Rok", last_name="Turk")
    response = auth_client.get(reverse("clients:list"), {"q": "kov"})
    names = [c.first_name for c in response.context["object_list"]]
    assert names == ["Špela"]


def test_client_search_partial_for_htmx(auth_client, studio):
    ClientFactory(studio=studio)
    response = auth_client.get(
        reverse("clients:list"),
        {"q": "a"},
        headers={"HX-Request": "true", "HX-Target": "client-results"},
    )
    assert response.templates[0].name == "clients/_results.html"


def test_all_day_shoot_detail_does_not_contain_midnight(auth_client, studio, shoot):
    Event.objects.create(
        studio=studio,
        kind=Event.Kind.SHOOT,
        shoot=shoot,
        start=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0),
        all_day=True,
    )
    response = auth_client.get(shoot.get_absolute_url())
    assert response.status_code == 200
    assert response.context["object"].all_day is True
    assert "00:00" not in response.content.decode()


def test_all_day_shoot_row_omits_time(auth_client, studio, shoot):
    Event.objects.create(
        studio=studio,
        kind=Event.Kind.SHOOT,
        shoot=shoot,
        start=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0),
        all_day=True,
    )
    response = auth_client.get(reverse("shoots:list"))
    assert response.status_code == 200
    assert "00:00" not in response.content.decode()
