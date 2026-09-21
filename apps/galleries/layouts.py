"""How each theme arranges a list of photos."""

from itertools import groupby


def photobook_rows(photos) -> list[list]:
    """Like a book's spreads: a landscape gets the full width, two portraits share a row."""
    rows, pending = [], None
    for photo in photos:
        portrait = photo.aspect_ratio < 1
        if portrait and pending is not None:
            rows.append([pending, photo])
            pending = None
        elif portrait:
            pending = photo
        else:
            if pending is not None:
                rows.append([pending])
                pending = None
            rows.append([photo])
    if pending is not None:
        rows.append([pending])
    return rows


def group_by_section(photos, sections) -> list[dict]:
    """Photos without a section first, then each chapter in order; empty chapters are skipped."""
    by_section = {
        key: list(items)
        for key, items in groupby(
            sorted(photos, key=lambda p: (p.section_id or 0, p.position, p.pk)),
            key=lambda p: p.section_id,
        )
    }
    groups = []
    if by_section.get(None):
        groups.append({"section": None, "photos": by_section[None]})
    for section in sections:
        if by_section.get(section.pk):
            groups.append({"section": section, "photos": by_section[section.pk]})
    return groups
