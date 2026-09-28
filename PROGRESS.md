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

## Dashboard, branding and photo security
- Added monthly dashboard totals and gallery activity; client detail shows actual revenue.
- Added profile, password/email links, validated logo upload and gallery accent settings.
- Closed permanent rendition URL exposure: signed, expiring gateway checks password, expiry,
  publication and owner access; R2 rendition bucket is now private. Raw local rendition paths
  are blocked. Expired/unpublished galleries also revoke ZIP downloads.
- Added WebP derivatives, Pillow/BlurHash previews, owner photo detail with shared transition,
  EXIF lightbox captions, GSAP Flip favourite filtering and calendar shared transitions.
- Regression suite: 247 passed. New tests cover rendition tampering/expiry, tenant access,
  client revenue, profile ownership and branding validation.
- Fixed Vite development manifest reloads and missing finance header actions found visually.
- Final screenshots, translations, flow tests and Lighthouse remain in progress.

## Visual bug fixes — shell, theme, buttons, greeting (2026-09-28)
Verified with `node scripts/sidebar_check.mjs <chromium|webkit> <1|2>` (corner pixel probes at
rest / hover / mid-transition slowed to 4 s, 5× theme toggle layout diff, 10 navigations with
sidebar node identity, dashboard hover/press with transition-property audit; videos and corner
crops in screenshots/shell/). Chromium 1x/2x pass. WebKit passes except that its screenshot
path does not paint live `::view-transition-new` images, so the light-theme bottom shadow is
missing in paused captures (those pixels equal the page background); WebKit screencast
frames show the sidebar solid and the indicator gliding. 248 tests, ruff, check clean.

1. Sidebar rectangle behind the corners. Root cause: the sidebar's `backdrop-filter` was on
   the rounded box itself; Chromium does not clip backdrop-filter to border-radius in the
   view-transition capture (and some repaints), so the blurred backdrop painted as a sharp
   rectangle mid-navigation. The boosted `<body>` innerHTML swap also rebuilt the sidebar on
   every click, so it was captured and cross-faded each time. The sidebar never had SVG
   refraction (data-refract is only on the mobile tab bar/account button). Fix: glass moved
   to `.app-sidebar::before` with `clip-path: inset(0 round var(--sidebar-radius))`, rim on
   `::after`, one `--sidebar-radius` token for box, shadow and pseudos, `isolation: isolate`,
   no transforms/filters on it or ancestors. clip-path sits on ::before, not the sidebar: on
   the sidebar it would clip the drop shadow and make it a backdrop root (blur would vanish).
   Sidebar is `hx-preserve` (id app-sidebar) and `view-transition-name: sidebar` with only
   its live new image shown, so the iris affects main only. aria-current is synced from
   `<main data-nav-current>` after swaps; one `.nav-indicator` (server-positioned, no load
   animation) glides with a translate transition; hover never styles the current item.
   Also: WebKit drew a focus ring on `<main>` after main.js focused it — removed for #main.
2. Theme jump. Root cause: the toggle used morph() → startViewTransition, so the page iris
   (clip-path circle from the centre, the "light box" behind the greeting) ran on every theme
   change, and colour transitions re-ran inside the live snapshot. Clicks during it hit the
   transition overlay and light-dismissed the account menu; the menu, inside the sidebar
   layer, was clipped to the sidebar box. No load-time flash exists: data-theme is rendered
   server-side from the theme cookie before CSS, so no inline script was added. No
   `transition: all` exists. Fix: `.theme-switching` (transitions off), 300 ms fade on all
   layers, overlay `pointer-events: none`, menu has its own transition name, instant when
   unsupported or reduced motion, `scrollbar-gutter: stable` on html.
3. Hover/press. Root cause: text buttons pressed with `scale()` (blurs text) on a 420 ms
   spring against 120 ms colour changes; box-shadow animated; menu items had no transition.
   Fix: all states use --dur-1/--ease-out, animate only colour/border/opacity/transform, press
   is translateY(1px) (btn, tab, gallery bar, portfolio CTA); icon-only heart keeps its scale.
4. Greeting "Dober dan, Maja." Root cause: seed_demo created the demo user as "Maja Kovač",
   which reads as client Maja Kovačič. Fix: demo user has no personal name; greeting falls
   back to the studio name ("Dober dan, Studio Svetloba."). Regression test added; re-run
   `manage.py seed_demo` on existing databases.
Note: layout.css, gallery.css and dashboard.html commits include small pre-existing
uncommitted hunks (mobile schedule-row, gallery cover timing) that shared those files.
