# 008 – UI: pages adopt the shared components

Read `tasks/README.md` first. Context: `UI-UX-AUDIT.md` items B5, B6, B7, C2, C3, C4, C6.
Pure template/CSS work plus one queryset annotation. **Don't edit** `assets/css/tokens.css`,
`assets/css/components.css`, `assets/css/layout.css`, `assets/css/gallery.css`, `static/js/`,
`templates/cotton/` (except where section 6 allows it), `templates/base.html`, `templates/partials/`.

Shared classes you use (already in `assets/css/components.css`):
- `.section-title`: the one size for an in-page `<h2>` (replaces `text-xl` / `text-2xl`).
- `.row-aside`: the trailing column of a `.row` (date, count, badge). On a phone it drops
  under the title so the name is not cut off.
- `.action-link`: quiet 44 px text action.
- `text-accent-ink`: gold for TEXT (the `accent` colour is for fills only; it fails contrast as
  text in the light theme).

## 1. Section headings (B5)

In the templates below, every `<h2>` whose class list contains `text-xl` or `text-2xl`: replace
that size class with `section-title` and keep the other classes (margins etc.).
`clients/detail.html`, `core/dashboard.html`, `galleries/_activity.html`,
`galleries/_photo_grid.html`, `galleries/editor.html`, `scheduling/_event_form.html`,
`scheduling/calendar.html`, `shoots/detail.html`, `shoots/list.html`. Leave `styleguide.html`,
`allauth/`, and everything under `*/public/` alone.
In `galleries/_photo_grid.html` the section heading also has a count `<span>`; keep it.

## 2. List rows (B6)

In `templates/clients/_results.html`, `templates/clients/detail.html` (the shoot rows) and
`templates/shoots/_row.html`: the third `<span>` inside `a.row` (the trailing column) gets
`class="row-aside tnum"` instead of its current utility classes (`tnum text-right text-sm
text-ink-2` / `grid justify-items-end gap-1`). Keep the inner markup. In `_results.html` the
inner `<span class="block text-ink">` (the date) stays.

## 3. Dashboard (C2)

`templates/core/dashboard.html`:
- Both section header rows (`mb-4 flex items-baseline justify-between gap-4`): the heading gets
  `section-title` (see 1). The link beside it ("Open calendar", "All inquiries") becomes
  `<a class="action-link shrink-0" …>text <c-icon name="chevron-right" size="sm" /></a>`
  (drop `link text-sm`). Change the row to `flex items-center justify-between gap-4`.
- "Waiting for a reply" must stay on one line in the 22rem aside on desktop: give the `<h2>`
  `whitespace-nowrap`.
- The "Today" `<h3>`: `text-accent` → `text-accent-ink`.

## 4. Shoot time for all-day or undated shoots (C3)

On `/fotografiranja/<pk>/` the "Time" fact shows "00:00" for an inquiry created from the
portfolio (its calendar event is `all_day=True`). In `apps/shoots/models.py`, the queryset
method that annotates `starts_at`/`ends_at` from the main event (around line 57): also annotate
`all_day` from the same event (same Subquery pattern). In `templates/shoots/detail.html`, the
"Time" `<dd>`: if `object.all_day` show `{% translate "All day" %}` (existing msgid), else the
current times. In `templates/shoots/_row.html`, don't print `H:i` for all-day shoots (show only
the weekday). Add a test that the detail page of an all-day shoot does not contain "00:00".

## 5. Calendar: short events (C4)

In week and day view a one-hour event cuts its title off half-way through a line. In
`assets/css/calendar.css` (look at how `.cal-event-title` and the event content are styled; the
content is built in `static/js/calendar.js` `eventContent` — read it, don't change it): inside
`.fc-timegrid-event`, the title is one line with ellipsis (`white-space: nowrap; overflow:
hidden; text-overflow: ellipsis`), and for `.fc-timegrid-event-short` put time and title on one
line. Nothing may be clipped mid-glyph.

## 6. Form field alignment (B7)

On `/fotografiranja/novo/` the "Paket" select sits ~13 px lower than the "Cena" input next to
it in the same two-column row. Find the cause (inspect the rendered HTML of both fields with
`curl -s -b` or the test client; the markup comes from `templates/cotton/field.html` and the
form in `apps/shoots/forms.py`) and fix it so both controls align at the top. You may edit
`templates/cotton/field.html` for this ONLY if the cause is there; say what the cause was.

## 7. Public portfolio (C6)

`assets/css/portfolio.css`:
- `.pf-cards`: `auto-fill` → `auto-fit`, so two stories fill the row instead of leaving an
  empty third column.
- `.pf-hero-line`: remove `font-style: italic` (Outfit has no italic; the browser fakes it) and
  use `font-weight: 350` instead.

## Done

The five checks from `tasks/README.md` pass. Report the changed files and, for section 6, the
cause.
