from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("stranke/", views.ClientListView.as_view(), name="list"),
    path("stranke/nova/", views.ClientCreateView.as_view(), name="create"),
    path("stranke/<int:pk>/", views.ClientDetailView.as_view(), name="detail"),
    path("stranke/<int:pk>/uredi/", views.ClientUpdateView.as_view(), name="update"),
    path("stranke/<int:pk>/izbrisi/", views.ClientDeleteView.as_view(), name="delete"),
]
