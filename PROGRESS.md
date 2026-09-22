# Progress

Plan: `docs/NACRT.md`. Worker tasks: `tasks/`. Claude plans, builds the design system and
security-sensitive parts, and reviews; the Antigravity worker writes the rest.

## Done

- **Phase 1** – design system (tokens, Liquid Glass, cotton components, style page), login
  (allauth, e-mail + Google), dashboard, tenancy layer and meta-tests.
- **Phase 2** – clients, shoots (pipeline, packages, locations), calendar (FullCalendar,
  drag and drop, ICS feed), dashboard "next 7 days".
- **Phase 3** – chunked upload, Celery renditions (libvips, AVIF/JPEG, LQIP, GPS strip,
  watermark), gallery editor, client gallery (token, password, expiry, favourites, notes,
  downloads, ZIP by e-mail, analytics).

## Phase 4 – public portfolio (in progress, branch `faza-4-portfolio`)

- [x] Models: Portfolio, PortfolioCategory, PortfolioStory (+ photos), Inquiry
- [x] Public pages `/p/<slug>/`: home, category, story; Lenis + GSAP
- [x] Inquiry form → client, shoot (inquiry), tentative event, two e-mails; honeypot,
      signed timestamp, rate limit; autoresponder carries no visitor text
- [x] Plain-text e-mail helper (`apps/core/mail.py`), no HTML escaping
- [x] Dashboard widget "Waiting for a reply"
- [x] Tests: 26 portfolio tests incl. N+1 checks; translations
- [ ] Portfolio management UI (worker 4A: forms, views, urls, templates)
- [ ] Tenancy URL cases for the management UI; review; merge

## Phase 5 – finance (next)

## Phase 6 – polish (accessibility, Lighthouse, security review, README)
