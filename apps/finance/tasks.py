from celery import shared_task

from .services import generate_recurring


@shared_task
def generate_recurring_expenses():
    """Daily beat task – materialise all missing recurring expenses."""
    generate_recurring()
