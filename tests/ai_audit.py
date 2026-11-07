"""Testing-only AI configuration, evidence collection, and balance reporting.

Uses the production auto-game loop; never resolves plays or writes standings.
Random isolation is serial/in-process, not thread-safe. No chart cells or narrative
logs are exported. Reports are local developer evidence, not usage quotas.
"""

import contextlib
import hashlib
import io
import json
import logging
import math
import platform
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from unittest.mock import patch

from paydirt.auto_game import run_auto_game
from paydirt.computer_ai import ComputerAI, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.offense_strategy import situation_key
from paydirt.play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType
from tests.run_full_season import validate_game
from tests.semantic_audit import SemanticAudit

DIFFICULTIES = ("easy", "medium", "hard", "balanced")
SITUATION_CSV_FIELDS = ("team", "difficulty", "mode", "down", "distance_band", "calls",
                        "largest_share", "distinct_plays", "longest_streak", "small_sample",
                        "play_counts", "primary_play_shares")


@dataclass(frozen=True)
class GameSpec:
    """One independently reproducible matchup; week zero denotes an exhibition."""

    away: str
    home: str
    seed: int
    away_difficulty: str = "hard"
    home_difficulty: str = "hard"
    week: int = 0
    is_playoff: bool = False

    def __post_init__(self) -> None:
        if self.away_difficulty not in DIFFICULTIES or self.home_difficulty not in DIFFICULTIES:
            raise ValueError("Unknown audit difficulty")
        if not self.away or not self.home or self.away == self.home:
            raise ValueError("Audit requires two distinct teams")


def game_seed(seed: int, identity: str) -> int:
    """Stable across processes/Python hash randomization; independent of run order."""
    return int.from_bytes(hashlib.sha256(f"paydirt-audit-v1:{seed}:{identity}".encode()).digest()[:8], "big")


def generated_schedule(
    teams: list[str], weeks: int, seed: int,
    away_difficulty: str = "hard", home_difficulty: str = "hard",
) -> list[GameSpec]:
    """Circle-method generated regular season, not a historical schedule/bracket."""
    if len(teams) < 2 or len(teams) % 2 or len(set(teams)) != len(teams) or weeks < 1:
        raise ValueError("Schedule requires an even number of distinct teams and positive weeks")
    rotation = sorted(teams)
    schedule = []
    for week in range(1, weeks + 1):
        for index in range(len(rotation) // 2):
            away, home = rotation[index], rotation[-index - 1]
            if week % 2 == 0:
                away, home = home, away
            identity = f"week={week}:{away}@{home}"
            schedule.append(GameSpec(away, home, game_seed(seed, identity),
                                     away_difficulty, home_difficulty, week))
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return schedule


def _team_label(specification: str) -> str:
    """Keep only season/team identity, not absolute local chart paths."""
    parts = specification.rstrip("/").split("/")
    return "/".join(parts[-2:]) if len(parts) > 1 else parts[0]


def audit_game(spec: GameSpec, play_limit: int = 500) -> dict:
    """Run and validate a complete game, returning failures with partial evidence.

    Pre-play evidence is captured before resolution; results are captured once
    after all penalty decisions. PATs/kickoffs are engine flow, not selected calls.
    """
    config = asdict(spec)
    config.update(away=_team_label(spec.away), home=_team_label(spec.home))
    record = {"config": config, "status": "failed", "calls": []}
    output = io.StringIO()
    original_random = random.getstate()
    original_kickoff = PaydirtGameEngine.kickoff
    semantics = SemanticAudit()
    original_penalty_choice = ComputerAI.should_accept_penalty

    def checked_penalty(ai: ComputerAI, outcome: PlayOutcome, *args, **kwargs) -> tuple:
        decision = original_penalty_choice(ai, outcome, *args, **kwargs)
        semantics.penalty(outcome, decision)
        return decision

    def guarded_kickoff(engine: PaydirtGameEngine, *args, **kwargs) -> PlayOutcome:
        if engine.state.game_over:
            raise ValueError("Kickoff attempted after game over")
        return original_kickoff(engine, *args, **kwargs)

    def factory(game: PaydirtGameEngine, is_home: bool) -> ComputerAI:
        difficulty = spec.home_difficulty if is_home else spec.away_difficulty
        if difficulty == "balanced":
            ai = ComputerAI(aggression=.5, ai_behavior=game.season_rules.ai_behavior)
        else:
            ai = create_computer_ai(difficulty, game, is_home)
        # Keep the balanced comparison identical to plain auto orchestration.
        # Configured difficulty runs use independent team streams; balanced
        # retains production's lazy stream initialization from the game seed.
        if difficulty != "balanced":
            ai._offense_rng = random.Random(game_seed(spec.seed, f"{is_home}:offense"))
            ai._defense_rng = random.Random(game_seed(spec.seed, f"{is_home}:defense"))
        return ai

    def decision(game: PaydirtGameEngine, ai: ComputerAI, play: PlayType, defense: DefenseType) -> None:
        semantics.before(game)
        state = game.state
        home = state.is_home_possession
        weights = {}
        if ai.last_mode is None and ai.offense_strategy is not None:
            weights = ai.offense_strategy.weights(state.down, state.yards_to_go,
                                                  game.offensive_call_history, home)
        elif ai.last_mode in ("Two-Minute Drill", "Play + Spike") and play in CHART_PLAY_TYPES:
            weights = ai.get_hurry_up_weights(game)
        total = sum(weights.values())
        record["calls"].append({"before": {
            "team": config["home" if home else "away"], "is_home": home,
            "difficulty": spec.home_difficulty if home else spec.away_difficulty,
            "quarter": state.quarter, "minutes_remaining": state.time_remaining,
            "overtime_period": state.ot_period, "down": state.down,
            "distance": state.yards_to_go, "ball_position": state.ball_position,
            "score_differential": (state.home_score - state.away_score) * (1 if home else -1),
            "mode": ai.last_mode or "ordinary", "play": play.value,
            "probabilities": {p.value: weight / total for p, weight in weights.items()},
        }})
        # Deliberately do not record the simultaneously selected defense as
        # offense evidence: the offense cannot see that unrevealed decision.

    def result(game: PaydirtGameEngine, outcome: PlayOutcome) -> None:
        if outcome.pending_penalty_decision:
            raise ValueError("Audit result still requires a penalty decision")
        semantics.result(game, outcome)
        call = record["calls"][-1]
        if "result" in call:
            raise ValueError("Duplicate audit result")
        call["result"] = {
            "play": outcome.play_type.value, "yards": outcome.yards_gained,
            "first_down": outcome.first_down, "turnover": outcome.turnover,
            "turnover_on_downs": outcome.turnover_on_downs, "touchdown": outcome.touchdown,
            "safety": outcome.safety, "field_goal_made": outcome.field_goal_made,
            "penalty_applied": outcome.penalty_applied,
            "pending_penalty_decision": outcome.pending_penalty_decision,
            "spike_used": outcome.spike_used, "timeout_used": outcome.timeout_used,
        }

    try:
        random.seed(spec.seed)
        with (patch.object(PaydirtGameEngine, "kickoff", guarded_kickoff),
              patch.object(ComputerAI, "should_accept_penalty", checked_penalty),
              contextlib.redirect_stdout(output)):
            game = run_auto_game(spec.away, spec.home, is_playoff=spec.is_playoff,
                                 ai_factory=factory, on_decision=decision, on_result=result,
                                 play_limit=play_limit)
        if game is None:
            raise ValueError("Team lookup failed")
        validate_game(game, output.getvalue())
        if not record["calls"] or any("result" not in call for call in record["calls"]):
            raise ValueError("Incomplete audit evidence")
        record.update(status="passed", final={
            "home_score": game.state.home_score, "away_score": game.state.away_score,
            "overtime_periods": game.state.ot_period, "game_over": game.state.game_over,
            "untimed_down_pending": game.has_untimed_down(),
        })
    except Exception as error:
        # Never serialize engine exception text: malformed chart errors can
        # contain private cells/paths. Matchup/seed reproduce the local failure.
        logging.getLogger(__name__).debug("Operation failed", exc_info=True)
        limits = {
            "Auto-game play limit reached before game completion",
            "Auto-game penalty decision limit reached",
            "Auto-game scoring/kickoff sequence limit reached",
        }
        reason = "play/sequence limit reached" if str(error) in limits else "game or evidence validation failed"
        record["error"] = f"{type(error).__name__}: {reason}"
    finally:
        random.setstate(original_random)
    record["semantics"] = semantics.report()
    return record


def run_games(specs: Iterable[GameSpec], play_limit: int = 500) -> list[dict]:
    """Serial batch; failed games never suppress later independent matchups."""
    return [audit_game(spec, play_limit) for spec in specs]


def make_report(games: list[dict]) -> dict:
    """Aggregate selected calls, keeping team/difficulty/mode/situation separate.

    Streaks are consecutive appearances in the same comparable situation; they
    reset between games. Small samples and concentration are observational only.
    Partial failed games are retained but excluded from balance aggregates.
    """
    groups = defaultdict(list)
    longest = Counter()
    all_calls = sum(len(game["calls"]) for game in games)
    completed_calls = 0
    for game in games:
        if game["status"] != "passed":
            continue
        streaks = {}
        for call in game["calls"]:
            before = call["before"]
            key = (before["team"], before["difficulty"], before["mode"],
                   *situation_key(before["down"], before["distance"]))
            play = before["play"]
            groups[key].append(play)
            previous, count = streaks.get(key, (None, 0))
            count = count + 1 if previous == play else 1
            streaks[key] = play, count
            longest[key] = max(longest[key], count)
            completed_calls += 1
    situations, warnings = [], []
    bands = ("1-3", "4-6", "7-10", "11+")
    primary = {play.value for play in CHART_PLAY_TYPES}
    for key, plays in sorted(groups.items()):
        team, difficulty, mode, down, band = key
        counts = Counter(plays)
        total = len(plays)
        share = max(counts.values()) / total
        group = {"team": team, "difficulty": difficulty, "mode": mode,
                 "down": down, "distance_band": bands[band], "calls": total,
                 "play_counts": dict(sorted(counts.items())),
                 "primary_play_shares": {play: counts[play] / total for play in sorted(primary)},
                 "largest_share": share, "distinct_plays": len(counts),
                 "longest_streak": longest[key], "small_sample": total < 30}
        situations.append(group)
        if mode == "ordinary" and total >= 30 and share >= .5:
            warnings.append({"team": team, "difficulty": difficulty, "down": down,
                             "distance_band": bands[band], "calls": total,
                             "message": "Concentrated ordinary calls: inspect chart strengths and alternatives; not a failure or usage cap."})
    return {"schema_version": 1, "python": platform.python_version(),
            "notes": "Generated games, not historical results. Serial seeds reproduce within the same code, data, and Python environment. Small samples are not balance verdicts. No standings saved.",
            "semantic_coverage": {event: sum(game.get("semantics", {}).get("covered", {}).get(event, 0)
                                             for game in games if game["status"] == "passed")
                                  for event in SemanticAudit.EVENTS},
            "games": games, "summary": {
                "games": len(games), "passed": sum(g["status"] == "passed" for g in games),
                "failed": sum(g["status"] != "passed" for g in games), "calls": all_calls,
                "balance_calls": completed_calls, "situations": situations, "warnings": warnings,
            }}


def validate_report(report: dict, teams: list[str]) -> dict:
    """Reconcile saved checklist evidence without rerunning games or trusting totals.

    The report retains final-state and selected-call receipts, not complete box
    scores or runtime identity. Those still require the actual bound execution
    and the engine/regression controls. Concentration warnings are advisory.
    """
    errors = []
    games, calls, warnings = 0, 0, []
    try:
        if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
                or report["schema_version"] != 1):
            raise ValueError("Requires a schema-1 AI report")
        if report.get("python") != platform.python_version():
            errors.append("AI report belongs to a different Python runtime")
        if (report.get("run") != {"master_seed": 8306, "comparison": True, "schedule": "generated regular season"}
                or type(report["run"].get("master_seed")) is not int
                or report["run"].get("comparison") is not True):
            errors.append("AI evidence must use the complete seed-8306 generated schedule and balanced comparison")
        expected = generated_schedule(teams, 16, 8306)
        expected += [GameSpec(spec.away, spec.home, spec.seed, "balanced", "balanced", spec.week) for spec in expected]
        recorded = report.get("games")
        if not isinstance(recorded, list) or len(recorded) != len(expected):
            raise ValueError("AI evidence omits or adds scheduled games")
        valid_plays = {play.value for play in PlayType}
        boolean_results = {
            "first_down", "turnover", "turnover_on_downs", "touchdown", "safety", "field_goal_made",
            "penalty_applied", "pending_penalty_decision", "spike_used", "timeout_used",
        }
        for number, (game, spec) in enumerate(zip(recorded, expected), 1):
            try:
                if not isinstance(game, dict):
                    raise TypeError("Invalid game receipt")
                config = game.get("config")
                if (not isinstance(config, dict) or config != asdict(spec)
                        or any(type(config.get(key)) is not int for key in ("week", "seed"))
                        or config.get("is_playoff") is not False):
                    raise ValueError("Wrong matchup, week, seed or difficulty")
                if game.get("status") != "passed" or "error" in game:
                    raise ValueError("Failed or contradictory game receipt")
                final = game.get("final")
                if (not isinstance(final, dict) or final.get("game_over") is not True
                        or final.get("untimed_down_pending") is not False
                        or any(type(final.get(key)) is not int or final[key] < 0
                               for key in ("home_score", "away_score", "overtime_periods"))):
                    raise ValueError("Invalid final state")
                semantics = game.get("semantics")
                covered = semantics.get("covered") if isinstance(semantics, dict) else None
                if (not isinstance(covered, dict) or set(covered) != set(SemanticAudit.EVENTS)
                        or any(type(value) is not int or value < 0 for value in covered.values())
                        or semantics.get("unexercised") != [event for event in SemanticAudit.EVENTS if not covered[event]]):
                    raise ValueError("Invalid or missing semantic coverage")
                observations = game.get("calls")
                if not isinstance(observations, list) or not observations:
                    raise ValueError("Missing selected-call evidence")
                for call in observations:
                    before, result = call["before"], call["result"]
                    if (not isinstance(before, dict) or not isinstance(result, dict)
                            or type(before.get("is_home")) is not bool):
                        raise ValueError("Missing call/result identity")
                    home = before["is_home"]
                    if (before.get("team") != (spec.home if home else spec.away)
                            or before.get("difficulty") != (spec.home_difficulty if home else spec.away_difficulty)
                            or not isinstance(before.get("mode"), str) or not before["mode"]
                            or type(before.get("down")) is not int or before["down"] not in range(1, 5)
                            or type(before.get("distance")) is not int or before["distance"] < 0
                            or before.get("play") not in valid_plays or result.get("play") != before["play"]):
                        raise ValueError("Selected call has inconsistent team, situation or result")
                    if (any(type(result.get(key)) is not bool for key in boolean_results)
                            or result["pending_penalty_decision"] is not False
                            or type(result.get("yards")) is not int):
                        raise ValueError("Invalid or pending finalized result")
                    probabilities = before.get("probabilities")
                    if (not isinstance(probabilities, dict)
                            or any(key not in valid_plays or type(value) not in (int, float)
                                   or not math.isfinite(value) or not 0 <= value <= 1
                                   for key, value in probabilities.items())
                            or probabilities and (not math.isclose(sum(probabilities.values()), 1, abs_tol=1e-9)
                                                  or probabilities.get(before["play"], 0) <= 0)):
                        raise ValueError("Invalid recorded selection probabilities")
            except (ValueError, KeyError, TypeError) as error:
                errors.append(f"Game {number}: {error}")
        rebuilt = make_report(recorded)
        for field in ("summary", "semantic_coverage"):
            saved_json = json.dumps(report.get(field), sort_keys=True, allow_nan=False)
            rebuilt_json = json.dumps(rebuilt[field], sort_keys=True, allow_nan=False)
            if saved_json != rebuilt_json:
                errors.append(f"Saved {field} does not reconcile with game receipts")
        games, calls = len(recorded), rebuilt["summary"]["calls"]
        warnings = rebuilt["summary"]["warnings"]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(str(error))
    return {"passed": not errors, "errors": errors, "games": games, "calls": calls, "warnings": warnings}
