"""Forms for the portfolio module: public page, categories and stories."""

from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.forms import DateInput, StudioModelForm

from .models import Portfolio, PortfolioCategory, PortfolioStory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ready_photos_qs(studio):
    """Return a Photo queryset limited to *ready* photos owned by *studio*."""
    from apps.photos.models import Photo  # local import - avoids circular deps

    return Photo.objects.filter(studio=studio, status=Photo.Status.READY).select_related("gallery")


def _photo_label(photo):
    """Human-readable label: 'Gallery name - original_name'."""
    return f"{photo.gallery} - {photo.original_name}"


def _configure_photo_field(field, studio, *, empty_label=None):
    """Apply studio-scoped queryset and a readable label to a ModelChoiceField."""
    field.queryset = _ready_photos_qs(studio)
    field.empty_label = empty_label if empty_label is not None else str(_("None"))
    field.label_from_instance = _photo_label


# ---------------------------------------------------------------------------
# PortfolioForm
# ---------------------------------------------------------------------------


class PortfolioForm(StudioModelForm):
    """Edit the studio's single public portfolio page."""

    layout = [
        (None, ["headline", "about"]),
        (
            _("Appearance"),
            ["portrait", "look"],
        ),
        (
            _("Contact and social"),
            ["instagram", "accept_inquiries"],
        ),
        (
            _("SEO"),
            ["seo_description"],
        ),
        (None, ["is_published"]),
    ]

    class Meta:
        model = Portfolio
        fields = [
            "is_published",
            "headline",
            "about",
            "portrait",
            "look",
            "instagram",
            "accept_inquiries",
            "seo_description",
        ]
        widgets = {
            "about": forms.Textarea(attrs={"rows": 5}),
            "seo_description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_photo_field(
            self.fields["portrait"],
            self.studio,
            empty_label=_("No portrait photo"),
        )
        self.fields["instagram"].assume_scheme = "https"
        self.fields["headline"].help_text = _(
            "One line under your name, e.g. \u201cWedding and portrait photography\u201d."
        )
        self.fields["seo_description"].help_text = _(
            "Shown by search engines under your name. Up to 160 characters."
        )


def _clean_unique_slug(form, source_field):
    """Fill an empty slug from `source_field` and keep it unique within the studio.

    The (studio, slug) constraint is not checked by the ModelForm because `studio` is not a form
    field, so without this a duplicate would reach the database as an IntegrityError.
    """
    cleaned = form.cleaned_data
    max_length = form._meta.model._meta.get_field("slug").max_length
    slug = slugify(cleaned.get("slug") or cleaned.get(source_field) or "")[:max_length].strip("-")
    if not slug:
        if source_field in cleaned:
            form.add_error("slug", _("Enter an address."))
        return
    cleaned["slug"] = slug
    taken = form._meta.model.objects.filter(studio=form.studio, slug=slug)
    if form.instance.pk:
        taken = taken.exclude(pk=form.instance.pk)
    if taken.exists():
        form.add_error("slug", _("You already use this address."))


# ---------------------------------------------------------------------------
# CategoryForm
# ---------------------------------------------------------------------------


class CategoryForm(StudioModelForm):
    """Create or edit a portfolio category (a section of the public page)."""

    layout = [
        (None, ["name", "slug"]),
        (None, ["description"]),
        (None, ["cover_photo"]),
        (None, ["position"]),
    ]

    class Meta:
        model = PortfolioCategory
        fields = ["name", "slug", "description", "cover_photo", "position"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_photo_field(
            self.fields["cover_photo"],
            self.studio,
            empty_label=_("No cover photo"),
        )
        self.fields["slug"].required = False
        self.fields["slug"].help_text = _(
            "Used in the URL, e.g. /weddings/. Leave empty to make it from the name."
        )
        self.fields["position"].help_text = _("Categories with a lower number appear first.")

    def clean(self):
        cleaned = super().clean()
        _clean_unique_slug(self, "name")
        return cleaned


# ---------------------------------------------------------------------------
# StoryForm
# ---------------------------------------------------------------------------


class StoryForm(StudioModelForm):
    """Create or edit a portfolio story (a curated set of photos with a short text)."""

    layout = [
        (None, ["category", "title", "slug"]),
        (
            _("Story"),
            ["intro", ("place", "story_date")],
        ),
        (
            _("Photos"),
            ["gallery", "cover_photo"],
        ),
        (
            _("Visibility"),
            [("is_published", "is_featured"), "position"],
        ),
    ]

    class Meta:
        model = PortfolioStory
        fields = [
            "category",
            "title",
            "slug",
            "intro",
            "place",
            "story_date",
            "gallery",
            "cover_photo",
            "is_published",
            "is_featured",
            "position",
        ]
        widgets = {
            "intro": forms.Textarea(attrs={"rows": 5}),
            "story_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Category - only this studio's categories
        self.fields["category"].queryset = PortfolioCategory.objects.filter(
            studio=self.studio
        ).order_by("position", "name")
        self.fields["category"].empty_label = None  # category is required

        # Gallery - only this studio's galleries, ordered by title
        from apps.galleries.models import Gallery  # local import - avoids circular deps

        self.fields["gallery"].queryset = Gallery.objects.filter(studio=self.studio).order_by(
            "shoot__title", "id"
        )
        self.fields["gallery"].empty_label = _("No gallery linked")
        self.fields["gallery"].help_text = _(
            "Link a gallery to pick photos from it on the next step."
        )

        # Cover photo - ready photos from this studio
        _configure_photo_field(
            self.fields["cover_photo"],
            self.studio,
            empty_label=_("No cover photo"),
        )

        self.fields["slug"].required = False
        self.fields["slug"].help_text = _("Used in the URL. Leave empty to make it from the title.")
        self.fields["position"].help_text = _(
            "Stories with a lower number appear first within the category."
        )
        self.fields["is_featured"].help_text = _(
            "Featured stories appear on the portfolio front page."
        )

    def clean(self):
        cleaned = super().clean()
        _clean_unique_slug(self, "title")
        return cleaned
