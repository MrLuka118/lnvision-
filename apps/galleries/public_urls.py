from django.urls import path

from . import public_views

app_name = "public_gallery"

urlpatterns = [
    path("g/<str:token>/", public_views.gallery, name="gallery"),
]
