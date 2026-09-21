import pytest
from django.urls import reverse

from apps.galleries.models import Gallery
from apps.galleries.tests.factories import GalleryFactory, GallerySectionFactory, PhotoFactory
from apps.shoots.tests.factories import ShootFactory

pytestmark = pytest.mark.django_db


def test_create_from_a_shoot_takes_its_client_and_title(auth_client, studio):
    shoot = ShootFactory(studio=studio, title="Poroka Novak in Kranjc")
    form = auth_client.get(reverse("galleries:create"), {"shoot": shoot.pk}).context["form"]
    assert form.initial["title"] == "Poroka Novak in Kranjc"
    response = auth_client.post(
        reverse("galleries:create"), {"title": "Poroka", "shoot": shoot.pk, "theme": "darkroom"}
    )
    gallery = Gallery.objects.get()
    assert response["Location"] == gallery.get_absolute_url()
    assert gallery.client == shoot.client
    assert not gallery.is_published  # drafts until the photographer publishes


def settings_data(gallery, **extra):
    data = {
        "title": gallery.title,
        "theme": gallery.theme,
        "downloads": gallery.downloads,
        "strip_gps": "on",
    }
    data.update(extra)
    return data


def test_password_is_hashed_and_changing_it_signs_visitors_out(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    url = reverse("galleries:settings", args=[gallery.pk])
    auth_client.post(url, settings_data(gallery, password="skrivnost-42"))
    gallery.refresh_from_db()
    assert gallery.has_password and "skrivnost" not in gallery.password_hash
    assert gallery.check_password("skrivnost-42")
    version = gallery.password_version
    auth_client.post(url, settings_data(gallery, remove_password="on"))
    gallery.refresh_from_db()
    assert not gallery.has_password
    assert gallery.password_version == version + 1


def test_saving_without_a_new_password_keeps_the_old_one(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    gallery.set_password("staro-geslo-1")
    gallery.save()
    auth_client.post(reverse("galleries:settings", args=[gallery.pk]), settings_data(gallery))
    gallery.refresh_from_db()
    assert gallery.check_password("staro-geslo-1")


def test_publish_hide_and_new_link(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    old_token = gallery.token
    auth_client.post(reverse("galleries:action", args=[gallery.pk, "publish"]))
    gallery.refresh_from_db()
    assert gallery.is_published and gallery.published_at
    auth_client.post(reverse("galleries:action", args=[gallery.pk, "new-link"]))
    gallery.refresh_from_db()
    assert gallery.token != old_token
    auth_client.post(reverse("galleries:action", args=[gallery.pk, "hide"]))
    gallery.refresh_from_db()
    assert not gallery.is_published
    assert (
        auth_client.post(reverse("galleries:action", args=[gallery.pk, "nope"])).status_code == 400
    )


def test_photo_actions_stay_inside_the_gallery(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    elsewhere = PhotoFactory(studio=studio)  # same studio, other gallery
    url = reverse("galleries:photo_action", args=[gallery.pk, elsewhere.pk, "cover"])
    assert auth_client.post(url).status_code == 404


def test_cover_and_section_moves(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    photo = PhotoFactory(studio=studio, gallery=gallery)
    section = GallerySectionFactory(studio=studio, gallery=gallery)
    auth_client.post(reverse("galleries:photo_action", args=[gallery.pk, photo.pk, "cover"]))
    auth_client.post(
        reverse("galleries:photo_action", args=[gallery.pk, photo.pk, "move"]),
        {"section": section.pk},
    )
    gallery.refresh_from_db()
    photo.refresh_from_db()
    assert gallery.cover_photo == photo
    assert photo.section == section


def test_moving_into_another_galleries_section_is_ignored(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    photo = PhotoFactory(studio=studio, gallery=gallery)
    foreign_section = GallerySectionFactory(studio=studio)
    auth_client.post(
        reverse("galleries:photo_action", args=[gallery.pk, photo.pk, "move"]),
        {"section": foreign_section.pk},
    )
    photo.refresh_from_db()
    assert photo.section is None


def test_editor_grid_partial_for_polling(auth_client, studio):
    gallery = GalleryFactory(studio=studio)
    PhotoFactory(studio=studio, gallery=gallery, status="processing")
    response = auth_client.get(
        gallery.get_absolute_url(), headers={"HX-Request": "true", "HX-Target": "photo-grid"}
    )
    assert response.templates[0].name == "galleries/_photo_grid.html"
    assert "every 2s" in response.content.decode()


def test_unpublished_gallery_link_is_not_found(client, studio):
    gallery = GalleryFactory(studio=studio)
    assert client.get(gallery.get_public_url()).status_code == 404


def test_sending_the_link_to_the_client(
    auth_client, studio, mailoutbox, django_capture_on_commit_callbacks
):
    from apps.clients.tests.factories import ClientFactory

    client = ClientFactory(studio=studio, first_name="Ana", email="ana@example.si")
    gallery = GalleryFactory(studio=studio, client=client, is_published=True)
    gallery.set_password("geslo-za-ano")
    gallery.save()
    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(reverse("galleries:action", args=[gallery.pk, "send"]))
    assert response.status_code == 302
    [mail] = mailoutbox
    assert mail.to == ["ana@example.si"]
    assert gallery.get_public_url() in mail.body
    assert "geslo-za-ano" not in mail.body  # the password never travels with the link


def test_drafts_are_not_sent(auth_client, studio):
    from apps.clients.tests.factories import ClientFactory

    gallery = GalleryFactory(studio=studio, client=ClientFactory(studio=studio))
    assert (
        auth_client.post(reverse("galleries:action", args=[gallery.pk, "send"])).status_code == 400
    )
