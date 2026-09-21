from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    path("galerije/<int:gallery_pk>/nalaganje/", views.start_upload, name="upload_start"),
    path("nalaganje/<uuid:uuid>/", views.upload_chunk, name="upload_chunk"),
]
