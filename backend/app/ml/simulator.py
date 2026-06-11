"""FIFA 2026 World Cup Monte Carlo tournament simulator.

Simulates the full FIFA 2026 format:
  - 48 teams in 12 groups of 4
  - Top 2 from each group + 8 best 3rd-place → 32 for Round of 32
  - Standard single-elimination knockout bracket

Each simulation is independent — results are accumulated across N runs.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.ml.predictor import elo_expected


@dataclass
class TeamEntry:
    code: str
    name: str
    elo: float
    group: Optional[str] = None


@dataclass
class SimulationResult:
    n_simulations: int
    win_probabilities: Dict[str, float]      # code → P(win tournament)
    final_probabilities: Dict[str, float]    # code → P(reach final)
    semifinal_probabilities: Dict[str, float]
    expected_bracket: Dict[str, Any]         # most-likely bracket based on ELO
    params: Dict[str, Any]


def _simulate_match(elo_h: float, elo_a: float, knockout: bool = False) -> Tuple[str, str]:
    """Return ('home','away') result as ('H', 'A') or ('D') — no draws in knockout."""
    e_h = elo_expected(elo_h, elo_a)
    r = random.random()

    if knockout:
        # In knockout: decide by extra time / penalties — still probability-based
        if r < e_h:
            return "H", "A"
        else:
            return "A", "H"

    # Group stage: draws possible
    # Approximate: draw band proportional to closeness
    draw_band = 0.28 * (1 - abs(e_h - 0.5) * 2)
    if r < e_h - draw_band / 2:
        return "H", "A"
    elif r < e_h + draw_band / 2:
        return "D", "D"
    else:
        return "A", "H"


def _run_group_stage(
    teams: List[TeamEntry],
    groups: Dict[str, List[str]],
) -> Dict[str, List[TeamEntry]]:
    """Simulate group stage. Return dict[group_label] → sorted list (pts desc)."""
    team_map = {t.code: t for t in teams}
    standings: Dict[str, Dict[str, Dict]] = {}  # group → code → {pts, gd}

    for grp, codes in groups.items():
        standings[grp] = {c: {"pts": 0, "gd": 0, "gf": 0} for c in codes}
        members = [team_map[c] for c in codes if c in team_map]
        for i, ta in enumerate(members):
            for tb in members[i + 1:]:
                res_a, res_b = _simulate_match(ta.elo, tb.elo)
                if res_a == "H":
                    standings[grp][ta.code]["pts"] += 3
                    standings[grp][ta.code]["gf"] += 2
                    standings[grp][ta.code]["gd"] += 1
                    standings[grp][tb.code]["gd"] -= 1
                elif res_a == "D":
                    standings[grp][ta.code]["pts"] += 1
                    standings[grp][tb.code]["pts"] += 1
                    standings[grp][ta.code]["gf"] += 1
                    standings[grp][tb.code]["gf"] += 1
                else:
                    standings[grp][tb.code]["pts"] += 3
                    standings[grp][tb.code]["gf"] += 2
                    standings[grp][tb.code]["gd"] += 1
                    standings[grp][ta.code]["gd"] -= 1

    result: Dict[str, List[TeamEntry]] = {}
    for grp, stats in standings.items():
        ordered = sorted(stats.keys(), key=lambda c: (stats[c]["pts"], stats[c]["gd"], stats[c]["gf"]), reverse=True)
        result[grp] = [team_map[c] for c in ordered if c in team_map]
    return result


def _advance_from_groups(
    group_results: Dict[str, List[TeamEntry]],
) -> List[TeamEntry]:
    """Top 2 per group + 8 best 3rd-place → 32 teams."""
    qualifiers: List[TeamEntry] = []
    third_place: List[TeamEntry] = []
    for ranked in group_results.values():
        if len(ranked) >= 1:
            qualifiers.append(ranked[0])
        if len(ranked) >= 2:
            qualifiers.append(ranked[1])
        if len(ranked) >= 3:
            third_place.append(ranked[2])

    # Sort 3rd-place by ELO (proxy for pts since we don't carry pts across)
    third_place.sort(key=lambda t: t.elo, reverse=True)
    qualifiers.extend(third_place[:8])
    return qualifiers


def _run_knockout(teams: List[TeamEntry]) -> Tuple[TeamEntry, Dict[str, str]]:
    """Run single-elimination bracket. Returns (winner, round_map)."""
    round_map: Dict[str, str] = {}
    bracket = list(teams)
    random.shuffle(bracket)

    round_names = ["R32", "R16", "QF", "SF", "Final"]
    rnd_idx = 0

    while len(bracket) > 1:
        name = round_names[min(rnd_idx, len(round_names) - 1)]
        next_round = []
        for i in range(0, len(bracket) - 1, 2):
            ta, tb = bracket[i], bracket[i + 1]
            res, _ = _simulate_match(ta.elo, tb.elo, knockout=True)
            winner = ta if res == "H" else tb
            loser = tb if res == "H" else ta
            round_map[loser.code] = name
            next_round.append(winner)
        if len(bracket) % 2 == 1:
            next_round.append(bracket[-1])  # bye
        bracket = next_round
        rnd_idx += 1

    winner = bracket[0]
    round_map[winner.code] = "Champion"
    return winner, round_map


def run_simulation(
    teams: List[TeamEntry],
    n_simulations: int = 1000,
    seed: Optional[int] = None,
) -> SimulationResult:
    """Run Monte Carlo tournament simulation."""
    if seed is not None:
        random.seed(seed)

    if not teams:
        return SimulationResult(
            n_simulations=0,
            win_probabilities={},
            final_probabilities={},
            semifinal_probabilities={},
            expected_bracket={},
            params={"n_simulations": n_simulations},
        )

    # Build groups — assign teams round-robin if no group label set
    groups: Dict[str, List[str]] = defaultdict(list)
    group_labels = [chr(ord("A") + i) for i in range(12)]
    unassigned = [t for t in teams if not t.group]
    assigned = [t for t in teams if t.group]

    for t in assigned:
        groups[t.group].append(t.code)  # type: ignore[index]

    for i, t in enumerate(unassigned):
        groups[group_labels[i % 12]].append(t.code)

    # Pad groups to 4 — repeat last team if needed (edge case for small datasets)
    for grp in list(groups.keys()):
        while len(groups[grp]) < 4:
            groups[grp].append(groups[grp][-1])

    win_counts: Dict[str, int] = defaultdict(int)
    final_counts: Dict[str, int] = defaultdict(int)
    sf_counts: Dict[str, int] = defaultdict(int)

    for _ in range(n_simulations):
        group_results = _run_group_stage(teams, groups)
        qualifiers = _advance_from_groups(group_results)
        if not qualifiers:
            continue
        winner, round_map = _run_knockout(qualifiers)
        win_counts[winner.code] += 1
        for code, rnd in round_map.items():
            if rnd in ("Final", "Champion"):
                final_counts[code] += 1
            if rnd in ("SF", "Final", "Champion"):
                sf_counts[code] += 1

    def _probs(counts: Dict[str, int]) -> Dict[str, float]:
        total = n_simulations
        return {code: round(cnt / total, 4) for code, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)}

    # Expected bracket: deterministic ELO-based run for display
    exp_winner, exp_bracket = _deterministic_bracket(teams, groups)

    return SimulationResult(
        n_simulations=n_simulations,
        win_probabilities=_probs(win_counts),
        final_probabilities=_probs(final_counts),
        semifinal_probabilities=_probs(sf_counts),
        expected_bracket=exp_bracket,
        params={"n_simulations": n_simulations, "teams": len(teams), "groups": len(groups)},
    )


def _deterministic_bracket(
    teams: List[TeamEntry], groups: Dict[str, List[str]]
) -> Tuple[Optional[TeamEntry], Dict[str, Any]]:
    """Best-ELO-wins bracket (no randomness) for display."""
    team_map = {t.code: t for t in teams}

    # Group stage: top ELO advances
    qualifiers: List[TeamEntry] = []
    for codes in groups.values():
        grp_teams = sorted([team_map[c] for c in codes if c in team_map], key=lambda t: t.elo, reverse=True)
        qualifiers.extend(grp_teams[:2])

    # Pad to nearest power of 2
    qualifiers.sort(key=lambda t: t.elo, reverse=True)

    bracket: Dict[str, str] = {}
    current = list(qualifiers)
    rnd_names = ["R32", "R16", "QF", "SF", "Final"]
    rnd_idx = 0

    while len(current) > 1:
        name = rnd_names[min(rnd_idx, len(rnd_names) - 1)]
        nxt = []
        for i in range(0, len(current) - 1, 2):
            winner = current[i] if current[i].elo >= current[i + 1].elo else current[i + 1]
            loser = current[i + 1] if current[i].elo >= current[i + 1].elo else current[i]
            bracket[loser.code] = name
            nxt.append(winner)
        if len(current) % 2 == 1:
            nxt.append(current[-1])
        current = nxt
        rnd_idx += 1

    if current:
        bracket[current[0].code] = "Champion"
        return current[0], bracket
    return None, bracket
