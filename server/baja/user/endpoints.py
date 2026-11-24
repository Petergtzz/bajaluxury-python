from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from baja.auth.dependencies import CurrentUser
from baja.authz.dependencies import Authorize
from baja.authz.permission import Permission
from baja.exceptions import NotPermitted, ResourceNotFound, Unauthorized
from baja.kit.db.postgres import AsyncReadSession, AsyncSession
from baja.models import User
from baja.postgres import get_db_read_session, get_db_session

from .schemas import (
    ManagedUserCreate,
    ManagedUserSchema,
    ManagedUserUpdate,
    UserSchema,
    UserUpdate,
)
from .service import CannotChangeYourself, EmailTaken, InvalidAssignment
from .service import user as user_service

router = APIRouter(prefix="/users", tags=["users"])

ReadUser = Annotated[User, Depends(Authorize(Permission.users_read))]
ManageUser = Annotated[User, Depends(Authorize(Permission.users_manage))]

Errors: dict[int | str, dict[str, Any]] = {
    401: {"model": Unauthorized.schema()},
    403: {"model": NotPermitted.schema()},
}
NotFound: dict[int | str, dict[str, Any]] = {404: {"model": ResourceNotFound.schema()}}


@router.get("/me", response_model=UserSchema, responses=Errors)
async def get_me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserSchema, responses=Errors)
async def update_me(user_update: UserUpdate, user: CurrentUser) -> User:
    if "name" in user_update.model_fields_set:
        user.name = user_update.name or None
    return user


@router.get("/", response_model=list[ManagedUserSchema], responses=Errors)
async def list_users(
    user: ReadUser, session: AsyncReadSession = Depends(get_db_read_session)
) -> list[ManagedUserSchema]:
    return await user_service.list(session)


@router.post(
    "/",
    response_model=ManagedUserSchema,
    status_code=201,
    responses={
        **Errors,
        409: {"model": EmailTaken.schema()},
        422: {"model": InvalidAssignment.schema()},
    },
)
async def create_user(
    user_create: ManagedUserCreate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ManagedUserSchema:
    """Adds someone who can log in with a code sent to their email."""
    created = await user_service.create(session, user_create)
    return await user_service.get_schema(session, created)


@router.patch(
    "/{user_id}",
    response_model=ManagedUserSchema,
    responses={
        **Errors,
        **NotFound,
        409: {"model": CannotChangeYourself.schema()},
        422: {"model": InvalidAssignment.schema()},
    },
)
async def update_user(
    user_id: UUID,
    user_update: ManagedUserUpdate,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> ManagedUserSchema:
    target = await user_service.get(session, user_id)
    updated = await user_service.update(session, user, target, user_update)
    return await user_service.get_schema(session, updated)


@router.delete(
    "/{user_id}",
    status_code=204,
    responses={**Errors, **NotFound, 409: {"model": CannotChangeYourself.schema()}},
)
async def delete_user(
    user_id: UUID,
    user: ManageUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    target = await user_service.get(session, user_id)
    await user_service.delete(session, user, target)
