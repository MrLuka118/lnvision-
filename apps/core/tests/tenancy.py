"""Registry for the tenant-isolation tests.

Every studio-owned model registers a factory here, and every URL that takes an object id
registers a case. test_tenancy.py then checks that a photographer can never reach another
studio's objects, and fails if a new TenantModel was added without being registered.
"""

from dataclasses import dataclass, field
from typing import Any

# model class -> factory creating an instance for a given studio: factory(studio=...)
TENANT_FACTORIES: dict[type, Any] = {}


@dataclass(frozen=True)
class TenantURLCase:
    url_name: str
    model: type
    # Builds reverse() kwargs from the object, e.g. lambda obj: {"pk": obj.pk}
    kwargs: Any = field(default=lambda obj: {"pk": obj.pk})
    methods: tuple[str, ...] = ("get",)


TENANT_URL_CASES: list[TenantURLCase] = []


def register_factory(model, factory):
    TENANT_FACTORIES[model] = factory


def register_url(case: TenantURLCase):
    TENANT_URL_CASES.append(case)


def _register_url_cases():
    """Every URL that takes a studio-owned object. A foreign id must always give 404."""
    from apps.clients.models import Client
    from apps.scheduling.models import Event
    from apps.shoots.models import Location, Package, Shoot

    for name, methods in [
        ("clients:detail", ("get",)),
        ("clients:update", ("get", "post")),
        ("clients:delete", ("get", "post")),
    ]:
        register_url(TenantURLCase(name, Client, methods=methods))
    for name, methods in [
        ("shoots:detail", ("get",)),
        ("shoots:update", ("get", "post")),
        ("shoots:delete", ("get", "post")),
        ("shoots:status", ("post",)),
    ]:
        register_url(TenantURLCase(name, Shoot, methods=methods))
    for name, methods in [
        ("scheduling:detail", ("get",)),
        ("scheduling:update", ("get", "post")),
        ("scheduling:delete", ("post",)),
        ("scheduling:move", ("patch",)),
    ]:
        register_url(TenantURLCase(name, Event, methods=methods))
    from apps.galleries.models import Gallery
    from apps.photos.models import Photo, UploadSession

    for name, methods in [
        ("galleries:editor", ("get",)),
        ("galleries:settings", ("get", "post")),
        ("galleries:delete", ("get", "post")),
        ("galleries:section_create", ("post",)),
        ("photos:upload_start", ("post",)),
    ]:
        kwargs = (lambda o: {"gallery_pk": o.pk}) if name.startswith("photos") else None
        register_url(
            TenantURLCase(name, Gallery, methods=methods, kwargs=kwargs or (lambda o: {"pk": o.pk}))
        )
    register_url(
        TenantURLCase(
            "galleries:action",
            Gallery,
            methods=("post",),
            kwargs=lambda o: {"pk": o.pk, "action": "publish"},
        )
    )
    register_url(TenantURLCase("photos:detail", Photo, kwargs=lambda o: {"uuid": o.uuid}))
    register_url(
        TenantURLCase(
            "photos:upload_chunk",
            UploadSession,
            methods=("get", "put"),
            kwargs=lambda o: {"uuid": o.uuid},
        )
    )

    for name, model in [
        ("shoots:package_update", Package),
        ("shoots:package_delete", Package),
        ("shoots:location_update", Location),
        ("shoots:location_delete", Location),
    ]:
        register_url(TenantURLCase(name, model, methods=("get", "post")))

    from apps.portfolio.models import PortfolioCategory, PortfolioStory

    for name, model in [
        ("portfolio:category_update", PortfolioCategory),
        ("portfolio:category_delete", PortfolioCategory),
        ("portfolio:story_update", PortfolioStory),
        ("portfolio:story_delete", PortfolioStory),
        ("portfolio:story_photos", PortfolioStory),
    ]:
        register_url(TenantURLCase(name, model, methods=("get", "post")))

    from apps.finance.models import Expense, ExpenseCategory, Income, RecurringExpense

    for kind, model in [
        ("income", Income),
        ("expense", Expense),
        ("category", ExpenseCategory),
        ("recurring", RecurringExpense),
    ]:
        for action in ["update", "delete"]:
            register_url(TenantURLCase(f"finance:{kind}_{action}", model, methods=("get", "post")))
    register_url(TenantURLCase("finance:receipt", Expense))


_register_url_cases()
