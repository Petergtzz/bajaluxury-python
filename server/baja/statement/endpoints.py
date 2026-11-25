import datetime as dt
import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.company.service import get_company
from baja.company.service import today as company_today
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession
from baja.models import Currency, User
from baja.postgres import get_db_read_session

from .excel import render_statement_excel
from .pdf import render_statement_pdf
from .schemas import Statement
from .service import PeriodInvalid, build_statement

router = APIRouter(prefix="/properties", tags=["statements"])

ReadUser = Annotated[User, Depends(Authorize(Permission.transactions_read))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
    404: {"model": ResourceNotFound.schema()},
    422: {"model": PeriodInvalid.schema()},
}
PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def get_statement(
    property_id: UUID,
    user: ReadUser,
    start: dt.date = Query(description="The first day, included."),
    end: dt.date = Query(description="The last day, included."),
    currency: Currency | None = Query(
        None, description="Converted at the company's rate. The company's if left out."
    ),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Statement:
    return await build_statement(
        session, user, property_id, start, end, currency=currency
    )


StatementDep = Annotated[Statement, Depends(get_statement)]


@router.get("/{property_id}/statement", response_model=Statement, responses=Errors)
async def statement(statement: StatementDep) -> Statement:
    """The property's ledger over a period, with every total a report shows."""
    return statement


@router.get(
    "/{property_id}/statement.pdf",
    response_class=Response,
    responses={**Errors, 200: {"content": {PDF: {}}}},
)
async def statement_pdf(
    statement: StatementDep, session: AsyncReadSession = Depends(get_db_read_session)
) -> Response:
    company = await get_company(session)
    content = render_statement_pdf(
        statement, company=company.name, generated=await company_today(session)
    )
    return download(content, PDF, _filename(statement, "pdf"))


@router.get(
    "/{property_id}/statement.xlsx",
    response_class=Response,
    responses={**Errors, 200: {"content": {XLSX: {}}}},
)
async def statement_excel(
    statement: StatementDep, session: AsyncReadSession = Depends(get_db_read_session)
) -> Response:
    company = await get_company(session)
    content = render_statement_excel(statement, company=company.name)
    return download(content, XLSX, _filename(statement, "xlsx"))


def download(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _filename(statement: Statement, extension: str) -> str:
    """`campo-9-statement-2026-11-01-2026-11-30.pdf`: safe in any header or disk."""
    slug = re.sub(r"[^a-z0-9]+", "-", statement.property_name.lower()).strip("-")
    return f"{slug}-statement-{statement.start}-{statement.end}.{extension}"
