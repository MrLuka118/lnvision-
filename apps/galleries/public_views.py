"""The client-facing gallery at /g/<token>/. Nothing here needs an account; the token is the key."""

import json
from datetime import timedelta
from pathlib import PurePosixPath

from django.core.files.storage import storages
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.core import is_ratelimited

from apps.core.colour import accessible_accent, text_on
from apps.photos.delivery import file_response
from apps.photos.models import Photo, rendition_key

from . import access, analytics
from .layouts import group_by_section, photobook_rows
from .models import DownloadRequest, Favorite, Gallery, GalleryEvent, PhotoComment
from .tasks import SIGNER_SALT, ZIP_DAYS, build_zip, fingerprint, photos_for_zip, zip_link

DARK_THEMES = {Gallery.Theme.DARKROOM, Gallery.Theme.CONTACT_SHEET}
SURROUND = {"dark": "#262626", "light": "#f4f4f4"}


def _limited(request, group, rate):
    token = request.resolver_match.kwargs.get("token", "")
    return is_ratelimited(
        request,
        group=group,
        key=lambda _g, r: f"{r.META.get('REMOTE_ADDR', '')}:{token}",
        rate=rate,
        method="POST",
        increment=True,
    )


def _noindex(response):
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "private, no-store"
    return response


def _page_context(gallery):
    mode = "dark" if gallery.theme in DARK_THEMES else "light"
    base = gallery.studio.accent_colour
    accent = accessible_accent(base or "#9a9a9a", SURROUND[mode], minimum=4.5)
    # "theme" overrides the visitor's app setting: the photographer chose this gallery's look.
    return {"gallery": gallery, "studio": gallery.studio, "mode": mode, "theme": mode,
            "accent": accent, "on_accent": text_on(accent)}  # fmt: skip


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _allowed(request, token):
    """The gallery if the visitor may use it right now, else raise 404/403-style responses."""
    gallery = access.load(token)
    if access.state(request, gallery) != access.OK:
        raise Http404
    return gallery


# --- pages ---------------------------------------------------------------------------------


@require_GET
def gallery(request, token):
    gallery = access.load(token)
    state = access.state(request, gallery)
    context = _page_context(gallery)
    if state == access.EXPIRED:
        return _noindex(render(request, "galleries/public/unavailable.html", context, status=410))
    if state == access.LOCKED:
        return _noindex(render(request, "galleries/public/password.html", context))

    owner = access.is_owner(request, gallery)
    visitor = access.get_visitor(request, gallery, create=not owner)
    seen_key = f"gallery_seen_{gallery.pk}"
    if not request.session.get(seen_key):
        analytics.record(request, gallery, GalleryEvent.Kind.VIEW, visitor=visitor, owner=owner)
        request.session[seen_key] = True

    photos = list(
        gallery.photos.filter(status=Photo.Status.READY)
        .select_related("section")
        .order_by("position", "pk")
    )
    groups = group_by_section(photos, list(gallery.sections.all()))
    if gallery.theme == Gallery.Theme.PHOTOBOOK:
        for group in groups:
            group["rows"] = photobook_rows(group["photos"])
    for number, photo in enumerate(photos, start=1):
        photo.frame = number  # contact-sheet frame numbers
    favorites = set(visitor.favorites.values_list("photo_id", flat=True)) if visitor else set()
    context.update(
        groups=groups,
        photo_count=len(photos),
        favorite_ids=favorites,
        visitor=visitor,
        preview=owner and not gallery.is_live,
        owner=owner,
        open_photo=request.GET.get("foto", ""),
    )
    context["gallery_config"] = _client_config(gallery, visitor, request.GET.get("foto", ""))
    response = render(request, "galleries/public/gallery.html", context)
    if visitor:
        access.remember_visitor(response, gallery, visitor)
    return _noindex(response)


PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000000"


def _client_config(gallery, visitor, open_photo):
    """Everything static/js/gallery.js needs, as JSON (json_script escapes it safely)."""
    token = gallery.token
    photo_url = lambda name: reverse(f"public_gallery:{name}", args=[token, PLACEHOLDER_UUID])  # noqa: E731
    return {
        "urls": {
            "favorite": photo_url("favorite"),
            "seen": photo_url("seen"),
            "download": photo_url("download"),
            "identify": reverse("public_gallery:identify", args=[token]),
            "comment": reverse("public_gallery:comment", args=[token]),
            "zip": reverse("public_gallery:zip_request", args=[token]),
        },
        "placeholder": PLACEHOLDER_UUID,
        "sprite": static("icons/sprite.svg"),
        "open": open_photo,
        "known": bool(visitor and visitor.is_known),
        "favorites": gallery.allow_favorites,
        "comments": gallery.allow_comments,
        "web": gallery.allows_web_downloads,
        "original": gallery.allows_original_downloads,
        "labels": {
            "favorite": _("Favourite"),
            "comment": _("Leave a note"),
            "download": _("Download"),
            "downloadOriginal": _("Download original"),
            "close": _("Close"),
            "next": _("Next"),
            "previous": _("Previous"),
            "preparing": _(
                "Preparing your ZIP. You can close this; the link also arrives by e-mail."
            ),
            "ready": _("Ready."),
            "failed": _("Something went wrong. Try again in a moment."),
            "sent": _("Sent. Thank you."),
        },
    }


@require_POST
def unlock(request, token):
    gallery = access.load(token)
    context = _page_context(gallery)
    if _limited(request, "gallery-password-minute", "5/m") or _limited(
        request, "gallery-password-hour", "30/h"
    ):
        context["error"] = _("Too many attempts. Wait a few minutes and try again.")
        return _noindex(render(request, "galleries/public/password.html", context, status=429))
    if gallery.is_live and gallery.check_password(request.POST.get("password", "")):
        access.unlock(request, gallery)
        return redirect(gallery.get_public_url())
    context["error"] = _("That password doesn't match. Check with your photographer.")
    return _noindex(render(request, "galleries/public/password.html", context, status=400))


# --- interactions (JSON) -------------------------------------------------------------------


@require_POST
def identify(request, token):
    """Name (and e-mail) so the photographer knows whose favourites these are."""
    gallery = _allowed(request, token)
    data = _json_body(request)
    name = str(data.get("name", "")).strip()[:120]
    email = str(data.get("email", "")).strip()[:254]
    if not name:
        return JsonResponse({"error": _("Add your name.")}, status=400)
    visitor = access.get_visitor(request, gallery, create=True)
    visitor.name, visitor.email = name, email
    visitor.save(update_fields=["name", "email", "updated_at"])
    return access.remember_visitor(JsonResponse({"name": visitor.name}), gallery, visitor)


@require_POST
def favorite(request, token, photo_uuid):
    gallery = _allowed(request, token)
    if not gallery.allow_favorites:
        raise Http404
    photo = get_object_or_404(gallery.photos, uuid=photo_uuid, status=Photo.Status.READY)
    visitor = access.get_visitor(request, gallery)
    if visitor is None or not visitor.is_known:
        return JsonResponse({"needsName": True}, status=403)
    existing = Favorite.objects.filter(visitor=visitor, photo=photo)
    if existing.exists():
        existing.delete()
        favorited = False
    else:
        Favorite.objects.get_or_create(studio_id=gallery.studio_id, visitor=visitor, photo=photo)
        analytics.record(request, gallery, GalleryEvent.Kind.FAVORITE, visitor, photo)
        favorited = True
    return JsonResponse({"favorite": favorited, "count": visitor.favorites.count()})


@require_POST
def comment(request, token):
    gallery = _allowed(request, token)
    if not gallery.allow_comments:
        raise Http404
    if _limited(request, "gallery-comment", "20/h"):
        return JsonResponse({"error": _("Too many comments. Try again later.")}, status=429)
    data = _json_body(request)
    body = str(data.get("body", "")).strip()[:2000]
    if not body:
        return JsonResponse({"error": _("Write something first.")}, status=400)
    visitor = access.get_visitor(request, gallery)
    if visitor is None or not visitor.is_known:
        return JsonResponse({"needsName": True}, status=403)
    photo = None
    if data.get("photo"):
        photo = gallery.photos.filter(uuid=data["photo"]).first()
    PhotoComment.objects.create(
        studio_id=gallery.studio_id, gallery=gallery, visitor=visitor, photo=photo, body=body
    )
    analytics.record(request, gallery, GalleryEvent.Kind.COMMENT, visitor, photo)
    return JsonResponse({"ok": True}, status=201)


@require_POST
def seen(request, token, photo_uuid):
    """Lightbox beacon: a photo was opened (once per photo per page load, client-side)."""
    gallery = _allowed(request, token)
    photo = gallery.photos.filter(uuid=photo_uuid).first()
    if photo:
        visitor = access.get_visitor(request, gallery)
        owner = access.is_owner(request, gallery)
        analytics.record(request, gallery, GalleryEvent.Kind.PHOTO_VIEW, visitor, photo, owner)
    return HttpResponse(status=204 if photo else 404)


# --- downloads -----------------------------------------------------------------------------


@require_GET
def download_photo(request, token, photo_uuid):
    gallery = _allowed(request, token)
    photo = get_object_or_404(gallery.photos, uuid=photo_uuid, status=Photo.Status.READY)
    size = request.GET.get("velikost", "web")
    stem = PurePosixPath(photo.original_name).stem or str(photo.uuid)
    if size == "original" and gallery.allows_original_downloads:
        storage, key, filename = photo.original.storage, photo.original.name, photo.original_name
    elif size == "web" and gallery.allows_web_downloads:
        width = photo.renditions["widths"][-1]
        storage = storages["renditions"]
        key = rendition_key(photo.uuid, photo.rendition_version, width, "jpg")
        filename = f"{stem}.jpg"
    else:
        raise Http404
    visitor = access.get_visitor(request, gallery)
    owner = access.is_owner(request, gallery)
    analytics.record(request, gallery, GalleryEvent.Kind.DOWNLOAD_PHOTO, visitor, photo, owner)
    return file_response(storage, key, filename)


@require_POST
def request_zip(request, token):
    gallery = _allowed(request, token)
    data = _json_body(request)
    size = data.get("size", "web")
    allowed = (size == "web" and gallery.allows_web_downloads) or (
        size == "original" and gallery.allows_original_downloads
    )
    if not allowed:
        raise Http404
    if _limited(request, "gallery-zip", "6/h"):
        return JsonResponse({"error": _("Too many requests. Try again in an hour.")}, status=429)
    visitor = access.get_visitor(request, gallery, create=True)
    email = str(data.get("email", "") or visitor.email).strip()[:254]

    # The same photos in the same size were packed recently: hand that one out again.
    current = fingerprint(photos_for_zip(gallery), size)
    ready = (
        DownloadRequest.objects.filter(
            gallery=gallery,
            size=size,
            fingerprint=current,
            status=DownloadRequest.Status.READY,
            expires_at__gt=timezone.now() + timedelta(days=1),
        )
        .exclude(file="")
        .first()
    )
    if ready:
        return JsonResponse({"status": "ready", "url": zip_link(ready.pk)})

    req = DownloadRequest.objects.create(
        studio_id=gallery.studio_id, gallery=gallery, visitor=visitor, size=size, email=email
    )
    transaction.on_commit(lambda: build_zip.delay(req.pk))
    return JsonResponse(
        {"status": req.status, "statusUrl": _zip_status_url(gallery, req)}, status=202
    )


def _zip_status_url(gallery, req):
    return reverse("public_gallery:zip_status", args=[gallery.token, req.pk])


@require_GET
def zip_status(request, token, pk):
    gallery = _allowed(request, token)
    req = get_object_or_404(DownloadRequest, gallery=gallery, pk=pk)
    visitor = access.get_visitor(request, gallery)
    if req.visitor_id and (visitor is None or visitor.pk != req.visitor_id):
        raise Http404
    data = {"status": req.status}
    if req.status == DownloadRequest.Status.READY:
        data["url"] = zip_link(req.pk)
    return JsonResponse(data)


@require_GET
def zip_file(request, signed):
    """The link from the e-mail. Signed and time-limited; no session needed."""
    try:
        pk = TimestampSigner(salt=SIGNER_SALT).unsign(signed, max_age=ZIP_DAYS * 24 * 3600)
    except (BadSignature, SignatureExpired) as exc:
        raise Http404 from exc
    req = get_object_or_404(
        DownloadRequest.objects.select_related("gallery"),
        pk=pk,
        status=DownloadRequest.Status.READY,
    )
    if not req.file or (req.expires_at and req.expires_at < timezone.now()):
        raise Http404
    gallery = req.gallery
    if not gallery.is_live:
        raise Http404
    analytics.record(request, gallery, GalleryEvent.Kind.DOWNLOAD_ZIP, visitor=req.visitor)
    filename = f"{gallery.title}.zip".replace("/", "-")
    return file_response(req.file.storage, req.file.name, filename)
