"""
Baja's clock: `python -m baja.scheduler`, one process.

Everything else starts with a request or a job. What has to happen on its
own is here, on a cron schedule.
"""

import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from baja.kit.db.postgres import create_async_sessionmaker
from baja.postgres import create_async_engine
from baja.recurring.service import recurring_charge as recurring_charge_service

log = logging.getLogger("baja.scheduler")


async def _charge_recurring() -> int:
    engine = create_async_engine("scheduler")
    try:
        async with create_async_sessionmaker(engine)() as session:
            charged = await recurring_charge_service.charge_due(session)
            await session.commit()
            return charged
    finally:
        await engine.dispose()


def charge_recurring() -> None:
    """
    Records the recurring charges that fell due.

    Hourly, so a charge lands within the hour after midnight where the company
    is, and a missed run is caught up by the next one.
    """
    asyncio.run(_charge_recurring())


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        charge_recurring,
        CronTrigger(minute=5),
        id=charge_recurring.__name__,
        # Late after a restart or a slow run: run once, not once per missed hour.
        coalesce=True,
        max_instances=1,
        misfire_grace_time=None,
    )
    return scheduler


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    scheduler = create_scheduler()
    log.info("Scheduler started")
    try:
        scheduler.start()
    except KeyboardInterrupt, SystemExit:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
