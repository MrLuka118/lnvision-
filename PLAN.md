# Build plan

The existing application is retained; checked phases have existing implementation, with
regression and visual verification still required in the final pass.

- [x] 1. Audit baseline, restore local services, migrate assets to Vite + Tailwind v4
- [x] 2. Align design tokens/typography/motion with darkroom and print room; /styleguide
- [x] 3. Verify auth, tenant app shell, HTMX navigation and account settings
- [x] 4. Verify clients; fix list hierarchy, revenue and shared transitions
- [x] 5. Verify calendar, drag reschedule, ICS and all-day presentation
- [x] 6. Audit uploads and private gallery security, responsive derivatives, favourites/ZIP
- [x] 7. Complete finance ledger/forms/filtering/CSV, reports and Chart.js
- [x] 8. Complete dashboard: schedule, deadlines, monthly finance and activity
- [ ] 9. Polish all main screens, empty/error/loading states, accessibility and mobile
- [ ] 10. Full tests, build, visual matrix, public Lighthouse >=90, README and final progress

Existing invoice models are retained. Invoicing extensions in older task documents are
additional scope to evaluate after completing the requested feature set.
