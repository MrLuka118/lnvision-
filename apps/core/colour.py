"""WCAG contrast helpers, used to turn a photo's dominant colour into a legible accent."""

import colorsys


def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def accessible_accent(hex_colour: str, background: str, minimum: float = 4.5) -> str:
    """Keep the hue, add a little saturation, move lightness away from the background until the
    colour reaches `minimum` contrast against it."""
    try:
        r, g, b = (int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except (ValueError, IndexError):
        return "#ededed" if luminance(background) < 0.2 else "#1c1c1c"
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    s = min(1.0, max(s, 0.35))
    step = 0.02 if luminance(background) < 0.2 else -0.02
    for _ in range(60):
        rr, gg, bb = colorsys.hls_to_rgb(h, lightness, s)
        candidate = f"#{round(rr * 255):02x}{round(gg * 255):02x}{round(bb * 255):02x}"
        if contrast(candidate, background) >= minimum:
            return candidate
        lightness = min(1.0, max(0.0, lightness + step))
    return "#ffffff" if step > 0 else "#000000"


def text_on(hex_colour: str) -> str:
    """Near-black or near-white, whichever reads better on the colour."""
    return (
        "#161616"
        if contrast(hex_colour, "#161616") >= contrast(hex_colour, "#f5f5f5")
        else "#f5f5f5"
    )
