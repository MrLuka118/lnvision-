from datetime import datetime, time, timedelta
from itertools import groupby

from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, UpdateView

from .forms import StudioForm
from .generic import FormPageMixin
from .models import Studio


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        from apps.scheduling.models import Event

        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, time.min))
        week = (
            Event.objects.for_studio(self.request.studio)
            .filter(start__gte=start, start__lt=start + timedelta(days=7))
            .select_related("shoot", "client", "location")
            .order_by("start")
        )
        # Group by local date: an evening event is still "today" in Ljubljana, not tomorrow in UTC.
        days = [
            {"date": day, "events": list(events)}
            for day, events in groupby(week, key=lambda e: timezone.localdate(e.start))
        ]
        return super().get_context_data(days=days, today=today, **kwargs)


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "core/settings.html"


class StudioSettingsView(LoginRequiredMixin, FormPageMixin, SuccessMessageMixin, UpdateView):
    model = Studio
    form_class = StudioForm
    page_title = _("Studio")
    back_label = _("Settings")
    success_message = _("Studio details saved.")

    def get_object(self, queryset=None):
        return self.request.studio

    def get_success_url(self):
        return reverse_lazy("core:settings")

    def get_cancel_url(self):
        return reverse_lazy("core:settings")


class StyleGuideView(TemplateView):
    """The design system on one page. Only in DEBUG or for staff."""

    template_name = "core/styleguide.html"

    def dispatch(self, request, *args, **kwargs):
        if not (settings.DEBUG or request.user.is_staff):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        form = StyleGuideForm(data={"name": "Ana Novak", "email": "ana@", "package": "wedding"})
        form.is_valid()
        return super().get_context_data(
            form=form,
            tokens=[
                "surround",
                "surface",
                "raised",
                "well",
                "line",
                "ink",
                "ink-2",
                "ink-3",
                "danger",
                "success",
            ],
            event_colours=[
                (_("Shoot"), "var(--color-cc-orange-yellow)", "orange yellow"),
                (_("Client meeting"), "var(--color-cc-blue-sky)", "blue sky"),
                (_("Editing deadline"), "var(--color-cc-blue-flower)", "blue flower"),
                (_("Delivery deadline"), "var(--color-cc-moderate-red)", "moderate red"),
                (_("Personal"), "var(--color-cc-foliage)", "foliage"),
            ],
            statuses=[
                (_("Inquiry"), "var(--color-cc-light-skin)"),
                (_("Confirmed"), "var(--color-cc-blue-sky)"),
                (_("Shot"), "var(--color-cc-orange-yellow)"),
                (_("Editing"), "var(--color-cc-blue-flower)"),
                (_("Delivered"), "var(--color-cc-bluish-green)"),
                (_("Paid"), "var(--color-cc-yellow-green)"),
            ],
            samples=[
                {"name": "snow", "dim": True, "label": _("Bright photo, dimming on")},
                {"name": "harbour", "dim": True, "label": _("Busy photo")},
                {"name": "dunes", "dim": False, "label": _("Dark photo")},
            ],
            icons=[
                "layout-dashboard",
                "calendar",
                "users",
                "images",
                "camera",
                "wallet",
                "settings",
                "heart",
                "download",
                "share-2",
                "lock",
                "upload",
                "mail",
                "map-pin",
                "clock",
                "eye",
                "message-circle",
                "search",
                "filter",
                "link",
                "pencil",
                "trash-2",
                "check",
                "x",
                "sun",
                "moon",
                "aperture",
                "ellipsis",
            ],
            **kwargs,
        )


class StyleGuideForm(forms.Form):
    """Demo form for the style page: every field type the app uses."""

    name = forms.CharField(label=_("Client name"), initial="Ana Novak")
    email = forms.EmailField(label=_("Email"), help_text=_("The gallery link is sent here."))
    package = forms.ChoiceField(
        label=_("Package"),
        choices=[("", "—"), ("wedding", "Poroka, cel dan"), ("portrait", "Portret, 1 ura")],
        required=False,
    )
    notes = forms.CharField(label=_("Notes"), widget=forms.Textarea, required=False)
    newsletter = forms.BooleanField(label=_("Send a reminder a day before"), required=False)
