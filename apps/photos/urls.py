from django.urls import path

from . import renditions, views

app_name = "photos"

urlpatterns = [
    path("galerije/fotografije/<uuid:uuid>/", views.photo_detail, name="detail"),
    path("fotografije/<str:signed>/", renditions.rendition, name="rendition"),
    path("media/r/<path:path>", renditions.deny_raw_rendition),
    path("galerije/<int:gallery_pk>/nalaganje/", views.start_upload, name="upload_start"),
    path("nalaganje/<uuid:uuid>/", views.upload_chunk, name="upload_chunk"),
]
