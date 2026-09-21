from django.urls import path

from . import views, views_catalogue

app_name = "shoots"

urlpatterns = [
    path("fotografiranja/", views.ShootListView.as_view(), name="list"),
    path("fotografiranja/novo/", views.ShootCreateView.as_view(), name="create"),
    path("fotografiranja/<int:pk>/", views.ShootDetailView.as_view(), name="detail"),
    path("fotografiranja/<int:pk>/uredi/", views.ShootUpdateView.as_view(), name="update"),
    path("fotografiranja/<int:pk>/status/", views.ShootStatusView.as_view(), name="status"),
    path("fotografiranja/<int:pk>/izbrisi/", views.ShootDeleteView.as_view(), name="delete"),
    # Catalogue: Packages
    path(
        "nastavitve/paketi/",
        views_catalogue.PackageListView.as_view(),
        name="package_list",
    ),
    path(
        "nastavitve/paketi/nov/",
        views_catalogue.PackageCreateView.as_view(),
        name="package_create",
    ),
    path(
        "nastavitve/paketi/<int:pk>/uredi/",
        views_catalogue.PackageUpdateView.as_view(),
        name="package_update",
    ),
    path(
        "nastavitve/paketi/<int:pk>/izbrisi/",
        views_catalogue.PackageDeleteView.as_view(),
        name="package_delete",
    ),
    # Catalogue: Locations
    path(
        "nastavitve/lokacije/",
        views_catalogue.LocationListView.as_view(),
        name="location_list",
    ),
    path(
        "nastavitve/lokacije/nova/",
        views_catalogue.LocationCreateView.as_view(),
        name="location_create",
    ),
    path(
        "nastavitve/lokacije/<int:pk>/uredi/",
        views_catalogue.LocationUpdateView.as_view(),
        name="location_update",
    ),
    path(
        "nastavitve/lokacije/<int:pk>/izbrisi/",
        views_catalogue.LocationDeleteView.as_view(),
        name="location_delete",
    ),
]
