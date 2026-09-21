"""Who may see a gallery, and who they are. The link's token is the only key to it."""

from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Gallery, GalleryVisitor

SESSION_KEY = "gallery_access"
VISITOR_SALT = "gallery-visitor"
VISITOR_MAX_AGE = 60 * 60 * 24 * 365

OK, EXPIRED, LOCKED = "ok", "expired", "locked"


def load(token: str) -> Gallery:
    return get_object_or_404(
        Gallery.objects.select_related("studio", "cover_photo", "client"), token=token
    )


def is_owner(request, gallery: Gallery) -> bool:
    studio = getattr(request, "studio", None)
    return studio is not None and studio.pk == gallery.studio_id


def state(request, gallery: Gallery) -> str:
    """OK, EXPIRED or LOCKED; unpublished galleries don't exist for anyone but their owner."""
    owner = is_owner(request, gallery)
    if not gallery.is_published and not owner:
        raise Http404
    if owner:
        return OK
    if gallery.is_expired:
        return EXPIRED
    if gallery.has_password and not is_unlocked(request, gallery):
        return LOCKED
    return OK


def is_unlocked(request, gallery: Gallery) -> bool:
    unlocked = request.session.get(SESSION_KEY, {})
    return unlocked.get(str(gallery.pk)) == gallery.password_version


def unlock(request, gallery: Gallery):
    request.session.cycle_key()  # a new session id after the password, against fixation
    unlocked = request.session.get(SESSION_KEY, {})
    unlocked[str(gallery.pk)] = gallery.password_version
    request.session[SESSION_KEY] = unlocked


def cookie_name(gallery: Gallery) -> str:
    return f"gv{gallery.pk}"


def get_visitor(request, gallery: Gallery, create: bool = False) -> GalleryVisitor | None:
    key = request.get_signed_cookie(cookie_name(gallery), default=None, salt=VISITOR_SALT)
    visitor = GalleryVisitor.objects.filter(gallery=gallery, key=key).first() if key else None
    if visitor is None and create:
        visitor = GalleryVisitor.objects.create(studio_id=gallery.studio_id, gallery=gallery)
    elif visitor is not None and timezone.now() - visitor.last_seen > timedelta(hours=1):
        GalleryVisitor.objects.filter(pk=visitor.pk).update(last_seen=timezone.now())
    return visitor


def remember_visitor(response, gallery: Gallery, visitor: GalleryVisitor):
    response.set_signed_cookie(
        cookie_name(gallery),
        visitor.key,
        salt=VISITOR_SALT,
        max_age=VISITOR_MAX_AGE,
        path=gallery.get_public_url(),
        httponly=True,
        samesite="Lax",
        secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
    )
    return response
