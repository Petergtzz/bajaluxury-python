from typing import Any

import pytest
from httpx import AsyncClient

from baja.checklist import tasks
from baja.models import ChecklistTemplateItem, ChecklistType, Company, Role, User
from tests.email.test_tasks import RecordingSender
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_user,
)


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    sender = RecordingSender()
    monkeypatch.setattr(tasks, "get_email_sender", lambda: sender)
    return sender


async def template(save_fixture: SaveFixture) -> None:
    for type, position, description in [
        (ChecklistType.check_in, 2, "Pool is clean"),
        (ChecklistType.check_in, 1, "Keys are in the lockbox"),
        (ChecklistType.weekly, 1, "Run every tap"),
    ]:
        await save_fixture(
            ChecklistTemplateItem(type=type, position=position, description=description)
        )


async def set_recipients(
    client: AsyncClient, property_id: object, *recipients: tuple[User, str]
) -> Any:
    response = await client.put(
        f"/v1/checklists/properties/{property_id}",
        json={
            "recipients": [
                {"user_id": str(u.id), "kind": kind} for u, kind in recipients
            ]
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def start(
    client: AsyncClient, property_id: object, type: str = "check_in"
) -> Any:
    response = await client.post(
        "/v1/checklists/", json={"property_id": str(property_id), "type": type}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_checklist_starts_with_its_types_template(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await template(save_fixture)
    campo = await create_property(save_fixture)
    await login(user)

    checklist = await start(client, campo.id)

    assert (
        checklist["type"],
        checklist["created_by_id"],
        checklist["completed_at"],
    ) == (
        "check_in",
        str(user.id),
        None,
    )
    assert [
        (i["position"], i["description"], i["is_checked"]) for i in checklist["items"]
    ] == [
        (1, "Keys are in the lockbox", False),
        (2, "Pool is clean", False),
    ]


async def test_items_are_ticked_and_noted(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    await template(save_fixture)
    campo = await create_property(save_fixture)
    await login(user)
    checklist = await start(client, campo.id)
    keys, pool = (item["id"] for item in checklist["items"])
    url = f"/v1/checklists/{checklist['id']}/items"

    ticked = await client.patch(f"{url}/{keys}", json={"is_checked": True})
    noted = await client.patch(f"{url}/{pool}", json={"note": "Leaves in the skimmer"})
    unticked = await client.patch(
        f"{url}/{keys}", json={"is_checked": False, "note": ""}
    )

    keys_ticked = ticked.json()["items"][0]
    assert keys_ticked["is_checked"] is True
    assert keys_ticked["checked_at"] is not None
    assert noted.json()["items"][1]["note"] == "Leaves in the skimmer"
    assert noted.json()["items"][1]["is_checked"] is False
    assert unticked.json()["items"][0]["checked_at"] is None
    assert unticked.json()["items"][0]["note"] is None


async def test_completing_sends_the_report_and_freezes_it(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    sent_jobs: list[tuple[str, tuple[Any, ...]]],
    worker_resources: None,
) -> None:
    await template(save_fixture)
    campo = await create_property(save_fixture, name="Campo 9")
    await create_user(save_fixture, Role.owner, email="boss@example.com")
    lore = await create_user(save_fixture, Role.homeowner, email="lore@example.com")
    await assign_properties(save_fixture, lore, campo)
    await login(user)
    await set_recipients(client, campo.id, (lore, "to"), (user, "cc"))
    checklist = await start(client, campo.id)
    keys, pool = (item["id"] for item in checklist["items"])
    url = f"/v1/checklists/{checklist['id']}"
    await client.patch(
        f"{url}/items/{keys}", json={"is_checked": True, "note": "Two sets"}
    )
    await client.patch(f"{url}/items/{pool}", json={"note": "Needs a clean"})

    completed = await client.post(f"{url}/complete")
    # Who hears about the next one changes; who heard about this one doesn't.
    await set_recipients(client, campo.id, (user, "to"))
    again = await client.post(f"{url}/complete")
    edit = await client.patch(f"{url}/items/{pool}", json={"is_checked": True})

    assert completed.json()["completed_at"] is not None
    assert (completed.json()["emailed_to"], completed.json()["emailed_cc"]) == (
        ["lore@example.com"],
        [user.email],
    )
    assert (again.status_code, edit.status_code) == (409, 409)
    assert edit.json()["error"] == "ChecklistCompleted"
    assert sent_jobs == [("checklist.send_report", (checklist["id"],))]

    await tasks.send_checklist_report(checklist["id"])

    [email] = sender.sent
    assert (email.to, email.cc, email.bcc) == (
        ("lore@example.com",),
        (user.email,),
        ("boss@example.com",),
    )
    assert email.subject == "Check-in completed · Campo 9"
    checked, unchecked = email.text.split("Not checked:")
    assert "Keys are in the lockbox (Note: Two sets)" in checked
    assert "Pool is clean (Note: Needs a clean)" in unchecked
    assert "Completed by: Pedro Gutierrez" in email.text
    assert "Pool is clean" in email.html


async def test_homeowners_read_their_own_and_change_nothing(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
) -> None:
    await template(save_fixture)
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    await login(user)
    own = await start(client, mine.id)
    other = await start(client, theirs.id, "weekly")
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    listed = await client.get("/v1/checklists/")
    hidden = await client.get(f"/v1/checklists/{other['id']}")
    tick = await client.patch(
        f"/v1/checklists/{own['id']}/items/{own['items'][0]['id']}",
        json={"is_checked": True},
    )
    templates = await client.get("/v1/checklist-templates/")

    assert [c["id"] for c in listed.json()] == [own["id"]]
    assert (hidden.status_code, tick.status_code, templates.status_code) == (
        404,
        403,
        403,
    )


async def test_list_by_property_newest_first_and_delete(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    colinas = await create_property(save_fixture, name="Colinas 21")
    await login(user)
    first = await start(client, campo.id)
    second = await start(client, campo.id, "weekly")
    await start(client, colinas.id)

    listed = await client.get("/v1/checklists/", params={"property_id": str(campo.id)})
    deleted = await client.delete(f"/v1/checklists/{first['id']}")
    after = await client.get("/v1/checklists/", params={"property_id": str(campo.id)})

    assert [c["id"] for c in listed.json()] == [second["id"], first["id"]]
    assert deleted.status_code == 204
    assert [c["id"] for c in after.json()] == [second["id"]]


async def test_archived_properties_get_no_new_checklists(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    sold = await create_property(save_fixture, is_archived=True)
    await login(user)

    response = await client.post(
        "/v1/checklists/", json={"property_id": str(sold.id), "type": "weekly"}
    )

    assert response.status_code == 409


async def test_managers_rewrite_a_template_whole(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    await template(save_fixture)
    campo = await create_property(save_fixture)
    await login(await create_user(save_fixture, Role.manager))
    started = await start(client, campo.id)
    keys, pool = (
        i["id"]
        for i in (await client.get("/v1/checklist-templates/")).json()
        if i["type"] == "check_in"
    )

    # The pool goes first, the keys are dropped, and the gas is new.
    saved = await client.put(
        "/v1/checklist-templates/check_in",
        json={
            "items": [
                {"id": pool, "description": " Pool and jacuzzi are clean "},
                {"description": "Gas tank above half"},
            ]
        },
    )
    listed = (await client.get("/v1/checklist-templates/")).json()
    after = await client.get(f"/v1/checklists/{started['id']}")
    fresh = await start(client, campo.id)

    assert [
        (i["id"] == pool, i["description"], i["position"]) for i in saved.json()
    ] == [
        (True, "Pool and jacuzzi are clean", 1),
        (False, "Gas tank above half", 2),
    ]
    assert keys not in {i["id"] for i in listed}
    # Other types are untouched, and walks already started keep what they had.
    assert [i["description"] for i in listed if i["type"] == "weekly"] == [
        "Run every tap"
    ]
    assert [i["description"] for i in after.json()["items"]] == [
        "Keys are in the lockbox",
        "Pool is clean",
    ]
    assert [i["description"] for i in fresh["items"]] == [
        "Pool and jacuzzi are clean",
        "Gas tank above half",
    ]


@pytest.mark.parametrize("problem", ["twice", "another type's", "unknown"])
async def test_a_template_only_keeps_its_own_items_once(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    problem: str,
) -> None:
    await template(save_fixture)
    await login(user)
    listed = (await client.get("/v1/checklist-templates/")).json()
    check_in = [i["id"] for i in listed if i["type"] == "check_in"]
    weekly = [i["id"] for i in listed if i["type"] == "weekly"]
    ids = {
        "twice": [check_in[0], check_in[0]],
        "another type's": [weekly[0]],
        "unknown": ["01a21454-0000-7000-8000-000000000000"],
    }[problem]

    response = await client.put(
        "/v1/checklist-templates/check_in",
        json={"items": [{"id": id, "description": "x"} for id in ids]},
    )

    assert (response.status_code, response.json()["error"]) == (422, "TemplateInvalid")


async def test_every_active_property_says_who_hears_about_it(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    await create_property(save_fixture, name="Sold", is_archived=True)
    lore = await create_user(save_fixture, Role.homeowner, email="lore@example.com")
    stranger = await create_user(save_fixture, Role.homeowner, email="s@example.com")
    await assign_properties(save_fixture, lore, campo)
    await assign_properties(save_fixture, stranger, colinas)
    await login(user)

    saved = await set_recipients(client, campo.id, (user, "cc"), (lore, "to"))
    listed = (await client.get("/v1/checklists/properties")).json()
    outsider = await client.put(
        f"/v1/checklists/properties/{campo.id}",
        json={"recipients": [{"user_id": str(stranger.id), "kind": "to"}]},
    )
    copies_only = await client.put(
        f"/v1/checklists/properties/{campo.id}",
        json={"recipients": [{"user_id": str(user.id), "kind": "cc"}]},
    )
    nobody = await set_recipients(client, colinas.id)

    assert [p["property_name"] for p in listed] == ["Campo 9", "Colinas 21"]
    assert listed[0] == saved
    assert [(r["email"], r["kind"]) for r in saved["recipients"]] == [
        ("lore@example.com", "to"),
        (user.email, "cc"),
    ]
    assert outsider.json()["detail"] == (
        "Everyone who receives it must be able to see the property."
    )
    assert copies_only.status_code == 422
    assert nobody["recipients"] == []


async def test_homeowners_set_up_no_recipients(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, campo)
    await login(homeowner)

    listed = await client.get("/v1/checklists/properties")
    put = await client.put(
        f"/v1/checklists/properties/{campo.id}", json={"recipients": []}
    )

    assert (listed.status_code, put.status_code) == (403, 403)


async def test_a_property_naming_nobody_reports_to_the_owners(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
    sender: RecordingSender,
    worker_resources: None,
) -> None:
    await template(save_fixture)
    campo = await create_property(save_fixture, name="Campo 9")
    await create_user(save_fixture, Role.owner, email="boss@example.com")
    await login(user)
    checklist = await start(client, campo.id)

    completed = await client.post(f"/v1/checklists/{checklist['id']}/complete")
    await tasks.send_checklist_report(checklist["id"])

    assert completed.json()["emailed_to"] == []
    [email] = sender.sent
    assert (set(email.to), email.cc, email.bcc) == (
        {"boss@example.com", user.email},
        (),
        (),
    )
