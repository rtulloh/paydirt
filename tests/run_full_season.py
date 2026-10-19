#!/usr/bin/env python3
"""Validate a generated 16-week 1983 season and postseason, not historical results.

Run from the repository root: python3 tests/run_full_season.py
Uses real engine rules/dice and CLI flow, with AI supplying human decisions.
Requires the test dependencies (pytest). Never writes saved standings.
"""

import contextlib
import io
from pathlib import Path
import sys
from typing import Optional
from unittest.mock import patch

import pytest

# Support direct execution as well as importing this runner in unit tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.game_engine import PaydirtGameEngine
from paydirt.computer_ai import ComputerAI
from paydirt.play_resolver import PlayType
from paydirt.standings import Season
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
    if getattr(state, "is_playoff", False):
        checks["Tie game in playoffs"] = state.home_score != state.away_score
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
    for previous, current in zip(state.scoring_plays, state.scoring_plays[1:]):
        if getattr(current, "play_type", None) in ("PAT", "2PT", "Def 2PT"):
            checks["conversion period differs from touchdown period"] = (
                checks.get("conversion period differs from touchdown period", True)
                and getattr(previous, "play_type", None) == "TD"
                and current.quarter == previous.quarter
            )
    failures = [message for message, passed in checks.items() if not passed]
    if failures:
        raise ValueError("; ".join(failures))


def run_full_season(teams: list[str]) -> int:
    """Run 224 regular games and a generated postseason; return nonzero on failure."""
    failures = overtime = ties = 0
    season = Season(1983)
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
                season.add_game(home, engine.state.home_score, away, engine.state.away_score, week)
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
    if failures:
        print("Generated playoffs: not run because regular-season validation failed.")
        return 1
    return run_playoffs(season)


def seed_playoffs(season: Season) -> dict[str, list[str]]:
    """Seed three division winners and two wildcards in each conference.

    This generated bracket uses win percentage (ties count as half a win), point
    differential, points scored, then team name. These deterministic regression
    tiebreakers are deliberately not the complete historical NFL tiebreakers.
    """
    if len(season.divisions) != 2 or any(len(divs) != 3 for divs in season.divisions.values()):
        raise ValueError("Postseason requires two conferences with three divisions each")
    records = season.get_standings()
    teams = [team for divs in season.divisions.values() for members in divs.values() for team in members]
    if len(set(teams)) != len(teams) or not set(teams).issubset(records):
        raise ValueError("Postseason teams must be distinct and have regular-season records")

    def rank(team: str) -> tuple:
        record = records[team]
        return (-record.win_pct, -record.point_diff, -record.points_for, team)

    seeds = {}
    for conference, divisions in sorted(season.divisions.items()):
        if any(not members for members in divisions.values()):
            raise ValueError("Every postseason division must have teams")
        winners = sorted((min(members, key=rank) for members in divisions.values()), key=rank)
        remaining = sorted((team for members in divisions.values() for team in members
                            if team not in winners), key=rank)
        if len(remaining) < 2:
            raise ValueError("Every conference needs two wildcard teams")
        seeds[conference] = winners + remaining[:2]
    return seeds


def run_playoffs(season: Season) -> int:
    """Run a nine-game, ten-team bracket with real playoff rules and no tied finals."""
    seeds = seed_playoffs(season)
    conferences = sorted(seeds)
    attempted = failures = overtime = ties = 0
    original_kickoff = PaydirtGameEngine.kickoff

    def guarded_kickoff(engine: PaydirtGameEngine, *args, **kwargs):
        if engine.state.game_over:
            raise ValueError("Kickoff attempted after game over")
        return original_kickoff(engine, *args, **kwargs)

    def play(round_name: str, away: str, home: str, seed: int) -> Optional[str]:
        nonlocal attempted, failures, overtime, ties
        attempted += 1
        output = io.StringIO()
        try:
            with pytest.MonkeyPatch.context() as monkeypatch, contextlib.redirect_stdout(output):
                engine = run_seeded_cli_game(
                    monkeypatch, f"1983/{away}", f"1983/{home}", seed, is_playoff=True,
                )
            overtime += engine.state.ot_period > 0
            ties += engine.state.home_score == engine.state.away_score
            if not engine.state.is_playoff:
                raise ValueError("Playoff rules were not enabled")
            validate_game(engine, output.getvalue())
            winner = home if engine.state.home_score > engine.state.away_score else away
            print(f"{round_name}: {away} {engine.state.away_score} - "
                  f"{home} {engine.state.home_score}; winner={winner}; seed={seed}", flush=True)
            return winner
        except Exception as error:
            failures += 1
            print(f"FAIL {round_name} {away}@{home} seed={seed}: "
                  f"{type(error).__name__}: {error}", file=sys.stderr)
            print(output.getvalue(), file=sys.stderr)
            return None

    def progress(round_name: str) -> None:
        print(f"{round_name}: {attempted - failures}/{attempted} playoff games passed", flush=True)

    for conference in conferences:
        print(f"{conference} playoff seeds: " + ", ".join(
            f"{number}={team}" for number, team in enumerate(seeds[conference], 1)))
    with patch.object(PaydirtGameEngine, "kickoff", guarded_kickoff):
        wildcards = {
            conference: play(f"{conference} Wild Card", seeds[conference][4], seeds[conference][3],
                             19831701 + number)
            for number, conference in enumerate(conferences)
        }
        progress("Wild Card")
        divisional = {}
        for number, conference in enumerate(conferences):
            first, second, third = seeds[conference][:3]
            wildcard = wildcards[conference]
            # Before 1990, division opponents could not meet in this round.
            # If the wildcard shares #1's division, #1 plays #3 instead.
            same_division = wildcard is not None and (
                season.get_team_division(first) == season.get_team_division(wildcard))
            first_opponent, second_opponent = (third, wildcard) if same_division else (wildcard, third)
            winners = []
            for matchup, (away, home) in enumerate(((first_opponent, first), (second_opponent, second))):
                winners.append(play(f"{conference} Divisional", away, home, 19831801 + 2 * number + matchup)
                               if away is not None else None)
            divisional[conference] = winners
        progress("Divisional")
        champions = {}
        for number, conference in enumerate(conferences):
            winners = divisional[conference]
            if all(winners):
                home, away = sorted(winners, key=seeds[conference].index)
                champions[conference] = play(f"{conference} Conference Championships", away, home,
                                            19831901 + number)
            else:
                champions[conference] = None
        progress("Conference Championships")
        champion = None
        if all(champions.values()):
            champion = play("Championship", champions[conferences[0]], champions[conferences[1]], 19832001)
        progress("Championship")
    print(f"Generated playoffs: {attempted - failures}/9 passed; {failures} failed; "
          f"{9 - attempted} not played; {overtime} OT games; {ties} ties. "
          "Standings persistence disabled.")
    if champion is not None:
        print(f"Champion: {champion}")
    return 1 if failures or attempted != 9 else 0


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
        ("Raiders", "Eagles", 19831104, False),
        # Narration now has its own RNG. Retain the old complete games and
        # require real untimed downs in supplements, without changing dice.
        ("Raiders", "Eagles", 19831107, True),
        # Retain prior reproductions when corrected commentary/timing changes
        # their seeded trajectories; require a real extension in the new supplement.
        ("Chiefs", "Giants", 19831603, False),
        ("Chiefs", "Giants", 19831607, False),
        ("Chiefs", "Giants", 19831621, False),
        ("Chiefs", "Giants", 19831623, False),
        ("Chiefs", "Giants", 19831624, True),
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
