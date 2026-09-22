# 002 – Finance: recurring expenses generator

Read `tasks/README.md` first. Depends on 001.

## Goal

Recurring expenses (subscriptions, rent) turn into real `Expense` rows on their dates, once
each, also for months that were missed while the worker was down.

## Files

- `apps/finance/services.py` (new): `occurrences`, `generate_recurring`
- `apps/finance/tasks.py` (new): Celery task
- `config/settings/base.py`: add to `CELERY_BEAT_SCHEDULE`
- `apps/finance/tests/test_recurring.py` (new)

Patterns: `apps/galleries/tasks.py` (`@shared_task`), the existing `CELERY_BEAT_SCHEDULE` entry
`galleries-clean-up` in `config/settings/base.py`.

## Behaviour

`occurrences(recurring, until: date) -> list[date]`
- Occurrence *n* (n = 0, 1, 2, …) is `start_date` plus n months (monthly) or n years (yearly),
  always counted **from `start_date`**, not from the previous occurrence. If that month is
  shorter, use its last day: start 31. 1. 2027 → 28. 2. 2027 → 31. 3. 2027 → 30. 4. 2027;
  29. 2. 2028 yearly → 28. 2. 2029.
- Stop after `until`, and after `end_date` if set. Pure function, no database access. Use
  `calendar.monthrange`, no new dependencies.

`generate_recurring(today: date | None = None) -> int`
- `today` defaults to `timezone.localdate()`.
- For every `RecurringExpense` with `is_active=True` (all studios), create an `Expense` for each
  occurrence ≤ today that doesn't exist yet: `studio`, `recurring`, `period` = `date` = the
  occurrence, `amount`, `category`, `supplier` copied, `description` = the recurring name.
- One query for the existing periods per recurring expense (not one per occurrence); create the
  missing ones with `bulk_create(..., ignore_conflicts=True)` so a parallel run can't create
  duplicates (the unique constraint from 001 backs this up).
- Returns how many expenses were created.

Task `apps.finance.tasks.generate_recurring_expenses` calls it. Beat entry
`"finance-recurring"`: every day at 05:30 (`crontab(hour=5, minute=30)`).

## Acceptance tests

- the 31st rule above, both examples, and a yearly one
- `end_date` and `is_active=False` are respected
- running `generate_recurring` twice creates nothing the second time
- a recurring expense started three months ago gets its four occurrences (catch-up)
- a change of `amount` affects only expenses generated afterwards
- expenses land in the recurring expense's own studio
- query count doesn't grow with the number of occurrences
  (`django_assert_max_num_queries`)
