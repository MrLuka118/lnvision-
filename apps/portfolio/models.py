from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel


class Portfolio(TenantModel):
    """The studio's public page at /p/<studio slug>/. One per studio."""

    class Look(models.TextChoices):
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")

    is_published = models.BooleanField(_("published"), default=False)
    headline = models.CharField(
        _("headline"),
        max_length=160,
        blank=True,
        help_text=_(
            "One line under your name, e.g. “Wedding and portrait photography, Ljubljana”."
        ),
    )
    about = models.TextField(_("about you"), blank=True)
    portrait = models.ForeignKey(
        "photos.Photo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("portrait"),
    )
    look = models.CharField(_("look"), max_length=10, choices=Look.choices, default=Look.LIGHT)
    instagram = models.URLField(_("Instagram"), blank=True)
    accept_inquiries = models.BooleanField(_("show the inquiry form"), default=True)
    seo_description = models.CharField(
        _("search description"),
        max_length=160,
        blank=True,
        help_text=_("Shown by search engines under your name. Up to 160 characters."),
    )

    class Meta:
        verbose_name = _("portfolio")
        constraints = [models.UniqueConstraint(fields=["studio"], name="one_portfolio_per_studio")]

    def __str__(self):
        return str(self.studio)

    def get_public_url(self):
        return reverse("public_portfolio:home", args=[self.studio.slug])


class PortfolioCategory(TenantModel):
    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(_("address"), max_length=80)
    description = models.TextField(_("description"), blank=True)
    cover_photo = models.ForeignKey(
        "photos.Photo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("cover photo"),
    )
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(fields=["studio", "slug"], name="category_slug_per_studio")
        ]

    def __str__(self):
        return self.name

    def get_public_url(self):
        return reverse("public_portfolio:category", args=[self.studio.slug, self.slug])


class PortfolioStory(TenantModel):
    """A shoot told as a short story: a cover, a few lines, a sequence of chosen photos."""

    category = models.ForeignKey(
        PortfolioCategory,
        on_delete=models.CASCADE,
        related_name="stories",
        verbose_name=_("category"),
    )
    gallery = models.ForeignKey(
        "galleries.Gallery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
        verbose_name=_("photos from gallery"),
    )
    title = models.CharField(_("title"), max_length=160)
    slug = models.SlugField(_("address"), max_length=160)
    intro = models.TextField(_("story"), blank=True)
    place = models.CharField(_("place"), max_length=120, blank=True)
    story_date = models.DateField(_("date"), null=True, blank=True)
    cover_photo = models.ForeignKey(
        "photos.Photo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("cover photo"),
    )
    photos = models.ManyToManyField(
        "photos.Photo", through="PortfolioStoryPhoto", related_name="stories", blank=True
    )
    is_published = models.BooleanField(_("published"), default=False)
    is_featured = models.BooleanField(_("show on the front page"), default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("story")
        verbose_name_plural = _("stories")
        ordering = ["position", "-story_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["studio", "slug"], name="story_slug_per_studio")
        ]

    def __str__(self):
        return self.title

    def get_public_url(self):
        return reverse(
            "public_portfolio:story", args=[self.studio.slug, self.category.slug, self.slug]
        )


class PortfolioStoryPhoto(models.Model):
    story = models.ForeignKey(PortfolioStory, on_delete=models.CASCADE, related_name="entries")
    photo = models.ForeignKey("photos.Photo", on_delete=models.CASCADE, related_name="+")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["story", "photo"], name="photo_once_per_story")
        ]

    def __str__(self):
        return f"Photo {self.photo.id}"


class Inquiry(TenantModel):
    """A message from the public portfolio. It also becomes a client, a shoot and a date."""

    name = models.CharField(_("name"), max_length=120)
    email = models.EmailField(_("email"))
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    desired_date = models.DateField(_("preferred date"), null=True, blank=True)
    package = models.ForeignKey(
        "shoots.Package",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("package"),
    )
    message = models.TextField(_("message"), max_length=4000)
    client = models.ForeignKey(
        "clients.Client", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    shoot = models.ForeignKey(
        "shoots.Shoot", on_delete=models.SET_NULL, null=True, blank=True, related_name="inquiries"
    )
    ip_hash = models.CharField(max_length=16, blank=True)

    class Meta:
        verbose_name = _("inquiry")
        verbose_name_plural = _("inquiries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"
