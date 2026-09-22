# 001 – Finance: app, models, migration, admin, factories

Read `tasks/README.md` first.

## Goal

Create the `apps/finance` app with its data model. No views yet (a later task).

## Files

- `apps/finance/__init__.py`, `apps.py` (`name = "apps.finance"`, `verbose_name = _("Finance")`)
- `apps/finance/models.py`, `apps/finance/migrations/0001_initial.py` (via `makemigrations finance`)
- `apps/finance/admin.py`
- `apps/finance/defaults.py`
- `apps/finance/tests/__init__.py`, `apps/finance/tests/factories.py`, `apps/finance/tests/test_models.py`
- `config/settings/base.py`: add `"apps.finance"` to `INSTALLED_APPS` after `apps.portfolio`
- `conftest.py`: import the finance factories module like the others (registers them)

Pattern to copy: `apps/portfolio/models.py` (TenantModel, TextChoices, verbose names, Meta,
constraints), `apps/portfolio/tests/factories.py` (factories + `register_factory`).

## Models (all subclass `TenantModel` unless noted)

Money: `DecimalField(max_digits=10, decimal_places=2)`. All verbose names English via `_()`.

**ExpenseCategory**: `name` (60), `colour` (CharField 7, a hex like `#627a9d`), `position`
(PositiveSmallIntegerField, default 0). Ordering `["position", "name"]`. Unique `(studio, name)`.

**RecurringExpense**: `name` (120), `supplier` (120, blank), `amount`, `category` (FK
ExpenseCategory, `PROTECT`), `interval` (TextChoices `MONTHLY="monthly"`, `YEARLY="yearly"`),
`start_date`, `end_date` (null/blank), `is_active` (default True). Ordering `["name"]`.

**Expense**: `date`, `amount` (gross), `vat_amount` (null/blank, "VAT included"), `category` (FK,
`PROTECT`, related_name `expenses`), `supplier` (120, blank), `description` (200, blank),
`receipt` (FileField, blank, `upload_to=receipt_path`, max_length 255), `recurring` (FK
RecurringExpense, `SET_NULL`, null, related_name `expenses`), `period` (DateField, null — the
occurrence date a recurring expense was generated for).
Constraint: `UniqueConstraint(fields=["recurring", "period"], condition=Q(recurring__isnull=False), name="one_expense_per_period")`.
Ordering `["-date", "-id"]`.
`receipt_path(instance, filename)` → `receipts/<studio_id>/<uuid4 hex><suffix>` with the suffix
lower-cased and cut to 6 chars, like `original_path` in `apps/photos/models.py`.

**Income**: `date`, `amount`, `description` (200, blank), `method` (TextChoices
`TRANSFER="transfer"` "Bank transfer", `CASH="cash"`, `CARD="card"`, `OTHER="other"`, default
transfer), `client` (FK clients.Client, `SET_NULL`, null, related_name `incomes`), `shoot` (FK
shoots.Shoot, `SET_NULL`, null, related_name `incomes`), `invoice` (FK Invoice, `SET_NULL`, null,
related_name `payments`). Ordering `["-date", "-id"]`.

**Invoice**: `number` (CharField 20, blank — assigned when issued), `year`
(PositiveSmallIntegerField, null), `sequence` (PositiveIntegerField, null), `client` (FK,
`PROTECT`, related_name `invoices`), `shoot` (FK, `SET_NULL`, null, related_name `invoices`),
`issue_date` (null/blank), `service_date` (null/blank), `due_date` (null/blank), `vat_rate`
(DecimalField 5,2, default 0), `vat_note` (CharField 200, blank — e.g. the legal reason no VAT
is charged), `notes` (TextField, blank), `status` (TextChoices `DRAFT="draft"`,
`ISSUED="issued"`, `PAID="paid"`, default draft), `pdf` (FileField, blank,
`upload_to=invoice_pdf_path` → `invoices/<studio_id>/<uuid4 hex>.pdf`).
Constraint: `UniqueConstraint(fields=["studio", "number"], condition=~Q(number=""), name="invoice_number_per_studio")`.
Ordering `["-issue_date", "-id"]`. Properties (Decimal, rounded to 0.01 with ROUND_HALF_UP):
`subtotal` = sum of line totals, `vat` = subtotal × vat_rate / 100, `total` = subtotal + vat.
They must work on `self.lines.all()` so a `prefetch_related("lines")` avoids queries.

**InvoiceLine** (plain `models.Model`, NOT TenantModel): `invoice` (FK, CASCADE, related_name
`lines`), `description` (200), `quantity` (DecimalField 8,2, default 1), `unit_price` (money),
`position` (default 0). Ordering `["position", "id"]`. Property `total` = quantity × unit_price
rounded to 0.01.

**InvoiceSequence** (TenantModel): `year` (PositiveSmallIntegerField), `last_number`
(PositiveIntegerField, default 0). Unique `(studio, year)`. Only the model — the numbering
service is written by the reviewer.

## defaults.py

`DEFAULT_CATEGORIES` — list of (English name, hex colour):
Equipment `#735244`, Software and subscriptions `#627a9d`, Travel `#d67e2c`, Marketing
`#8580b1`, Studio and rent `#576c43`, Other `#8f8f8f`.
`seed_categories(studio)` creates them (with `position` 0..5) only if the studio has no
categories yet; names go through `gettext` so they are stored in the studio's language.
Call it from `apps/core/services.py:ensure_studio` right after the studio is created (import
inside the function to avoid circular imports).

## Admin

Register every model. Invoice gets an `InvoiceLine` TabularInline. Lists show studio and the
main fields; `list_filter` on status / category where it exists.

## Factories

One per TenantModel (ExpenseCategory, RecurringExpense, Expense, Income, Invoice,
InvoiceSequence), each with `studio = SubFactory(StudioFactory)` and related objects in the SAME
studio (`factory.SelfAttribute("..studio")`, see `ShootFactory`). Plus `InvoiceLineFactory`.
Register the tenant ones with `register_factory`.

## Acceptance tests (`test_models.py`)

- a new studio (via `ensure_studio`) gets the six default categories; calling
  `seed_categories` again adds none
- two expenses for the same recurring expense and period raise `IntegrityError`; two with
  `recurring=None` and the same period don't
- invoice totals: lines 2 × 100.00 and 1 × 49.99 at 22 % VAT → subtotal 249.99, vat 55.00,
  total 304.99
- two draft invoices with an empty number in one studio are allowed; the same non-empty number
  twice in one studio is not; the same number in two studios is
- `receipt_path` keeps no part of the original filename except a short lower-case suffix
- all existing tests still pass (the tenancy meta-tests check the factories)
