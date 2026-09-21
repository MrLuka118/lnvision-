from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.clients.models import Client
from apps.core.generic import (
    StudioCreateView,
    StudioDeleteView,
    StudioDetailView,
    StudioListView,
    StudioUpdateView,
)
from apps.core.mixins import StudioScopedMixin
from apps.scheduling.models import Event

from . import services
from .forms import ShootForm
from .models import Shoot

ACTIVE = [
    Shoot.Status.INQUIRY,
    Shoot.Status.CONFIRMED,
    Shoot.Status.SHOT,
    Shoot.Status.EDITING,
    Shoot.Status.DELIVERED,
]


class ShootListView(StudioListView):
    model = Shoot
    template_name = "shoots/list.html"

    FILTERS = {
        "active": (_("Active"), ACTIVE),
        "inquiry": (_("Inquiries"), [Shoot.Status.INQUIRY]),
        "paid": (_("Paid"), [Shoot.Status.PAID]),
        "all": (_("All"), None),
    }

    def current_filter(self):
        key = self.request.GET.get("status", "active")
        return key if key in self.FILTERS else "active"

    def get_queryset(self):
        qs = super().get_queryset().with_dates().select_related("client", "package", "location")
        statuses = self.FILTERS[self.current_filter()][1]
        if statuses:
            qs = qs.filter(status__in=statuses)
        return qs.order_by(F("starts_at").desc(nulls_first=True), "-created_at")

    def get_paginate_by(self, queryset):
        # Active shoots are a working list, shown whole in two groups.
        return None if self.current_filter() == "active" else self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        groups = None
        shoots = list(context["object_list"])
        if self.current_filter() == "active" and shoots:
            upcoming = [s for s in shoots if s.starts_at is None or s.starts_at >= now]
            upcoming.sort(key=lambda s: (s.starts_at is None, s.starts_at or now))
            groups = [
                (_("Coming up"), upcoming),
                (_("Shot, not finished yet"), [s for s in shoots if s not in upcoming]),
            ]
        context.update(
            filters=[(key, label) for key, (label, _statuses) in self.FILTERS.items()],
            current=self.current_filter(),
            groups=groups,
            now=now,
        )
        return context


class ShootDetailView(StudioDetailView):
    model = Shoot
    template_name = "shoots/detail.html"

    def get_queryset(self):
        return super().get_queryset().with_dates().select_related("client", "package", "location")

    def get_context_data(self, **kwargs):
        shoot = self.object
        pipeline = [
            {
                "value": status,
                "label": Shoot.Status(status).label,
                "done": shoot.pipeline_index >= index,
                "current": shoot.status == status,
            }
            for index, status in enumerate(Shoot.PIPELINE)
        ]
        deadlines = shoot.events.exclude(kind=Event.Kind.SHOOT).order_by("start")
        return super().get_context_data(pipeline=pipeline, deadlines=deadlines, **kwargs)


class ShootCreateView(StudioCreateView):
    model = Shoot
    form_class = ShootForm
    page_title = _("New shoot")
    submit_label = _("Add shoot")
    back_label = _("Shoots")
    success_message = _("Shoot added.")

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")
        if client_id and client_id.isdigit():
            client = Client.objects.for_studio(self.request.studio).filter(pk=client_id).first()
            if client:
                initial["client"] = client
        for key in ("starts_at", "ends_at"):
            if value := self.request.GET.get(key):
                initial[key] = value[:16]
        return initial

    def get_cancel_url(self):
        return reverse("shoots:list")

    def get_success_url(self):
        return self.object.get_absolute_url()


class ShootUpdateView(StudioUpdateView):
    model = Shoot
    form_class = ShootForm
    submit_label = _("Save changes")
    success_message = _("Changes saved.")

    @property
    def page_title(self):
        return self.object.title

    @property
    def back_label(self):
        return self.object.title

    def get_success_url(self):
        return self.object.get_absolute_url()


class ShootDeleteView(StudioDeleteView):
    model = Shoot
    success_url = reverse_lazy("shoots:list")
    confirm_label = _("Delete shoot")

    @property
    def page_title(self):
        return _("Delete “%(title)s”?") % {"title": self.object.title}

    @property
    def lede(self):
        return _("Its calendar events and deadlines are removed too. This can't be undone.")

    @property
    def success_message(self):
        return _("“%(title)s” deleted.") % {"title": self.object.title}


class ShootStatusView(StudioScopedMixin, View):
    """POST a new status. Plain forms get a redirect; HTMX swaps the page body in place."""

    http_method_names = ["post"]

    def post(self, request, pk):
        shoot = get_object_or_404(Shoot.objects.for_studio(request.studio), pk=pk)
        services.set_status(shoot, request.POST.get("status", ""))
        return HttpResponseRedirect(shoot.get_absolute_url())
