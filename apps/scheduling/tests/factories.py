from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory
from apps.scheduling.models import Event


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    studio = factory.SubFactory(StudioFactory)
    kind = Event.Kind.MEETING
    title = factory.Sequence(lambda n: f"Dogodek {n}")
    start = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    end = factory.LazyAttribute(lambda e: e.start + timedelta(hours=1) if e.start else None)


register_factory(Event, EventFactory)
