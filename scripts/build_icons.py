"""Build static/icons/sprite.svg from pinned Lucide icons.

Run: uv run python scripts/build_icons.py
"""

import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VERSION = "1.47.0"
ICONS = [
    "layout-dashboard",
    "calendar",
    "users",
    "images",
    "camera",
    "wallet",
    "settings",
    "log-out",
    "plus",
    "search",
    "x",
    "chevron-left",
    "chevron-right",
    "chevron-down",
    "heart",
    "download",
    "share-2",
    "lock",
    "sun",
    "moon",
    "check",
    "triangle-alert",
    "info",
    "menu",
    "ellipsis",
    "upload",
    "mail",
    "map-pin",
    "clock",
    "eye",
    "message-circle",
    "trash-2",
    "pencil",
    "filter",
    "link",
    "external-link",
    "layout-grid",
    "list",
    "user",
    "arrow-left",
    "circle-check",
    "aperture",
    "sliders-horizontal",
    "sun-moon",
]

URL = "https://cdn.jsdelivr.net/npm/lucide-static@{v}/icons/{n}.svg"


def fetch(name: str) -> tuple[str, str]:
    with urllib.request.urlopen(URL.format(v=VERSION, n=name), timeout=20) as r:  # noqa: S310
        return name, r.read().decode()


def main() -> None:
    with ThreadPoolExecutor(8) as pool:
        svgs = dict(pool.map(fetch, ICONS))
    symbols = []
    for name in ICONS:
        svg = re.sub(r"<!--.*?-->", "", svgs[name], flags=re.S)
        inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        inner = re.sub(r"\s+", " ", inner).strip()
        symbols.append(f'<symbol id="{name}" viewBox="0 0 24 24">{inner}</symbol>')
    out = Path(__file__).resolve().parent.parent / "static/icons/sprite.svg"
    out.write_text('<svg xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(symbols) + "\n</svg>\n")
    print(f"{len(symbols)} icons -> {out}")


if __name__ == "__main__":
    main()
