# Progress

Plan: `docs/NACRT.md`. Worker tasks: `tasks/`. Claude plans, builds the design system and
security-sensitive parts, and reviews; the Antigravity worker writes the rest.

## Status (2026-09-22, session restart)

Stack starts, `check` clean, no pending migrations, ruff clean, 171 tests green.

| Phase / module | State |
|---|---|
| 1 Skeleton, auth, design system, tenancy | ✅ |
| 2 Clients, shoots, calendar, ICS | ✅ |
| 3a Upload pipeline, gallery editor | ✅ |
| 3b Client gallery | ✅ |
| 4 Public portfolio + inquiry | ✅ merged 2026-09-22 |
| 5 Finance | 🟡 001 models done (DeepSeek V4 Pro via aider); 002–005 next |
| 6 Polish (a11y, Lighthouse, security review, README) | ⬜ |

Decisions:
- The plan lives in `docs/NACRT.md` (it covers the whole spec); no separate `PLAN.md`.
- Working autonomously across phases now, no pause for "naprej" between phases.
- Portfolio management is reached from Settings, not the main nav (the main nav stays at five
  destinations for the mobile tab bar).
- Story photo picker keeps gallery order; manual ordering is a phase 6 nice-to-have.

Known issues for phase 6:
- Console error after the login redirect: "Transition was aborted because of invalid state"
  (View Transitions on a form POST navigation).
- Font preload warnings on some pages.

## Done

- **Phase 1** – design system (tokens, Liquid Glass, cotton components, style page), login
  (allauth, e-mail + Google), dashboard, tenancy layer and meta-tests.
- **Phase 2** – clients, shoots (pipeline, packages, locations), calendar (FullCalendar,
  drag and drop, ICS feed), dashboard "next 7 days".
- **Phase 3** – chunked upload, Celery renditions (libvips, AVIF/JPEG, LQIP, GPS strip,
  watermark), gallery editor, client gallery (token, password, expiry, favourites, notes,
  downloads, ZIP by e-mail, analytics).

## Phase 4 – public portfolio (done)

- [x] Models: Portfolio, PortfolioCategory, PortfolioStory (+ photos), Inquiry
- [x] Public pages `/p/<slug>/`: home, category, story; Lenis + GSAP
- [x] Inquiry form → client, shoot (inquiry), tentative event, two e-mails; honeypot,
      signed timestamp, rate limit; autoresponder carries no visitor text
- [x] Plain-text e-mail helper (`apps/core/mail.py`), no HTML escaping
- [x] Dashboard widget "Waiting for a reply"
- [x] Tests: 26 portfolio tests incl. N+1 checks; translations
- [x] Portfolio management UI (worker 4A: forms, views, urls, templates)
- [x] Tenancy URL cases for the management UI
- [x] Review fixes: picker shows selection, missing `image-plus` icon, translations
- [x] Management view tests (worker, task 006)
- [x] Review fixes: empty slug is made from the name/title and a slug already used in the studio
      is refused (was an IntegrityError); a story without a gallery offers no photos; the
      story cover always stays one of the story's photos; story list uses the model order
- [x] Tests no longer compare English strings (they broke once translations were compiled)
- [x] Merged into `main`

## Phase 5 – finance (in progress, branch `faza-5-finance`)

- [ ] 001 models · [ ] 002 recurring · [ ] 003 ledger · [ ] 004 dashboard · [ ] 005 invoices

## Phase 6 – polish (accessibility, Lighthouse, security review, README)
