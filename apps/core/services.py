from django.db import IntegrityError, transaction
from django.utils.text import slugify

from .models import Studio


def unique_studio_slug(name: str) -> str:
    base = slugify(name)[:50] or "studio"
    slug, n = base, 2
    while Studio.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def ensure_studio(user, name: str = "") -> Studio:
    """Return the user's studio, creating it on first use (sign-up, social login, CLI users)."""
    try:
        return user.studio
    except Studio.DoesNotExist:
        pass
    name = name.strip() or user.get_full_name() or user.email.split("@")[0]
    for _attempt in range(3):
        try:
            with transaction.atomic():
                studio = Studio.objects.create(
                    owner=user, name=name, slug=unique_studio_slug(name), email=user.email
                )
                from apps.finance.defaults import seed_categories

                seed_categories(studio)
        except IntegrityError:
            # Lost a race on the slug or the owner; re-read and retry.
            if Studio.objects.filter(owner=user).exists():
                return Studio.objects.get(owner=user)
            continue
        user.studio = studio
        return studio
    raise RuntimeError("Could not allocate a studio slug.")
