# Progress — 2026-09-28

## Audit
Working branch: luka, initially clean. Existing implementation includes authentication,
tenancy, clients, shoots/calendar/ICS, upload derivatives, private galleries, public portfolio
and finance models/recurring jobs. Previous session reported 171 passing tests.
Missing: finance screens, Vite integration, required darkroom visual alignment, complete
dashboard metrics, final systematic verification. AGENTS.md and PLAN.md now track this build.

## In progress
Restoring local PostgreSQL/Redis services and checking the baseline. Docker daemon was stopped.

## Next
Vite build, design system alignment, finish finance and dashboard, security and visual audit.

## Known issues / decisions
- Existing frontend uses vendored ESM/import maps and django-tailwind-cli; migrate to Vite.
- Existing palette is blue slate with Outfit; requested palette is warm darkroom and serif.
- Old UI audit lists heading hierarchy, mobile row truncation and all-day time issues.
- Existing photo pipeline uses libvips and LQIP; retain its efficient working implementation
  while reviewing requested Pillow/WebP/ThumbHash support.
- No credentials requested; local development needs no external R2 or SMTP credentials.
- Do not mark APP_COMPLETE until the plan and verification are complete.

## Verified working step: foundation + finance
- Baseline: 210 tests passed against PostgreSQL.
- Vite/django-vite now bundles Tailwind v4, self-hosted Fraunces/Inter, HTMX and Alpine.
- Warm darkroom/print-room tokens, grain, iris transitions, keyboard skip link and branding.
- Finance ledger CRUD, recurring/category management, private receipt download, period filters,
  spreadsheet-safe CSV, remaining-payment suggestions and lazy-loaded Chart.js reports.
- Validation: 239 tests pass; 33 finance tests pass; Django check, Ruff and build clean.
- Playwright foundation screenshots reviewed at desktop/mobile; dark/light captures saved under
  screenshots/. In-app Browser was unavailable; standalone Playwright is installed.
- Remaining visual fixes: dashboard inquiry header crowding, gallery 40px favourites; full
  final matrix still pending. Receipt and relationship validation are covered by tests.
