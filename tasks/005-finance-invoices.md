# 005 – Finance: invoices (editor, PDF)

Read `tasks/README.md` first. Depends on 001–004 and on the reviewer's
`apps/finance/services.py:issue_invoice(invoice)` and `finance:invoice_pdf` view (already there
when you get this task — use them, don't rewrite them).

## Goal

The photographer writes an invoice with lines, issues it (it gets its number and a stored
PDF), marks it paid (which records the income), and downloads the PDF.

## Files

- `pyproject.toml` + `uv.lock`: add `weasyprint` (latest); `Dockerfile`: apt packages WeasyPrint
  needs on Debian trixie (`libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`), then
  `docker compose build web worker` and restart them
- `apps/finance/forms.py`: `InvoiceForm`, `InvoiceLineFormSet` (inline formset, `extra=1`,
  `can_delete=True`, fields description / quantity / unit_price)
- `apps/finance/views.py`: list, create, update (drafts only), detail, delete (drafts only),
  issue (POST), mark paid (POST)
- `apps/finance/pdf.py`: `render_invoice_pdf(invoice) -> bytes`
- `templates/finance/invoice_list.html`, `invoice_form.html`, `invoice_detail.html`,
  `templates/finance/pdf/invoice.html` (+ its CSS inline in a `<style>` in that template —
  it's for WeasyPrint, not the browser, so CSP doesn't apply)
- `static/js/components.js`: an Alpine `formset` component for adding/removing line rows
  (clone a `<template>` row, update `TOTAL_FORMS`, live subtotal/VAT/total); Alpine CSP build,
  so no inline expressions beyond property names and method calls — copy the style of the
  existing components in that file
- `apps/finance/urls.py`, `_tabs.html` (add "Invoices"), `apps/core/tests/tenancy.py`
- `apps/finance/tests/test_invoices.py`

## URLs

`finance/racuni/` `invoice_list`, `nov/` `invoice_create`, `<pk>/` `invoice_detail`,
`<pk>/uredi/` `invoice_update`, `<pk>/izbrisi/` `invoice_delete`, `<pk>/izdaj/` `invoice_issue`
(POST), `<pk>/placano/` `invoice_paid` (POST). The PDF URL `<pk>/pdf/` `invoice_pdf` is the
reviewer's.

## Behaviour

- Create: client required (scoped), shoot optional (scoped; if given, prefill the client and one
  line from the shoot's package name and price), `vat_rate` defaults to the studio's
  `default_vat_rate` if `studio.vat_registered`, else 0 with `vat_note` defaulting to
  "VAT is not charged under Article 94 of the VAT Act (ZDDV-1)." (English msgid; the reviewer
  translates). `service_date` defaults to the shoot's date or today; `due_date` = today + 15 days.
- Update and delete only while `status == draft` (issued invoices are immutable → 404 for update,
  and the delete view refuses with a message).
- Issue (POST, drafts with at least one line): call `issue_invoice(invoice)` (it assigns the
  number, sets `issue_date` and status, all under a lock). Then render the PDF with
  `render_invoice_pdf` and save it to `invoice.pdf` (`ContentFile`, name `<number>.pdf`).
- Mark paid (POST, issued only): status `paid`, and create an `Income` (amount = total, today,
  method transfer, client, shoot, invoice) in the same transaction — unless an income for this
  invoice already exists.
- List: number (or "Draft"), client, issue date, total, status badge (draft grey, issued
  `--color-cc-orange-yellow`, paid `--color-cc-bluish-green`), overdue (issued and past
  due date) shown with a `--danger` "Overdue" badge. Filter pills by status. Prefetch lines
  (totals are computed from `lines`).
- Detail: the invoice laid out like the PDF (paper-white panel in both themes), with the actions
  (Edit / Issue / Mark paid / Download PDF / Delete) in the page header.

## PDF (`pdf.py`, `pdf/invoice.html`)

- A4, 20 mm margins, Hanken Grotesk for text and Bodoni Moda for the studio name, loaded with
  `@font-face` from the font files in `static/fonts/` (find their names there) via
  `base_url=settings.BASE_DIR`. Black on white, no colours except a hairline rule.
- Content: studio name, address, tax number, IBAN (from `Studio`); client name, address, e-mail;
  "Invoice <number>", issue / service / due dates (`j. n. Y`); lines table (description,
  quantity, unit price, amount — right-aligned, tabular numbers); subtotal, VAT at rate %,
  total; `vat_note` if no VAT; payment reference `SI00 <number without dashes>`; notes.
- Rendered with `translation.override(settings.LANGUAGE_CODE)`.

## Acceptance tests (`test_invoices.py`)

- create with two lines → draft with the right total; a foreign client or shoot pk is rejected
- editing or deleting an issued invoice is refused; a draft can be both
- issuing a draft without lines is refused; issuing stores a PDF that starts with `%PDF`
- mark paid creates exactly one income even when posted twice
- list shows only this studio's invoices, overdue badge appears for a past due date, and the
  list takes a constant number of queries for 2 vs 12 invoices
- (numbering and concurrency are tested by the reviewer)
