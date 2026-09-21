from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class NavEntry:
    url_name: str
    label: str
    icon: str


# Main destinations, in order. Entries whose URL does not exist yet (later phases) are skipped.
NAVIGATION = [
    NavEntry("core:dashboard", _("Overview"), "layout-dashboard"),
    NavEntry("scheduling:calendar", _("Calendar"), "calendar"),
    NavEntry("shoots:list", _("Shoots"), "camera"),
    NavEntry("clients:list", _("Clients"), "users"),
    NavEntry("galleries:list", _("Galleries"), "images"),
    NavEntry("finance:dashboard", _("Finance"), "wallet"),
]


def nav_items(request):
    match = getattr(request, "resolver_match", None)
    current_ns = match.namespace if match else ""
    current = match.view_name if match else ""
    items = []
    for entry in NAVIGATION:
        try:
            url = reverse(entry.url_name)
        except NoReverseMatch:
            continue
        namespace = entry.url_name.split(":")[0]
        is_current = current == entry.url_name or (namespace != "core" and current_ns == namespace)
        items.append({"url": url, "label": entry.label, "icon": entry.icon, "current": is_current})
    return items
