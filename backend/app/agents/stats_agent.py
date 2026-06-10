"""Stats Agent — retrieves team data, head-to-head records, and match stats from PostgreSQL."""

from __future__ import annotations

import time
from typing import Any, Dict

import structlog

from app.agents.state import AgentTrace, PlatformState
from app.agents.tools.db_tools import (
    get_all_teams,
    get_head_to_head,
    get_team_by_code,
    get_team_match_stats,
    get_team_players,
)
from app.db.session import AsyncSessionLocal

log = structlog.get_logger()


async def stats_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — populates state.team_data."""
    t0 = time.monotonic()
    team_codes = state.get("team_codes", [])

    team_data: Dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        # If specific teams requested, fetch their data
        for code in team_codes:
            team = await get_team_by_code(db, code)
            if team:
                players = await get_team_players(db, code)
                match_stats = await get_team_match_stats(db, code)
                team_data[code] = {
                    **team,
                    "players": players[:11],          # top 11 by rating
                    "match_stats": match_stats,
                }

        # Head-to-head for exactly two teams
        h2h = []
        if len(team_codes) == 2:
            h2h = await get_head_to_head(db, team_codes[0], team_codes[1])

        # Always fetch all teams for simulation / ranking context
        if not team_codes or state.get("intent") in ("simulate", "analyze"):
            team_data["_all_teams"] = await get_all_teams(db)

    team_data["head_to_head"] = h2h

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info("stats_agent.done", teams=team_codes, h2h_records=len(h2h), ms=elapsed)

    trace_entry: AgentTrace = {
        "agent": "stats",
        "input_keys": ["team_codes", "intent"],
        "output_keys": ["team_data"],
        "duration_ms": elapsed,
        "notes": f"fetched {len(team_codes)} teams, {len(h2h)} h2h records",
    }

    return {"team_data": team_data, "trace": [trace_entry]}
