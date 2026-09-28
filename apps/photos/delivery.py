"""Handing files to visitors: short-lived signed URLs on S3, streamed from disk otherwise."""

from django.http import FileResponse, HttpResponseRedirect
from django.utils.http import content_disposition_header

SIGNED_URL_SECONDS = 600


def file_response(storage, name: str, filename: str):
    if hasattr(storage, "bucket_name"):  # django-storages S3: the bucket stays private
        url = storage.url(
            name,
            parameters={"ResponseContentDisposition": content_disposition_header(True, filename)},
            expire=SIGNED_URL_SECONDS,
        )
        response = HttpResponseRedirect(url)
    else:
        response = FileResponse(storage.open(name, "rb"), as_attachment=True, filename=filename)
    response["Cache-Control"] = "private, no-store"
    return response
