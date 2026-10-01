# UI/UX audit

Date: 2026-09-23. Branch `faza-5-finance`, demo studio "Studio Svetloba".

Method: `scripts/ui_audit.mjs` screenshots every page at 390 px and 1440 px (dark scheme) into
`screenshots/before/` and records console errors, overflow and tap targets under 44 px.
`scripts/ui_clicks.mjs` clicks every non-destructive control on a fresh page load.
`scripts/ui_flows.mjs` runs the forms, dialogs, HTMX swaps and client gallery end to end.

Working well (no change needed): client search (HTMX, URL sync, empty state), client
create/edit/delete, calendar navigation, views, event dialog and subscribe dialog, gallery share
dialog, photo menu, sections, client gallery favourites + identify dialog, lightbox (mouse,
keyboard, touch), ZIP dialog, favourites filter, portfolio inquiry, settings saves, theme switch,
mobile tab bar and account button. No horizontal overflow on any page at 390 px.

Severity: **H** broken or inaccessible, **M** clearly wrong or inconsistent, **L** polish.
Fix order: functional first, then shared tokens/components, then pages.

## A. Functional

- [x] **A1 H – every page: console error on navigation.** `pageerror: Transition was aborted
  because of invalid state. ViewTransition opt-in disabled` after most cross-document navigations
  (login, links, form POST redirects). **Done:** the new page intermittently arrives with no
  transition and Chrome rejects a promise that no page code can reach. Moving the opt-in out of
  its media query, a render-blocking `<link rel=expect>` and an inline opt-in didn't help, and
  the root cause wasn't isolated (it only happens when the app's JS is fetched). An inline head
  script settles only that `InvalidStateError`; navigation is unaffected.
- [x] **A2 H – gallery editor: "Izbriši fotografijo" deletes with no confirmation.** Irreversible.
  Fix: a shared confirm dialog (glass modal) wired to `hx-confirm` and `data-confirm` on forms,
  used by every destructive action.
- [x] **A3 H – shoot detail: "Odpovej fotografiranje" cancels at once, no confirmation.** It is also a
  20 px tall text button. Fix: use the shared confirm dialog and a proper quiet button.
- [x] **A4 H – all forms and HTMX actions: no pending state.** Nothing shows a request is in
  flight (`includeIndicatorStyles: false` and no replacement). Slow uploads, status changes and
  saves can be double-submitted. Fix: global `aria-busy` + disabled submitter + spinner on
  `.btn` during `htmx:beforeRequest` and native form submit.
- [x] **A5 M – `/koledar/dogodki/<pk>/` opened directly renders an unstyled HTML fragment.** Fix: full
  page for non-HTMX requests (fragment stays for the calendar popover).
- [x] **A6 M – no styled 404/500 pages.** Production would show the bare Django text. Fix: add
  `404.html` and `500.html` using the design system.
- [x] **A7 M – dialogs only close with Esc in Safari/Firefox.** `closedby="any"` is Chromium-only,
  and the modals have no visible close button. Fix: backdrop click polyfill and a close button in
  the shared modal.
- [x] **A8 L – shoot status change gives no confirmation message.** The pipeline updates, but
  screen readers get nothing. Fix: announce the new status in a live region.
- [x] **A9 L – theme switch writes a stale `theme-color` (#262626)** instead of the slate surround.

## B. Design tokens and shared components

- [x] **B1 H – tap targets under 44 px on phones.**
  - account button 36 px
  - `.btn-sm` and `.btn-icon` 36 px (calendar prev/next/new, toolbars)
  - checkboxes 18 px
  - text actions like "Izbriši …" 20 px
  - client gallery hearts and bar buttons 40 px

  Fix in the component layer: `.btn-sm` grows to 44 px on `pointer: coarse`, checkbox rows get
  a 44 px label hit area, and text actions use the new `.action-link` (44 px).
- [x] **B2 H – light theme fails WCAG AA and does not match the direction.**
  - accent text on surround measures 2.9:1
  - accent text on surface measures 3.4:1
  - the primary button (white on gold) measures 3.5:1
  - the light palette is still the old neutral grey, not slate

  Fix: slate light palette, darker gold for text (≥ 4.5:1), dark text on the gold button.
- [x] **B3 M – input borders 1.7:1 against the surround** (WCAG 1.4.11 wants 3:1 for control
  boundaries). Fix: a stronger `--line-strong` for inputs and checkboxes.
- [x] **B4 M – `ink-3` on raised surfaces is 4.4:1** (tertiary meta text on list rows). Fix: lift
  `--ink-3`.
- [x] **B5 M – heading scale too flat.** Section H2s ("Izbor strank", "Kdaj in kje") are nearly the
  size of the page H1, and stat numbers compete with the title. Fix: a clear section-title
  token (`.section-title`), smaller stat numerals.
- [x] **B6 M – list rows truncate the primary text first.**
  - clients on mobile: "Anže Kast…", because the two-line meta column keeps its full width
  - shoot rows on client detail

  Fix: the shared row lets the title shrink last and the meta wrap under it on narrow screens.
- [x] **B7 L – form grid misalignment:** a select next to an input with help text sits 13 px lower
  (shoot form "Paket"/"Cena"). Fix: align field grid items to start.

## C. Pages

- [x] **C1 H – client gallery hero and grid (1440 px).** The grid fills two columns and leaves the
  right third empty, and the cover's title sits low and heavy. Fix: balanced columns, refined
  hero (owned by lead).
- [x] **C2 M – dashboard, desktop:** the "Čakajo na odgovor" heading and the "Vsa povpraševanja"
  link wrap to two lines in the narrow aside. Fix: header row stacks the link and the heading
  stays on one line.
- [x] **C3 M – shoot detail: time shows "00:00"** for an inquiry that has a date but no time.
  Fix: show "Čas še ni določen" when the time is unset or all-day.
- [x] **C4 M – calendar week/day view:** one-hour events clip the title mid-line ("Sestanek:
  Špela / Rozman" cut in half). Fix: short events show time + single-line title with ellipsis.
- [x] **C5 L – styleguide:** demo buttons (lightbox toolbar, dialog actions) do nothing. That is
  expected on a style page, so it stays as it is.
- [x] **C6 L – portfolio public:** the "Nedavne zgodbe" grid leaves an empty third column with two
  stories. Fix: auto-fit grid.

2026-09-28: re-audited during Codex completion. Warm darkroom/print-room palette replaces
slate. Existing B5–B7/C2–C6 fixes verified and dashboard mobile rows refined. See PROGRESS.md
and docs/VERIFICATION.md for current evidence.
