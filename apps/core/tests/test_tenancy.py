import importlib
import inspect

import pytest
from django.apps import apps
from django.forms import ModelForm
from django.test import RequestFactory
from django.urls import reverse

from apps.core.forms import StudioModelForm
from apps.core.middleware import StudioMiddleware
from apps.core.models import TenantModel

from .tenancy import TENANT_FACTORIES, TENANT_URL_CASES


def tenant_models():
    return [m for m in apps.get_models() if issubclass(m, TenantModel)]


def test_every_tenant_model_has_a_factory():
    missing = [m.__name__ for m in tenant_models() if m not in TENANT_FACTORIES]
    assert not missing, f"Register a factory in tests/tenancy.py for: {missing}"


def test_every_model_form_over_a_tenant_model_scopes_its_choices():
    offenders = []
    for config in apps.get_app_configs():
        if not config.name.startswith("apps."):
            continue
        try:
            module = importlib.import_module(f"{config.name}.forms")
        except ModuleNotFoundError:
            continue
        for _name, cls in inspect.getmembers(module, inspect.isclass):
            meta = getattr(cls, "_meta", None)
            model = getattr(meta, "model", None)
            if (
                issubclass(cls, ModelForm)
                and model is not None
                and issubclass(model, TenantModel)
                and not issubclass(cls, StudioModelForm)
            ):
                offenders.append(f"{module.__name__}.{cls.__name__}")
    assert not offenders, f"Use StudioModelForm for: {offenders}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "case", TENANT_URL_CASES, ids=[c.url_name for c in TENANT_URL_CASES] or None
)
def test_other_studios_objects_are_not_found(case, auth_client, other_studio):
    foreign = TENANT_FACTORIES[case.model](studio=other_studio)
    url = reverse(case.url_name, kwargs=case.kwargs(foreign))
    for method in case.methods:
        response = getattr(auth_client, method)(url)
        assert response.status_code == 404, f"{method.upper()} {url} -> {response.status_code}"


@pytest.mark.django_db
def test_middleware_gives_anonymous_visitors_no_studio():
    from django.contrib.auth.models import AnonymousUser

    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    StudioMiddleware(lambda r: None)(request)
    assert request.studio is None


@pytest.mark.django_db
def test_middleware_gives_photographers_their_own_studio(studio, other_studio):
    request = RequestFactory().get("/")
    request.user = studio.owner
    StudioMiddleware(lambda r: None)(request)
    assert request.studio == studio


@pytest.mark.django_db
def test_dashboard_shows_only_the_signed_in_studio(auth_client, studio, other_studio):
    html = auth_client.get(reverse("core:dashboard")).content.decode()
    assert studio.name in html
    assert other_studio.name not in html


@pytest.mark.django_db
def test_deleting_an_account_removes_the_whole_studio(studio, other_studio):
    from apps.clients.models import Client
    from apps.scheduling.models import Event
    from apps.shoots import services
    from apps.shoots.models import Shoot
    from apps.shoots.tests.factories import ShootFactory

    shoot = ShootFactory(studio=studio)
    services.save_main_event(shoot, shoot.created_at)
    kept = ShootFactory(studio=other_studio)
    studio.owner.delete()
    assert not Shoot.objects.filter(studio_id=studio.pk).exists()
    assert not Client.objects.filter(studio_id=studio.pk).exists()
    assert not Event.objects.filter(studio_id=studio.pk).exists()
    assert Shoot.objects.filter(pk=kept.pk).exists()
