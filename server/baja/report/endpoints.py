from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import ReportSend, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived
from baja.recipient.service import RecipientsInvalid, to_schemas
from baja.statement.endpoints import PDF, download

from .schemas import (
    FailedStatementCount,
    ReportSchema,
    ReportSendRequest,
    ReportSent,
    ReportUpdate,
    SentStatementSchema,
)
from .service import MonthNotOver, ReportIsOff, ReportView
from .service import report as report_service

router = APIRouter(prefix="/reports", tags=["reports"])

ManageUser = Annotated[User, Depends(Authorize(Permission.reports_manage))]
ReadUser = Annotated[User, Depends(Authorize(Permission.transactions_read))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}


def _schema(view: ReportView) -> ReportSchema:
    recipients = view.report.recipients if view.report else []
    return ReportSchema(
        property_id=view.property.id,
        property_name=view.property.name,
        send_day=view.report.send_day if view.report else 2,
        recipients=to_schemas(recipients),
        last_sent_at=view.last_sent_at,
    )


def _sent(send: ReportSend) -> SentStatementSchema:
    return SentStatementSchema(
        id=send.id,
        property_id=send.property_id,
        property_name=send.property.name,
        month=send.month,
        status=send.status,
        sent_at=send.sent_at,
        to=send.to_addresses,
        cc=send.cc_addresses,
        error=send.error,
        has_statement=send.has_statement,  # type: ignore[attr-defined]
    )


@router.get("/properties/", response_model=list[ReportSchema], responses=Errors)
async def list_reports(
    user: ManageUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> list[ReportSchema]:
    """Every active property and what it sends, by name."""
    return [_schema(view) for view in await report_service.list(session, user)]


@router.put(
    "/properties/{property_id}",
    response_model=ReportSchema,
    responses={
        **Errors,
        **NotFound,
        409: {"model": PropertyArchived.schema()},
        422: {"model": RecipientsInvalid.schema()},
    },
)
async def set_report(
    property_id: UUID,
    update: ReportUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ReportSchema:
    """Who receives the property's monthly statement, and on which day."""
    return _schema(await report_service.set(session, user, property_id, update))


@router.delete(
    "/properties/{property_id}", status_code=204, responses={**Errors, **NotFound}
)
async def turn_off_report(
    property_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await report_service.turn_off(session, user, property_id)


@router.post(
    "/properties/{property_id}/send",
    response_model=ReportSent,
    status_code=202,
    responses={
        **Errors,
        **NotFound,
        409: {"model": ReportIsOff.schema()},
        422: {"model": MonthNotOver.schema()},
    },
)
async def send_report(
    property_id: UUID,
    user: ManageUser,
    request: ReportSendRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ReportSent:
    """Sends a month's statement now; a month already sent is sent anew."""
    queued = await report_service.send_now(
        session, user, property_id, request.month if request else None
    )
    return ReportSent(
        month=queued.month,
        recipient_count=len(queued.to_addresses) + len(queued.cc_addresses),
    )


@router.get("/sends/", response_model=list[SentStatementSchema], responses=Errors)
async def list_sent_statements(
    user: ReadUser,
    property_id: UUID | None = None,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[SentStatementSchema]:
    """What went out, newest month first: a homeowner's own properties only."""
    return [
        _sent(send)
        for send in await report_service.list_sends(
            session, user, property_id=property_id
        )
    ]


@router.get("/sends/count", response_model=FailedStatementCount, responses=Errors)
async def count_failed_statements(
    user: ManageUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> FailedStatementCount:
    """How many statements didn't go, for the count beside Reports."""
    return FailedStatementCount(count=await report_service.count_failed(session))


@router.get(
    "/sends/{send_id}/statement.pdf",
    response_class=Response,
    responses={**Errors, **NotFound, 200: {"content": {PDF: {}}}},
)
async def get_sent_statement(
    send_id: UUID,
    user: ReadUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Response:
    """The statement exactly as it was sent, not one made again from today's ledger."""
    send = await report_service.get_statement(session, user, send_id)
    assert send.statement is not None
    return download(
        send.statement,
        PDF,
        f"{send.property.name.lower().replace(' ', '-')}-statement-{send.month:%Y-%m}.pdf",
    )
