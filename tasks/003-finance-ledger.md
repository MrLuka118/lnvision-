# 003 – Finance: income and expenses (lists, forms, CSV)

Read `tasks/README.md` first. Depends on 001 and 002.

## Goal

The photographer records income and expenses, manages recurring expenses and categories,
filters by period and exports CSV. The dashboard with charts is a later task (004); here
`finance:dashboard` is a temporary redirect to `finance:income_list`.

## Files

- `apps/finance/forms.py`, `apps/finance/views.py`, `apps/finance/urls.py` (`app_name = "finance"`)
- `config/urls.py`: `path("", include("apps.finance.urls"))` after portfolio
- `templates/finance/`: `_tabs.html`, `income_list.html`, `expense_list.html`,
  `recurring_list.html`, `category_list.html`, `suggestions.html`
- `apps/core/tests/tenancy.py`: URL cases for every URL with a pk
- `apps/finance/tests/test_views.py`

Patterns: `apps/clients/` (views, urls, list template with search), `apps/shoots/views_catalogue.py`
and `templates/shoots/package_list.html` (small catalogue lists), `templates/generic/form.html`.
Look at how `templates/shoots/list.html` renders filter pills (`.filter-pill`) — reuse them.

## URLs (Slovenian paths, English names)

| path | name |
| --- | --- |
| `finance/` | `dashboard` (redirect to `income_list` for now) |
| `finance/prihodki/`, `nov/`, `<pk>/uredi/`, `<pk>/izbrisi/` | `income_list`, `income_create`, `income_update`, `income_delete` |
| `finance/stroski/`, `nov/`, `<pk>/uredi/`, `<pk>/izbrisi/` | `expense_list`, `expense_create`, `expense_update`, `expense_delete` |
| `finance/ponavljajoci/`, `nov/`, `<pk>/uredi/`, `<pk>/izbrisi/` | `recurring_list`, `recurring_create`, `recurring_update`, `recurring_delete` |
| `finance/kategorije/`, `nova/`, `<pk>/uredi/`, `<pk>/izbrisi/` | `category_list`, `category_create`, `category_update`, `category_delete` |
| `finance/predlogi/` | `suggestions` (GET list, POST `shoot=<pk>` creates the income) |
| `finance/izvoz.csv` | `export` |

Do **not** add a receipt download URL or view; the reviewer writes it (`finance:receipt`,
`finance/stroski/<pk>/racun/`). In templates link to it only inside
`{% if expense.receipt %}` using `{% url 'finance:receipt' expense.pk %}` — it will exist when
the reviewer merges. Until then, leave that link out of the template and write a
`{# receipt link: finance:receipt #}` comment where it goes.

## Pages

- `_tabs.html`: segmented navigation Income / Expenses / Recurring / Categories (use the
  `c-segmented` component or filter pills, whichever `shoots/list.html` uses), included on all
  four lists.
- **Filters** on income and expense lists via GET: `leto` (year, default current), `mesec`
  (1–12, optional), and for expenses `kategorija` (pk). A select for year (years that have
  data plus the current one) and pills for months. Total for the filtered period shown
  above the list with the `eur` filter. Paginate by 50 with `partials/pagination.html`.
- Income row: date, description or the shoot/client name, method, amount. Expense row: date,
  supplier and description, category name with a dot in its colour (`style="--dot: …"` like the
  dashboard rows), amount, a small paperclip icon if it has a receipt.
- Forms via the generic views and `generic/form.html`. `ExpenseForm` includes `receipt`
  (accept `image/*,application/pdf`, max 10 MB, validated in `clean_receipt`). The expense
  form's view must handle `request.FILES` (`enctype="multipart/form-data"` — check
  `generic/form.html` supports it; add an `enctype` context flag there if needed, without
  changing other forms). Income form: client and shoot selects scoped by `StudioModelForm`.
- Category delete: categories with expenses can't be deleted (PROTECT) — the generic delete view
  already turns `ProtectedError` into a message; make sure it does for this model.
- Recurring create/update: after save call `generate_recurring(today)` restricted to that one
  recurring expense (add an optional `queryset` parameter to `generate_recurring`).
- **Suggestions** (a query, not a table): shoots of the studio with status `paid` or
  `delivered` whose `price` is greater than the sum of their incomes. Show client, shoot, price,
  already received, remaining. POST with a shoot pk creates an `Income` for the remaining amount,
  dated today, method transfer, linked to shoot and client, then redirects back with a success
  message. The shoot is looked up with `get_object_or_404` scoped to `request.studio`. One query
  for the list (annotate the sum), no N+1.
- **CSV export** of the filtered income and expenses for the chosen year (and month):
  columns `Datum;Vrsta;Opis;Kategorija;Znesek;DDV`, `Vrsta` is `prihodek` / `strošek`, dates
  `d. m. yyyy`, amounts with a decimal comma and no thousands separator, expenses negative.
  Delimiter `;`, UTF-8 with BOM (`﻿`) so Excel opens it with č/š/ž. Filename
  `finance-<year>[-<month>].csv`. Use the `csv` module.

## Acceptance tests (`test_views.py`)

- every list loads (200) for the owner and redirects anonymous users to login
- lists show only the studio's own rows; year/month/category filters narrow them; totals match
- a foreign client/shoot/category pk in a form is rejected (400 re-render, nothing saved)
- a receipt over 10 MB or with a `.exe` name is rejected
- deleting a category in use keeps it and shows a message
- suggestions list a paid shoot with price 500 and income 200 as 300 remaining; POST creates
  the income; a foreign shoot pk gives 404; a fully paid shoot is not listed
- CSV: starts with the BOM, uses `;`, has `1234,50` for 1234.50, expenses negative, only this
  studio's rows
- saving a recurring expense that started two months ago creates its past expenses
- list pages: `django_assert_max_num_queries` with 20 rows doesn't exceed the count with 2
