from django.urls import path

from . import views

app_name = "galleries"

urlpatterns = [
    path("galerije/", views.GalleryListView.as_view(), name="list"),
    path("galerije/nova/", views.GalleryCreateView.as_view(), name="create"),
    path("galerije/<int:pk>/", views.GalleryEditorView.as_view(), name="editor"),
    path("galerije/<int:pk>/nastavitve/", views.GallerySettingsView.as_view(), name="settings"),
    path("galerije/<int:pk>/izbrisi/", views.GalleryDeleteView.as_view(), name="delete"),
    path(
        "galerije/<int:pk>/sekcije/",
        views.SectionCreateView.as_view(),
        name="section_create",
    ),
    path(
        "galerije/<int:pk>/sekcije/<int:section_pk>/izbrisi/",
        views.SectionDeleteView.as_view(),
        name="section_delete",
    ),
    path(
        "galerije/<int:pk>/fotografije/<int:photo_pk>/<slug:action>/",
        views.PhotoActionView.as_view(),
        name="photo_action",
    ),
    path("galerije/<int:pk>/<slug:action>/", views.GalleryActionView.as_view(), name="action"),
]
