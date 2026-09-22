"""The studio's public portfolio at /p/<studio slug>/. Indexable, unlike client galleries."""

from django.db.models import Prefetch
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.core import is_ratelimited

from apps.core.models import Studio
from apps.galleries.analytics import ip_hash
from apps.galleries.layouts import photobook_rows

from .models import Portfolio, PortfolioCategory, PortfolioStory, PortfolioStoryPhoto
from .public_forms import InquiryForm
from .services import create_inquiry


def _load(request, studio_slug):
    studio = get_object_or_404(Studio, slug=studio_slug)
    portfolio = Portfolio.objects.filter(studio=studio).select_related("portrait", "studio").first()
    owner = getattr(request, "studio", None) == studio
    if portfolio is None or (not portfolio.is_published and not owner):
        raise Http404
    return studio, portfolio, owner


def _base_context(studio, portfolio, owner):
    categories = list(
        PortfolioCategory.objects.for_studio(studio)
        .filter(stories__is_published=True)
        .select_related("cover_photo", "studio")  # studio: for get_public_url
        .distinct()
        .order_by("position", "name")
    )
    return {
        "studio": studio,
        "portfolio": portfolio,
        "categories": categories,
        "preview": owner and not portfolio.is_published,
        "theme": portfolio.look,  # the photographer's look, not the visitor's app setting
    }


def _published_stories(studio, owner):
    stories = PortfolioStory.objects.for_studio(studio).select_related(
        "category", "cover_photo", "studio"
    )
    return stories if owner else stories.filter(is_published=True)


def _home_context(request, studio, portfolio, owner, form=None):
    context = _base_context(studio, portfolio, owner)
    stories = list(_published_stories(studio, owner).filter(is_published=True)[:24])
    featured = [s for s in stories if s.is_featured] or stories[:6]
    hero = next((s for s in featured if s.cover_photo_id), None)
    if len(featured) > 3:  # enough to go round: don't show the hero's photo twice in a row
        featured = [s for s in featured if s != hero]
    context.update(
        stories=featured,
        hero=hero,
        form=form or (InquiryForm(studio=studio) if portfolio.accept_inquiries else None),
        thanks=request.GET.get("hvala") == "1",
    )
    return context


@require_GET
def home(request, studio_slug):
    studio, portfolio, owner = _load(request, studio_slug)
    context = _home_context(request, studio, portfolio, owner)
    return render(request, "portfolio/public/home.html", context)


@require_GET
def category(request, studio_slug, category_slug):
    studio, portfolio, owner = _load(request, studio_slug)
    current = get_object_or_404(PortfolioCategory.objects.for_studio(studio), slug=category_slug)
    context = _base_context(studio, portfolio, owner)
    context.update(
        category=current,
        stories=list(_published_stories(studio, owner).filter(category=current)),
    )
    return render(request, "portfolio/public/category.html", context)


@require_GET
def story(request, studio_slug, category_slug, story_slug):
    studio, portfolio, owner = _load(request, studio_slug)
    entries = PortfolioStoryPhoto.objects.select_related("photo").order_by("position", "id")
    current = get_object_or_404(
        _published_stories(studio, owner).prefetch_related(Prefetch("entries", queryset=entries)),
        slug=story_slug,
        category__slug=category_slug,
    )
    photos = [e.photo for e in current.entries.all() if e.photo.is_ready]
    siblings = list(_published_stories(studio, owner).filter(category=current.category))
    index = next((i for i, s in enumerate(siblings) if s.pk == current.pk), 0)
    context = _base_context(studio, portfolio, owner)
    context.update(
        story=current,
        rows=photobook_rows(photos),
        previous_story=siblings[index - 1] if index > 0 else None,
        next_story=siblings[index + 1] if index + 1 < len(siblings) else None,
    )
    return render(request, "portfolio/public/story.html", context)


@require_POST
def inquiry(request, studio_slug):
    studio, portfolio, owner = _load(request, studio_slug)
    if not portfolio.accept_inquiries:
        raise Http404
    form = InquiryForm(request.POST, studio=studio)
    limited = is_ratelimited(
        request,
        group="portfolio-inquiry",
        key=lambda _g, r: f"{r.META.get('REMOTE_ADDR', '')}:{studio.pk}",
        rate="5/h",
        method="POST",
        increment=True,
    )
    if limited:
        form.add_error(
            None, _("Too many messages from here. Try again in an hour, or write by e-mail.")
        )
    elif form.is_valid():
        create_inquiry(studio, form.cleaned_data, ip_hash=ip_hash(request))
        if request.htmx:
            return render(request, "portfolio/public/_inquiry_thanks.html", {"studio": studio})
        return HttpResponseRedirect(
            reverse("public_portfolio:home", args=[studio.slug]) + "?hvala=1#povprasevanje"
        )
    if request.htmx:
        context = {"studio": studio, "portfolio": portfolio, "form": form}
        return render(request, "portfolio/public/_inquiry_form.html", context)
    context = _home_context(request, studio, portfolio, owner, form=form)
    return render(request, "portfolio/public/home.html", context, status=400)
