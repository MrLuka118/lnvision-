import logging

from celery import shared_task

from .imaging import UnreadableImage
from .models import Photo

logger = logging.getLogger(__name__)


@shared_task(bind=True, acks_late=True, max_retries=2, default_retry_delay=30)
def process_photo(self, photo_id: int):
    from .services import process

    photo = Photo.objects.select_related("gallery", "studio").filter(pk=photo_id).first()
    if photo is None:
        return
    try:
        process(photo)
    except UnreadableImage as exc:
        Photo.objects.filter(pk=photo_id).update(status=Photo.Status.FAILED, error=str(exc)[:500])
    except Exception as exc:
        logger.exception("Processing photo %s failed", photo_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        Photo.objects.filter(pk=photo_id).update(status=Photo.Status.FAILED, error=str(exc)[:500])
