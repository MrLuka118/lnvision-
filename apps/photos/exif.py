"""exiftool wrapper: read the few tags we show, and remove GPS without re-encoding."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.utils import timezone

EXIFTOOL = shutil.which("exiftool") or "exiftool"
TAGS = {
    "Make": "make",
    "Model": "model",
    "LensModel": "lens",
    "FocalLength": "focal_length",
    "FNumber": "aperture",
    "ExposureTime": "shutter",
    "ISO": "iso",
    "Artist": "artist",
    "Copyright": "copyright",
}


def _run(*args: str) -> str:
    result = subprocess.run(  # noqa: S603
        [EXIFTOOL, *args], capture_output=True, text=True, timeout=60, check=True
    )
    return result.stdout


def read(path: Path) -> tuple[dict, datetime | None]:
    """Camera and exposure details (never GPS) and the time the photo was taken."""
    raw = json.loads(_run("-json", "-n", *[f"-{t}" for t in TAGS], "-DateTimeOriginal", str(path)))
    data = raw[0] if raw else {}
    details = {key: data[tag] for tag, key in TAGS.items() if data.get(tag) not in (None, "")}
    taken_at = None
    if value := data.get("DateTimeOriginal"):
        try:
            taken_at = timezone.make_aware(datetime.strptime(str(value)[:19], "%Y:%m:%d %H:%M:%S"))
        except ValueError:
            taken_at = None
    return details, taken_at


def strip_gps(path: Path) -> None:
    """Remove location tags in place; pixels and other metadata are untouched."""
    _run("-overwrite_original", "-quiet", "-gps:all=", "-XMP-exif:GPS*=", str(path))


def has_gps(path: Path) -> bool:
    raw = json.loads(_run("-json", "-n", "-gps:all", str(path)))
    return any(key.startswith("GPS") for key in (raw[0] if raw else {}))
