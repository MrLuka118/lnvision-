# Aperture Studio

Read AGENTS.md, PLAN.md and PROGRESS.md first each session. Work on `luka`; never commit
on production. Preserve existing work. Commit each verified working step. The current user's
build specification supersedes older worker instructions in tasks/ and docs/NACRT.md.

## Stack and conventions
Django 5.2 / Python 3.13, PostgreSQL, Redis/Celery, local storage in development and R2 in
production. Django templates, Cotton components, HTMX 2.0.10, Alpine CSP, Tailwind v4.
Migrate the existing static asset pipeline to Vite/django-vite. No React.
Tenant models extend TenantModel; all queries use for_studio(request.studio), CRUD uses
StudioScopedMixin and StudioModelForm limits relationship choices. Add URL cases to
apps/core/tests/tenancy.py. English translation message IDs, Slovenian default locale.
Decimal for money, eur template filter. Dates use DateInput. Never commit secrets.

## Commands
- Infrastructure: `colima start`, `docker compose up -d`
- Python: `uv sync`, `uv run pytest -q`, `uv run ruff check .`
- Django: `uv run python manage.py check`, `uv run python manage.py makemigrations --check --dry-run`
- Container equivalents: `docker compose exec -T web ...`
- Frontend (after Vite setup): `npm ci`, `npm run build`, `npm run dev`
- Visual checks: Playwright scripts under scripts/; save desktop/mobile dark/light captures.

## Design rules
Darkroom, but futuristic: warm black and warm paper, restrained amber/safelight accent,
editorial display serif with precise sans UI, tabular money/dates. Photography is primary.
Tokens in Tailwind @theme for colours, radii, shadows, durations 120/240/480ms and soft expo
entrances. Iris root View Transitions, subtle crossfades for partial swaps; progressively
 enhanced with normal navigation fallback. Shared element names must be unique.
Glass only for navigation, gallery toolbar and dialogs, with contrast and frosted fallback.
No stacked glass, generic grey card grids, purple gradients or emoji. Thin rules and space.
Animate transform/opacity/clip-path/filter; reduced motion disables iris, Lenis and staggers.
Lenis only on public pages. GSAP ScrollTrigger/SplitText/Flip where appropriate; PhotoSwipe
for galleries; Chart.js for finances. Responsive 360–2560px, visible focus, labelled controls,
AA contrast and alt text. Review screenshots and correct faults before marking phases done.
