"""Source-calendar season checks; historical results are diagnostics, never an oracle."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import random
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

from .auto_game import run_auto_game
from .chart_calibration import EngineCalibrationObserver
from .chart_engine_audit import _factory, _game_receipt, chart_fingerprint, engine_fingerprint
from .chart_loader import load_team_chart
from .chart_runtime_identity import loaded_runtime_identity
from .game_engine import PaydirtGameEngine
from .season_rules import load_season_rules
from .standings import Season

FORMATS = {"ten_team": (3, 2, 9), "fourteen_team": (4, 3, 13)}
TIEBREAK = "win_pct_point_diff_points_for_name"


def validate_historical_schedule(data: dict, year: int) -> dict:
    """Require a complete sourced calendar, membership and historical result set."""
    if (type(year) is not int or type(data.get("season")) is not int
            or data["season"] != year or data.get("schema_version") != 1):
        raise ValueError("Historical schedule year/schema differs from selected year")
    format_name = data.get("postseason_format")
    if format_name not in FORMATS:
        raise ValueError("Unsupported source-year postseason format")
    division_count, wildcards, _ = FORMATS[format_name]
    divisions = data["divisions"]
    if (not isinstance(divisions, dict) or len(divisions) != 2
            or any(not isinstance(ds, dict) or len(ds) != division_count for ds in divisions.values())):
        raise ValueError("Membership does not match declared postseason format")
    teams = []
    for ds in divisions.values():
        for members in ds.values():
            if not isinstance(members, list) or not members:
                raise ValueError("Every source-year division needs teams")
            teams.extend(members)
    if (any(not isinstance(t, str) or not t or Path(t).name != t or t in {".", ".."}
            or "\\" in t for t in teams) or len(set(teams)) != len(teams)
            or any(sum(map(len, ds.values())) < division_count + wildcards for ds in divisions.values())):
        raise ValueError("Source-year teams must be safe distinct folders with enough qualifiers")
    if (data.get("tiebreaker") != TIEBREAK or not data.get("attribution")
            or any(not isinstance(r, dict) or not str(r.get("url", "")).startswith("https://")
                   or len(str(r.get("sha256", ""))) != 64
                   or any(c not in "0123456789abcdef" for c in r["sha256"]) for r in data["attribution"])):
        raise ValueError("Missing provenance or explicit regression tiebreak specification")
    for field in ("games_per_team", "regular_weeks"):
        if type(data.get(field)) is not int or data[field] < 1:
            raise ValueError(f"Invalid historical {field}")
    rows = data["games"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Missing historical fixtures")
    seen, weekly = set(), set()
    counts, phases = Counter(), Counter()
    conference = {t: c for c, ds in divisions.items() for members in ds.values() for t in members}
    previous_winners: dict[str, set[str]] = {}
    for row in rows:
        game_id, phase, week = row["game_id"], row["phase"], row["week"]
        away, home = row["away"], row["home"]
        if not isinstance(game_id, str) or not game_id or game_id in seen:
            raise ValueError("Missing/duplicate source game ID")
        seen.add(game_id)
        if phase not in {"REG", "WC", "DIV", "CON", "SB"} or type(week) is not int or week < 1:
            raise ValueError("Unsupported historical phase/week")
        if away not in teams or home not in teams or away == home:
            raise ValueError("Unknown/self historical matchup")
        played = date.fromisoformat(row["date"])
        if played.year not in {year, year + 1}:
            raise ValueError("Historical game date is outside selected season")
        if type(row.get("neutral")) is not bool:
            raise ValueError("Historical neutral-site designation must be explicit")
        for side in ("away", "home"):
            score = row[f"{side}_score"]
            if type(score) is not int or score < 0:
                raise ValueError("Historical final scores must be nonnegative integers")
            key = (week, row[side])
            if key in weekly:
                raise ValueError("Team has multiple historical fixtures in one week")
            weekly.add(key)
        if phase == "REG":
            if week > data["regular_weeks"]:
                raise ValueError("Regular fixture exceeds declared calendar")
            counts.update((away, home))
        elif (week <= data["regular_weeks"] or row["away_score"] == row["home_score"]
              or (phase != "SB" and conference[away] != conference[home])
              or (phase == "SB" and conference[away] == conference[home])):
            raise ValueError("Invalid historical postseason week/conference/final")
        phases[phase] += 1
    if counts != Counter({team: data["games_per_team"] for team in teams}):
        raise ValueError("Incomplete historical regular-season team/game inventory")
    expected = {"REG": len(teams) * data["games_per_team"] // 2,
                "WC": 2 if format_name == "ten_team" else 6, "DIV": 4, "CON": 2, "SB": 1}
    if dict(phases) != expected:
        raise ValueError("Incomplete historical game/round inventory")
    # Historical winners, rather than simulated replay winners, bind this source bracket.
    for phase in ("WC", "DIV", "CON", "SB"):
        phase_rows = [r for r in rows if r["phase"] == phase]
        participants = [t for r in phase_rows for t in (r["away"], r["home"])]
        if len(participants) != len(set(participants)):
            raise ValueError("Duplicate historical round participant")
        if phase == "DIV" and not previous_winners["WC"].issubset(participants):
            raise ValueError("Historical wildcard winner missing from divisional round")
        if phase in {"CON", "SB"}:
            previous = "DIV" if phase == "CON" else "CON"
            if set(participants) != previous_winners[previous]:
                raise ValueError("Historical losing team advances or winning team is omitted")
        previous_winners[phase] = {
            r["home"] if r["home_score"] > r["away_score"] else r["away"] for r in phase_rows}
    return data


def load_historical_schedule(path: Path, year: int) -> dict:
    """Read actual source fixtures; missing data never generates a replacement."""
    return validate_historical_schedule(json.loads(Path(path).read_text()), year)


def validate_chart_inputs(spec: dict, directory: Path) -> dict:
    """Decode every selected team and source-year rule before the first game."""
    before = chart_fingerprint(directory)
    rules = load_season_rules(directory)
    if rules.season != spec["season"]:
        raise ValueError("Chart rules differ from historical fixture year")
    hashes = {}
    names = []
    for ds in spec["divisions"].values():
        for members in ds.values():
            for team in members:
                folder = directory / team
                chart = load_team_chart(folder)
                names.append(chart.peripheral.short_name)
                names_to_bind = ["offense.csv", "defense.csv", "special.csv", "team.yaml"]
                if (folder / "roster.json").is_file():
                    names_to_bind.append("roster.json")
                for name in names_to_bind:
                    path = folder / name
                    hashes[f"{team}/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(names) != len(set(names)):
        raise ValueError("Selected charts have duplicate team identifiers")
    for path in directory.glob("*.yaml"):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if before != chart_fingerprint(directory):
        raise ValueError("Selected chart bytes changed while decoding")
    hashes["__chart_fingerprint__"] = before
    return hashes


def _snapshot(game: Any) -> dict:
    state = game.state
    return {"state": {key: getattr(state, key) for key in (
        "quarter", "time_remaining", "home_score", "away_score", "down",
        "yards_to_go", "ball_position", "is_home_possession", "game_over", "ot_period")},
        "untimed_down": game.has_untimed_down(),
        "home_box": asdict(state.home_stats), "away_box": asdict(state.away_stats)}


def simulate_historical_game(
    directory: Path, away: str, home: str, seed: int, *, is_playoff: bool, policy: str,
) -> dict:
    """Run the existing auto engine and retain selected-action plus final receipts."""
    random_state = random.getstate()
    observer = EngineCalibrationObserver()
    actions, pending = [], []
    output = io.StringIO()
    original_kickoff = PaydirtGameEngine.kickoff

    def guarded_kickoff(game: Any, *args: Any, **kwargs: Any) -> Any:
        if game.state.game_over:
            raise ValueError("Kickoff attempted after game over")
        return original_kickoff(game, *args, **kwargs)

    def decision(game: Any, ai: Any, play: Any, defense: Any) -> None:
        observer.on_decision(game, ai, play, defense)
        pending[:] = [{"before": _snapshot(game), "play": play.name, "defense": defense.name,
                      "mode": str(ai.last_mode or "normal")}]

    def result(game: Any, outcome: Any) -> None:
        observer.on_result(game, outcome)
        if len(pending) != 1:
            raise ValueError("Selected action/result inventory differs")
        action = pending.pop()
        action.update(after=_snapshot(game), result=outcome.result.result_type.name,
                      yards=outcome.yards_gained, initial_yards=outcome.result.yards,
                      penalty_applied=bool(outcome.penalty_applied),
                      replay_down=bool(outcome.result.replay_down),
                      touchdown=bool(outcome.touchdown), safety=bool(outcome.safety),
                      field_goal_made=bool(outcome.field_goal_made))
        actions.append(action)

    try:
        random.seed(seed)
        with contextlib.redirect_stdout(output), patch.object(PaydirtGameEngine, "kickoff", guarded_kickoff):
            game = run_auto_game(str(directory / away), str(directory / home), is_playoff=is_playoff,
                                 ai_factory=_factory(policy), on_decision=decision,
                                 on_result=result, play_limit=750)
        if game is None or pending or "FINAL" not in output.getvalue():
            raise ValueError("Missing/incomplete auto engine game")
        observer.finalize_game(game)
        receipt = _game_receipt(game, observer.report(), away, home, seed)
        receipt.update(is_playoff=game.state.is_playoff, ot_period=game.state.ot_period,
                       accounting_errors=[], selected_calls=actions, final=_snapshot(game),
                       periods=game.get_period_scores(),
                       scoring_plays=[asdict(play) for play in game.state.scoring_plays])
        if is_playoff and receipt["home_score"] == receipt["away_score"]:
            raise ValueError("Tie game in playoffs")
        return receipt
    finally:
        random.setstate(random_state)


def _season(spec: dict) -> Season:
    season = Season(spec["season"])
    season.divisions = spec["divisions"]
    return season


def historical_comparison(spec: dict, season: Season, receipts: list[dict]) -> dict:
    """Compare outcomes without requiring historical scores or winners."""
    actual = _season(spec)
    fixtures = {r["game_id"]: r for r in spec["games"] if r["phase"] == "REG"}
    for row in fixtures.values():
        actual.add_game(row["home"], row["home_score"], row["away"], row["away_score"], row["week"])
    simulated, historical = season.get_standings(), actual.get_standings()
    rows = [r for r in receipts if r["phase"] == "REG"]
    errors = [abs(r[f"{side}_score"] - fixtures[r["game_id"]][f"{side}_score"])
              for r in rows for side in ("away", "home")]
    return {"regular_games": len(rows),
            "exact_score_matches": sum(all(r[f"{s}_score"] == fixtures[r["game_id"]][f"{s}_score"]
                                           for s in ("away", "home")) for r in rows),
            "mean_absolute_team_score_error": sum(errors) / len(errors),
            "uncertainty": "One season; no repeated-season confidence or predictive-accuracy claim.",
            "teams": {t: {"simulated": asdict(simulated[t]), "historical": asdict(historical[t]),
                          "win_fraction_delta": simulated[t].win_pct - historical[t].win_pct,
                          "point_differential_delta": simulated[t].point_diff - historical[t].point_diff}
                      for t in sorted(simulated)}}


def audit_historical_season(
    spec: dict, directory: Path, *, master: int = 20261108, policy: str = "hard",
    postseason_mode: str = "simulated",
) -> dict:
    """Run source regular fixtures and a distinct simulated or historical postseason."""
    validate_historical_schedule(spec, spec["season"])
    if (type(master) is not int or master < 0 or policy not in {"hard", "balanced"}
            or postseason_mode not in {"simulated", "historical"}):
        raise ValueError("Unsupported seed, policy or postseason mode")
    regular = [r for r in spec["games"] if r["phase"] == "REG"]
    expected = FORMATS[spec["postseason_format"]][2]
    report: dict = {"passed": False, "errors": [], "game_receipts": [], "season": spec["season"],
                    "policy": policy, "master": master, "historical_comparison": None,
                    "developer_reference": "not_requested", "release_certified": False,
                    "source_accepted": False, "postseason": {
                        "mode": "simulated_standings" if postseason_mode == "simulated" else "historical_fixture_replay",
                        "expected_games": expected, "not_played": expected, "champion": None,
                        "tiebreaker": TIEBREAK, "official_tiebreaks_verified": False,
                        "seeds": {}, "tied_record_groups": []}}
    season = _season(spec)
    original_engine, runtime = engine_fingerprint(), loaded_runtime_identity()
    report["engine_fingerprint"], report["runtime_identity"] = original_engine, runtime
    sequence = 0

    def play(away: str, home: str, phase: str, game_id: str, week: int) -> str | None:
        nonlocal sequence
        seed = master + sequence * 1009
        sequence += 1
        try:
            receipt = simulate_historical_game(directory, away, home, seed,
                                                is_playoff=phase != "REG", policy=policy)
            if (receipt["away"] != away or receipt["home"] != home or receipt["seed"] != seed
                    or receipt["game_over"] is not True or receipt["untimed_down"] is not False
                    or receipt["is_playoff"] is not (phase != "REG") or receipt["accounting_errors"]
                    or any(type(receipt[f"{s}_score"]) is not int or receipt[f"{s}_score"] < 0
                           for s in ("away", "home"))
                    or (phase != "REG" and receipt["home_score"] == receipt["away_score"])):
                raise ValueError("Invalid game final/rules/accounting receipt")
            receipt.update(phase=phase, game_id=game_id, week=week)
            report["game_receipts"].append(receipt)
            if phase == "REG":
                season.add_game(home, receipt["home_score"], away, receipt["away_score"], week)
            return home if receipt["home_score"] > receipt["away_score"] else away
        except (ValueError, KeyError, TypeError, OSError, RuntimeError, AssertionError) as error:
            report["errors"].append(f"{phase} {game_id} {away}@{home} seed={seed}: {type(error).__name__}: {error}")
            return None

    for row in regular:
        play(row["away"], row["home"], "REG", row["game_id"], row["week"])
    if not report["errors"]:
        report["historical_comparison"] = historical_comparison(spec, season, report["game_receipts"])
        if postseason_mode == "historical":
            for row in spec["games"]:
                if row["phase"] != "REG":
                    play(row["away"], row["home"], row["phase"], row["game_id"], row["week"])
        else:
            records = season.get_standings()

            def rank(team: str) -> tuple:
                record = records[team]
                return (-record.win_pct, -record.point_diff, -record.points_for, team)

            seeds = {}
            for conference, divisions in sorted(spec["divisions"].items()):
                winners = sorted((min(members, key=rank) for members in divisions.values()), key=rank)
                remaining = sorted((t for members in divisions.values() for t in members if t not in winners), key=rank)
                wildcards = FORMATS[spec["postseason_format"]][1]
                seeds[conference] = winners + remaining[:wildcards]
                tied = {}
                for team in sorted(t for members in divisions.values() for t in members):
                    tied.setdefault(records[team].win_pct, []).append(team)
                report["postseason"]["tied_record_groups"].extend(
                    {"conference": conference, "win_fraction": fraction, "teams": names}
                    for fraction, names in tied.items() if len(names) > 1)
            report["postseason"]["seeds"] = seeds
            modern = spec["postseason_format"] == "fourteen_team"
            champions = []
            for conference, order in seeds.items():
                def playoff(away: str, home: str, phase: str, conference: str = conference) -> str | None:
                    index = sum(r["phase"] == phase for r in report["game_receipts"])
                    return play(away, home, phase, f"simulated-{conference}-{phase}-{index}",
                                spec["regular_weeks"] + {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}[phase])

                if modern:
                    wild = [playoff(order[a], order[h], "WC") for a, h in ((6, 1), (5, 2), (4, 3))]
                    if any(t is None for t in wild):
                        champions.append(None)
                        continue
                    alive = sorted([order[0], *wild], key=order.index)
                    pairs = ((alive[3], alive[0]), (alive[2], alive[1]))
                else:
                    wild = playoff(order[4], order[3], "WC")
                    if wild is None:
                        champions.append(None)
                        continue
                    same = season.get_team_division(wild) == season.get_team_division(order[0])
                    pairs = ((order[2], order[0]), (wild, order[1])) if same else (
                        (wild, order[0]), (order[2], order[1]))
                winners = [playoff(away, home, "DIV") for away, home in pairs]
                if any(t is None for t in winners):
                    champions.append(None)
                else:
                    home, away = sorted(winners, key=order.index)
                    champions.append(playoff(away, home, "CON"))
            if all(champions):
                report["postseason"]["champion"] = play(
                    champions[0], champions[1], "SB", "simulated-SB",
                    spec["regular_weeks"] + 4)
    observed = sum(r["phase"] != "REG" for r in report["game_receipts"])
    report["postseason"]["not_played"] = expected - observed
    if observed != expected:
        report["errors"].append(f"Postseason inventory {observed}/{expected}; failed/dependent games do not advance")
    report["standings"] = {t: asdict(r) for t, r in season.get_standings().items()}
    if original_engine != engine_fingerprint() or runtime != loaded_runtime_identity():
        report["errors"].append("Engine or loaded runtime changed during season")
    report["passed"] = not report["errors"]
    report["limitations"] = [
        "Regression tiebreaks use win fraction, point differential, points scored and name; official NFL tiebreaks are unverified.",
        "Selected-action callbacks omit intervening PAT/kickoff transitions; final boxes/scoring are retained, not complete per-action conformance.",
        "One development season is not a fit, strength-confidence, qualification-probability or release acceptance study.",
        "Historical fixture replay does not calculate counterfactual qualification or a simulated bracket champion."]
    return report
