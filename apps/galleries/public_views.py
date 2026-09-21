"""The client-facing gallery. Phase 3b builds this out; for now it proves the link works."""

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Gallery


def gallery(request, token):
    gallery = get_object_or_404(Gallery.objects.select_related("studio"), token=token)
    if not gallery.is_published:
        raise Http404
    return render(request, "galleries/public/placeholder.html", {"gallery": gallery})
