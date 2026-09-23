# 007 – UI: confirmations and functional fixes

Read `tasks/README.md` first. Context: `UI-UX-AUDIT.md` items A2, A3, A5, A6, A7, A8.

The shared pieces already exist; **don't change them**, only use them:
- `static/js/actions.js` + `templates/partials/confirm_dialog.html`: a glass confirmation dialog.
  - HTMX element: add `hx-confirm="{% translate '…?' %}"`.
  - Plain POST form: add `data-confirm="{% translate '…?' %}"` on the form or on its submit button.
  - Optional on the same element: `data-confirm-detail="…"` (one sentence under the question)
    and `data-confirm-label="…"` (confirm button text; default "Potrdi").
- `.action-link` (+ `.is-danger`) in `assets/css/components.css`: a quiet 44 px text action.
- `<c-modal-close for="<dialog id>" />`: close button for a `<dialog class="modal">`, placed as
  the dialog's first child.
- `#toasts` in `templates/partials/messages.html` is always on the page; an HTMX request can
  refresh it with `hx-select-oob="#toasts"` when the response is a full page.

All user-facing strings are English msgids wrapped in `{% translate %}` / `_()`. Add the Slovenian
translation of every NEW msgid to `locale/sl/LC_MESSAGES/django.po` (append at the end, same
format as the existing entries) and run
`docker compose exec -T web python manage.py compilemessages -l sl`.

## 1. Destructive actions ask first

- `templates/galleries/_tile.html`, the "Delete photo" menu button: add
  `hx-confirm` "Delete this photo?" with `data-confirm-detail` "The original and all its sizes
  are removed. This can't be undone." and `data-confirm-label` "Delete photo" (existing msgid).
- `templates/galleries/_photo_grid.html`, the "Remove section" form: `data-confirm` on the form
  "Remove this section?" with detail "Its photos stay in the gallery, without a section."
- `templates/scheduling/_event_detail.html`, the "Remove" form: `hx-confirm` "Remove from the
  calendar?" (the form has hx-post, so hx-confirm goes on the form).
- `templates/shoots/detail.html`, the "Cancel shoot" button (line ~102): `data-confirm`
  "Cancel this shoot?" with detail "It moves to the history. You can reopen it as an inquiry."
  and `data-confirm-label` "Cancel shoot" (existing msgid). Replace its utility classes with
  `class="action-link"`. The "Delete shoot" link below it: `class="action-link is-danger"`.
- Same `action-link is-danger` class (instead of `inline-flex items-center gap-2 text-sm
  text-danger`) for "Delete client" in `templates/clients/detail.html` and the delete link in
  `templates/generic/form.html` (keep its `ml-auto`).

## 2. Status change feedback (A8)

`apps/shoots/views.py` `ShootStatusView.post`: after `services.set_status(...)` add
`messages.success(request, _("Status: %(status)s") % {"status": shoot.get_status_display()})`
(refresh the object first if needed so the display is the new status). In
`templates/shoots/detail.html`, add `hx-select-oob="#toasts"` to BOTH status forms (the ones with
`hx-select="#shoot-body"`). Add a test in `apps/shoots/tests/` that the message is set after
a status POST.

## 3. Event detail opened directly (A5)

`/koledar/dogodki/<pk>/` returns the HTMX fragment `scheduling/_event_detail.html` even for a
normal browser request, so it renders unstyled. In `apps/scheduling/views.py`
`EventDetailView`, return the fragment only when `request.htmx`; otherwise render a new
`templates/scheduling/event_detail.html` that extends `layouts/app.html`, shows a back link to
the calendar (copy the back-link markup from `templates/shoots/detail.html`), a page title with
the event's display title, and includes the fragment inside a `panel p-5` card with max width
`max-w-xl`. Add tests: HTMX request → fragment (no `<html`), normal request → full page.

## 4. Styled 404 and 500 (A6)

Create `templates/404.html` and `templates/500.html`. Both extend `layouts/auth.html` if its
blocks fit (read it), otherwise `base.html`. Content: a large display title ("Page not found" /
"Something went wrong"), one sentence, and a primary button back to the dashboard (`/`). 500 must
not rely on request context (Django renders it without context processors), so no `{{ studio }}`
or `{{ request }}`. Add a test that a missing URL returns 404 and uses `404.html`
(`assertTemplateUsed` or checking the content).

## 5. Every modal can be closed with a button (A7)

Add `<c-modal-close for="…" />` as the first child of each raw `<dialog class="modal …">`:
`templates/scheduling/calendar.html` (event-dialog, ics-dialog), `templates/galleries/editor.html`
(share-dialog), `templates/galleries/public/gallery.html` (g-identify, g-zip, g-comment).
Also change each of those dialogs' `<h2>` class list to use `section-title` instead of a
`text-*` size class, if it has one.

## Done

The five checks from `tasks/README.md` pass. Report the changed files.
