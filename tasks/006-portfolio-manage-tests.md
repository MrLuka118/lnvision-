# 006 – Portfolio: tests for the management UI

Read `tasks/README.md` first.

## Goal

The management views in `apps/portfolio/views.py` (urls in `apps/portfolio/urls.py`) have no tests.
Add them. Do not change application code; if a test exposes a bug, stop and report it instead of
fixing it.

## Files

- `apps/portfolio/tests/test_manage.py` (new). Nothing else.

Patterns to copy: `apps/shoots/tests/` view tests (fixtures `studio`, `auth_client`, `client`),
`apps/portfolio/tests/factories.py`, `apps/photos/tests/factories.py` for `Photo`.
Tenant isolation is already covered by `apps/core/tests/tenancy.py` – don't repeat it.

## Tests (names read as sentences)

1. Anonymous visitors are redirected to login on `portfolio:index` and `portfolio:story_list`.
2. `portfolio:index` renders and creates the studio's `Portfolio` on first visit (exactly one).
3. `portfolio:profile` GET renders; POST with valid data saves and redirects to `portfolio:index`.
4. Category create / update / delete work and redirect to `portfolio:category_list`.
5. Deleting a category with stories shows the "will also delete its stories" warning on GET.
6. Story create redirects to `portfolio:story_photos` for the new story.
7. `story_photos` POST saves the chosen photos in the posted order (positions 0, 1, 2), ignores
   duplicates and non-numeric ids, and sets `cover_photo` to the first photo when it was empty.
8. `story_photos` POST ignores photos from another studio and photos that are not `READY`.
9. When the story has a `gallery`, `story_photos` only accepts photos from that gallery.
10. `category_list` and `story_list` with 5 objects each run a bounded number of queries
    (`django_assert_max_num_queries`, pick the smallest number that passes, max 12).

## Done

All checks in `tasks/README.md` pass. Report the files changed and the last lines of pytest.
