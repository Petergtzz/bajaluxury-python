import base64
import hashlib
import hmac
import secrets
import time
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken


def get_token_hash(token: str, *, secret: str) -> str:
    """What the database keeps instead of a token: a leaked row logs nobody in."""
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def generate_token_hash_pair(*, secret: str, prefix: str = "") -> tuple[str, str]:
    token = f"{prefix}{secrets.token_urlsafe(32)}"
    return token, get_token_hash(token, secret=secret)


class SealedValueInvalid(Exception):
    """The value was tampered with, sealed for another purpose, or is too old."""


def _fernet(secret: str, purpose: str) -> Fernet:
    key = hmac.new(secret.encode(), purpose.encode(), hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def seal(value: str, *, secret: str, purpose: str) -> str:
    return (
        _fernet(secret, purpose)
        .encrypt_at_time(value.encode(), int(time.time()))
        .decode()
    )


def unseal(token: str, *, secret: str, purpose: str, max_age: timedelta) -> str:
    try:
        return (
            _fernet(secret, purpose)
            .decrypt_at_time(
                token.encode(), int(max_age.total_seconds()), int(time.time())
            )
            .decode()
        )
    except InvalidToken as e:
        raise SealedValueInvalid() from e
