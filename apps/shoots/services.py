"""Shoot workflows. Views call these; they keep the calendar in step with the shoot."""

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.scheduling.models import Event

from .models import Shoot

# From here on the shoot is booked, so it gets editing and delivery deadlines.
BOOKED = {
    Shoot.Status.CONFIRMED,
    Shoot.Status.SHOT,
    Shoot.Status.EDITING,
    Shoot.Status.DELIVERED,
    Shoot.Status.PAID,
}


def main_event(shoot: Shoot) -> Event | None:
    return shoot.events.filter(kind=Event.Kind.SHOOT).order_by("start").first()


@transaction.atomic
def save_main_event(shoot: Shoot, starts_at, ends_at=None) -> Event | None:
    """Create, move or remove the shoot's own calendar event."""
    event = main_event(shoot)
    if starts_at is None:
        if event:
            event.delete()
        return None
    if ends_at is None and shoot.package_id:
        ends_at = starts_at + shoot.package.duration
    if event is None:
        event = Event(studio=shoot.studio, kind=Event.Kind.SHOOT, shoot=shoot)
    event.client = shoot.client
    event.location = shoot.location
    event.start = starts_at
    event.end = ends_at
    event.all_day = False
    event.is_tentative = shoot.status == Shoot.Status.INQUIRY
    event.save()
    if shoot.status in BOOKED:
        schedule_deadlines(shoot, event)
    return event


def schedule_deadlines(shoot: Shoot, event: Event | None = None) -> list[Event]:
    """Add editing and delivery deadlines from the package, once.

    Deadlines that already exist are left alone, so moving one by hand sticks.
    """
    event = event or main_event(shoot)
    if event is None or shoot.package is None:
        return []
    shoot_day = timezone.localdate(event.start)
    created = []
    for kind, days in (
        (Event.Kind.EDITING_DEADLINE, shoot.package.editing_days),
        (Event.Kind.DELIVERY_DEADLINE, shoot.package.delivery_days),
    ):
        if shoot.events.filter(kind=kind).exists():
            continue
        day = shoot_day + timedelta(days=days)
        created.append(
            Event.objects.create(
                studio=shoot.studio,
                kind=kind,
                shoot=shoot,
                client=shoot.client,
                start=timezone.make_aware(datetime.combine(day, time.min)),
                all_day=True,
            )
        )
    return created


@transaction.atomic
def set_status(shoot: Shoot, status: str) -> bool:
    """Move a shoot to another status. Returns False when nothing changed."""
    if status not in Shoot.Status.values or status == shoot.status:
        return False
    shoot.status = status
    shoot.status_changed_at = timezone.now()
    shoot.save(update_fields=["status", "status_changed_at", "updated_at"])
    shoot.events.filter(kind=Event.Kind.SHOOT).update(is_tentative=status == Shoot.Status.INQUIRY)
    if status in BOOKED:
        schedule_deadlines(shoot)
    return True
