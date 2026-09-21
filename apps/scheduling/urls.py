from django.urls import path

from . import views

app_name = "scheduling"

urlpatterns = [
    path("koledar/", views.CalendarView.as_view(), name="calendar"),
    path("koledar/api/dogodki/", views.events_feed, name="feed"),
    path("koledar/api/dogodki/<int:pk>/", views.event_move, name="move"),
    path("koledar/dogodki/nov/", views.EventCreateView.as_view(), name="create"),
    path("koledar/dogodki/<int:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("koledar/dogodki/<int:pk>/uredi/", views.EventUpdateView.as_view(), name="update"),
    path("koledar/dogodki/<int:pk>/izbrisi/", views.EventDeleteView.as_view(), name="delete"),
    path("koledar/naroci/nov-naslov/", views.IcsRotateView.as_view(), name="ics_rotate"),
    path("koledar/<str:token>.ics", views.ics_feed, name="ics"),
]
