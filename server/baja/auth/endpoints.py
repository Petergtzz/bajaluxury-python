from fastapi import APIRouter, Depends, Request, Response

from baja.kit.db.postgres import AsyncSession
from baja.postgres import get_db_session

from .dependencies import CurrentAuthSubject
from .service import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    auth_subject: CurrentAuthSubject,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if auth_subject.session is not None:
        await auth_service.delete_user_session(session, auth_subject.session)
    auth_service.clear_session_cookie(request, response)
