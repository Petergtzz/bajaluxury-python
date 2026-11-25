"""Queues the monthly reports owed, by hand.

Each homeowner who gets one is sent last month's statements, once: a month
already sent to someone is skipped, and one claimed but not sent yet is
queued again, so running this again sends nothing twice and loses nothing.
Not scheduled yet; the worker (`task worker`) does the sending.

Usage: python -m scripts.send_monthly_reports [YYYY-MM] [--dry-run]
"""

import asyncio
import datetime as dt
import sys

# Queuing looks a job up by name, so the jobs have to be declared here too.
from baja import tasks  # noqa: F401
from baja.company.service import today as company_today
from baja.kit.db.postgres import create_async_sessionmaker
from baja.monthly_report.service import previous_month, queue_due
from baja.postgres import create_async_engine
from baja.worker import collect_jobs, send_jobs


async def main(month: dt.date | None, *, dry_run: bool) -> int:
    engine = create_async_engine("script")
    try:
        async with collect_jobs() as jobs:
            async with create_async_sessionmaker(engine)() as session:
                month = month or previous_month(await company_today(session))
                queued = await queue_due(session, month, dry_run=dry_run)
                if dry_run:
                    await session.rollback()
                else:
                    await session.commit()
            await send_jobs(jobs)
    finally:
        await engine.dispose()
    for email in queued:
        print(email)  # noqa: T201
    print(  # noqa: T201
        f"{len(queued)} report(s) for {month:%B %Y}"
        + (" would be queued (dry run)" if dry_run else " queued")
    )
    return 0


if __name__ == "__main__":
    months = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    sys.exit(
        asyncio.run(
            main(
                dt.date.fromisoformat(f"{months[0]}-01") if months else None,
                dry_run="--dry-run" in sys.argv,
            )
        )
    )
