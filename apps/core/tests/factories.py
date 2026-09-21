from django.contrib.auth import get_user_model
from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory

from apps.core.models import Studio

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Test user factory."""

    class Meta:
        model = User

    email = Sequence(lambda n: f"user{n}@example.com")
    first_name = "John"
    last_name = "Doe"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create a user with password."""
        password = kwargs.pop("password", "geslo-za-teste-123")
        obj = model_class(*args, **kwargs)
        obj.set_password(password)
        obj.save()
        return obj


class StudioFactory(DjangoModelFactory):
    """Test studio factory."""

    class Meta:
        model = Studio

    owner = SubFactory(UserFactory)
    name = Sequence(lambda n: f"Studio {n}")
    slug = Sequence(lambda n: f"studio-{n}")
