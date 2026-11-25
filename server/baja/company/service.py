import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import select

from baja.exceptions import BajaError
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.kit.utils import utc_now
from baja.models import Company

from .schemas import CompanyUpdate


class CompanyNotSetUp(BajaError):
    def __init__(self) -> None:
        super().__init__("The company is not set up yet.", 503)


async def get_company(session: AsyncReadSession) -> Company:
    company = (await session.execute(select(Company))).scalar_one_or_none()
    if company is None:
        raise CompanyNotSetUp()
    return company


async def today(session: AsyncReadSession) -> dt.date:
    """Today where the company works: when a day's charges fall due."""
    company = await get_company(session)
    return utc_now().astimezone(ZoneInfo(company.timezone)).date()


async def update_company(session: AsyncSession, update: CompanyUpdate) -> Company:
    """Changes apply from now on: invoices and charges already made keep theirs."""
    company = await get_company(session)
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(company, field, value)
    await session.flush()
    # Read back as stored, so the answer matches every later read.
    await session.refresh(company)
    return company
