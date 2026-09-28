from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.utils import timezone

from apps.galleries.tests.factories import GalleryFactory
from apps.photos.models import Photo, rendition_key

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def photo(studio):
    gallery = GalleryFactory(studio=studio, is_published=True)
    photo = Photo.objects.create(
        studio=studio,
        gallery=gallery,
        status="ready",
        original_name="test.jpg",
        renditions={"widths": [480], "formats": ["jpg"]},
        rendition_version=1,
    )
    storages["renditions"].save(rendition_key(photo.uuid, 1, 480, "jpg"), ContentFile(b"image"))
    return photo


def test_rendition_requires_valid_unexpired_signature(client, photo):
    url = photo.rendition_url(480)
    response = client.get(url)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    response.close()
    assert client.get(url[:-2] + "x/").status_code == 404
    with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 3601):
        assert client.get(url).status_code == 404
    assert client.get(f"/media/r/{photo.uuid}/1/480.jpg").status_code == 404


def test_password_and_expiry_apply_to_renditions(client, auth_client, photo):
    photo.gallery.set_password("secret-password")
    photo.gallery.save()
    url = photo.rendition_url(480)
    assert client.get(url).status_code == 404
    response = auth_client.get(url)
    assert response.status_code == 200
    response.close()
    photo.gallery.expires_at = timezone.now() - timedelta(days=1)
    photo.gallery.save()
    assert client.get(url).status_code == 404


def test_unpublishing_revokes_existing_rendition_link(client, photo):
    url = photo.rendition_url(480)
    photo.gallery.is_published = False
    photo.gallery.save()
    assert client.get(url).status_code == 404
