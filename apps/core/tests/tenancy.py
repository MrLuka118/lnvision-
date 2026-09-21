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
