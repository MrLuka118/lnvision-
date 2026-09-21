"""Catalogue views: Packages and Locations (studio settings)."""

from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.core.generic import (
    StudioCreateView,
    StudioDeleteView,
    StudioListView,
    StudioUpdateView,
)

from .forms import LocationForm, PackageForm
from .models import Location, Package

# -- Packages ------------------------------------------------------------------


class PackageListView(StudioListView):
    model = Package
    template_name = "shoots/package_list.html"
    paginate_by = None

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .order_by("position", "name")
            .annotate(shoot_count=Count("shoots"))
        )


class PackageCreateView(StudioCreateView):
    model = Package
    form_class = PackageForm
    page_title = _("New package")
    back_label = _("Packages")
    submit_label = _("Add package")
    success_message = _("Package added.")

    def get_cancel_url(self):
        return reverse("shoots:package_list")

    def get_success_url(self):
        return reverse("shoots:package_list")


class PackageUpdateView(StudioUpdateView):
    model = Package
    form_class = PackageForm
    page_title = _("Edit package")
    back_label = _("Packages")
    submit_label = _("Save changes")
    success_message = _("Changes saved.")

    def get_delete_url(self):
        return reverse("shoots:package_delete", args=[self.object.pk])

    def get_success_url(self):
        return reverse("shoots:package_list")

    def get_cancel_url(self):
        return reverse("shoots:package_list")


class PackageDeleteView(StudioDeleteView):
    model = Package
    success_url = reverse_lazy("shoots:package_list")
    confirm_label = _("Delete package")

    @property
    def page_title(self):
        return _("Delete “%(name)s”?") % {"name": self.object.name}

    @property
    def lede(self):
        count = (
            self.object.shoot_count
            if hasattr(self.object, "shoot_count")
            else self.object.shoots.count()
        )
        if count:
            return ngettext(
                "%(count)s shoot uses this package. It keeps its price but loses the package. "
                "To stop offering it, switch off “Offered” instead.",
                "%(count)s shoots use this package. They keep their price but lose the package. "
                "To stop offering it, switch off “Offered” instead.",
                count,
            ) % {"count": count}
        return _("The package will be permanently removed. This can't be undone.")

    @property
    def success_message(self):
        return _("“%(name)s” deleted.") % {"name": self.object.name}

    def get_cancel_url(self):
        return reverse("shoots:package_list")


# -- Locations -----------------------------------------------------------------


class LocationListView(StudioListView):
    model = Location
    template_name = "shoots/location_list.html"
    paginate_by = None

    def get_queryset(self):
        return super().get_queryset().order_by("name").annotate(shoot_count=Count("shoots"))


class LocationCreateView(StudioCreateView):
    model = Location
    form_class = LocationForm
    page_title = _("New location")
    back_label = _("Locations")
    submit_label = _("Add location")
    success_message = _("Location added.")

    def get_cancel_url(self):
        return reverse("shoots:location_list")

    def get_success_url(self):
        return reverse("shoots:location_list")


class LocationUpdateView(StudioUpdateView):
    model = Location
    form_class = LocationForm
    page_title = _("Edit location")
    back_label = _("Locations")
    submit_label = _("Save changes")
    success_message = _("Changes saved.")

    def get_delete_url(self):
        return reverse("shoots:location_delete", args=[self.object.pk])

    def get_success_url(self):
        return reverse("shoots:location_list")

    def get_cancel_url(self):
        return reverse("shoots:location_list")


class LocationDeleteView(StudioDeleteView):
    model = Location
    success_url = reverse_lazy("shoots:location_list")
    confirm_label = _("Delete location")

    @property
    def page_title(self):
        return _("Delete “%(name)s”?") % {"name": self.object.name}

    @property
    def lede(self):
        count = (
            self.object.shoot_count
            if hasattr(self.object, "shoot_count")
            else self.object.shoots.count()
        )
        if count:
            return ngettext(
                "%(count)s shoot takes place here. It stays, without a location.",
                "%(count)s shoots take place here. They stay, without a location.",
                count,
            ) % {"count": count}
        return _("The location will be permanently removed. This can't be undone.")

    @property
    def success_message(self):
        return _("“%(name)s” deleted.") % {"name": self.object.name}

    def get_cancel_url(self):
        return reverse("shoots:location_list")
