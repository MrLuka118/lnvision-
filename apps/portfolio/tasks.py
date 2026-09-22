from celery import shared_task
from django.conf import settings
from django.utils import translation

from apps.core.mail import text_message

from .models import Inquiry


@shared_task
def send_inquiry_emails(inquiry_id: int):
    """Tell the photographer, and let the person know their message arrived."""
    inquiry = Inquiry.objects.select_related("studio", "studio__owner", "package", "shoot").get(
        pk=inquiry_id
    )
    studio = inquiry.studio
    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    context = {
        "inquiry": inquiry,
        "studio": studio,
        "shoot_link": base + inquiry.shoot.get_absolute_url() if inquiry.shoot else "",
    }
    photographer = studio.email or studio.owner.email
    with translation.override(settings.LANGUAGE_CODE):
        to_studio = text_message("inquiry_new", context, [photographer], reply_to=[inquiry.email])
        # Goes to whatever address was typed in, so it carries nothing the visitor wrote:
        # otherwise the form would relay anyone's text to anyone, signed by the studio.
        to_client = text_message(
            "inquiry_received", context, [inquiry.email], reply_to=[photographer]
        )
    to_studio.send()
    to_client.send()
