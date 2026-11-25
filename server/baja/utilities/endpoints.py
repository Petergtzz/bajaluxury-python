import datetime as dt
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
from baja.statement.endpoints import PDF, XLSX, download
from baja.statement.service import PeriodInvalid

from .buckets import BUCKETS, UTILITIES
from .excel import render_utilities_excel
from .pdf import render_utilities_pdf
from .schemas import BucketSchema, UtilitiesReport
from .service import UnknownBuckets, build_utilities_report

router = APIRouter(prefix="/reports", tags=["reports"])

ReadUser = Annotated[User, Depends(Authorize(Permission.transactions_read))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
    404: {"model": ResourceNotFound.schema()},
    422: {"model": PeriodInvalid.schema() | UnknownBuckets.schema()},
}


async def get_report(
    user: ReadUser,
    start: dt.date = Query(description="The first day, included."),
    end: dt.date = Query(description="The last day, included."),
    property_id: UUID | None = Query(
        None, description="Every property the caller may see, if left out."
    ),
    buckets: list[str] = Query(
        list(UTILITIES),
        description="Which kinds of bill, in this order. See /v1/reports/buckets.",
    ),
    currency: Currency | None = Query(
        None, description="Converted at the company's rate. The company's if left out."
    ),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> UtilitiesReport:
    return await build_utilities_report(
        session,
        user,
        start,
        end,
        property_id=property_id,
        buckets=buckets,
        currency=currency,
    )


ReportDep = Annotated[UtilitiesReport, Depends(get_report)]


@router.get("/buckets", response_model=list[BucketSchema])
async def list_buckets(user: ReadUser) -> list[BucketSchema]:
    """Every kind of bill a report can show, in the order a concept is sorted."""
    return [BucketSchema(key=b.key, label=b.label) for b in BUCKETS]


@router.get("/utilities", response_model=UtilitiesReport, responses=Errors)
async def utilities(report: ReportDep) -> UtilitiesReport:
    """
    What went to each kind of bill, month by month: the utilities breakdown
    reads the totals, the tracker the counts.
    """
    return report


@router.get(
    "/utilities.pdf",
    response_class=Response,
    responses={**Errors, 200: {"content": {PDF: {}}}},
)
async def utilities_pdf(
    report: ReportDep, session: AsyncReadSession = Depends(get_db_read_session)
) -> Response:
    company = await get_company(session)
    content = render_utilities_pdf(
        report, company=company.name, generated=await company_today(session)
    )
    return download(content, PDF, _filename(report, "pdf"))


@router.get(
    "/utilities.xlsx",
    response_class=Response,
    responses={**Errors, 200: {"content": {XLSX: {}}}},
)
async def utilities_excel(
    report: ReportDep, session: AsyncReadSession = Depends(get_db_read_session)
) -> Response:
    company = await get_company(session)
    content = render_utilities_excel(report, company=company.name)
    return download(content, XLSX, _filename(report, "xlsx"))


def _filename(report: UtilitiesReport, extension: str) -> str:
    return f"utilities-{report.start}-{report.end}.{extension}"
