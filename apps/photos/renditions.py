"""Expiring rendition capabilities; storage keys are never published to a browser."""

from django.core import signing
from django.core.files.storage import storages
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from apps.galleries import access
from apps.portfolio.models import Portfolio, PortfolioCategory, PortfolioStory

from .models import Photo, rendition_key

MAX_AGE = 3600


def is_public_portfolio_photo(photo):
    if not Portfolio.objects.for_studio(photo.studio_id).filter(is_published=True).exists():
        return False
    return (
        Portfolio.objects.for_studio(photo.studio_id)
        .filter(portrait=photo, is_published=True)
        .exists()
        or PortfolioCategory.objects.for_studio(photo.studio_id).filter(cover_photo=photo).exists()
        or PortfolioStory.objects.for_studio(photo.studio_id)
        .filter(is_published=True)
        .filter(Q(photos=photo) | Q(cover_photo=photo))
        .exists()
    )


@require_GET
def rendition(request, signed):
    try:
        uuid, version, width, fmt = signing.loads(signed, salt="photo-rendition", max_age=MAX_AGE)
    except (signing.BadSignature, ValueError, TypeError) as exc:
        raise Http404 from exc
    photo = get_object_or_404(
        Photo.objects.select_related("gallery"),
        uuid=uuid,
        rendition_version=version,
        status=Photo.Status.READY,
    )
    if width not in photo.renditions.get("widths", []) or fmt not in photo.renditions.get(
        "formats", []
    ):
        raise Http404
    try:
        allowed = access.state(request, photo.gallery) == access.OK
    except Http404:
        allowed = False
    if not allowed and not is_public_portfolio_photo(photo):
        raise Http404
    storage = storages["renditions"]
    key = rendition_key(photo.uuid, version, width, fmt)
    if hasattr(storage, "bucket_name"):
        response = HttpResponseRedirect(storage.url(key, expire=600))
    else:
        try:
            response = FileResponse(
                storage.open(key, "rb"),
                content_type={"jpg": "image/jpeg", "webp": "image/webp", "avif": "image/avif"}[fmt],
            )
        except FileNotFoundError as exc:
            raise Http404 from exc
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex"
    return response


def deny_raw_rendition(request, path):
    raise Http404
