from django.conf import settings

from .navigation import nav_items

THEMES = {"dark", "light", "auto"}


def app(request):
    theme = request.COOKIES.get("theme")
    user = getattr(request, "user", None)
    return {
        "APP_NAME": settings.APP_NAME,
        "studio": getattr(request, "studio", None),
        "theme": theme if theme in THEMES else "dark",
        "nav_items": nav_items(request) if user and user.is_authenticated else [],
    }
