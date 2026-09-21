import factory
from factory.django import DjangoModelFactory

from apps.clients.models import Client
from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client

    studio = factory.SubFactory(StudioFactory)
    first_name = factory.Faker("first_name", locale="sl_SI")
    last_name = factory.Faker("last_name", locale="sl_SI")
    email = factory.Sequence(lambda n: f"stranka{n}@example.com")
    phone = "+386 41 123 456"


register_factory(Client, ClientFactory)
