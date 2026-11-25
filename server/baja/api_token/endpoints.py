from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from baja.auth.dependencies import CurrentAuthSubject
from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import ApiToken, User
from baja.postgres import get_db_read_session, get_db_session

from .schemas import ApiTokenCreate, ApiTokenCreated, ApiTokenSchema, TokenUserSchema
from .service import api_token as api_token_service

router = APIRouter(prefix="/api-tokens", tags=["api tokens"])

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}


async def from_a_browser(
    auth_subject: CurrentAuthSubject,
    user: Annotated[User, Depends(Authorize(Permission.api_tokens_manage))],
) -> User:
    # A device holding a token mints no more of them, and revokes no others.
    if auth_subject.api_token is not None:
        raise NotPermitted("Connect devices from the dashboard, logged in.")
    return user


ManageUser = Annotated[User, Depends(from_a_browser)]


@router.get("/", response_model=list[ApiTokenSchema], responses=Errors)
async def list_api_tokens(
    user: ManageUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> Sequence[ApiToken]:
    """The caller's devices; an owner's sees everyone's."""
    return await api_token_service.list(session, user)


@router.post("/", response_model=ApiTokenCreated, status_code=201, responses=Errors)
async def create_api_token(
    create: ApiTokenCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ApiTokenCreated:
    """A token for one of your devices. The token is in this answer and nowhere else."""
    token, api_token = await api_token_service.issue(session, user, create.label)
    return ApiTokenCreated(
        id=api_token.id,
        label=api_token.label,
        user=TokenUserSchema.model_validate(user),
        last_used_at=None,
        created_at=api_token.created_at,
        token=token,
    )


@router.delete(
    "/{token_id}",
    status_code=204,
    responses={**Errors, 404: {"model": ResourceNotFound.schema()}},
)
async def revoke_api_token(
    token_id: UUID, user: ManageUser, session: AsyncSession = Depends(get_db_session)
) -> None:
    """It stops working at once; the device needs a new one."""
    await api_token_service.revoke(session, user, token_id)
