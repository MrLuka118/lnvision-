"""The public portfolio and its inquiry form: what strangers see and what they can send."""

import time
from datetime import timedelta

import pytest
from django.core import signing
from django.core.cache import cache
from django.test import Client as HttpClient
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext

from apps.clients.models import Client
from apps.clients.tests.factories import ClientFactory
from apps.portfolio.models import Inquiry
from apps.portfolio.public_forms import SALT
from apps.portfolio.tests.factories import (
    PortfolioCategoryFactory,
    PortfolioFactory,
    PortfolioStoryFactory,
)
from apps.scheduling.models import Event
from apps.shoots.models import Shoot
from apps.shoots.tests.factories import PackageFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()


@pytest.fixture
def portfolio(studio):
    return PortfolioFactory(studio=studio, accept_inquiries=True)


def home(studio):
    return reverse("public_portfolio:home", args=[studio.slug])


def inquiry_url(studio):
    return reverse("public_portfolio:inquiry", args=[studio.slug])


def started(seconds_ago=10):
    return signing.dumps(time.time() - seconds_ago, salt=SALT)


def payload(**overrides):
    data = {
        "name": "Nina Zorko",
        "email": "nina@example.si",
        "phone": "041 123 456",
        "desired_date": "",
        "package": "",
        "message": "Poročiva se junija, bi nas fotografirali?",
        "website": "",
        "started": started(),
    }
    return data | overrides


def send(client, studio, **overrides):
    return client.post(inquiry_url(studio), payload(**overrides))


# --- who sees what -------------------------------------------------------------------------


def test_published_portfolio_is_public_and_indexable(client, portfolio, studio):
    story = PortfolioStoryFactory(studio=studio, title="Poroka na Bledu")
    response = client.get(home(studio))
    assert response.status_code == 200
    assert "X-Robots-Tag" not in response
    assert story.title in response.content.decode()
    assert response.context["theme"] == portfolio.look


def test_unpublished_portfolio_is_only_previewed_by_its_owner(client, auth_client, studio):
    PortfolioFactory(studio=studio, is_published=False)
    assert client.get(home(studio)).status_code == 404
    response = auth_client.get(home(studio))
    assert response.status_code == 200 and response.context["preview"]


def test_another_photographer_cannot_preview_it(studio, other_studio):
    PortfolioFactory(studio=studio, is_published=False)
    stranger = HttpClient()
    stranger.force_login(other_studio.owner)
    assert stranger.get(home(studio)).status_code == 404


def test_a_studio_without_a_portfolio_has_no_page(client, studio):
    assert client.get(home(studio)).status_code == 404


def test_unpublished_stories_stay_hidden(client, auth_client, portfolio, studio):
    draft = PortfolioStoryFactory(studio=studio, is_published=False, title="Še v delu")
    assert client.get(draft.get_public_url()).status_code == 404
    category = client.get(draft.category.get_public_url())
    assert draft.title not in category.content.decode()
    assert auth_client.get(draft.get_public_url()).status_code == 200


def test_stories_are_found_only_under_their_own_studio(client, portfolio, studio, other_studio):
    PortfolioFactory(studio=other_studio)
    theirs = PortfolioStoryFactory(studio=other_studio)
    mine = PortfolioCategoryFactory(studio=studio, slug=theirs.category.slug)
    target = reverse("public_portfolio:story", args=[studio.slug, mine.slug, theirs.slug])
    assert client.get(target).status_code == 404


# --- inquiries -----------------------------------------------------------------------------


def test_an_inquiry_becomes_a_client_a_shoot_and_a_tentative_date(
    client, portfolio, studio, django_capture_on_commit_callbacks, mailoutbox
):
    package = PackageFactory(studio=studio, name="Poroka, cel dan")
    day = timezone.localdate() + timedelta(days=200)
    with django_capture_on_commit_callbacks(execute=True):
        response = send(
            client, studio, desired_date=day.isoformat(), package=package.pk, name="Nina  Zorko"
        )
    assert response.status_code == 302
    assert response["Location"].endswith("?hvala=1#povprasevanje")

    inquiry = Inquiry.objects.get()
    assert inquiry.studio == studio and inquiry.name == "Nina Zorko" and inquiry.ip_hash
    client_ = inquiry.client
    assert (client_.first_name, client_.last_name) == ("Nina", "Zorko")
    assert client_.source == Client.Source.PORTFOLIO
    shoot = inquiry.shoot
    assert shoot.status == Shoot.Status.INQUIRY and shoot.package == package
    assert shoot.price == package.price
    event = Event.objects.get(shoot=shoot)
    assert event.all_day and event.is_tentative
    assert timezone.localtime(event.start).date() == day

    to_studio, to_client = mailoutbox
    assert to_studio.to == [studio.owner.email] and to_studio.reply_to == ["nina@example.si"]
    assert "Poročiva se junija" in to_studio.body
    assert to_client.to == ["nina@example.si"] and to_client.reply_to == [studio.owner.email]


def test_the_reply_to_a_stranger_carries_nothing_they_wrote(
    client, portfolio, studio, django_capture_on_commit_callbacks, mailoutbox
):
    """Otherwise the form sends anyone's text to any address, signed by the studio."""
    with django_capture_on_commit_callbacks(execute=True):
        send(client, studio, name="Kupi zdaj https://spam.example", message="Poceni ure!")
    to_client = mailoutbox[1]
    assert "spam.example" not in to_client.subject + to_client.body
    assert "Poceni ure" not in to_client.body


def test_emails_are_plain_text_not_html_escaped(
    client, portfolio, studio, django_capture_on_commit_callbacks, mailoutbox
):
    with django_capture_on_commit_callbacks(execute=True):
        send(client, studio, name="Ana & Luka", message='"Pozdravljeni" <3')
    to_studio = mailoutbox[0]
    assert "Ana & Luka" in to_studio.subject
    assert '"Pozdravljeni" <3' in to_studio.body


def test_a_returning_client_is_matched_by_email(client, portfolio, studio):
    known = ClientFactory(studio=studio, email="Nina@Example.si")
    send(client, studio, email="nina@example.SI")
    assert Inquiry.objects.get().client == known
    assert Client.objects.for_studio(studio).count() == 1


def test_a_client_of_another_studio_is_never_matched(client, portfolio, studio, other_studio):
    theirs = ClientFactory(studio=other_studio, email="nina@example.si")
    send(client, studio)
    assert Inquiry.objects.get().client != theirs
    assert Client.objects.for_studio(other_studio).get() == theirs


def test_htmx_submit_swaps_in_the_thank_you(client, portfolio, studio):
    response = client.post(inquiry_url(studio), payload(), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert response.templates[0].name == "portfolio/public/_inquiry_thanks.html"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"website": "https://spam.example"}, id="honeypot"),
        pytest.param({"started": "just now"}, id="too-fast"),
        pytest.param({"started": "nonsense"}, id="tampered-timestamp"),
        pytest.param({"started": ""}, id="no-timestamp"),
        pytest.param({"desired_date": "2020-01-01"}, id="past-date"),
        pytest.param({"email": "ni-naslov"}, id="bad-email"),
        pytest.param({"message": ""}, id="no-message"),
    ],
)
def test_rejected_submissions_create_nothing(client, portfolio, studio, overrides):
    if overrides.get("started") == "just now":
        overrides = {"started": started(seconds_ago=0)}  # stamped here, not at collection
    response = send(client, studio, **overrides)
    assert response.status_code == 400
    assert not Inquiry.objects.exists() and not Shoot.objects.exists()


def test_an_old_form_has_expired(client, portfolio, studio, monkeypatch):
    two_days_ago = time.time() - 2 * 24 * 3600
    with monkeypatch.context() as patched:
        patched.setattr(signing.time, "time", lambda: two_days_ago)
        old = signing.dumps(two_days_ago, salt=SALT)
    assert send(client, studio, started=old).status_code == 400
    assert not Inquiry.objects.exists()


def test_packages_of_other_studios_or_retired_ones_cannot_be_chosen(
    client, portfolio, studio, other_studio
):
    theirs = PackageFactory(studio=other_studio)
    retired = PackageFactory(studio=studio, is_active=False)
    assert send(client, studio, package=theirs.pk).status_code == 400
    assert send(client, studio, package=retired.pk).status_code == 400
    assert not Inquiry.objects.exists()


def test_inquiries_are_rate_limited(client, portfolio, studio):
    codes = [send(client, studio, message="").status_code for _ in range(5)]
    assert codes == [400] * 5
    blocked = send(client, studio)  # even a good one waits
    assert blocked.status_code == 400
    limit = gettext("Too many messages from here. Try again in an hour, or write by e-mail.")
    assert limit in blocked.content.decode()
    assert not Inquiry.objects.exists()


def test_closed_inquiries_have_no_form_and_no_endpoint(client, studio):
    PortfolioFactory(studio=studio, accept_inquiries=False)
    assert client.get(home(studio)).context["form"] is None
    assert send(client, studio).status_code == 404


def test_an_unpublished_portfolio_takes_no_inquiries(client, studio):
    PortfolioFactory(studio=studio, is_published=False, accept_inquiries=True)
    assert send(client, studio).status_code == 404


def test_pages_do_not_query_per_story(client, portfolio, studio):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from apps.galleries.tests.factories import PhotoFactory

    category = PortfolioCategoryFactory(studio=studio)

    def queries(path):
        with CaptureQueriesContext(connection) as captured:
            assert client.get(path).status_code == 200
        return len(captured)

    def add_stories(n):
        for _ in range(n):
            PortfolioStoryFactory(
                studio=studio, category=category, cover_photo=PhotoFactory(studio=studio)
            )

    add_stories(2)
    few = queries(home(studio)), queries(category.get_public_url())
    add_stories(6)
    assert (queries(home(studio)), queries(category.get_public_url())) == few


def test_a_story_page_does_not_query_per_photo(client, portfolio, studio):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from apps.galleries.tests.factories import PhotoFactory
    from apps.portfolio.models import PortfolioStoryPhoto

    story = PortfolioStoryFactory(studio=studio)
    PortfolioStoryFactory(studio=studio, category=story.category)  # a neighbour for prev/next

    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert client.get(story.get_public_url()).status_code == 200
        return len(captured)

    def add_photos(n):
        for i in range(n):
            photo = PhotoFactory(studio=studio)
            PortfolioStoryPhoto.objects.create(story=story, photo=photo, position=i)

    add_photos(2)
    few = queries()
    add_photos(8)
    assert queries() == few
