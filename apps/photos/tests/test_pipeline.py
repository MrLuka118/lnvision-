"""The photo pipeline end to end, on a real file: wide-gamut, rotated, with GPS in it."""

import json
import subprocess
from pathlib import Path

import pytest
import pyvips
from django.core.files import File
from django.core.files.storage import storages
from django.urls import reverse
from django.utils import timezone

from apps.galleries.tests.factories import GalleryFactory
from apps.photos import exif, services
from apps.photos.models import Photo, UploadSession

pytestmark = pytest.mark.django_db


@pytest.fixture
def camera_file(tmp_path) -> Path:
    """3000x2000 red frame in Display P3, EXIF orientation 6 (portrait), with GPS."""
    path = tmp_path / "IMG_0042.jpg"
    image = pyvips.Image.black(3000, 2000, bands=3).linear([1, 1, 1], [200, 40, 40]).cast("uchar")
    image = image.copy(interpretation="srgb").icc_transform("p3", input_profile="srgb")
    image.write_to_file(str(path), Q=90)
    subprocess.run(  # noqa: S603
        [
            exif.EXIFTOOL, "-overwrite_original", "-Orientation#=6",
            "-GPSLatitude=46.3625", "-GPSLatitudeRef=N",
            "-GPSLongitude=14.0936", "-GPSLongitudeRef=E",
            "-DateTimeOriginal=2026:06:14 15:30:00", "-Make=Canon", "-Model=EOS R5",
            str(path),
        ],
        check=True, capture_output=True,
    )  # fmt: skip
    assert exif.has_gps(path)
    return path


def make_photo(gallery, path: Path) -> Photo:
    photo = Photo(studio=gallery.studio, gallery=gallery, original_name=path.name)
    with path.open("rb") as fh:
        photo.original.save(path.name, File(fh), save=False)
    photo.save()
    return photo


def test_processing_makes_srgb_renditions_without_location(studio, camera_file, tmp_path):
    gallery = GalleryFactory(studio=studio)
    photo = services.process(make_photo(gallery, camera_file))

    assert photo.status == Photo.Status.READY
    assert (photo.width, photo.height) == (2000, 3000)  # orientation applied
    assert photo.renditions == {
        "widths": [480, 960, 1600, 2000],
        "formats": ["avif", "jpg", "webp"],
    }
    assert photo.exif["make"] == "Canon" and "gps" not in json.dumps(photo.exif).lower()
    assert timezone.localtime(photo.taken_at).strftime("%Y-%m-%d %H:%M") == "2026-06-14 15:30"
    assert len(photo.blurhash) > 10
    assert photo.lqip.startswith("data:image/webp;base64,")
    assert photo.dominant_color.startswith("#") and 0 <= photo.luminance <= 1

    storage = storages["renditions"]
    key = f"r/{photo.uuid}/1/960.jpg"
    rendition = tmp_path / "960.jpg"
    rendition.write_bytes(storage.open(key).read())
    image = pyvips.Image.new_from_file(str(rendition))
    assert (image.width, image.height) == (960, 1440)
    assert image.get_typeof("icc-profile-data") == 0  # plain sRGB, nothing embedded
    assert not exif.has_gps(rendition)

    original = tmp_path / "original.jpg"
    original.write_bytes(photo.original.open("rb").read())
    assert not exif.has_gps(original)
    assert exif.read(original)[0]["model"] == "EOS R5"  # the rest of the metadata stays


def test_gps_is_kept_when_the_photographer_wants_it(studio, camera_file, tmp_path):
    gallery = GalleryFactory(studio=studio, strip_gps=False)
    photo = services.process(make_photo(gallery, camera_file))
    original = tmp_path / "original.jpg"
    original.write_bytes(photo.original.open("rb").read())
    assert exif.has_gps(original)


def test_reprocessing_replaces_the_old_renditions(studio, camera_file):
    gallery = GalleryFactory(studio=studio, watermark=True)
    photo = services.process(make_photo(gallery, camera_file))
    photo = services.process(photo)
    storage = storages["renditions"]
    assert photo.rendition_version == 2
    assert storage.exists(f"r/{photo.uuid}/2/480.avif")
    assert not storage.exists(f"r/{photo.uuid}/1/480.avif")


def test_small_photos_are_not_upscaled(studio, tmp_path):
    path = tmp_path / "small.png"
    pyvips.Image.black(700, 500, bands=3).linear([1, 1, 1], [128] * 3).cast("uchar").write_to_file(
        str(path)
    )
    photo = services.process(make_photo(GalleryFactory(studio=studio), path))
    assert photo.renditions["widths"] == [480, 700]


# --- chunked upload API -------------------------------------------------------------------


@pytest.fixture
def small_chunks(monkeypatch):
    monkeypatch.setattr(services, "CHUNK_SIZE", 64 * 1024)


def start(client, gallery, name, size):
    return client.post(
        reverse("photos:upload_start", args=[gallery.pk]),
        data=json.dumps({"name": name, "size": size}),
        content_type="application/json",
    )


def put(client, url, data: bytes, offset: int):
    return client.put(
        url, data=data, content_type="application/octet-stream", headers={"Upload-Offset": offset}
    )


def test_upload_in_chunks_creates_and_processes_a_photo(
    auth_client, studio, camera_file, small_chunks, django_capture_on_commit_callbacks
):
    gallery = GalleryFactory(studio=studio)
    data = camera_file.read_bytes()
    session = start(auth_client, gallery, camera_file.name, len(data)).json()
    offset = 0
    with django_capture_on_commit_callbacks(execute=True):
        while offset < len(data):
            response = put(auth_client, session["url"], data[offset : offset + 64 * 1024], offset)
            assert response.status_code == 200, response.content
            offset = response.json()["received"]
    photo = Photo.objects.get(gallery=gallery)
    assert photo.status == Photo.Status.READY
    assert photo.original_name == "IMG_0042.jpg"
    assert UploadSession.objects.get().status == UploadSession.Status.COMPLETE
    assert not services.partial_path(UploadSession.objects.get()).exists()


def test_wrong_offset_reports_where_the_server_is(auth_client, studio, small_chunks):
    gallery = GalleryFactory(studio=studio)
    session = start(auth_client, gallery, "a.jpg", 200_000).json()
    response = put(auth_client, session["url"], b"x" * 1000, offset=5000)
    assert response.status_code == 409
    assert response.json()["received"] == 0


def test_sending_more_than_announced_is_refused(auth_client, studio, small_chunks):
    gallery = GalleryFactory(studio=studio)
    session = start(auth_client, gallery, "a.jpg", 100).json()
    assert put(auth_client, session["url"], b"x" * 500, offset=0).status_code == 413
    assert UploadSession.objects.get().received_bytes == 0


def test_files_that_are_not_images_are_rejected(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    session = start(auth_client, gallery, "notes.jpg", 11).json()
    response = put(auth_client, session["url"], b"hello world", offset=0)
    assert response.status_code == 422
    assert not Photo.objects.exists()
    assert UploadSession.objects.get().status == UploadSession.Status.FAILED


@pytest.mark.parametrize(("name", "size", "status"), [("a.exe", 10, 400), ("a.jpg", 0, 413)])
def test_upload_start_validates(auth_client, studio, name, size, status):
    gallery = GalleryFactory(studio=studio)
    assert start(auth_client, gallery, name, size).status_code == status


def test_uploads_into_another_studios_gallery_are_not_found(auth_client, other_studio):
    gallery = GalleryFactory(studio=other_studio)
    assert start(auth_client, gallery, "a.jpg", 10).status_code == 404


def test_another_studios_upload_session_is_not_found(auth_client, other_studio):
    gallery = GalleryFactory(studio=other_studio)
    session = UploadSession.objects.create(
        studio=other_studio, gallery=gallery, filename="a.jpg", size_bytes=10
    )
    url = reverse("photos:upload_chunk", args=[session.uuid])
    assert auth_client.get(url).status_code == 404
    assert put(auth_client, url, b"x", offset=0).status_code == 404


def test_deleting_a_gallery_removes_its_files(
    studio, camera_file, django_capture_on_commit_callbacks
):
    gallery = GalleryFactory(studio=studio)
    photo = services.process(make_photo(gallery, camera_file))
    storage = storages["renditions"]
    original = photo.original.name
    with django_capture_on_commit_callbacks(execute=True):
        gallery.delete()
    assert not storage.exists(f"r/{photo.uuid}/1/480.jpg")
    assert not photo.original.storage.exists(original)
