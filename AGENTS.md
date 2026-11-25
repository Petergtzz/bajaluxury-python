# Baja Luxury

Property management for Baja Luxury's homes: managers record income and expenses (also from an Apple Shortcut), homeowners read the ledgers of their own properties. One company, no tenancy.

This repository holds the FastAPI backend (`server/`) and the Next.js dashboard (`clients/apps/web`, see its `AGENTS.md`). It is written fresh. `~/Documents/projects/doorstep-python` and Polar are references for patterns only: read them to see how something is done, never copy their files.

## Rules

- Never use the em dash character. Use a plain `-`.
- Comment only what the code cannot say: why, not what.
- Write code like the surrounding code: same naming, idioms and structure.
- Every behavior change comes with a test that fails without it.
- Verify end to end against the real stack, not only through tests.
- Keep lint, types and tests green. Fix failures and flakiness you come across, even if unrelated.

## Server

Run every command from `server/`, with the virtualenv at `../venv`:

```
source ../venv/bin/activate
pip install -e . --group dev   # after changing dependencies
cp .env.example .env           # first time; set BAJA_POSTGRES_USER
task db_migrate                # apply migrations
task api                       # http://127.0.0.1:8100
task worker                    # background jobs (emails)
task scheduler                 # the clock: recurring charges, hourly
task import_legacy <dsn>       # copy the Laravel database in (re-runnable, --dry-run)
task api_tokens issue <email> <label>   # a token for a phone; also list, revoke
task send_monthly_reports [YYYY-MM] [--dry-run]   # queue homeowners' monthly statements
task test                      # pytest, one database per worker
task lint && task lint_types
```

Requirements: Python 3.14, Postgres 17 and Redis on localhost.

### Patterns

- Tables inherit `RecordModel`: UUIDv7 `id`, `created_at`, `modified_at`, `deleted_at`. Deleting is soft.
- Money is `NUMERIC(12,2)` mapped to `Decimal` (never float), in the company's currency. JSON carries it as a number.
- Balances are derived from `transactions`, never stored. Whether a row moves the balance (`affects_balance`) is decided by the ledger when it is written: income always, an expense when its payment method is in the property's `balance_methods`.
- Writes from outside clients are idempotent on `(source, external_id)`: a resend returns the row already recorded.
- One database transaction per request (`TransactionalMiddleware`): services never commit, the response does.
- Errors are always `{"error": <code>, "detail": <message>}`. Raise a `BajaError` subclass.
- Tests run inside a transaction that is rolled back; requests in a test use savepoints in it.
- Background work goes through `enqueue_job`; jobs are sent only after the transaction commits, and emails are only sent from jobs. Tests use an in-memory broker and read what was queued from the `sent_jobs` fixture.
- Login is by emailed code (no passwords, no sign-up): only existing users get a code, and an unknown address gets the same answer. The session cookie holds a token; the database keeps only its hash. Devices such as the Shortcut send an API token instead (`Authorization: Bearer`, issued with `task api_tokens`); it acts as its user, with their role.
- Permissions come from the user's role only (`authz/permission.py`). Endpoints take `Authorize(Permission.x)`. Owners and managers see every property; a homeowner sees the properties assigned in `property_members`, and every query over property-owned rows applies `visible_properties` so anything else is a 404.
- Recurring charges are data (`recurring_charges`), charged by the scheduler. Each keeps a `charged_through` cursor that only moves forward, and each month's row has a fixed id, so a run never charges a month twice or charges for the past.
- Reports render one model: a property's `Statement` (`statement/`), or the utilities report. PDFs are A4 on `kit/paper`, IBM Plex Sans; look at a rendered page after changing one.
- Rate limits are fixed windows in Redis (`kit/rate_limit.py`), charged before the work they guard.
