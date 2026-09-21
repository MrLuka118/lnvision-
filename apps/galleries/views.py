import json
from pathlib import PurePosixPath

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views import View

from apps.core.generic import (
    StudioCreateView,
    StudioDeleteView,
    StudioDetailView,
    StudioListView,
    StudioUpdateView,
)
from apps.core.mixins import StudioScopedMixin
from apps.photos.models import Photo
from apps.photos.tasks import process_photo
from apps.shoots.models import Shoot

from .forms import GalleryCreateForm, GallerySettingsForm, SectionForm
from .models import Favorite, Gallery, GalleryEvent, PhotoComment
from .tasks import send_gallery_link


class GalleryListView(StudioListView):
    model = Gallery
    template_name = "galleries/list.html"
    paginate_by = 24

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("client", "cover_photo")
            .annotate(photo_count=Count("photos"))
            .order_by("-created_at")
        )


class GalleryCreateView(StudioCreateView):
    model = Gallery
    form_class = GalleryCreateForm
    page_title = _("New gallery")
    submit_label = _("Create gallery")
    back_label = _("Galleries")
    success_message = _("Gallery created. Add the photos.")

    def get_initial(self):
        initial = super().get_initial()
        shoot_id = self.request.GET.get("shoot", "")
        if shoot_id.isdigit():
            shoot = (
                Shoot.objects.for_studio(self.request.studio)
                .with_dates()
                .filter(pk=shoot_id)
                .first()
            )
            if shoot:
                initial.update(shoot=shoot, client=shoot.client, title=shoot.title)
                if shoot.starts_at:
                    initial["event_date"] = timezone.localdate(shoot.starts_at)
        return initial

    def get_cancel_url(self):
        return reverse("galleries:list")

    def get_success_url(self):
        return self.object.get_absolute_url()


class GalleryEditorView(StudioDetailView):
    model = Gallery
    template_name = "galleries/editor.html"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "shoot", "cover_photo")

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == "photo-grid":
            return ["galleries/_photo_grid.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        gallery = self.object
        photos = list(gallery.photos.select_related("section"))
        sections = list(gallery.sections.all())
        counts = {
            "total": len(photos),
            "ready": sum(p.status == Photo.Status.READY for p in photos),
            "failed": sum(p.status == Photo.Status.FAILED for p in photos),
        }
        counts["busy"] = counts["total"] - counts["ready"] - counts["failed"]
        grouped = [
            {"section": s, "photos": [p for p in photos if p.section_id == s.pk]} for s in sections
        ]
        loose = [p for p in photos if p.section_id is None]
        activity_data = activity(gallery)
        return super().get_context_data(
            activity=activity_data,
            groups=[{"section": None, "photos": loose}, *grouped],
            sections=sections,
            counts=counts,
            public_url=self.request.build_absolute_uri(gallery.get_public_url()),
            section_form=SectionForm(studio=self.request.studio),
            **kwargs,
        )


def activity(gallery):
    """What clients did: selections per person, notes, and a few counts."""
    events = gallery.events.values("kind").annotate(n=Count("id"))
    counts = {row["kind"]: row["n"] for row in events}
    visitors = list(
        gallery.visitors.filter(favorites__isnull=False)
        .distinct()
        .prefetch_related(
            Prefetch(
                "favorites",
                queryset=Favorite.objects.select_related("photo").order_by("photo__position"),
            )
        )
    )
    for visitor in visitors:
        visitor.picked = [f.photo for f in visitor.favorites.all()]
        visitor.filenames = ", ".join(PurePosixPath(p.original_name).stem for p in visitor.picked)
    comments = list(gallery.comments.select_related("visitor", "photo")[:50])
    unread = [c.pk for c in comments if c.read_at is None]
    if unread:
        PhotoComment.objects.filter(pk__in=unread).update(read_at=timezone.now())
    for comment in comments:
        comment.is_new = comment.pk in unread
    return {
        "views": counts.get(GalleryEvent.Kind.VIEW, 0),
        "visitors": gallery.events.filter(kind=GalleryEvent.Kind.VIEW)
        .values("ip_hash")
        .distinct()
        .count(),
        "downloads": counts.get(GalleryEvent.Kind.DOWNLOAD_PHOTO, 0)
        + counts.get(GalleryEvent.Kind.DOWNLOAD_ZIP, 0),
        "selections": visitors,
        "comments": comments,
    }


class GallerySettingsView(StudioUpdateView):
    model = Gallery
    form_class = GallerySettingsForm
    template_name = "generic/form.html"
    page_title = _("Gallery settings")
    submit_label = _("Save settings")
    success_message = _("Settings saved.")

    @property
    def back_label(self):
        return self.object.title

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_delete_url(self):
        return reverse("galleries:delete", args=[self.object.pk])


class GalleryDeleteView(StudioDeleteView):
    model = Gallery
    success_url = reverse_lazy("galleries:list")
    confirm_label = _("Delete gallery")

    @property
    def page_title(self):
        return _("Delete “%(title)s”?") % {"title": self.object.title}

    @property
    def lede(self):
        count = self.object.photos.count()
        return ngettext(
            "%(count)s photo, its original and every favourite and comment are removed. "
            "The client link stops working immediately. This can't be undone.",
            "%(count)s photos, their originals and every favourite and comment are removed. "
            "The client link stops working immediately. This can't be undone.",
            count,
        ) % {"count": count}

    @property
    def success_message(self):
        return _("“%(title)s” deleted.") % {"title": self.object.title}


class GalleryActionView(StudioScopedMixin, View):
    """Small POST actions from the editor: publish, hide, new link."""

    http_method_names = ["post"]

    def post(self, request, pk, action):
        gallery = get_object_or_404(Gallery.objects.for_studio(request.studio), pk=pk)
        if action == "publish":
            gallery.is_published = True
            gallery.published_at = gallery.published_at or timezone.now()
            messages.success(request, _("Published. The link works now."))
        elif action == "hide":
            gallery.is_published = False
            messages.success(request, _("Hidden. The link shows a note until you publish again."))
        elif action == "send":
            if not (gallery.is_live and gallery.client and gallery.client.email):
                return HttpResponse(status=400)
            transaction.on_commit(lambda: send_gallery_link.delay(gallery.pk))
            messages.success(
                request,
                _("Link sent to %(email)s.") % {"email": gallery.client.email},
            )
            return HttpResponseRedirect(gallery.get_absolute_url())
        elif action == "new-link":
            gallery.rotate_token()
            messages.success(request, _("New link created. The old link no longer works."))
        else:
            return HttpResponse(status=400)
        gallery.save()
        return HttpResponseRedirect(gallery.get_absolute_url())


class PhotoActionView(StudioScopedMixin, View):
    """Per-photo actions from the editor grid: cover, move to section, delete."""

    http_method_names = ["post"]

    def post(self, request, pk, photo_pk, action):
        gallery = get_object_or_404(Gallery.objects.for_studio(request.studio), pk=pk)
        photo = get_object_or_404(gallery.photos, pk=photo_pk)
        if action == "cover":
            gallery.cover_photo = photo
            gallery.save(update_fields=["cover_photo", "updated_at"])
        elif action == "move":
            section_id = request.POST.get("section", "")
            photo.section = (
                gallery.sections.filter(pk=section_id).first() if section_id.isdigit() else None
            )
            photo.save(update_fields=["section", "updated_at"])
        elif action == "delete":
            photo.delete()  # files follow via the post_delete signal
        elif action == "retry":
            Photo.objects.filter(pk=photo.pk).update(status=Photo.Status.PENDING, error="")
            transaction.on_commit(lambda: process_photo.delay(photo.pk))
        else:
            return HttpResponse(status=400)
        if request.htmx:
            return HttpResponse(status=204, headers={"HX-Trigger": json.dumps({"grid:refresh": 1})})
        return HttpResponseRedirect(gallery.get_absolute_url())


class SectionCreateView(StudioScopedMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        gallery = get_object_or_404(Gallery.objects.for_studio(request.studio), pk=pk)
        form = SectionForm(request.POST, studio=request.studio)
        if form.is_valid():
            section = form.save(commit=False)
            section.studio = request.studio
            section.gallery = gallery
            section.position = gallery.sections.count()
            section.save()
        return HttpResponseRedirect(gallery.get_absolute_url())


class SectionDeleteView(StudioScopedMixin, View):
    """Removes the chapter; its photos stay in the gallery, outside any section."""

    http_method_names = ["post"]

    def post(self, request, pk, section_pk):
        gallery = get_object_or_404(Gallery.objects.for_studio(request.studio), pk=pk)
        get_object_or_404(gallery.sections, pk=section_pk).delete()
        return HttpResponseRedirect(gallery.get_absolute_url())
