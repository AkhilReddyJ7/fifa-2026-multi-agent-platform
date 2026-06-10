"""Matches API tests."""

import pytest
from httpx import AsyncClient


async def _ensure_teams(client: AsyncClient) -> tuple[int, int]:
    """Create home and away teams, return (home_id, away_id)."""
    r1 = await client.post("/api/v1/teams", json={"name": "Germany", "fifa_code": "GER", "confederation": "UEFA"})
    r2 = await client.post("/api/v1/teams", json={"name": "Spain", "fifa_code": "ESP", "confederation": "UEFA"})
    # May already exist (409) — either way get the IDs
    for r in [r1, r2]:
        if r.status_code not in (201, 409):
            raise AssertionError(f"Unexpected: {r.status_code} {r.text}")

    g = (await client.get("/api/v1/teams/GER")).json()
    s = (await client.get("/api/v1/teams/ESP")).json()
    return g["id"], s["id"]


@pytest.mark.asyncio
async def test_list_matches_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches")
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_create_match(client: AsyncClient) -> None:
    home_id, away_id = await _ensure_teams(client)
    payload = {
        "home_team_id": home_id,
        "away_team_id": away_id,
        "tournament_year": 2018,
        "stage": "final",
        "home_goals": 4,
        "away_goals": 2,
        "venue": "Luzhniki Stadium",
    }
    r = await client.post("/api/v1/matches", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["home_goals"] == 4
    assert body["away_goals"] == 2
    assert body["stage"] == "final"
    assert body["home_team_code"] == "GER"
    assert body["away_team_code"] == "ESP"


@pytest.mark.asyncio
async def test_get_match_by_id(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/1")
    # Either 200 (match exists) or 404 (clean slate)
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_create_match_invalid_team(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/matches",
        json={"home_team_id": 99999, "away_team_id": 99998, "tournament_year": 2026, "stage": "group"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_matches_filter_year(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches?year=2018")
    assert r.status_code == 200
    for m in r.json()["items"]:
        assert m["tournament_year"] == 2018


@pytest.mark.asyncio
async def test_list_matches_filter_stage(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches?stage=final")
    assert r.status_code == 200
    for m in r.json()["items"]:
        assert m["stage"] == "final"


@pytest.mark.asyncio
async def test_match_stats_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches/99999/stats")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_matches_pagination(client: AsyncClient) -> None:
    r = await client.get("/api/v1/matches?page=1&page_size=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 5
    assert body["page_size"] == 5
