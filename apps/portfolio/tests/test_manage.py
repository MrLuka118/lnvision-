import pytest
from django.urls import reverse
from django.utils.translation import gettext, ngettext

from apps.galleries.tests.factories import GalleryFactory, PhotoFactory
from apps.photos.models import Photo
from apps.portfolio.models import Portfolio, PortfolioCategory, PortfolioStory, PortfolioStoryPhoto
from apps.portfolio.tests.factories import (
    PortfolioCategoryFactory,
    PortfolioStoryFactory,
)

pytestmark = pytest.mark.django_db


# 1. Anonymous visitors are redirected to login on portfolio:index and portfolio:story_list.
def test_anonymous_visitors_are_redirected_to_login_on_index_and_story_list(client):
    for url_name in ["portfolio:index", "portfolio:story_list"]:
        response = client.get(reverse(url_name))
        assert response.status_code == 302
        assert "login" in response["Location"]


# 2. portfolio:index renders and creates the studio's Portfolio on first visit (exactly one).
def test_index_renders_and_creates_the_studios_portfolio_on_first_visit(auth_client, studio):
    assert not Portfolio.objects.filter(studio=studio).exists()

    response = auth_client.get(reverse("portfolio:index"))
    assert response.status_code == 200
    assert Portfolio.objects.filter(studio=studio).count() == 1
    assert response.context["portfolio"] == Portfolio.objects.get(studio=studio)

    # Visiting again still leaves exactly one Portfolio
    response2 = auth_client.get(reverse("portfolio:index"))
    assert response2.status_code == 200
    assert Portfolio.objects.filter(studio=studio).count() == 1


# 3. portfolio:profile GET renders; POST with valid data saves and redirects to portfolio:index.
def test_profile_get_renders_and_valid_post_saves_and_redirects_to_index(auth_client, studio):
    response = auth_client.get(reverse("portfolio:profile"))
    assert response.status_code == 200

    data = {
        "headline": "Fotograf Ljubljana",
        "about": "O meni in mojem delu.",
        "look": "dark",
        "instagram": "https://instagram.com/studio",
        "accept_inquiries": "on",
        "seo_description": "Vrhunska fotografija",
        "is_published": "on",
    }
    post_response = auth_client.post(reverse("portfolio:profile"), data)
    assert post_response.status_code == 302
    assert post_response["Location"] == reverse("portfolio:index")

    portfolio = Portfolio.objects.get(studio=studio)
    assert portfolio.headline == "Fotograf Ljubljana"
    assert portfolio.about == "O meni in mojem delu."
    assert portfolio.look == "dark"
    assert portfolio.instagram == "https://instagram.com/studio"
    assert portfolio.accept_inquiries is True
    assert portfolio.seo_description == "Vrhunska fotografija"
    assert portfolio.is_published is True


# 4. Category create / update / delete work and redirect to portfolio:category_list.
def test_category_create_update_and_delete_work_and_redirect_to_category_list(auth_client, studio):
    # Create
    create_data = {
        "name": "Poroke",
        "slug": "poroke",
        "description": "Poročna fotografija",
        "position": 1,
    }
    response = auth_client.post(reverse("portfolio:category_create"), create_data)
    assert response.status_code == 302
    assert response["Location"] == reverse("portfolio:category_list")

    category = PortfolioCategory.objects.get(studio=studio, slug="poroke")
    assert category.name == "Poroke"
    assert category.position == 1

    # Update
    update_data = {
        "name": "Poroke in slavja",
        "slug": "poroke-in-slavja",
        "description": "Posodobljen opis",
        "position": 2,
    }
    update_response = auth_client.post(
        reverse("portfolio:category_update", args=[category.pk]), update_data
    )
    assert update_response.status_code == 302
    assert update_response["Location"] == reverse("portfolio:category_list")

    category.refresh_from_db()
    assert category.name == "Poroke in slavja"
    assert category.slug == "poroke-in-slavja"
    assert category.position == 2

    # Delete
    delete_response = auth_client.post(reverse("portfolio:category_delete", args=[category.pk]))
    assert delete_response.status_code == 302
    assert delete_response["Location"] == reverse("portfolio:category_list")
    assert not PortfolioCategory.objects.filter(pk=category.pk).exists()


# 5. Deleting a category with stories shows the "will also delete its stories" warning on GET.
def test_deleting_a_category_with_stories_shows_warning_on_get(auth_client, studio):
    category = PortfolioCategoryFactory(studio=studio)
    PortfolioStoryFactory(studio=studio, category=category)

    response = auth_client.get(reverse("portfolio:category_delete", args=[category.pk]))
    assert response.status_code == 200
    warning = ngettext(
        "%(count)s story belongs to this category. "
        "Deleting the category will also delete its stories.",
        "%(count)s stories belong to this category. "
        "Deleting the category will also delete its stories.",
        1,
    ) % {"count": 1}
    assert response.context["view"].lede == warning


# 6. Story create redirects to portfolio:story_photos for the new story.
def test_story_create_redirects_to_story_photos_for_the_new_story(auth_client, studio):
    category = PortfolioCategoryFactory(studio=studio)
    data = {
        "category": category.pk,
        "title": "Moja poroka",
        "slug": "moja-poroka",
        "position": 0,
    }
    response = auth_client.post(reverse("portfolio:story_create"), data)
    story = PortfolioStory.objects.get(studio=studio, slug="moja-poroka")
    assert response.status_code == 302
    assert response["Location"] == reverse("portfolio:story_photos", args=[story.pk])


# 7. story_photos POST saves the chosen photos in the posted order (positions 0, 1, 2), ignores
#    duplicates and non-numeric ids, and sets cover_photo to the first photo when it was empty.
def test_story_photos_post_saves_chosen_photos_in_order_ignores_duplicates_and_sets_cover_photo(
    auth_client, studio
):
    gallery = GalleryFactory(studio=studio)
    story = PortfolioStoryFactory(studio=studio, gallery=gallery, cover_photo=None)
    p1 = PhotoFactory(studio=studio, gallery=gallery)
    p2 = PhotoFactory(studio=studio, gallery=gallery)
    p3 = PhotoFactory(studio=studio, gallery=gallery)

    raw_photos = ["foo", str(p2.pk), str(p3.pk), "abc", str(p2.pk), str(p1.pk), ""]
    response = auth_client.post(
        reverse("portfolio:story_photos", args=[story.pk]),
        {"photos": raw_photos},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("portfolio:story_list")

    entries = list(story.entries.order_by("position").values_list("photo_id", "position"))
    assert entries == [(p2.pk, 0), (p3.pk, 1), (p1.pk, 2)]

    story.refresh_from_db()
    assert story.cover_photo_id == p2.pk

    # A cover that is still selected stays; a deselected cover moves to the first photo.
    url = reverse("portfolio:story_photos", args=[story.pk])
    auth_client.post(url, {"photos": [str(p3.pk), str(p2.pk)]})
    story.refresh_from_db()
    assert story.cover_photo_id == p2.pk

    auth_client.post(url, {"photos": [str(p3.pk), str(p1.pk)]})
    story.refresh_from_db()
    assert story.cover_photo_id == p3.pk

    auth_client.post(url, {"photos": []})
    story.refresh_from_db()
    assert story.cover_photo_id is None


# 8. story_photos POST ignores photos from another studio and photos that are not READY.
def test_story_photos_post_ignores_photos_from_another_studio_and_unready_photos(
    auth_client, studio, other_studio
):
    gallery = GalleryFactory(studio=studio)
    story = PortfolioStoryFactory(studio=studio, gallery=gallery)
    own_ready = PhotoFactory(studio=studio, gallery=gallery, status=Photo.Status.READY)
    own_pending = PhotoFactory(studio=studio, gallery=gallery, status=Photo.Status.PENDING)
    own_processing = PhotoFactory(studio=studio, gallery=gallery, status=Photo.Status.PROCESSING)
    own_failed = PhotoFactory(studio=studio, gallery=gallery, status=Photo.Status.FAILED)
    other_ready = PhotoFactory(studio=other_studio, status=Photo.Status.READY)

    response = auth_client.post(
        reverse("portfolio:story_photos", args=[story.pk]),
        {
            "photos": [
                str(own_ready.pk),
                str(own_pending.pk),
                str(own_processing.pk),
                str(own_failed.pk),
                str(other_ready.pk),
            ]
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("portfolio:story_list")

    saved_photo_ids = list(story.entries.values_list("photo_id", flat=True))
    assert saved_photo_ids == [own_ready.pk]


# 9. When the story has a gallery, story_photos only accepts photos from that gallery.
def test_story_photos_with_gallery_only_accepts_photos_from_that_gallery(auth_client, studio):
    g1 = GalleryFactory(studio=studio)
    g2 = GalleryFactory(studio=studio)
    story = PortfolioStoryFactory(studio=studio, gallery=g1)

    p1 = PhotoFactory(studio=studio, gallery=g1, status=Photo.Status.READY)
    p2 = PhotoFactory(studio=studio, gallery=g2, status=Photo.Status.READY)

    response = auth_client.post(
        reverse("portfolio:story_photos", args=[story.pk]),
        {"photos": [str(p1.pk), str(p2.pk)]},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("portfolio:story_list")

    saved_photo_ids = list(story.entries.values_list("photo_id", flat=True))
    assert saved_photo_ids == [p1.pk]


def test_a_story_without_a_gallery_offers_and_accepts_no_photos(auth_client, studio):
    story = PortfolioStoryFactory(studio=studio, gallery=None)
    photo = PhotoFactory(studio=studio, status=Photo.Status.READY)
    url = reverse("portfolio:story_photos", args=[story.pk])

    response = auth_client.get(url)
    assert response.status_code == 200
    assert list(response.context["photos"]) == []

    auth_client.post(url, {"photos": [str(photo.pk)]})
    assert not story.entries.exists()


@pytest.mark.parametrize(
    ("url_name", "factory", "source", "data"),
    [
        ("portfolio:category_create", PortfolioCategoryFactory, "name", {"position": 0}),
        ("portfolio:story_create", PortfolioStoryFactory, "title", {"position": 0}),
    ],
)
def test_an_empty_address_is_made_from_the_name_and_a_taken_one_is_refused(
    auth_client, studio, other_studio, url_name, factory, source, data
):
    category = PortfolioCategoryFactory(studio=studio)
    if url_name == "portfolio:story_create":
        data = {**data, "category": category.pk}
    model = factory._meta.model

    response = auth_client.post(reverse(url_name), {**data, source: "Poroka Božič", "slug": ""})
    assert response.status_code == 302
    assert model.objects.filter(studio=studio, slug="poroka-bozic").exists()

    # Another studio using the address doesn't matter; this studio using it does.
    factory(studio=other_studio, slug="jesen")
    response = auth_client.post(reverse(url_name), {**data, source: "Jesen", "slug": ""})
    assert response.status_code == 302

    response = auth_client.post(reverse(url_name), {**data, source: "Jesen 2", "slug": "Jesen"})
    assert response.status_code == 200
    assert response.context["form"].errors["slug"] == [gettext("You already use this address.")]
    assert model.objects.filter(studio=studio, slug="jesen").count() == 1


def test_editing_keeps_the_objects_own_address(auth_client, studio):
    category = PortfolioCategoryFactory(studio=studio, slug="poroke")
    response = auth_client.post(
        reverse("portfolio:category_update", args=[category.pk]),
        {"name": "Poroke", "slug": "poroke", "position": 3},
    )
    assert response.status_code == 302
    category.refresh_from_db()
    assert category.position == 3


# 10. category_list and story_list with 5 objects each run a bounded number of queries
#     (django_assert_max_num_queries, pick the smallest number that passes, max 12).
def test_category_list_and_story_list_with_five_objects_each_run_bounded_queries(
    auth_client, studio, django_assert_max_num_queries
):
    for _ in range(5):
        category = PortfolioCategoryFactory(studio=studio)
        PortfolioStoryFactory(studio=studio, category=category)

    with django_assert_max_num_queries(4):
        auth_client.get(reverse("portfolio:category_list"))

    for _ in range(5):
        photo = PhotoFactory(studio=studio)
        story = PortfolioStoryFactory(studio=studio, cover_photo=photo)
        PortfolioStoryPhoto.objects.create(story=story, photo=photo, position=0)

    with django_assert_max_num_queries(4):
        auth_client.get(reverse("portfolio:story_list"))
