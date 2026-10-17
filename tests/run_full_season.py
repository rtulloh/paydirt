#!/usr/bin/env python3
"""Validate a generated 16-week 1983 season, not the historical NFL schedule.

Run from the repository root: python3 tests/run_full_season.py
Uses real engine rules/dice and CLI flow, with AI supplying human decisions.
Requires the test dependencies (pytest). Never writes saved standings.
"""

import contextlib
import io
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

# Support direct execution as well as importing this runner in unit tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.game_engine import PaydirtGameEngine
from paydirt.computer_ai import ComputerAI
from paydirt.play_resolver import PlayType
from tests.test_untimed_down_flow import run_seeded_cli_game


SEASON_DIR = Path(__file__).resolve().parents[1] / "seasons" / "1983"


def build_schedule(teams: list[str]) -> list[tuple[int, int, str, str, int]]:
    """Return deterministic (week, matchup, away, home, seed) entries."""
    if len(teams) != 28 or len(set(teams)) != 28:
        raise ValueError("Full-season validation requires 28 distinct 1983 teams")
    rotation = sorted(teams)
    schedule = []
    for week in range(1, 17):
        for matchup in range(1, 15):
            away, home = rotation[matchup - 1], rotation[-matchup]
            if week % 2 == 0:
                away, home = home, away
            schedule.append((week, matchup, away, home, 19830000 + week * 100 + matchup))
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return schedule


def validate_game(engine: PaydirtGameEngine, output: str) -> None:
    """Raise on incomplete games or inconsistent period/scoring-log totals."""
    state = engine.state
    checks = {
        "game_over flag is false": state.game_over,
        "untimed down remains pending": not engine.has_untimed_down(),
        "CLI did not display FINAL": "FINAL" in output,
    }
    periods = engine.get_period_scores()
    for side, score, is_home in (
        ("home", state.home_score, True), ("away", state.away_score, False),
    ):
        checks[f"{side} period scores do not sum to final score"] = (
            sum(period[side] for period in periods) == score
        )
        checks[f"{side} scoring log does not sum to final score"] = (
            sum(play.points for play in state.scoring_plays if play.is_home_team == is_home) == score
        )
    failures = [message for message, passed in checks.items() if not passed]
    if failures:
        raise ValueError("; ".join(failures))


def run_full_season(teams: list[str]) -> int:
    """Run all 224 games; print reproduction details and return nonzero on failure."""
    failures = overtime = ties = 0
    original_kickoff = PaydirtGameEngine.kickoff

    def guarded_kickoff(engine: PaydirtGameEngine, *args, **kwargs):
        if engine.state.game_over:
            raise ValueError("Kickoff attempted after game over")
        return original_kickoff(engine, *args, **kwargs)

    with patch.object(PaydirtGameEngine, "kickoff", guarded_kickoff):
        for number, (week, matchup, away, home, seed) in enumerate(build_schedule(teams), 1):
            output = io.StringIO()
            try:
                with pytest.MonkeyPatch.context() as monkeypatch, contextlib.redirect_stdout(output):
                    engine = run_seeded_cli_game(monkeypatch, f"1983/{away}", f"1983/{home}", seed)
                validate_game(engine, output.getvalue())
                overtime += engine.state.ot_period > 0
                ties += engine.state.home_score == engine.state.away_score
            except Exception as error:
                failures += 1
                print(
                    f"FAIL week={week} matchup={matchup} {away}@{home} seed={seed}: "
                    f"{type(error).__name__}: {error}", file=sys.stderr,
                )
                print(output.getvalue(), file=sys.stderr)
            if matchup == 14:
                print(f"Week {week}: {number - failures}/{number} games passed", flush=True)
    print(
        f"Generated season: {224 - failures}/224 passed; {failures} failed; "
        f"{overtime} OT games; {ties} ties. Standings persistence disabled."
    )
    return 1 if failures else 0


def run_historical_reproductions() -> int:
    """Keep private-chart reproductions in local integration, never unit tests."""
    # These are engine/CLI flow regressions, not AI benchmarks. Keep calling
    # legal scrimmage plays even when the live AI could safely kneel, so late
    # penalty rolls and untimed downs remain exercised. Do not alter dice or
    # engine rules. The generated season above uses the unmodified live AI.
    select = ComputerAI.select_offense_with_clock_management

    def play_on(ai: ComputerAI, game: PaydirtGameEngine) -> tuple:
        decision = select(ai, game)
        if decision[0] != PlayType.QB_KNEEL:
            return decision
        state = game.state
        if state.down == 1:
            play = ai._first_down_offense(state.ball_position)
        elif state.down == 2:
            play = ai._second_down_offense(state.yards_to_go)
        else:
            play = ai._third_down_offense(state.yards_to_go, state.ball_position)
        return (play, False, False, False, 0, False)

    failures = 0
    cases = (
        ("Raiders", "Eagles", 19831104, True),
        # Retain prior reproductions when corrected commentary/timing changes
        # their seeded trajectories; require a real extension in the new supplement.
        ("Chiefs", "Giants", 19831603, False),
        ("Chiefs", "Giants", 19831607, False),
        ("Chiefs", "Giants", 19831621, True),
        ("Rams", "49ers", 19830601, False),
        ("Browns", "Buccaneers", 19830914, False),
    )
    for away, home, seed, needs_untimed in cases:
        output = io.StringIO()
        try:
            with pytest.MonkeyPatch.context() as monkeypatch, contextlib.redirect_stdout(output):
                with patch.object(ComputerAI, "select_offense_with_clock_management", play_on):
                    engine = run_seeded_cli_game(monkeypatch, f"1983/{away}", f"1983/{home}", seed)
            validate_game(engine, output.getvalue())
            if needs_untimed and "UNTIMED DOWN" not in output.getvalue():
                raise ValueError("Expected untimed-down reproduction was not exercised")
        except Exception as error:
            failures += 1
            print(f"FAIL {away}@{home} seed={seed}: {error}", file=sys.stderr)
            print(output.getvalue(), file=sys.stderr)
    print(f"Historical reproductions: {len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


def main() -> int:
    """Run local integration using private, untracked 1983 data."""
    try:
        teams = [path.name for path in SEASON_DIR.iterdir() if path.is_dir() and (path / "team.yaml").is_file()]
        build_schedule(teams)  # Validate availability before running any games.
        reproduction_status = run_historical_reproductions()
        season_status = run_full_season(teams)
        return reproduction_status or season_status
    except (OSError, ValueError) as error:
        print(f"Full-season validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
