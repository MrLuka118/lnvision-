from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from apps.core.services import ensure_studio


@receiver(user_signed_up)
def create_studio_on_signup(sender, request, user, **kwargs):
    # E-mail sign-ups already have one (SignupForm.save); this covers Google sign-ups.
    ensure_studio(user)
