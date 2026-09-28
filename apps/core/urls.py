from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("nastavitve/profil/", views.ProfileSettingsView.as_view(), name="profile_settings"),
    path("znamka/<slug:slug>/logo/", views.studio_logo, name="studio_logo"),
    path("styleguide/", views.StyleGuideView.as_view(), name="styleguide_alias"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("stil/", views.StyleGuideView.as_view(), name="styleguide"),
    path("nastavitve/", views.SettingsView.as_view(), name="settings"),
    path("nastavitve/studio/", views.StudioSettingsView.as_view(), name="studio_settings"),
]
