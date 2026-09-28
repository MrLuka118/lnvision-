"""Chunked upload API used by static/js/uploader.js.

POST /galerije/<pk>/nalaganje/          {name, size, section?} -> session
GET  /nalaganje/<uuid>/                 -> {received} (to resume)
PUT  /nalaganje/<uuid>/  Upload-Offset  raw bytes -> {received[, photo]}
"""

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.galleries.models import Gallery, GallerySection

from . import services
from .imaging import UnreadableImage
from .models import Photo, UploadSession


def _error(message, status=400, **extra):
    return JsonResponse({"error": message, **extra}, status=status)


@login_required
@require_POST
def start_upload(request, gallery_pk):
    gallery = get_object_or_404(Gallery.objects.for_studio(request.studio), pk=gallery_pk)
    try:
        data = json.loads(request.body or b"{}")
        name = str(data.get("name", ""))[:255]
        size = int(data.get("size", 0))
    except (ValueError, TypeError):
        return _error(_("Invalid upload."))
    suffix = name[name.rfind(".") :].lower() if "." in name else ""
    if suffix not in services.ALLOWED_SUFFIXES:
        return _error(_("Only JPEG, PNG, TIFF, WebP and AVIF photos can be uploaded."))
    if not 0 < size <= services.max_upload_bytes():
        return _error(_("This file is too large."), status=413)
    section = None
    if data.get("section"):
        section = (
            GallerySection.objects.for_studio(request.studio)
            .filter(gallery=gallery, pk=data["section"])
            .first()
        )
    session = UploadSession.objects.create(
        studio=request.studio, gallery=gallery, section=section, filename=name, size_bytes=size
    )
    return JsonResponse(
        {
            "url": reverse("photos:upload_chunk", args=[session.uuid]),
            "chunkSize": services.CHUNK_SIZE,
            "received": 0,
        },
        status=201,
    )


@login_required
@require_http_methods(["GET", "PUT"])
def upload_chunk(request, uuid):
    if request.method == "GET":
        session = get_object_or_404(UploadSession.objects.for_studio(request.studio), uuid=uuid)
        return JsonResponse({"received": session.received_bytes, "status": session.status})

    with transaction.atomic():
        session = get_object_or_404(
            UploadSession.objects.for_studio(request.studio).select_for_update(), uuid=uuid
        )
        if session.status != UploadSession.Status.OPEN:
            return _error(_("This upload is already finished."), status=409)
        try:
            offset = int(request.headers.get("Upload-Offset", "-1"))
        except ValueError:
            offset = -1
        if offset != session.received_bytes:
            return _error("offset mismatch", status=409, received=session.received_bytes)

        remaining = session.size_bytes - session.received_bytes
        limit = min(services.CHUNK_SIZE, remaining)
        written = 0
        with services.partial_path(session).open("ab") as fh:
            while True:
                block = request.read(min(1024 * 1024, limit - written + 1))
                if not block:
                    break
                written += len(block)
                if written > limit:
                    fh.truncate(session.received_bytes)
                    return _error(_("The upload sent more data than announced."), status=413)
                fh.write(block)
        session.received_bytes += written
        session.save(update_fields=["received_bytes", "updated_at"])

    if session.received_bytes < session.size_bytes:
        return JsonResponse({"received": session.received_bytes})
    try:
        photo = services.finalize(session)
    except UnreadableImage:
        return _error(_("This file isn't a photo we can read."), status=422)
    return JsonResponse(
        {"received": session.received_bytes, "photo": {"id": photo.pk, "status": photo.status}}
    )


@login_required
@require_http_methods(["GET"])
def photo_detail(request, uuid):
    photo = get_object_or_404(
        Photo.objects.for_studio(request.studio).select_related("gallery"), uuid=uuid
    )
    return render(request, "photos/detail.html", {"photo": photo})
