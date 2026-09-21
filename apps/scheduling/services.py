from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def parse_moment(value: str | None) -> datetime | None:
    """ISO date or datetime from the calendar → aware datetime. Dates mean local midnight."""
    if not value:
        return None
    moment = parse_datetime(value)
    if moment is None:
        day = parse_date(value[:10])
        if day is None:
            return None
        moment = datetime.combine(day, time.min)
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    return moment


def event_json(event) -> dict:
    """The shape FullCalendar reads. Colours are drawn by our own event content."""
    data = {
        "id": str(event.pk),
        "title": event.display_title,
        "start": timezone.localtime(event.start).isoformat(),
        "allDay": event.all_day,
        "backgroundColor": "transparent",
        "borderColor": "transparent",
        "textColor": "inherit",
        "extendedProps": {
            "kind": event.kind,
            "kindLabel": str(event.get_kind_display()),
            "colour": event.colour,
            "tentative": event.is_tentative,
            "client": event.client.display_name if event.client_id else "",
            "location": event.location.name if event.location_id else "",
        },
    }
    if event.end:
        data["end"] = timezone.localtime(event.end).isoformat()
    if event.all_day:
        data["start"] = timezone.localdate(event.start).isoformat()
        if event.end:
            data["end"] = timezone.localdate(event.end).isoformat()
    return data
