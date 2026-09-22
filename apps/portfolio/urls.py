from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    # Dashboard & Profile
    path("portfolio/", views.PortfolioIndexView.as_view(), name="index"),
    path("portfolio/profil/", views.PortfolioProfileView.as_view(), name="profile"),
    # Categories
    path("portfolio/kategorije/", views.CategoryListView.as_view(), name="category_list"),
    path(
        "portfolio/kategorije/nova/",
        views.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "portfolio/kategorije/<int:pk>/uredi/",
        views.CategoryUpdateView.as_view(),
        name="category_update",
    ),
    path(
        "portfolio/kategorije/<int:pk>/izbrisi/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    # Stories
    path("portfolio/zgodbe/", views.StoryListView.as_view(), name="story_list"),
    path("portfolio/zgodbe/nova/", views.StoryCreateView.as_view(), name="story_create"),
    path(
        "portfolio/zgodbe/<int:pk>/uredi/",
        views.StoryUpdateView.as_view(),
        name="story_update",
    ),
    path(
        "portfolio/zgodbe/<int:pk>/izbrisi/",
        views.StoryDeleteView.as_view(),
        name="story_delete",
    ),
    path(
        "portfolio/zgodbe/<int:pk>/fotografije/",
        views.StoryPhotosView.as_view(),
        name="story_photos",
    ),
]
