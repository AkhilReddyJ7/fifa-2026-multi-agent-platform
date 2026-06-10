"""Teams API tests — CRUD and player sub-resource."""

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

TEAM_BRA = {
    "name": "Brazil",
    "fifa_code": "BRA",
    "confederation": "CONMEBOL",
    "elo_rating": 2150.0,
}

TEAM_ARG = {
    "name": "Argentina",
    "fifa_code": "ARG",
    "confederation": "CONMEBOL",
    "elo_rating": 2140.0,
}

TEAM_FRA = {
    "name": "France",
    "fifa_code": "FRA",
    "confederation": "UEFA",
    "elo_rating": 2060.0,
}


async def _create_team(client: AsyncClient, payload: dict) -> dict:
    r = await client.post("/api/v1/teams", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_teams_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/teams")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_create_team(client: AsyncClient) -> None:
    team = await _create_team(client, TEAM_BRA)
    assert team["fifa_code"] == "BRA"
    assert team["name"] == "Brazil"
    assert team["confederation"] == "CONMEBOL"
    assert "id" in team


@pytest.mark.asyncio
async def test_create_team_duplicate_returns_409(client: AsyncClient) -> None:
    await _create_team(client, TEAM_ARG)
    r = await client.post("/api/v1/teams", json=TEAM_ARG)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_get_team_by_code(client: AsyncClient) -> None:
    await _create_team(client, TEAM_FRA)
    r = await client.get("/api/v1/teams/FRA")
    assert r.status_code == 200
    assert r.json()["name"] == "France"


@pytest.mark.asyncio
async def test_get_team_case_insensitive(client: AsyncClient) -> None:
    await client.post("/api/v1/teams", json={"name": "France CI", "fifa_code": "FCI", "confederation": "UEFA"})
    r = await client.get("/api/v1/teams/fci")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_team_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/v1/teams/ZZZ")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_team(client: AsyncClient) -> None:
    await client.post("/api/v1/teams", json={"name": "Brazil Up", "fifa_code": "BRU", "confederation": "CONMEBOL"})
    r = await client.patch("/api/v1/teams/BRU", json={"elo_rating": 2200.0, "group_label": "A"})
    assert r.status_code == 200
    assert r.json()["elo_rating"] == 2200.0
    assert r.json()["group_label"] == "A"


@pytest.mark.asyncio
async def test_list_teams_filter_confederation(client: AsyncClient) -> None:
    r = await client.get("/api/v1/teams?confederation=UEFA")
    assert r.status_code == 200
    for t in r.json()["items"]:
        assert t["confederation"] == "UEFA"


@pytest.mark.asyncio
async def test_list_teams_pagination(client: AsyncClient) -> None:
    r = await client.get("/api/v1/teams?page=1&page_size=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["page"] == 1
    assert body["page_size"] == 2


@pytest.mark.asyncio
async def test_add_player_to_team(client: AsyncClient) -> None:
    await client.post("/api/v1/teams", json={"name": "Brazil PL", "fifa_code": "BPL", "confederation": "CONMEBOL"})
    r = await client.post(
        "/api/v1/teams/BPL/players",
        json={"name": "Vinicius Jr", "position": "FW", "caps": 40, "goals": 14, "team_id": 0},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Vinicius Jr"


@pytest.mark.asyncio
async def test_list_players(client: AsyncClient) -> None:
    await client.post("/api/v1/teams", json={"name": "Brazil LS", "fifa_code": "BLS", "confederation": "CONMEBOL"})
    r = await client.get("/api/v1/teams/BLS/players")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_delete_team(client: AsyncClient) -> None:
    payload = {"name": "TestTeam", "fifa_code": "TST", "confederation": "UEFA"}
    await _create_team(client, payload)
    r = await client.delete("/api/v1/teams/TST")
    assert r.status_code == 204
    r2 = await client.get("/api/v1/teams/TST")
    assert r2.status_code == 404
