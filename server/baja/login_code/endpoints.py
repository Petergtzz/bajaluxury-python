from fastapi import APIRouter, Depends, Request, Response

from baja.auth.service import auth as auth_service
from baja.kit.db.postgres import AsyncSession
from baja.kit.rate_limit import TooManyRequests
from baja.models import User
from baja.postgres import get_db_session
from baja.redis import Redis, get_redis
from baja.user.schemas import UserSchema

from .schemas import LoginCodeAuthenticate, LoginCodeRequest
from .service import LoginCodeInvalidOrExpired
from .service import login_code as login_code_service

router = APIRouter(prefix="/auth/login-code", tags=["auth"])


@router.post(
    "/request",
    status_code=202,
    response_class=Response,
    responses={429: {"model": TooManyRequests.schema()}},
)
async def request_login_code(
    login_code_request: LoginCodeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> None:
    client_ip = request.client.host if request.client is not None else "unknown"
    await login_code_service.request(
        session, redis, login_code_request.email, client_ip=client_ip
    )


@router.post(
    "/authenticate",
    response_model=UserSchema,
    responses={
        401: {"model": LoginCodeInvalidOrExpired.schema()},
        429: {"model": TooManyRequests.schema()},
    },
)
async def authenticate_login_code(
    login_code_authenticate: LoginCodeAuthenticate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> User:
    user = await login_code_service.authenticate(
        session, redis, login_code_authenticate.email, login_code_authenticate.code
    )
    token, user_session = await auth_service.create_user_session(
        session, user, user_agent=request.headers.get("user-agent", "")
    )
    auth_service.set_session_cookie(request, response, token, user_session.expires_at)
    return user
