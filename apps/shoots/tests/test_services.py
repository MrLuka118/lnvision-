from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.scheduling.models import Event
from apps.shoots import services
from apps.shoots.models import Shoot
from apps.shoots.tests.factories import PackageFactory, ShootFactory

pytestmark = pytest.mark.django_db


def local(*args):
    return timezone.make_aware(datetime(*args))


@pytest.fixture
def package(studio):
    return PackageFactory(studio=studio, duration_minutes=90, editing_days=14, delivery_days=21)


@pytest.fixture
def inquiry(studio, package):
    return ShootFactory(studio=studio, package=package, status=Shoot.Status.INQUIRY)


def test_main_event_takes_its_length_from_the_package(inquiry):
    event = services.save_main_event(inquiry, local(2026, 10, 3, 14, 0))
    assert event.kind == Event.Kind.SHOOT
    assert event.end - event.start == timedelta(minutes=90)
    assert event.is_tentative  # still an inquiry
    assert event.client == inquiry.client
    assert event.studio == inquiry.studio


def test_moving_the_date_updates_the_same_event(inquiry):
    first = services.save_main_event(inquiry, local(2026, 10, 3, 14, 0))
    second = services.save_main_event(inquiry, local(2026, 10, 10, 9, 0))
    assert first.pk == second.pk
    assert inquiry.events.filter(kind=Event.Kind.SHOOT).count() == 1


def test_clearing_the_date_removes_the_event(inquiry):
    services.save_main_event(inquiry, local(2026, 10, 3, 14, 0))
    services.save_main_event(inquiry, None)
    assert not inquiry.events.exists()


def test_confirming_adds_deadlines_from_the_package(inquiry):
    services.save_main_event(inquiry, local(2026, 10, 3, 22, 30))  # late evening, local time
    assert services.set_status(inquiry, Shoot.Status.CONFIRMED)
    editing = inquiry.events.get(kind=Event.Kind.EDITING_DEADLINE)
    delivery = inquiry.events.get(kind=Event.Kind.DELIVERY_DEADLINE)
    assert timezone.localdate(editing.start).isoformat() == "2026-10-17"
    assert timezone.localdate(delivery.start).isoformat() == "2026-10-24"
    assert editing.all_day and delivery.all_day
    assert not inquiry.events.get(kind=Event.Kind.SHOOT).is_tentative


def test_deadlines_are_added_once_and_manual_moves_stick(inquiry):
    services.save_main_event(inquiry, local(2026, 10, 3, 14, 0))
    services.set_status(inquiry, Shoot.Status.CONFIRMED)
    delivery = inquiry.events.get(kind=Event.Kind.DELIVERY_DEADLINE)
    delivery.start = local(2026, 11, 20)
    delivery.save()
    services.set_status(inquiry, Shoot.Status.SHOT)
    services.save_main_event(inquiry, local(2026, 10, 4, 14, 0))
    assert inquiry.events.filter(kind=Event.Kind.DELIVERY_DEADLINE).count() == 1
    delivery.refresh_from_db()
    assert timezone.localdate(delivery.start).isoformat() == "2026-11-20"


def test_inquiries_get_no_deadlines(inquiry):
    services.save_main_event(inquiry, local(2026, 10, 3, 14, 0))
    assert not inquiry.events.exclude(kind=Event.Kind.SHOOT).exists()


def test_unknown_or_same_status_changes_nothing(inquiry):
    assert not services.set_status(inquiry, "archived")
    assert not services.set_status(inquiry, Shoot.Status.INQUIRY)
    assert inquiry.status_changed_at is None


def test_status_change_is_timestamped(inquiry):
    services.set_status(inquiry, Shoot.Status.CANCELLED)
    inquiry.refresh_from_db()
    assert inquiry.status == Shoot.Status.CANCELLED
    assert inquiry.status_changed_at is not None
