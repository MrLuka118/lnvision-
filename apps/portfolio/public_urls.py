from django.urls import path

from . import public_views as views

app_name = "public_portfolio"

urlpatterns = [
    path("p/<slug:studio_slug>/", views.home, name="home"),
    path("p/<slug:studio_slug>/povprasevanje/", views.inquiry, name="inquiry"),
    path("p/<slug:studio_slug>/<slug:category_slug>/", views.category, name="category"),
    path(
        "p/<slug:studio_slug>/<slug:category_slug>/<slug:story_slug>/",
        views.story,
        name="story",
    ),
]
