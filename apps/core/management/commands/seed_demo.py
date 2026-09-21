from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.services import ensure_studio

User = get_user_model()


class Command(BaseCommand):
    """Seed a demo user and studio."""

    help = _("Create or update demo user and studio for testing")

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default="demo-geslo-2026",
            help="Demo user password (default: demo-geslo-2026)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo user before seeding",
        )

    def handle(self, *args, **options):
        """Main handler."""
        if options["reset"]:
            self.reset_demo()
        with transaction.atomic():
            user = self.seed_user(options["password"])
            self.seed_studio(user)
            self.seed_email(user)
            self.seed_business(user.studio)
        self.stdout.write(self.style.SUCCESS("Demo user seeded successfully"))
        self.stdout.write(self.style.SUCCESS(f"Email: {user.email}"))
        self.stdout.write(self.style.SUCCESS(f"Password: {options['password']}"))
        self.stdout.write(self.style.SUCCESS("http://localhost:8000/"))

    def reset_demo(self):
        """Delete demo user if exists."""
        try:
            user = User.objects.get(email="demo@aperture.local")
            user.delete()
            self.stdout.write(self.style.WARNING("Deleted existing demo user"))
        except User.DoesNotExist:
            pass

    def seed_user(self, password):
        """Create or update demo user."""
        user, created = User.objects.update_or_create(
            email="demo@aperture.local",
            defaults={
                "first_name": "Maja",
                "last_name": "Kovač",
                "is_staff": True,
            },
        )
        user.set_password(password)
        user.save()
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} demo user")
        return user

    def seed_studio(self, user):
        """Create or update demo studio."""
        ensure_studio(user, "Studio Svetloba")
        self.stdout.write("Ensured demo studio")

    def seed_business(self, studio):
        """Clients, shoots and calendar for an empty demo studio (skipped when it has data)."""
        from apps.clients.models import Client
        from apps.core.demo import seed_studio

        if Client.objects.for_studio(studio).exists():
            self.stdout.write("Demo studio already has data; use --reset to start over")
            return
        counts = seed_studio(studio)
        self.stdout.write(", ".join(f"{n} {name}" for name, n in counts.items()))

    def seed_email(self, user):
        """Create or update verified email address."""
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={
                "verified": True,
                "primary": True,
            },
        )
        self.stdout.write("Set email as verified and primary")
