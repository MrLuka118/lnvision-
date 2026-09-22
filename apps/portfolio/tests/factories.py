import factory
from factory.django import DjangoModelFactory

from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory
from apps.portfolio.models import Inquiry, Portfolio, PortfolioCategory, PortfolioStory


class PortfolioFactory(DjangoModelFactory):
    class Meta:
        model = Portfolio

    studio = factory.SubFactory(StudioFactory)
    is_published = True
    headline = "Poročna in portretna fotografija"


class PortfolioCategoryFactory(DjangoModelFactory):
    class Meta:
        model = PortfolioCategory

    studio = factory.SubFactory(StudioFactory)
    name = factory.Sequence(lambda n: f"Kategorija {n}")
    slug = factory.Sequence(lambda n: f"kategorija-{n}")


class PortfolioStoryFactory(DjangoModelFactory):
    class Meta:
        model = PortfolioStory

    studio = factory.SubFactory(StudioFactory)
    category = factory.SubFactory(
        PortfolioCategoryFactory, studio=factory.SelfAttribute("..studio")
    )
    title = factory.Sequence(lambda n: f"Zgodba {n}")
    slug = factory.Sequence(lambda n: f"zgodba-{n}")
    is_published = True


class InquiryFactory(DjangoModelFactory):
    class Meta:
        model = Inquiry

    studio = factory.SubFactory(StudioFactory)
    name = "Ana Novak"
    email = factory.Sequence(lambda n: f"povprasevanje{n}@example.si")
    message = "Zanima me poroka."


register_factory(Portfolio, PortfolioFactory)
register_factory(PortfolioCategory, PortfolioCategoryFactory)
register_factory(PortfolioStory, PortfolioStoryFactory)
register_factory(Inquiry, InquiryFactory)
