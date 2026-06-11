#!/usr/bin/env python3
"""Seed script — loads historical WC data into PostgreSQL and ChromaDB.

Usage:
    cd backend
    python -m scripts.seed_data
"""

from __future__ import annotations

import asyncio
import os
import sys

# Make sure the app package is importable when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import structlog
from sqlalchemy import select

from app.db.models import Match, Player, Team
from app.db.session import AsyncSessionLocal

log = structlog.get_logger()

# ── 48-team FIFA 2026 World Cup roster ───────────────────────────────────────
# ELO ratings reflect approximate standings entering the 2026 tournament.
# Confederations: UEFA (16), CONMEBOL (6), CONCACAF (6), CAF (9), AFC (8),
#                 OFC (1), Inter-confederation playoffs (2).

TEAMS = [
    # UEFA (16)
    {"name": "France",          "fifa_code": "FRA", "confederation": "UEFA",     "elo_rating": 2060.0},
    {"name": "Brazil",          "fifa_code": "BRA", "confederation": "CONMEBOL", "elo_rating": 2150.0},
    {"name": "Argentina",       "fifa_code": "ARG", "confederation": "CONMEBOL", "elo_rating": 2140.0},
    {"name": "England",         "fifa_code": "ENG", "confederation": "UEFA",     "elo_rating": 2020.0},
    {"name": "Spain",           "fifa_code": "ESP", "confederation": "UEFA",     "elo_rating": 2010.0},
    {"name": "Germany",         "fifa_code": "GER", "confederation": "UEFA",     "elo_rating": 1985.0},
    {"name": "Portugal",        "fifa_code": "POR", "confederation": "UEFA",     "elo_rating": 1975.0},
    {"name": "Netherlands",     "fifa_code": "NED", "confederation": "UEFA",     "elo_rating": 1970.0},
    {"name": "Belgium",         "fifa_code": "BEL", "confederation": "UEFA",     "elo_rating": 1960.0},
    {"name": "Italy",           "fifa_code": "ITA", "confederation": "UEFA",     "elo_rating": 1940.0},
    {"name": "Croatia",         "fifa_code": "CRO", "confederation": "UEFA",     "elo_rating": 1920.0},
    {"name": "Switzerland",     "fifa_code": "SUI", "confederation": "UEFA",     "elo_rating": 1900.0},
    {"name": "Denmark",         "fifa_code": "DEN", "confederation": "UEFA",     "elo_rating": 1895.0},
    {"name": "Austria",         "fifa_code": "AUT", "confederation": "UEFA",     "elo_rating": 1875.0},
    {"name": "Turkey",          "fifa_code": "TUR", "confederation": "UEFA",     "elo_rating": 1865.0},
    {"name": "Serbia",          "fifa_code": "SRB", "confederation": "UEFA",     "elo_rating": 1855.0},
    {"name": "Poland",          "fifa_code": "POL", "confederation": "UEFA",     "elo_rating": 1840.0},
    {"name": "Ukraine",         "fifa_code": "UKR", "confederation": "UEFA",     "elo_rating": 1835.0},
    # CONMEBOL (6)
    {"name": "Uruguay",         "fifa_code": "URU", "confederation": "CONMEBOL", "elo_rating": 1880.0},
    {"name": "Colombia",        "fifa_code": "COL", "confederation": "CONMEBOL", "elo_rating": 1890.0},
    {"name": "Ecuador",         "fifa_code": "ECU", "confederation": "CONMEBOL", "elo_rating": 1760.0},
    {"name": "Chile",           "fifa_code": "CHL", "confederation": "CONMEBOL", "elo_rating": 1820.0},
    # CONCACAF (6)
    {"name": "United States",   "fifa_code": "USA", "confederation": "CONCACAF", "elo_rating": 1830.0},
    {"name": "Mexico",          "fifa_code": "MEX", "confederation": "CONCACAF", "elo_rating": 1820.0},
    {"name": "Canada",          "fifa_code": "CAN", "confederation": "CONCACAF", "elo_rating": 1800.0},
    {"name": "Panama",          "fifa_code": "PAN", "confederation": "CONCACAF", "elo_rating": 1750.0},
    {"name": "Costa Rica",      "fifa_code": "CRC", "confederation": "CONCACAF", "elo_rating": 1755.0},
    {"name": "Jamaica",         "fifa_code": "JAM", "confederation": "CONCACAF", "elo_rating": 1710.0},
    # CAF (9)
    {"name": "Morocco",         "fifa_code": "MAR", "confederation": "CAF",      "elo_rating": 1850.0},
    {"name": "Senegal",         "fifa_code": "SEN", "confederation": "CAF",      "elo_rating": 1810.0},
    {"name": "Nigeria",         "fifa_code": "NGA", "confederation": "CAF",      "elo_rating": 1790.0},
    {"name": "Ghana",           "fifa_code": "GHA", "confederation": "CAF",      "elo_rating": 1780.0},
    {"name": "Cameroon",        "fifa_code": "CMR", "confederation": "CAF",      "elo_rating": 1770.0},
    {"name": "Ivory Coast",     "fifa_code": "CIV", "confederation": "CAF",      "elo_rating": 1785.0},
    {"name": "Egypt",           "fifa_code": "EGY", "confederation": "CAF",      "elo_rating": 1755.0},
    {"name": "Tunisia",         "fifa_code": "TUN", "confederation": "CAF",      "elo_rating": 1745.0},
    {"name": "South Africa",    "fifa_code": "RSA", "confederation": "CAF",      "elo_rating": 1740.0},
    # AFC (8)
    {"name": "Japan",           "fifa_code": "JPN", "confederation": "AFC",      "elo_rating": 1840.0},
    {"name": "South Korea",     "fifa_code": "KOR", "confederation": "AFC",      "elo_rating": 1790.0},
    {"name": "Iran",            "fifa_code": "IRN", "confederation": "AFC",      "elo_rating": 1800.0},
    {"name": "Australia",       "fifa_code": "AUS", "confederation": "AFC",      "elo_rating": 1770.0},
    {"name": "Saudi Arabia",    "fifa_code": "KSA", "confederation": "AFC",      "elo_rating": 1740.0},
    {"name": "Qatar",           "fifa_code": "QAT", "confederation": "AFC",      "elo_rating": 1700.0},
    {"name": "Iraq",            "fifa_code": "IRQ", "confederation": "AFC",      "elo_rating": 1705.0},
    {"name": "Indonesia",       "fifa_code": "IDN", "confederation": "AFC",      "elo_rating": 1680.0},
    # OFC (1)
    {"name": "New Zealand",     "fifa_code": "NZL", "confederation": "OFC",      "elo_rating": 1680.0},
    # Inter-confederation playoff spots (2)
    {"name": "Venezuela",       "fifa_code": "VEN", "confederation": "CONMEBOL", "elo_rating": 1720.0},
    {"name": "United Arab Emirates", "fifa_code": "UAE", "confederation": "AFC", "elo_rating": 1690.0},
]

# Representative matches from WC 2022 knockout stage
MATCHES_2022 = [
    # Quarter-finals
    {"home": "FRA", "away": "ENG", "stage": "qf",    "home_g": 2, "away_g": 1, "year": 2022, "venue": "Al Bayt Stadium"},
    {"home": "ARG", "away": "NED", "stage": "qf",    "home_g": 2, "away_g": 2, "year": 2022, "venue": "Lusail Stadium",
     "home_pen": 4, "away_pen": 3},
    {"home": "MAR", "away": "POR", "stage": "qf",    "home_g": 1, "away_g": 0, "year": 2022, "venue": "Al Thumama Stadium"},
    {"home": "CRO", "away": "BRA", "stage": "qf",    "home_g": 1, "away_g": 1, "year": 2022, "venue": "Education City Stadium",
     "home_pen": 4, "away_pen": 2},
    # Semi-finals
    {"home": "ARG", "away": "CRO", "stage": "sf",    "home_g": 3, "away_g": 0, "year": 2022, "venue": "Lusail Stadium"},
    {"home": "FRA", "away": "MAR", "stage": "sf",    "home_g": 2, "away_g": 0, "year": 2022, "venue": "Al Bayt Stadium"},
    # Final
    {"home": "ARG", "away": "FRA", "stage": "final", "home_g": 3, "away_g": 3, "year": 2022,
     "venue": "Lusail Stadium", "home_pen": 4, "away_pen": 2},
    # Third place
    {"home": "CRO", "away": "MAR", "stage": "3rd",   "home_g": 2, "away_g": 1, "year": 2022,
     "venue": "Khalifa International Stadium"},
]

MATCHES_2018 = [
    {"home": "FRA", "away": "CRO", "stage": "final", "home_g": 4, "away_g": 2, "year": 2018, "venue": "Luzhniki Stadium"},
    {"home": "FRA", "away": "BEL", "stage": "sf",    "home_g": 1, "away_g": 0, "year": 2018, "venue": "Saint Petersburg Stadium"},
    {"home": "CRO", "away": "ENG", "stage": "sf",    "home_g": 2, "away_g": 1, "year": 2018, "venue": "Luzhniki Stadium"},
    {"home": "FRA", "away": "URU", "stage": "qf",    "home_g": 2, "away_g": 0, "year": 2018, "venue": "Nizhny Novgorod Stadium"},
    {"home": "BEL", "away": "BRA", "stage": "qf",    "home_g": 2, "away_g": 1, "year": 2018, "venue": "Kazan Arena"},
]

MATCHES_2014 = [
    {"home": "GER", "away": "ARG", "stage": "final", "home_g": 1, "away_g": 0, "year": 2014,
     "venue": "Estádio do Maracanã"},
    {"home": "GER", "away": "BRA", "stage": "sf",    "home_g": 7, "away_g": 1, "year": 2014,
     "venue": "Estádio Governador Magalhães Pinto"},
    {"home": "ARG", "away": "NED", "stage": "sf",    "home_g": 0, "away_g": 0, "year": 2014,
     "venue": "Arena de São Paulo", "home_pen": 4, "away_pen": 2},
]


async def seed_teams(session) -> dict[str, int]:
    """Insert teams, return fifa_code → id map."""
    code_to_id: dict[str, int] = {}
    for t in TEAMS:
        existing = (await session.execute(select(Team).where(Team.fifa_code == t["fifa_code"]))).scalar_one_or_none()
        if not existing:
            team = Team(**t)
            session.add(team)
            await session.flush()
            code_to_id[t["fifa_code"]] = team.id
            log.info("seed.team.created", code=t["fifa_code"])
        else:
            code_to_id[t["fifa_code"]] = existing.id
            log.debug("seed.team.exists", code=t["fifa_code"])
    return code_to_id


async def seed_matches(session, code_to_id: dict[str, int]) -> None:
    all_matches = MATCHES_2022 + MATCHES_2018 + MATCHES_2014
    for m in all_matches:
        home_id = code_to_id.get(m["home"])
        away_id = code_to_id.get(m["away"])
        if not home_id or not away_id:
            log.warning("seed.match.skip", home=m["home"], away=m["away"])
            continue

        existing = (
            await session.execute(
                select(Match).where(
                    Match.home_team_id == home_id,
                    Match.away_team_id == away_id,
                    Match.tournament_year == m["year"],
                    Match.stage == m["stage"],
                )
            )
        ).scalar_one_or_none()

        if not existing:
            match = Match(
                home_team_id=home_id,
                away_team_id=away_id,
                tournament_year=m["year"],
                stage=m["stage"],
                venue=m.get("venue"),
                home_goals=m.get("home_g"),
                away_goals=m.get("away_g"),
                home_goals_pen=m.get("home_pen"),
                away_goals_pen=m.get("away_pen"),
            )
            session.add(match)
            log.info("seed.match.created", home=m["home"], away=m["away"], year=m["year"])


async def seed_rag() -> None:
    try:
        from app.rag.ingestion import ingest_all
        counts = ingest_all()
        log.info("seed.rag.complete", **counts)
    except Exception as exc:
        log.warning("seed.rag.skipped", reason=str(exc))


async def main() -> None:
    log.info("seed.start", teams=len(TEAMS))
    async with AsyncSessionLocal() as session:
        code_to_id = await seed_teams(session)
        await seed_matches(session, code_to_id)
        await session.commit()
    await seed_rag()
    log.info("seed.complete")


if __name__ == "__main__":
    asyncio.run(main())
