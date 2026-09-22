from datetime import datetime, time

from django.db import transaction
from django.utils import timezone

from apps.clients.models import Client
from apps.scheduling.models import Event
from apps.shoots.models import Shoot

from .models import Inquiry


@transaction.atomic
def create_inquiry(studio, data: dict, ip_hash: str = "") -> Inquiry:
    """An inquiry from the portfolio becomes a client (matched by e-mail), a shoot in the
    'inquiry' status and, if a date was given, a tentative all-day event on it."""
    email = data["email"].strip().lower()
    client = Client.objects.for_studio(studio).filter(email__iexact=email).first()
    if client is None:
        first, _space, last = data["name"].strip().partition(" ")
        client = Client.objects.create(
            studio=studio,
            first_name=first[:80],
            last_name=last[:80],
            email=email,
            phone=data.get("phone", ""),
            source=Client.Source.PORTFOLIO,
        )
    package = data.get("package")
    shoot = Shoot.objects.create(
        studio=studio,
        client=client,
        package=package,
        title=f"{package.name}: {client.display_name}" if package else client.display_name,
        status=Shoot.Status.INQUIRY,
        price=package.price if package else 0,
        inquiry_message=data["message"],
    )
    if day := data.get("desired_date"):
        Event.objects.create(
            studio=studio,
            kind=Event.Kind.SHOOT,
            shoot=shoot,
            client=client,
            start=timezone.make_aware(datetime.combine(day, time.min)),
            all_day=True,
            is_tentative=True,
        )
    inquiry = Inquiry.objects.create(
        studio=studio,
        name=data["name"].strip(),
        email=email,
        phone=data.get("phone", ""),
        desired_date=data.get("desired_date"),
        package=package,
        message=data["message"],
        client=client,
        shoot=shoot,
        ip_hash=ip_hash,
    )

    def notify():
        from .tasks import send_inquiry_emails

        send_inquiry_emails.delay(inquiry.pk)

    transaction.on_commit(notify)
    return inquiry
