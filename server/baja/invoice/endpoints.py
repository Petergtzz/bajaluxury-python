from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.company.service import get_company
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import Invoice, User
from baja.postgres import get_db_read_session, get_db_session
from baja.property.service import PropertyArchived
from baja.property.service import property as property_service
from baja.statement.endpoints import PDF, download

from .pdf import render_invoice_pdf
from .schemas import InvoiceCreate, InvoiceSchema
from .service import GuestExpenseInvoiced, InvoiceLinesInvalid
from .service import invoice as invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])

ManageUser = Annotated[User, Depends(Authorize(Permission.invoices_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}


@router.get("/", response_model=list[InvoiceSchema], responses=Errors)
async def list_invoices(
    user: ManageUser,
    property_id: UUID | None = None,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[Invoice]:
    """Newest number first."""
    return await invoice_service.list(session, user, property_id=property_id)


@router.post(
    "/",
    response_model=InvoiceSchema,
    status_code=201,
    responses={
        **Errors,
        **NotFound,
        409: {"model": PropertyArchived.schema() | GuestExpenseInvoiced.schema()},
        422: {"model": InvoiceLinesInvalid.schema()},
    },
)
async def issue_invoice(
    invoice_create: InvoiceCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> Invoice:
    """Numbers it and emails it to the recipient as a PDF."""
    return await invoice_service.issue(session, user, invoice_create)


# Before "/{invoice_id}", which would take "<id>.pdf" as a malformed id.
@router.get(
    "/{invoice_id}.pdf",
    response_class=Response,
    responses={**Errors, **NotFound, 200: {"content": {PDF: {}}}},
)
async def invoice_pdf(
    invoice_id: UUID,
    user: ManageUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Response:
    """The invoice as it was sent."""
    invoice = await invoice_service.get(session, user, invoice_id)
    property = await property_service.get(session, user, invoice.property_id)
    company = await get_company(session)
    content = render_invoice_pdf(
        invoice, company=company.name, property_name=property.name
    )
    return download(content, PDF, f"{invoice.number}.pdf")


@router.get(
    "/{invoice_id}", response_model=InvoiceSchema, responses={**Errors, **NotFound}
)
async def get_invoice(
    invoice_id: UUID,
    user: ManageUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> Invoice:
    return await invoice_service.get(session, user, invoice_id)


@router.delete("/{invoice_id}", status_code=204, responses={**Errors, **NotFound})
async def delete_invoice(
    invoice_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Its number stays used; its guest expenses can be billed again."""
    invoice = await invoice_service.get(session, user, invoice_id)
    await invoice_service.delete(session, invoice)
