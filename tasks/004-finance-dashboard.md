# 004 – Finance: dashboard with charts

Read `tasks/README.md` first. Depends on 003.

## Goal

`finance/` becomes the finance overview for a year: counters, monthly income vs expenses,
expenses by category, this year vs last year, best clients. Replaces the temporary redirect.

## Files

- `static/vendor/apexcharts-<version>/apexcharts.min.js` — download the latest 4.x
  `dist/apexcharts.min.js` from `https://cdn.jsdelivr.net/npm/apexcharts@4/dist/apexcharts.min.js`
  (check the exact version in the file header and use it in the folder name; keep its licence
  comment)
- `apps/finance/reports.py` (new): the queries
- `apps/finance/views.py`: `FinanceDashboardView`
- `templates/finance/dashboard.html`
- `static/js/finance.js` (new, `type="module"`)
- `assets/css/finance.css` (new, imported in `assets/css/app.css` like the others) — only if needed
- `apps/finance/tests/test_reports.py`

Patterns: `templates/scheduling/calendar.html` (vendor script with `defer`, config through
`json_script`, page module script), `static/js/calendar.js` (page module
reading its config), `<c-stat>` component (animated counter, `format="eur"`).

## Data (`reports.py`, all scoped to one studio and year, done in the database)

- `summary(studio, year)`: income total, expense total, profit, and the same three for the
  previous year (for "vs last year" notes, as a percentage change, `None` if last year is 0).
- `monthly(studio, year)`: 12 entries `{month, income, expenses, profit}` — `TruncMonth` +
  `Sum`, missing months filled with 0. One query for income, one for expenses.
- `by_category(studio, year)`: expense sum per category with its name and colour, largest
  first, zero categories left out.
- `last_year_monthly(studio, year)`: monthly income of `year - 1`, for the comparison line.
- `top_clients(studio, year, limit=5)`: clients by income sum in the year, with the sum.
- Amounts as `Decimal`; convert to float only when serialising for the charts.

## Page

- Header: `<c-page_header>` "Finance" with a year select (GET `leto`, years with data + the
  current one) and the tabs from `_tabs.html` (add "Overview" as the first tab).
- Row of four `<c-stat>`: Income, Expenses, Profit (all `format="eur"`), Invoices unpaid
  (count of issued invoices — 0 until task 005; compute it with a query that works now).
  Each stat's `note` = change vs last year, e.g. "+12 % vs 2025", omitted when `None`.
- Charts (ApexCharts), each in a `.panel` with an `h2`:
  1. Income vs expenses per month: grouped bars (income, expenses) + a line for profit.
  2. Expenses by category: donut, category colours from the data.
  3. This year vs last year: two lines of monthly income.
  4. Best clients: a plain `.rows` list (not a chart), client name and sum, link to the client.
- Chart styling: transparent background, no toolbar, no ApexCharts watermark/title, fonts
  `var(--font-sans)` read from CSS, text colour `--ink-2`, grid lines `--line-soft`, income
  colour `--color-cc-bluish-green`, expenses `--color-cc-moderate-red`, profit `--ink`, last
  year `--ink-3`. Axis labels in euros formatted `1.234 €` style with `Intl.NumberFormat("sl-SI",
  {style: "currency", currency: "EUR", maximumFractionDigits: 0})`. Month labels from
  `Intl.DateTimeFormat("sl-SI", {month: "short"})`.
- Re-read colours and re-render the charts when the theme changes: the theme switch sets
  `data-theme` on `<html>` (`themeSwitch` in `static/js/components.js`), so watch it with a
  `MutationObserver` on `document.documentElement` (attribute `data-theme`), and also listen to
  `matchMedia("(prefers-color-scheme: light)")` changes for the `auto` theme.
- `prefers-reduced-motion: reduce` → `chart.animations.enabled = false`.
- CSP: pass the page nonce to ApexCharts (`chart.nonce`). Render it into the `json_script` config as `nonce`
  (the template variable is `CSP_NONCE`, see `templates/base.html`).
- Empty year (no data): an `<c-empty>` instead of the charts, with buttons to add income or an
  expense.
- Mobile (390 px): stats in 2 columns, charts full width, heights ~260 px; desktop: chart 1
  full width, 2 and 3 side by side.

## Acceptance tests (`test_reports.py` + a view test)

- `monthly` returns 12 months with the right sums, zeros for empty months, only this studio
  and this year
- `summary` percentages, including `None` when last year is 0
- `by_category` skips empty categories and sorts by sum
- `top_clients` order and limit
- the dashboard view renders with data and without (empty state), `leto` filter works, and
  takes a constant number of queries regardless of row count
