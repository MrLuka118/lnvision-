# Aperture Studio · L&N Vision

A photography studio workspace and private client delivery experience. Django renders the
pages; HTMX enhances navigation, Alpine manages local controls, and Vite bundles Tailwind v4.
The default language is Slovenian. Darkroom and warm print-room appearances are included.

## Run locally

Requires Docker Compose, Node 22.12+ and npm. Python tooling uses `uv` and Python 3.13.
On macOS with Colima, run `colima start` first.

```sh
cp .env.example .env
# Set DJANGO_SECRET_KEY in .env to a new random value.
npm ci
npm run build
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo
```

Open **http://localhost:8000**. Demo account: `demo@aperture.local` /
`demo-geslo-2026`. Only seed this account in development. Email verification and password-reset
messages appear in Mailpit at **http://localhost:8025**. The design system is at `/styleguide/`
(DEBUG or staff only).

The frontend Compose service watches the Vite build. Alternatively run `npm run build -- --watch`
on the host. A completed build triggers Django's development reloader to refresh its manifest.
`npm run dev` serves Vite on port 5173; set `VITE_DEV_MODE=True` when using that mode.
The compiled-asset workflow is the default and matches production CSP.

## Included workflows

- Overview: next seven days of shoots/deadlines, inquiries, monthly finance, gallery activity.
- Clients: contacts, notes, shoot pipeline/history, earned revenue.
- Calendar: month/week/day/list, dragging/resizing, locations, deadlines, private ICS subscription.
- Galleries: resumable chunk uploads, progress, background processing, sections and ordering,
  cover selection, password/expiry, favourites, notes, individual downloads and emailed ZIPs.
- Public portfolio: categories, stories, inquiry form that creates a client and tentative shoot.
- Finance: income/expense CRUD, categories, recurring costs, period filters, CSV export,
  annual charts and client rankings. Existing invoice models are retained; invoice issuance
  and tax filing are not part of the requested finance workflow.
- Settings: profile, account email/password, logo, gallery accent, studio details and packages.

## Tests and review

```sh
npm run build
docker compose exec -T web pytest -q
docker compose exec -T web ruff check .
docker compose exec -T web ruff format --check .
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py makemigrations --check --dry-run
npx playwright install chromium
PW_CHANNEL=chromium node scripts/ui_flows.mjs
PW_CHANNEL=chromium node scripts/ui_audit.mjs final-dark
PW_CHANNEL=chromium THEME=light node scripts/ui_audit.mjs final-light
```

Visual scripts use the seeded demonstration database and write to ignored `screenshots/`.
The flow script performs writes in that demonstration studio; do not point it at a real studio.
`BASE_URL` overrides localhost. Screenshot routes include fixture-specific gallery/client IDs;
adjust those when using a fresh seed. See `docs/VERIFICATION.md` for the recorded final review.

## Architecture

- `apps/core`: tenant scoping, shared views/forms, design components, dashboard and settings.
- `apps/accounts`: email authentication, verification, password reset (django-allauth).
- `apps/clients`, `apps/shoots`, `apps/scheduling`: CRM, jobs, calendar and ICS.
- `apps/photos`, `apps/galleries`: processing, protected delivery and gallery interactions.
- `apps/portfolio`: public editorial portfolio and inquiries.
- `apps/finance`: ledger, recurring jobs, reporting and exports.
- `assets/css`: Tailwind tokens and component styles; `assets/js`: Vite entry points/charts.
- `static/js`: existing page modules; `static/vendor`: pinned self-hosted libraries/icons.
- `templates`: server-rendered pages and Cotton components.

Every tenant query uses the current studio. Related form choices are scoped too. Tests register
foreign-object URL cases centrally. Money uses Decimal. Receipts are validated and served as
private attachments; CSV text neutralises spreadsheet formula prefixes.

Photographs use the existing libvips worker for efficient full-size derivatives, with Pillow and
BlurHash for tiny previews. New processing generates 480/960/1600/2400px AVIF, WebP and JPEG,
without enlarging small originals. EXIF location is removed by default. Older photos retain their
existing formats until reprocessed. Celery runs image processing, ZIP generation and recurring
expenses; Redis is both broker and cache. Public pages alone use Lenis/GSAP. Reduced-motion
preferences disable page transitions and animated reveals. PhotoSwipe supplies touch/keyboard
zoom; EXIF is displayed in its caption. Chart.js is loaded only on finance pages with data.

## Production

Build the image, use `config.settings.prod`, run migrations and collect static files, then serve
with Gunicorn behind HTTPS. The image includes the Vite build. Collect assets before starting
workers so the manifest remains consistent:

```sh
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.prod web python manage.py collectstatic --noinput
```

Use your PostgreSQL, Redis and SMTP connection values in environment variables. Set
`SITE_URL`, allowed hosts and trusted CSRF origins to your HTTPS domain. Keep DEBUG off.
Do not expose the local media directory or storage buckets directly.

For Cloudflare R2:

```dotenv
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<key>
S3_SECRET_ACCESS_KEY=<secret>
S3_PRIVATE_BUCKET=aperture-private
S3_RENDITIONS_BUCKET=aperture-renditions-private
```

Both buckets must be **private**. Renditions pass through a signed one-hour app URL that checks
publication, expiry and password/owner access; R2 redirects then expire after ten minutes.
Reload a gallery left open for over an hour to renew its image links. Public portfolio selections
remain intentionally public through this gateway. Branding logos are public.

If upgrading an older installation, move existing rendition objects into the private bucket and
disable its former public/custom-domain access. The former `S3_PUBLIC_BUCKET` configuration is
no longer used. Existing local rendition files stay in place and are served only by the gateway.
Revoke old public bucket access before publishing the upgrade.

Real R2 and outbound SMTP delivery require deployment credentials; local development and all
verification use filesystem storage and Mailpit. Back up both PostgreSQL and private storage.
Never run `seed_demo` in production.

Project memory: `AGENTS.md`, `PLAN.md`, `PROGRESS.md`. Historical design notes: `docs/NACRT.md`.
