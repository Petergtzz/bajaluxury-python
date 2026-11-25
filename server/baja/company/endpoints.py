from typing import Annotated, Any

from fastapi import APIRouter, Depends

from baja.auth.dependencies import CurrentUser
from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Company, User
from baja.postgres import get_db_read_session, get_db_session

from .schemas import CompanySchema, CompanyUpdate
from .service import CompanyNotSetUp, get_company, update_company

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


@router.patch(
    "",
    response_model=CompanySchema,
    responses={**Errors, 403: {"model": NotPermitted.schema()}},
)
async def patch_company(
    update: CompanyUpdate,
    user: Annotated[User, Depends(Authorize(Permission.company_manage))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Company:
    """Its name, clock and exchange rate. Only an owner changes them."""
    return await update_company(session, update)
