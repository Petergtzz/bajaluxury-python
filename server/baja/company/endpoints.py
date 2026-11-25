from typing import Annotated, Any

from fastapi import APIRouter, Depends

from baja.auth.dependencies import CurrentUser
from baja.exceptions import Unauthorized
from baja.kit.db.postgres import AsyncReadSession
from baja.models import Company
from baja.postgres import get_db_read_session

from .schemas import CompanySchema
from .service import CompanyNotSetUp, get_company

router = APIRouter(prefix="/company", tags=["company"])

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    503: {"model": CompanyNotSetUp.schema()},
}


@router.get("", response_model=CompanySchema, responses=Errors)
async def read_company(
    user: CurrentUser,
    session: Annotated[AsyncReadSession, Depends(get_db_read_session)],
) -> Company:
    """The business everyone here works in: its name, money and clock."""
    return await get_company(session)
