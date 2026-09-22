from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("racun/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.shoots.urls")),
    path("", include("apps.scheduling.urls")),
    path("", include("apps.photos.urls")),
    path("", include("apps.galleries.urls")),
    path("", include("apps.galleries.public_urls")),
    path("", include("apps.portfolio.urls")),
    path("", include("apps.portfolio.public_urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
