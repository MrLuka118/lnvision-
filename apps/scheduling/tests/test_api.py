import json
from datetime import timedelta

import pytest
from django.test import Client as HttpClient
from django.urls import reverse
from django.utils import timezone
from icalendar import Calendar

from apps.scheduling.models import Event
from apps.scheduling.tests.factories import EventFactory

pytestmark = pytest.mark.django_db


def feed(client, start, end):
    return client.get(
        reverse("scheduling:feed"), {"start": start.isoformat(), "end": end.isoformat()}
    )


def test_feed_returns_only_own_events_in_range(auth_client, studio, other_studio):
    now = timezone.now()
    mine = EventFactory(studio=studio, start=now + timedelta(days=1), end=None)
    EventFactory(studio=studio, start=now + timedelta(days=60), end=None)
    EventFactory(studio=other_studio, start=now + timedelta(days=1), end=None)
    response = feed(auth_client, now, now + timedelta(days=7))
    assert response.status_code == 200
    assert [e["id"] for e in response.json()] == [str(mine.pk)]


def test_feed_includes_events_that_started_before_the_range(auth_client, studio):
    now = timezone.now()
    long = EventFactory(studio=studio, start=now - timedelta(days=2), end=now + timedelta(days=2))
    response = feed(auth_client, now, now + timedelta(days=7))
    assert [e["id"] for e in response.json()] == [str(long.pk)]


@pytest.mark.parametrize(
    "params",
    [{}, {"start": "nonsense", "end": "2026-10-01"}, {"start": "2026-01-01", "end": "2028-01-01"}],
)
def test_feed_rejects_bad_ranges(auth_client, params):
    assert auth_client.get(reverse("scheduling:feed"), params).status_code == 400


def test_feed_requires_login(client):
    assert client.get(reverse("scheduling:feed")).status_code == 302


def patch(client, event, body):
    return client.patch(
        reverse("scheduling:move", args=[event.pk]),
        data=json.dumps(body),
        content_type="application/json",
    )


def test_moving_an_event(auth_client, studio):
    event = EventFactory(studio=studio)
    response = patch(
        auth_client,
        event,
        {"start": "2026-10-05T09:00:00+02:00", "end": "2026-10-05T10:30:00+02:00", "allDay": False},
    )
    assert response.status_code == 200
    event.refresh_from_db()
    assert timezone.localtime(event.start).strftime("%Y-%m-%d %H:%M") == "2026-10-05 09:00"
    assert event.end - event.start == timedelta(minutes=90)


def test_moving_to_an_all_day_slot(auth_client, studio):
    event = EventFactory(studio=studio)
    patch(auth_client, event, {"start": "2026-10-05", "end": None, "allDay": True})
    event.refresh_from_db()
    assert event.all_day
    assert timezone.localdate(event.start).isoformat() == "2026-10-05"


@pytest.mark.parametrize(
    "body",
    [
        {"start": "later"},
        {"start": "2026-10-05T10:00:00+02:00", "end": "2026-10-05T09:00:00+02:00"},
    ],
)
def test_invalid_moves_are_rejected(auth_client, studio, body):
    event = EventFactory(studio=studio)
    original = event.start
    assert patch(auth_client, event, body).status_code == 400
    event.refresh_from_db()
    assert event.start == original


def test_invalid_json_is_rejected(auth_client, studio):
    event = EventFactory(studio=studio)
    response = auth_client.patch(
        reverse("scheduling:move", args=[event.pk]), data="{", content_type="application/json"
    )
    assert response.status_code == 400


def test_move_requires_csrf_token(studio):
    event = EventFactory(studio=studio)
    browser = HttpClient(enforce_csrf_checks=True)
    browser.force_login(studio.owner)
    response = patch(browser, event, {"start": "2026-10-05T09:00:00+02:00"})
    assert response.status_code == 403


def test_move_rejects_other_methods(auth_client, studio):
    event = EventFactory(studio=studio)
    assert auth_client.get(reverse("scheduling:move", args=[event.pk])).status_code == 405


def test_ics_feed_lists_own_events(client, studio, other_studio):
    EventFactory(studio=studio, title="Poroka na Bledu")
    EventFactory(studio=other_studio, title="Tuje")
    response = client.get(reverse("scheduling:ics", args=[studio.ics_token]))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    calendar = Calendar.from_ical(response.content)
    summaries = [str(c.get("summary")) for c in calendar.walk("VEVENT")]
    assert summaries == ["Poroka na Bledu"]


def test_ics_feed_with_wrong_token_is_not_found(client, studio):
    assert client.get(reverse("scheduling:ics", args=["x" * 43])).status_code == 404


def test_new_ics_link_invalidates_the_old_one(auth_client, client, studio):
    old = studio.ics_token
    response = auth_client.post(reverse("scheduling:ics_rotate"))
    assert response.status_code == 302
    studio.refresh_from_db()
    assert studio.ics_token != old
    assert client.get(reverse("scheduling:ics", args=[old])).status_code == 404
    assert client.get(reverse("scheduling:ics", args=[studio.ics_token])).status_code == 200


def test_shoot_events_are_not_deleted_from_the_calendar(auth_client, studio):
    from apps.shoots.tests.factories import ShootFactory

    shoot = ShootFactory(studio=studio)
    event = EventFactory(studio=studio, kind=Event.Kind.SHOOT, shoot=shoot)
    response = auth_client.post(reverse("scheduling:delete", args=[event.pk]))
    assert response.status_code == 404
    assert Event.objects.filter(pk=event.pk).exists()
