"""Demo data for `manage.py seed_demo`: a believable year of a Slovenian photographer's work.

Everything goes through the same services the app uses, so the calendar, deadlines and
statuses are consistent. Deterministic (seeded random), and only runs on an empty studio.
"""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal
from urllib.parse import quote_plus

from django.utils import timezone

from apps.clients.models import Client
from apps.scheduling.models import Event
from apps.shoots import services
from apps.shoots.models import Location, Package, Shoot

LOCATIONS = [
    ("Blejsko jezero", "Cesta svobode, 4260 Bled"),
    ("Grad Bled", "Grajska cesta 61, 4260 Bled"),
    ("Soteska Vintgar", "Podhom 80, 4247 Zgornje Gorje"),
    ("Piranska obala", "Tartinijev trg, 6330 Piran"),
    ("Logarska dolina", "Logarska Dolina 9, 3335 Solčava"),
    ("Ljubljanski grad", "Grajska planota 1, 1000 Ljubljana"),
    ("Park Tivoli", "Tivoli, 1000 Ljubljana"),
    ("Atelje Svetloba", "Trubarjeva cesta 20, 1000 Ljubljana"),
]

# name, price, minutes, photos, editing days, delivery days, kind
PACKAGES = [
    ("Poroka, cel dan", "1900", 600, None, 21, 42, "wedding"),
    ("Poroka, pol dneva", "1200", 300, None, 14, 30, "wedding"),
    ("Portret", "180", 90, 25, 7, 14, "portrait"),
    ("Družinsko fotografiranje", "250", 120, 40, 7, 14, "family"),
    ("Poslovni portret", "150", 60, 10, 5, 7, "business"),
]

FIRST = [
    "Ana", "Luka", "Maja", "Nejc", "Eva", "Jure", "Tina", "Matej", "Sara", "Žiga", "Nina", "Rok",
    "Petra", "Tilen", "Katja", "Gregor", "Urška", "Blaž", "Špela", "Anže", "Lara", "Jan",
    "Manca", "Miha",
]  # fmt: skip
LAST = [
    "Novak", "Horvat", "Kovačič", "Krajnc", "Zupančič", "Potočnik", "Kovač", "Mlakar", "Kos",
    "Vidmar", "Golob", "Turk", "Božič", "Kralj", "Zupan", "Bizjak", "Hribar", "Korošec",
    "Rozman", "Kastelic", "Oblak", "Petek", "Žagar", "Kolar",
]  # fmt: skip
PARTNERS = [
    "Luka Kranjc", "Eva Rozman", "Matic Jerman", "Tjaša Kern", "Aljaž Mrak", "Neža Šuštar",
    "David Zorko", "Pia Vovk",
]  # fmt: skip
COMPANIES = ["Arhitektura Rob d.o.o.", "Zelena pisarna d.o.o.", "Pekarna Kruhek s.p."]

ASCII = str.maketrans("čšžćđČŠŽĆĐ", "cszcdCSZCD")


def _aware(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def seed_catalogue(studio) -> tuple[list[Location], dict[str, list[Package]]]:
    locations = [
        Location.objects.create(
            studio=studio,
            name=name,
            address=address,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}",
        )
        for name, address in LOCATIONS
    ]
    packages: dict[str, list[Package]] = {}
    for position, (name, price, minutes, photos, editing, delivery, kind) in enumerate(PACKAGES):
        package = Package.objects.create(
            studio=studio,
            name=name,
            price=Decimal(price),
            duration_minutes=minutes,
            photo_count=photos,
            editing_days=editing,
            delivery_days=delivery,
            position=position,
        )
        packages.setdefault(kind, []).append(package)
    return locations, packages


def seed_clients(studio, rng: random.Random) -> list[Client]:
    clients = []
    sources = list(Client.Source.values)
    for i, (first, last) in enumerate(zip(FIRST, LAST, strict=True)):
        email = f"{first}.{last}@example.si".translate(ASCII).lower()
        clients.append(
            Client.objects.create(
                studio=studio,
                first_name=first,
                last_name=last,
                partner_name=PARTNERS[i // 3] if i % 3 == 0 else "",
                company=COMPANIES[i % len(COMPANIES)] if i % 7 == 5 else "",
                email=email,
                phone=f"+386 41 {rng.randint(100, 999)} {rng.randint(100, 999)}",
                source=sources[i % len(sources)],
            )
        )
    return clients


def _title(kind: str, client: Client) -> str:
    if kind == "wedding":
        partner_last = client.partner_name.split()[-1]
        return f"Poroka {client.last_name} in {partner_last}"
    if kind == "family":
        return f"Družinsko {client.last_name}"
    if kind == "business":
        return f"Poslovni portret {client.company or client.full_name}"
    return f"Portret {client.full_name}"


def _status_for(start, now, rng: random.Random, future_index: int) -> str:
    if start > now:
        if future_index in (1, 4, 7):
            return Shoot.Status.INQUIRY
        if future_index == 9:
            return Shoot.Status.CANCELLED
        return Shoot.Status.CONFIRMED
    if now - start < timedelta(days=14):
        return rng.choice([Shoot.Status.SHOT, Shoot.Status.EDITING])
    if now - start < timedelta(days=45):
        return rng.choice([Shoot.Status.EDITING, Shoot.Status.DELIVERED])
    return Shoot.Status.PAID if rng.random() < 0.8 else Shoot.Status.DELIVERED


def seed_shoots(studio, clients, locations, packages, rng: random.Random) -> list[Shoot]:
    today = timezone.localdate()
    now = timezone.now()
    couples = [c for c in clients if c.partner_name]
    singles = [c for c in clients if not c.partner_name]
    # Two shoots land in the coming week, so the dashboard has something to show.
    offsets = [2, 5, *sorted(rng.sample(range(-360, 95), 38))]
    shoots, future_index = [], 0
    for offset in offsets:
        day = today + timedelta(days=offset)
        is_weekend = day.weekday() >= 5
        if is_weekend and rng.random() < 0.7:
            kind, client = "wedding", rng.choice(couples)
            start = _aware(day, rng.choice([10, 14]))
            location = rng.choice(locations[:5])
        else:
            kind = rng.choice(["portrait", "portrait", "family", "business"])
            client = rng.choice(singles)
            start = _aware(day, rng.randint(9, 17), rng.choice([0, 30]))
            location = rng.choice(locations[5:])
        package = rng.choice(packages[kind])
        shoot = Shoot.objects.create(
            studio=studio,
            client=client,
            package=package,
            location=location,
            title=_title(kind, client),
            price=package.price,
        )
        services.save_main_event(shoot, start)
        status = _status_for(start, now, rng, future_index)
        if start > now:
            future_index += 1
        services.set_status(shoot, status)
        shoots.append(shoot)
    return shoots


def seed_other_events(studio, clients, rng: random.Random) -> int:
    today = timezone.localdate()
    count = 0
    meeting_days = [1, 3, *rng.sample(range(-14, 42), 8)]
    for offset in meeting_days:
        client = rng.choice(clients)
        start = _aware(today + timedelta(days=offset), rng.choice([9, 11, 16, 18]))
        Event.objects.create(
            studio=studio,
            kind=Event.Kind.MEETING,
            title=f"Sestanek: {client.full_name}",
            client=client,
            start=start,
            end=start + timedelta(hours=1),
        )
        count += 1
    personal = [
        (4, "Servis fotoaparata", 10, 1),
        (12, "Delavnica Lightroom", 9, 6),
        (-20, "Nakup objektiva", 15, 1),
        (30, "Varnostna kopija arhiva", 20, 2),
    ]
    for offset, title, hour, hours in personal:
        start = _aware(today + timedelta(days=offset), hour)
        Event.objects.create(
            studio=studio,
            kind=Event.Kind.PERSONAL,
            title=title,
            start=start,
            end=start + timedelta(hours=hours),
        )
        count += 1
    holiday = timezone.make_aware(datetime.combine(today + timedelta(days=50), time.min))
    Event.objects.create(
        studio=studio,
        kind=Event.Kind.PERSONAL,
        title="Dopust",
        start=holiday,
        end=holiday + timedelta(days=3),
        all_day=True,
    )
    return count + 1


def seed_studio(studio) -> dict[str, int]:
    rng = random.Random(2026)  # noqa: S311  (demo data, not security)
    locations, packages = seed_catalogue(studio)
    clients = seed_clients(studio, rng)
    shoots = seed_shoots(studio, clients, locations, packages, rng)
    others = seed_other_events(studio, clients, rng)
    return {
        "locations": len(locations),
        "packages": sum(len(p) for p in packages.values()),
        "clients": len(clients),
        "shoots": len(shoots),
        "events": Event.objects.for_studio(studio).count(),
        "other events": others,
    }
