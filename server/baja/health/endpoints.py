from fastapi import APIRouter, Depends
from sqlalchemy import text

from baja.kit.db.postgres import AsyncReadSession
from baja.postgres import get_db_read_session

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(
    session: AsyncReadSession = Depends(get_db_read_session),
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
