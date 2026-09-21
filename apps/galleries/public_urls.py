from django.urls import path

from . import public_views as views

app_name = "public_gallery"

urlpatterns = [
    path("g/<str:token>/", views.gallery, name="gallery"),
    path("g/<str:token>/geslo/", views.unlock, name="unlock"),
    path("g/<str:token>/ime/", views.identify, name="identify"),
    path("g/<str:token>/komentar/", views.comment, name="comment"),
    path("g/<str:token>/zip/", views.request_zip, name="zip_request"),
    path("g/<str:token>/zip/<int:pk>/", views.zip_status, name="zip_status"),
    path("g/<str:token>/foto/<uuid:photo_uuid>/srce/", views.favorite, name="favorite"),
    path("g/<str:token>/foto/<uuid:photo_uuid>/ogled/", views.seen, name="seen"),
    path("g/<str:token>/foto/<uuid:photo_uuid>/prenos/", views.download_photo, name="download"),
    path("prenos/<str:signed>/", views.zip_file, name="zip_file"),
]
