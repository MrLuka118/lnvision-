from django.db.models import Count, Max, Min, Q
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.generic import (
    StudioCreateView,
    StudioDeleteView,
    StudioDetailView,
    StudioListView,
    StudioUpdateView,
)
from apps.scheduling.models import Event
from apps.shoots.models import Shoot

from .forms import ClientForm
from .models import Client


class ClientListView(StudioListView):
    model = Client
    template_name = "clients/list.html"

    def get_queryset(self):
        now = timezone.now()
        shoot_events = Q(events__kind=Event.Kind.SHOOT)
        qs = (
            super()
            .get_queryset()
            .annotate(
                shoot_count=Count("shoots", distinct=True),
                next_shoot=Min("events__start", filter=shoot_events & Q(events__start__gte=now)),
                last_shoot=Max("events__start", filter=shoot_events & Q(events__start__lt=now)),
            )
            # Aggregating queries drop Meta.ordering, so order explicitly for stable pages.
            .order_by("first_name", "last_name", "pk")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            for term in query.split():
                qs = qs.filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(partner_name__icontains=term)
                    | Q(email__icontains=term)
                    | Q(company__icontains=term)
                    | Q(phone__icontains=term)
                )
        return qs

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == "client-results":
            return ["clients/_results.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        return super().get_context_data(query=self.request.GET.get("q", "").strip(), **kwargs)


class ClientDetailView(StudioDetailView):
    model = Client
    template_name = "clients/detail.html"

    def get_context_data(self, **kwargs):
        shoots = (
            Shoot.objects.for_studio(self.request.studio)
            .filter(client=self.object)
            .with_dates()
            .select_related("package", "location")
            .order_by("-starts_at", "-created_at")
        )
        return super().get_context_data(shoots=shoots, now=timezone.now(), **kwargs)


class ClientCreateView(StudioCreateView):
    model = Client
    form_class = ClientForm
    page_title = _("New client")
    submit_label = _("Add client")
    back_label = _("Clients")
    success_message = _("%(first_name)s added to your clients.")

    def get_cancel_url(self):
        return reverse("clients:list")

    def get_success_url(self):
        return self.object.get_absolute_url()


class ClientUpdateView(StudioUpdateView):
    model = Client
    form_class = ClientForm
    submit_label = _("Save changes")
    success_message = _("Changes saved.")

    @property
    def page_title(self):
        return self.object.display_name

    @property
    def back_label(self):
        return self.object.full_name

    def get_success_url(self):
        return self.object.get_absolute_url()


class ClientDeleteView(StudioDeleteView):
    model = Client
    success_url = reverse_lazy("clients:list")
    confirm_label = _("Delete client")
    protected_message = _(
        "This client has shoots. Delete or reassign the shoots first, "
        "so their history stays intact."
    )

    @property
    def page_title(self):
        return _("Delete %(name)s?") % {"name": self.object.display_name}

    @property
    def lede(self):
        return _("Their contact details and notes are removed. This can't be undone.")

    @property
    def success_message(self):
        return _("%(name)s deleted.") % {"name": self.object.display_name}
