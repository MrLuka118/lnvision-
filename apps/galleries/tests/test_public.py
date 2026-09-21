"""The client-facing gallery: who gets in, what they can do, and what is recorded."""

import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path

import pytest
import pyvips
from django.core.cache import cache
from django.core.files import File
from django.test import Client as HttpClient
from django.urls import reverse
from django.utils import timezone

from apps.galleries.models import DownloadRequest, Favorite, GalleryEvent, GalleryVisitor
from apps.galleries.tests.factories import GalleryFactory, PhotoFactory
from apps.photos import services
from apps.photos.models import Photo

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()


@pytest.fixture
def gallery(studio):
    return GalleryFactory(studio=studio, is_published=True, published_at=timezone.now())


@pytest.fixture
def real_photo(gallery, tmp_path):
    """A processed photo with real rendition files, for downloads and ZIPs."""
    path = tmp_path / "DSC_0001.jpg"
    image = pyvips.Image.black(1200, 800, bands=3).linear([1, 1, 1], [90, 120, 150])
    image.cast("uchar").write_to_file(str(path))
    photo = Photo(studio=gallery.studio, gallery=gallery, original_name=path.name)
    with path.open("rb") as fh:
        photo.original.save(path.name, File(fh), save=False)
    photo.save()
    return services.process(photo)


def url(gallery, name="gallery", *args):
    return reverse(f"public_gallery:{name}", args=[gallery.token, *args])


def post_json(client, target, body=None):
    return client.post(target, data=json.dumps(body or {}), content_type="application/json")


def identify(client, gallery, name="Ana"):
    client.get(url(gallery))  # gets the visitor cookie
    return post_json(client, url(gallery, "identify"), {"name": name, "email": "ana@example.si"})


# --- access --------------------------------------------------------------------------------


def test_a_published_gallery_opens_with_its_link(client, gallery):
    PhotoFactory(studio=gallery.studio, gallery=gallery)
    response = client.get(url(gallery))
    assert response.status_code == 200
    assert response["X-Robots-Tag"] == "noindex, nofollow"
    assert response.context["theme"] == "dark"


def test_a_wrong_token_is_not_found(client, gallery):
    assert client.get(reverse("public_gallery:gallery", args=["x" * 43])).status_code == 404


def test_drafts_are_hidden_from_clients_but_previewable_by_the_owner(client, auth_client, studio):
    draft = GalleryFactory(studio=studio)
    assert client.get(url(draft)).status_code == 404
    response = auth_client.get(url(draft))
    assert response.status_code == 200
    assert response.context["preview"]


def test_another_photographer_cannot_preview_a_draft(studio, other_studio):
    draft = GalleryFactory(studio=studio)
    stranger = HttpClient()
    stranger.force_login(other_studio.owner)
    assert stranger.get(url(draft)).status_code == 404


def test_expired_gallery_says_so(client, gallery):
    gallery.expires_at = timezone.now() - timedelta(minutes=1)
    gallery.save()
    response = client.get(url(gallery))
    assert response.status_code == 410
    assert response.templates[0].name == "galleries/public/unavailable.html"


def test_password_gate(client, gallery):
    photo = PhotoFactory(studio=gallery.studio, gallery=gallery)
    gallery.set_password("poroka-2026")
    gallery.save()

    locked = client.get(url(gallery))
    assert locked.templates[0].name == "galleries/public/password.html"
    assert str(photo.uuid) not in locked.content.decode()  # no photo leaks past the gate

    wrong = client.post(url(gallery, "unlock"), {"password": "napačno"})
    assert wrong.status_code == 400
    right = client.post(url(gallery, "unlock"), {"password": "poroka-2026"})
    assert right.status_code == 302
    assert client.get(url(gallery)).templates[0].name == "galleries/public/gallery.html"


def test_changing_the_password_locks_everyone_out_again(client, gallery):
    gallery.set_password("prvo-geslo")
    gallery.save()
    client.post(url(gallery, "unlock"), {"password": "prvo-geslo"})
    gallery.set_password("drugo-geslo")
    gallery.save()
    assert client.get(url(gallery)).templates[0].name == "galleries/public/password.html"


def test_password_attempts_are_rate_limited(client, gallery):
    gallery.set_password("pravo-geslo")
    gallery.save()
    codes = [client.post(url(gallery, "unlock"), {"password": "x"}).status_code for _ in range(6)]
    assert codes[:5] == [400] * 5
    assert codes[5] == 429
    # Even the right password waits out the limit.
    assert client.post(url(gallery, "unlock"), {"password": "pravo-geslo"}).status_code == 429


def test_interactions_are_closed_behind_the_password(client, gallery):
    photo = PhotoFactory(studio=gallery.studio, gallery=gallery)
    gallery.set_password("geslo-1234")
    gallery.save()
    assert post_json(client, url(gallery, "identify"), {"name": "Ana"}).status_code == 404
    assert client.post(url(gallery, "favorite", photo.uuid)).status_code == 404
    assert client.get(url(gallery, "download", photo.uuid)).status_code == 404


def test_visitor_cookie_is_scoped_to_the_gallery(client, gallery):
    response = client.get(url(gallery))
    cookie = response.cookies[f"gv{gallery.pk}"]
    assert cookie["path"] == gallery.get_public_url()
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"


# --- favourites and notes ------------------------------------------------------------------


def test_favourites_need_a_name_first(client, gallery):
    photo = PhotoFactory(studio=gallery.studio, gallery=gallery)
    client.get(url(gallery))
    response = client.post(url(gallery, "favorite", photo.uuid))
    assert response.status_code == 403 and response.json()["needsName"]
    assert identify(client, gallery).status_code == 200
    first = client.post(url(gallery, "favorite", photo.uuid)).json()
    assert first == {"favorite": True, "count": 1}
    second = client.post(url(gallery, "favorite", photo.uuid)).json()
    assert second == {"favorite": False, "count": 0}


def test_photos_of_other_galleries_cannot_be_favourited(client, gallery, studio):
    elsewhere = PhotoFactory(studio=studio)
    identify(client, gallery)
    assert client.post(url(gallery, "favorite", elsewhere.uuid)).status_code == 404
    assert not Favorite.objects.exists()


def test_favourites_off_means_off(client, gallery):
    gallery.allow_favorites = False
    gallery.save()
    photo = PhotoFactory(studio=gallery.studio, gallery=gallery)
    identify(client, gallery)
    assert client.post(url(gallery, "favorite", photo.uuid)).status_code == 404


def test_notes_are_saved_with_their_photo(client, gallery):
    photo = PhotoFactory(studio=gallery.studio, gallery=gallery)
    identify(client, gallery)
    response = post_json(client, url(gallery, "comment"), {"body": "Ta!", "photo": str(photo.uuid)})
    assert response.status_code == 201
    comment = gallery.comments.get()
    assert comment.photo == photo and comment.visitor.name == "Ana"


def test_each_visit_counts_once_and_the_owner_never(client, auth_client, gallery):
    client.get(url(gallery))
    client.get(url(gallery))
    auth_client.get(url(gallery))
    assert GalleryEvent.objects.filter(kind=GalleryEvent.Kind.VIEW).count() == 1
    assert GalleryVisitor.objects.count() == 1


# --- downloads -----------------------------------------------------------------------------


def test_single_photo_download_in_web_size(client, gallery, real_photo):
    response = client.get(url(gallery, "download", real_photo.uuid), {"velikost": "web"})
    assert response.status_code == 200
    assert 'attachment; filename="DSC_0001.jpg"' in response["Content-Disposition"]
    assert GalleryEvent.objects.filter(kind=GalleryEvent.Kind.DOWNLOAD_PHOTO).exists()


def test_originals_only_when_the_photographer_allows_them(client, gallery, real_photo):
    target = url(gallery, "download", real_photo.uuid)
    assert client.get(target, {"velikost": "original"}).status_code == 404
    gallery.downloads = "none"
    gallery.save()
    assert client.get(target, {"velikost": "web"}).status_code == 404
    gallery.downloads = "both"
    gallery.save()
    assert client.get(target, {"velikost": "original"}).status_code == 200


def test_zip_is_built_and_downloaded_from_the_signed_link(
    client, gallery, real_photo, django_capture_on_commit_callbacks, mailoutbox
):
    client.get(url(gallery))
    with django_capture_on_commit_callbacks(execute=True):
        response = post_json(
            client, url(gallery, "zip_request"), {"size": "web", "email": "a@b.si"}
        )
    assert response.status_code == 202
    status = client.get(response.json()["statusUrl"]).json()
    assert status["status"] == "ready"
    zip_response = HttpClient().get(status["url"])  # works without the session, from the e-mail
    assert zip_response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(b"".join(zip_response.streaming_content)))
    assert archive.namelist() == ["DSC_0001.jpg"]
    assert len(mailoutbox) == 1 and status["url"] in mailoutbox[0].body

    # Asking again for the same photos reuses the ZIP.
    again = post_json(client, url(gallery, "zip_request"), {"size": "web"}).json()
    assert again["status"] == "ready"
    assert DownloadRequest.objects.count() == 1


def test_tampered_or_expired_zip_links_are_not_found(client, gallery):
    req = DownloadRequest.objects.create(
        studio=gallery.studio, gallery=gallery, status="ready", file="zips/x.zip"
    )
    from apps.galleries.tasks import zip_link

    good = zip_link(req.pk)
    assert client.get(good[:-3] + "abc/").status_code == 404
    req.expires_at = timezone.now() - timedelta(minutes=1)
    req.save()
    assert client.get(good).status_code == 404


def test_zip_of_originals_needs_permission(client, gallery):
    assert post_json(client, url(gallery, "zip_request"), {"size": "original"}).status_code == 404


@pytest.mark.parametrize("size", ["web", "original"])
def test_uploaded_names_cannot_escape_the_zip(gallery, size):
    from apps.galleries.tasks import _entries
    from apps.galleries.tests.factories import GallerySectionFactory

    section = GallerySectionFactory(studio=gallery.studio, gallery=gallery, title="../../..")
    photos = [
        PhotoFactory(studio=gallery.studio, gallery=gallery, original_name="../../etc/passwd"),
        PhotoFactory(
            studio=gallery.studio, gallery=gallery, section=section, original_name="..\\a.jpg"
        ),
    ]
    for path, _storage, _key in _entries(photos, size):
        parts = Path(path).parts
        assert ".." not in parts and not path.startswith("/")
        assert len(parts) <= 2  # at most folder/file
