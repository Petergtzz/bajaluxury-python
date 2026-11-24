from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from baja.exceptions import Conflict
from baja.kit.db.postgres import AsyncSession
from baja.postgres import get_db_session
from baja.worker import enqueue_job
from tests.widget import Widget


def add_widget_routes(app: FastAPI) -> None:
    router = APIRouter()

    @router.post("/widgets/{name}")
    async def create_widget(
        name: str, session: AsyncSession = Depends(get_db_session)
    ) -> dict[str, str]:
        session.add(Widget(name=name))
        await session.flush()
        if name == "taken":
            raise Conflict("That name is taken.")
        return {"name": name}

    app.include_router(router)


async def widget_names(session: AsyncSession) -> list[str]:
    return list((await session.execute(select(Widget.name))).scalars())


async def test_health_reaches_the_database(client: AsyncClient) -> None:
    response = await client.get("/healthz")

    assert (response.status_code, response.json()) == (200, {"status": "ok"})


async def test_a_successful_request_commits(
    app: FastAPI, client: AsyncClient, session: AsyncSession
) -> None:
    add_widget_routes(app)

    response = await client.post("/widgets/lamp")

    assert response.status_code == 200
    assert await widget_names(session) == ["lamp"]


async def test_an_error_rolls_back_and_answers_error_and_detail(
    app: FastAPI, client: AsyncClient, session: AsyncSession
) -> None:
    add_widget_routes(app)

    response = await client.post("/widgets/taken")

    assert (response.status_code, response.json()) == (
        409,
        {"error": "Conflict", "detail": "That name is taken."},
    )
    assert await widget_names(session) == []


async def test_unknown_routes_answer_in_the_same_shape(client: AsyncClient) -> None:
    response = await client.get("/v1/nowhere")

    assert (response.status_code, response.json()) == (
        404,
        {"error": "ResourceNotFound", "detail": "Not found"},
    )


async def test_jobs_go_out_only_after_a_commit(
    app: FastAPI, client: AsyncClient, sent_jobs: list[tuple[str, tuple[object, ...]]]
) -> None:
    router = APIRouter()

    @router.post("/jobs/{outcome}")
    async def queue(outcome: str) -> None:
        enqueue_job("email.send_login_code", "owner@bajaluxurymgmt.com", "sealed")
        if outcome == "fail":
            raise Conflict("Not this time.")

    app.include_router(router)

    assert (await client.post("/jobs/fail")).status_code == 409
    assert sent_jobs == []
    assert (await client.post("/jobs/ok")).status_code == 200
    assert sent_jobs == [
        ("email.send_login_code", ("owner@bajaluxurymgmt.com", "sealed"))
    ]
