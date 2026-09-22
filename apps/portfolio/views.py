"""Management views for the portfolio: settings, categories, stories and photo selection."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views import View
from django.views.generic import TemplateView

from apps.core.generic import (
    StudioCreateView,
    StudioDeleteView,
    StudioListView,
    StudioUpdateView,
)
from apps.core.mixins import StudioScopedMixin
from apps.photos.models import Photo

from .forms import CategoryForm, PortfolioForm, StoryForm
from .models import Portfolio, PortfolioCategory, PortfolioStory, PortfolioStoryPhoto

# ---------------------------------------------------------------------------
# 1. Portfolio Index & Profile
# ---------------------------------------------------------------------------


class PortfolioIndexView(LoginRequiredMixin, TemplateView):
    template_name = "portfolio/manage/index.html"

    def get_context_data(self, **kwargs):
        studio = self.request.studio
        portfolio, _ = Portfolio.objects.get_or_create(studio=studio)
        category_count = PortfolioCategory.objects.filter(studio=studio).count()
        story_count = PortfolioStory.objects.filter(studio=studio).count()
        published_story_count = PortfolioStory.objects.filter(
            studio=studio, is_published=True
        ).count()
        public_url = portfolio.get_public_url()
        return super().get_context_data(
            portfolio=portfolio,
            category_count=category_count,
            story_count=story_count,
            published_story_count=published_story_count,
            public_url=public_url,
            **kwargs,
        )


class PortfolioProfileView(StudioUpdateView):
    model = Portfolio
    form_class = PortfolioForm
    page_title = _("Portfolio")
    back_label = _("Portfolio")
    submit_label = _("Save changes")
    success_url = reverse_lazy("portfolio:index")
    success_message = _("Portfolio saved.")

    def get_object(self, queryset=None):
        return Portfolio.objects.get_or_create(studio=self.request.studio)[0]

    def get_cancel_url(self):
        return reverse("portfolio:index")


# ---------------------------------------------------------------------------
# 2. Categories CRUD
# ---------------------------------------------------------------------------


class CategoryListView(StudioListView):
    model = PortfolioCategory
    template_name = "portfolio/manage/category_list.html"
    paginate_by = None

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(story_count=Count("stories"))
            .order_by("position", "name")
        )


class CategoryCreateView(StudioCreateView):
    model = PortfolioCategory
    form_class = CategoryForm
    page_title = _("New category")
    back_label = _("Categories")
    submit_label = _("Add category")
    success_url = reverse_lazy("portfolio:category_list")
    success_message = _("Category added.")

    def get_cancel_url(self):
        return reverse("portfolio:category_list")


class CategoryUpdateView(StudioUpdateView):
    model = PortfolioCategory
    form_class = CategoryForm
    page_title = _("Edit category")
    back_label = _("Categories")
    submit_label = _("Save changes")
    success_url = reverse_lazy("portfolio:category_list")
    success_message = _("Changes saved.")

    def get_delete_url(self):
        return reverse("portfolio:category_delete", args=[self.object.pk])

    def get_cancel_url(self):
        return reverse("portfolio:category_list")


class CategoryDeleteView(StudioDeleteView):
    model = PortfolioCategory
    success_url = reverse_lazy("portfolio:category_list")
    confirm_label = _("Delete category")

    @property
    def page_title(self):
        return _("Delete \u201c%(name)s\u201d?") % {"name": self.object.name}

    @property
    def lede(self):
        count = (
            self.object.story_count
            if hasattr(self.object, "story_count")
            else self.object.stories.count()
        )
        if count:
            return ngettext(
                "%(count)s story belongs to this category. "
                "Deleting the category will also delete its stories.",
                "%(count)s stories belong to this category. "
                "Deleting the category will also delete its stories.",
                count,
            ) % {"count": count}
        return _("The category will be permanently removed. This can't be undone.")

    @property
    def success_message(self):
        return _("\u201c%(name)s\u201d deleted.") % {"name": self.object.name}

    def get_cancel_url(self):
        return reverse("portfolio:category_list")


# ---------------------------------------------------------------------------
# 3. Stories CRUD & Photo Selection
# ---------------------------------------------------------------------------


class StoryListView(StudioListView):
    model = PortfolioStory
    template_name = "portfolio/manage/story_list.html"
    paginate_by = None

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("category", "cover_photo")
            .annotate(photo_count=Count("entries"))
            .order_by("position", "-story_date", "-created_at")
        )


class StoryCreateView(StudioCreateView):
    model = PortfolioStory
    form_class = StoryForm
    page_title = _("New story")
    back_label = _("Stories")
    submit_label = _("Add story")
    success_message = _("Story created.")

    def get_cancel_url(self):
        return reverse("portfolio:story_list")

    def get_success_url(self):
        return reverse("portfolio:story_photos", args=[self.object.pk])


class StoryUpdateView(StudioUpdateView):
    model = PortfolioStory
    form_class = StoryForm
    page_title = _("Edit story")
    back_label = _("Stories")
    submit_label = _("Save changes")
    success_url = reverse_lazy("portfolio:story_list")
    success_message = _("Changes saved.")

    def get_delete_url(self):
        return reverse("portfolio:story_delete", args=[self.object.pk])

    def get_cancel_url(self):
        return reverse("portfolio:story_list")


class StoryDeleteView(StudioDeleteView):
    model = PortfolioStory
    success_url = reverse_lazy("portfolio:story_list")
    confirm_label = _("Delete story")

    @property
    def page_title(self):
        return _("Delete \u201c%(title)s\u201d?") % {"title": self.object.title}

    @property
    def lede(self):
        return _("The story and all selections will be removed. This can't be undone.")

    @property
    def success_message(self):
        return _("\u201c%(title)s\u201d deleted.") % {"title": self.object.title}

    def get_cancel_url(self):
        return reverse("portfolio:story_list")


class StoryPhotosView(StudioScopedMixin, View):
    template_name = "portfolio/manage/story_photos.html"

    @staticmethod
    def allowed_photos(story):
        """Ready photos of the story's gallery. A story without a gallery offers none."""
        if not story.gallery_id:
            return Photo.objects.none()
        return Photo.objects.filter(
            studio=story.studio_id, gallery=story.gallery_id, status=Photo.Status.READY
        )

    def get(self, request, pk):
        story = get_object_or_404(PortfolioStory.objects.for_studio(request.studio), pk=pk)
        photos = self.allowed_photos(story).order_by("position", "id")

        selected_ids = set(story.entries.values_list("photo_id", flat=True))
        return render(
            request,
            self.template_name,
            {
                "story": story,
                "photos": photos,
                "available_photos": photos,
                "selected_ids": selected_ids,
            },
        )

    def post(self, request, pk):
        story = get_object_or_404(PortfolioStory.objects.for_studio(request.studio), pk=pk)
        raw_ids = request.POST.getlist("photos")

        allowed_qs = self.allowed_photos(story)

        valid_ids = [int(pid) for pid in raw_ids if pid.isdigit()]
        allowed_set = set(allowed_qs.filter(id__in=valid_ids).values_list("id", flat=True))

        chosen_ids = []
        seen = set()
        for pid in valid_ids:
            if pid in allowed_set and pid not in seen:
                seen.add(pid)
                chosen_ids.append(pid)

        with transaction.atomic():
            story.entries.all().delete()
            entries = [
                PortfolioStoryPhoto(story=story, photo_id=photo_id, position=index)
                for index, photo_id in enumerate(chosen_ids)
            ]
            PortfolioStoryPhoto.objects.bulk_create(entries)

            # The cover must be one of the story's photos; fall back to the first one.
            if story.cover_photo_id not in chosen_ids:
                story.cover_photo_id = chosen_ids[0] if chosen_ids else None
                story.save(update_fields=["cover_photo", "updated_at"])

        messages.success(request, _("Photos saved."))
        return HttpResponseRedirect(reverse("portfolio:story_list"))
