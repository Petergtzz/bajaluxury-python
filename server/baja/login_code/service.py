import hmac
import secrets
import string

from baja.config import settings
from baja.email.tasks import LOGIN_CODE_PURPOSE
from baja.exceptions import Unauthorized
from baja.kit.crypto import get_token_hash, seal
from baja.kit.db.postgres import AsyncSession
from baja.kit.rate_limit import limit
from baja.kit.utils import utc_now
from baja.models import LoginCode, User
from baja.redis import Redis
from baja.user.repository import UserRepository
from baja.worker import enqueue_job

from .repository import LoginCodeRepository


class LoginCodeInvalidOrExpired(Unauthorized):
    def __init__(self) -> None:
        super().__init__("This login code is invalid or has expired.")


def _hash_code(code: str) -> str:
    return get_token_hash(code, secret=settings.SECRET)


class LoginCodeService:
    async def request(
        self, session: AsyncSession, redis: Redis, email: str, *, client_ip: str
    ) -> None:
        """
        Emails a code to a user. An unknown address is answered the same way,
        without an email, so the form never tells who has an account.
        """
        window = settings.LOGIN_CODE_RATE_LIMIT_WINDOW
        await limit(
            redis,
            f"login_code:requests_by_ip:{client_ip}",
            window,
            settings.LOGIN_CODE_MAX_REQUESTS_PER_IP_PER_WINDOW,
        )
        await limit(
            redis,
            f"login_code:requests:{email.lower()}",
            window,
            settings.LOGIN_CODE_MAX_REQUESTS_PER_WINDOW,
        )
        user = await UserRepository.from_session(session).get_by_email(email)
        if user is None:
            return
        repository = LoginCodeRepository.from_session(session)
        await repository.delete_by_email(user.email)
        code = "".join(
            secrets.choice(string.digits) for _ in range(settings.LOGIN_CODE_LENGTH)
        )
        await repository.create(
            LoginCode(
                email=user.email,
                code_hash=_hash_code(code),
                expires_at=utc_now() + settings.LOGIN_CODE_TTL,
            )
        )
        enqueue_job(
            "email.send_login_code",
            user.email,
            seal(code, secret=settings.SECRET, purpose=LOGIN_CODE_PURPOSE),
        )

    async def authenticate(
        self, session: AsyncSession, redis: Redis, email: str, code: str
    ) -> User:
        # Charged before the code is checked, so guesses sent together can't all
        # slip in under the cap: six digits are only safe while it holds.
        await limit(
            redis,
            f"login_code:attempts:{email.lower()}",
            settings.LOGIN_CODE_RATE_LIMIT_WINDOW,
            settings.LOGIN_CODE_MAX_ATTEMPTS_PER_WINDOW,
        )
        repository = LoginCodeRepository.from_session(session)
        login_code = await repository.get_valid_by_email(email)
        if login_code is None or not hmac.compare_digest(
            login_code.code_hash, _hash_code(code.strip())
        ):
            raise LoginCodeInvalidOrExpired()
        user = await UserRepository.from_session(session).get_by_email(email)
        if user is None:
            raise LoginCodeInvalidOrExpired()
        await repository.delete_by_email(email)
        await redis.delete(f"login_code:attempts:{email.lower()}")
        user.email_verified = True
        return user


login_code = LoginCodeService()
