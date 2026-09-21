from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"


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
