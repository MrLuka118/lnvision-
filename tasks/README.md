# Tasks for the worker

Each task is one file, `tasks/NNN-name.md`. Read this file first, then the task.

## Ground rules

- Work only in the files the task names. Don't touch `.env`, `locale/`, `docs/`, `static/vendor/`
  or anything the task doesn't mention. Don't commit; the reviewer does.
- Run everything in Docker: `docker compose exec -T web <command>`.
- Done means all of these pass:
  ```
  docker compose exec -T web ruff check .
  docker compose exec -T web ruff format --check .
  docker compose exec -T web python manage.py check
  docker compose exec -T web python manage.py makemigrations --check --dry-run
  docker compose exec -T web pytest -q -n 4
  ```
- Finish with a short report: the files you changed, and the test output (last lines).

## Conventions (follow the existing code, copy its patterns)

- **Tenancy.** Every studio-owned model subclasses `apps.core.models.TenantModel` (a studio FK,
  `created_at`, `updated_at`, `objects.for_studio(studio)`). Views use the generic classes in
  `apps/core/generic.py` (`StudioListView`, `StudioCreateView`, `StudioUpdateView`,
  `StudioDeleteView`); they scope querysets to `request.studio` and set `studio` on save.
- **Forms** over tenant models subclass `apps.core.forms.StudioModelForm` (scopes FK choices to the
  studio) and may use `FormLayoutMixin.sections()`. Dates use `DateInput` / `DateTimeLocalInput`.
- **Every new TenantModel** gets a factory registered with `register_factory` in
  `apps/<app>/tests/factories.py`, imported in the root `conftest.py`. **Every URL that takes an
  object id** gets a `TenantURLCase` in `apps/core/tests/tenancy.py`. The meta-tests fail otherwise.
- **Strings:** English msgids with `gettext_lazy as _` (models, forms) or `{% translate %}`. Never
  write Slovenian into the code; the reviewer translates `locale/`.
- **Templates** extend `layouts/app.html` and use the cotton components in `templates/cotton/`
  (`<c-page_header>`, `<c-button>`, `<c-field>`, `<c-empty>`, `<c-badge>`, `<c-icon>`, ...).
  Plain CRUD pages reuse `templates/generic/form.html` and `generic/confirm_delete.html`. Lists
  follow `templates/shoots/package_list.html` (`.rows` / `.row` / `.row-title` / `.row-meta`).
  No inline `<script>`; no new CSS unless the task says so.
- **Money:** `DecimalField(max_digits=10, decimal_places=2)`, shown with the `eur` filter from
  `{% load formatting %}`. Dates shown with `|date:"j. n. Y"` or `long_date`.
- **Queries:** no N+1. Use `select_related` / `prefetch_related`; list pages get a test with
  `django_assert_max_num_queries`.
- **Tests:** pytest-django, factory_boy, fixtures `studio`, `other_studio`, `auth_client`, `client`
  from `conftest.py`. Test names read as sentences.
- Line length 100, ruff formats.
