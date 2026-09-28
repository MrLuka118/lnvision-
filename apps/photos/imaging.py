"""libvips renditions: sRGB, never upscaled, mildly sharpened, metadata stripped."""

import base64
import io
from dataclasses import dataclass, field
from pathlib import Path

import blurhash
import pyvips
from PIL import Image

from .models import RENDITION_FORMATS, RENDITION_WIDTHS

MAX_PIXELS = 200_000_000  # refuses decompression bombs; a 100 MP medium format file is 1e8
SAVE_OPTIONS = {
    "avif": {"Q": 55, "effort": 4, "keep": "none"},
    "jpg": {"Q": 82, "optimize_coding": True, "interlace": True, "keep": "none"},
    "webp": {"Q": 80, "keep": "none"},
}
ROTATED = {5, 6, 7, 8}  # EXIF orientations that swap width and height


class UnreadableImage(ValueError):
    pass


@dataclass
class Rendered:
    width: int
    height: int
    widths: list[int]
    lqip: str
    dominant_color: str
    luminance: float
    files: dict[tuple[int, str], bytes] = field(default_factory=dict)
    blurhash: str = ""


def inspect(path: Path) -> tuple[int, int]:
    """Oriented size, reading only the header. Raises UnreadableImage for anything else."""
    try:
        image = pyvips.Image.new_from_file(str(path), access="sequential")
    except pyvips.Error as exc:
        raise UnreadableImage(str(exc)) from exc
    if image.width * image.height > MAX_PIXELS:
        raise UnreadableImage("image too large")
    orientation = image.get("orientation") if image.get_typeof("orientation") else 1
    if orientation in ROTATED:
        return image.height, image.width
    return image.width, image.height


def target_widths(width: int, widths=RENDITION_WIDTHS) -> list[int]:
    targets = [w for w in widths if w < width]
    if width < widths[-1]:
        targets.append(width)
    return targets or [width]


def _thumbnail(path: Path, width: int) -> pyvips.Image:
    image = pyvips.Image.thumbnail(
        str(path), width, height=10_000_000, size="down", export_profile="srgb"
    )
    if image.hasalpha():
        image = image.flatten(background=[255, 255, 255])
    # Each rendition is encoded to several formats; decode once instead of re-reading the file
    # (which also fails for sequential-only sources such as PNG at full size).
    return image.copy_memory()


def watermark(image: pyvips.Image, text: str) -> pyvips.Image:
    """Quiet text in the lower right corner, 45% white."""
    size = max(11, round(image.width * 0.018))
    mask = pyvips.Image.text(text, font=f"DejaVu Sans {size}", dpi=72)
    white = mask.new_from_image([255, 255, 255]).copy(interpretation="srgb")
    overlay = white.bandjoin((mask * 0.45).cast("uchar"))
    margin = round(image.width * 0.025)
    x = max(0, image.width - overlay.width - margin)
    y = max(0, image.height - overlay.height - margin)
    return image.composite2(overlay, "over", x=x, y=y)[:3]


def render(path: Path, *, formats=RENDITION_FORMATS, watermark_text: str = "") -> Rendered:
    width, height = inspect(path)
    rendered = Rendered(width, height, [], "", "", 0.0)
    for target in target_widths(width):
        image = _thumbnail(path, target)
        if target < width:
            image = image.sharpen(sigma=0.5)
        if watermark_text:
            image = watermark(image, watermark_text)
        for fmt in formats:
            rendered.files[(target, fmt)] = image.write_to_buffer(f".{fmt}", **SAVE_OPTIONS[fmt])
        rendered.widths.append(target)

    tiny = _thumbnail(path, 24)
    # Pillow handles the tiny preview; the existing libvips pipeline retains full-size efficiency.
    preview = Image.open(io.BytesIO(tiny.write_to_buffer(".png"))).convert("RGB")
    pixels = list(preview.get_flattened_data())
    matrix = [pixels[y * preview.width : (y + 1) * preview.width] for y in range(preview.height)]
    rendered.blurhash = blurhash.encode(matrix, components_x=4, components_y=3)
    decoded = blurhash.decode(rendered.blurhash, 24, max(1, round(24 * height / width)))
    placeholder = Image.new("RGB", (24, len(decoded)))
    placeholder.putdata([tuple(pixel) for row in decoded for pixel in row])
    output = io.BytesIO()
    placeholder.save(output, format="WEBP", quality=40)
    rendered.lqip = "data:image/webp;base64," + base64.b64encode(output.getvalue()).decode()
    small = _thumbnail(path, 64)
    r, g, b = (round(small[band].avg()) for band in range(3))
    rendered.dominant_color = f"#{r:02x}{g:02x}{b:02x}"
    rendered.luminance = round(small.colourspace("b-w").avg() / 255, 3)
    return rendered
