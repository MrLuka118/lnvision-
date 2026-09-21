from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.clients.tests.factories import ClientFactory
from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory
from apps.shoots.models import Location, Package, Shoot

SAME_STUDIO = factory.SelfAttribute("..studio")


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    studio = factory.SubFactory(StudioFactory)
    name = factory.Sequence(lambda n: f"Lokacija {n}")
    address = "Trubarjeva 20, Ljubljana"


class PackageFactory(DjangoModelFactory):
    class Meta:
        model = Package

    studio = factory.SubFactory(StudioFactory)
    name = factory.Sequence(lambda n: f"Paket {n}")
    price = Decimal("250.00")
    duration_minutes = 120
    photo_count = 40
    editing_days = 14
    delivery_days = 21


class ShootFactory(DjangoModelFactory):
    class Meta:
        model = Shoot

    studio = factory.SubFactory(StudioFactory)
    client = factory.SubFactory(ClientFactory, studio=SAME_STUDIO)
    package = factory.SubFactory(PackageFactory, studio=SAME_STUDIO)
    location = factory.SubFactory(LocationFactory, studio=SAME_STUDIO)
    title = factory.Sequence(lambda n: f"Fotografiranje {n}")
    price = Decimal("250.00")


register_factory(Location, LocationFactory)
register_factory(Package, PackageFactory)
register_factory(Shoot, ShootFactory)
