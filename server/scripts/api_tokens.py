"""Issues, lists and revokes API tokens: one per device, such as a phone.

A token acts as its user, with their role. It is shown once, when issued:
only its hash is kept, so a lost one is revoked and a new one issued.

Usage: python -m scripts.api_tokens issue <email> <label>
       python -m scripts.api_tokens list
       python -m scripts.api_tokens revoke <token id>
"""

import asyncio
import sys
from uuid import UUID

from baja.auth.repository import ApiTokenRepository
from baja.auth.service import auth as auth_service
from baja.kit.db.postgres import AsyncSession, create_async_sessionmaker
from baja.models import ApiToken
from baja.postgres import create_async_engine
from baja.user.repository import UserRepository


async def issue(session: AsyncSession, email: str, label: str) -> str:
    user = await UserRepository.from_session(session).get_by_email(email)
    if user is None:
        return f"No user with the email {email}."
    token, api_token = await auth_service.issue_api_token(session, user, label=label)
    return (
        f"Issued {api_token.id} for {user.email} ({user.role}), {label!r}.\n"
        f"Token, shown only now:\n{token}"
    )


async def list_tokens(session: AsyncSession) -> str:
    api_tokens = await ApiTokenRepository.from_session(session).list_all()
    return (
        "\n".join(
            f"{t.id}  {t.user.email:<32}  {t.label:<24}  last used "
            + (f"{t.last_used_at:%Y-%m-%d %H:%M}" if t.last_used_at else "never")
            for t in api_tokens
        )
        or "No tokens."
    )


async def revoke(session: AsyncSession, token_id: str) -> str:
    try:
        id = UUID(token_id)
    except ValueError:
        return f"{token_id!r} is not a token id: see `list`."
    repository = ApiTokenRepository.from_session(session)
    api_token = await repository.get_one_or_none(
        repository.get_base_statement().where(ApiToken.id == id)
    )
    if api_token is None:
        return f"No active token {token_id}."
    await auth_service.revoke_api_token(session, api_token)
    return f"Revoked {token_id}, {api_token.label!r}."


async def run(session: AsyncSession, args: list[str]) -> str | None:
    match args:
        case ["issue", email, label]:
            return await issue(session, email, label)
        case ["list"]:
            return await list_tokens(session)
        case ["revoke", token_id]:
            return await revoke(session, token_id)
    return None


async def main(args: list[str]) -> int:
    engine = create_async_engine("script")
    try:
        async with create_async_sessionmaker(engine)() as session:
            output = await run(session, args)
            await session.commit()
    finally:
        await engine.dispose()
    print(output or __doc__)  # noqa: T201
    return 0 if output else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
