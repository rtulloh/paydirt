"""Fresh full-engine evidence for generated-chart release gates."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import multiprocessing
import random
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .auto_game import run_auto_game
from .chart_calibration import EngineCalibrationObserver, TeamCalibrationTotals
from .chart_loader import load_team_chart
from .chart_runtime_identity import loaded_runtime_identity
from .computer_ai import ComputerAI, create_computer_ai
from .play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType, ResultType

REQUIRED_METRICS = (
    "completion_rate", "interception_rate", "sack_rate",
    "yards_per_pass_attempt", "rushing_yards_per_attempt",
)
# Fixed by the owner acceptance contract before candidate tuning. League
# tolerances remain source-contract facts, independent of these team bounds.
TEAM_TOLERANCES = {
    "completion_rate": .03,
    "interception_rate": .01,
    "sack_rate": .015,
    "yards_per_pass_attempt": .75,
    "rushing_yards_per_attempt": .40,
}
_RAW_FIELDS = tuple(TeamCalibrationTotals.__dataclass_fields__)
_OFFENSE_PLAYS = (
    PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN, PlayType.DRAW,
    PlayType.SCREEN, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
    PlayType.LONG_PASS, PlayType.TE_SHORT_LONG,
)
_OFFENSE_WEIGHTS = (10, 14, 10, 10, 8, 22, 16, 6, 4)
_DEFENSE_PLAYS = (
    DefenseType.STANDARD, DefenseType.SHORT_YARDAGE, DefenseType.SPREAD,
    DefenseType.SHORT_PASS, DefenseType.LONG_PASS, DefenseType.BLITZ,
)
_DEFENSE_WEIGHTS = (22, 12, 16, 20, 14, 16)
_POLICY_WEIGHTS = {
    "chart-focused": _OFFENSE_WEIGHTS,
    "run-heavy": (25, 25, 25, 20, 1, 1, 1, 1, 1),
    "pass-heavy": (1, 1, 1, 2, 19, 19, 19, 19, 19),
    "repeat-line-plunge": (100, 0, 0, 0, 0, 0, 0, 0, 0),
    "repeat-off-tackle": (0, 100, 0, 0, 0, 0, 0, 0, 0),
    "repeat-end-run": (0, 0, 100, 0, 0, 0, 0, 0, 0),
    "repeat-draw": (0, 0, 0, 100, 0, 0, 0, 0, 0),
    "repeat-screen": (0, 0, 0, 0, 100, 0, 0, 0, 0),
    "repeat-short-pass": (0, 0, 0, 0, 0, 100, 0, 0, 0),
    "repeat-medium-pass": (0, 0, 0, 0, 0, 0, 100, 0, 0),
    "repeat-long-pass": (0, 0, 0, 0, 0, 0, 0, 100, 0),
    "repeat-te-short-long": (0, 0, 0, 0, 0, 0, 0, 0, 100),
}
_POLICIES = {*_POLICY_WEIGHTS, "hard", "balanced"}


def supported_audit_policies() -> tuple[str, ...]:
    """Return the policies supported by both collection and validation."""
    return tuple(sorted(_POLICIES))


def _fingerprint(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def engine_fingerprint() -> str:
    """Bind evidence to runtime sources and this measurement policy."""
    root = Path(__file__).parent
    return _fingerprint(root, sorted(p for p in root.glob("*.py") if (
        not any(word in p.stem for word in ("audit", "gate")) or p.name == Path(__file__).name
    )))


def chart_fingerprint(season_dir: Path) -> str:
    """Bind evidence to candidate charts, metadata and rules."""
    files = sorted(p for p in season_dir.rglob("*") if p.is_file() and (
        p.suffix in {".csv", ".yaml"} or p.name in {"roster.json", "generation-manifest.json"}
    ))
    return _fingerprint(season_dir, files)


def _schedule_hash(schedule: list[tuple[str, str]]) -> str:
    return hashlib.sha256(json.dumps(schedule, separators=(",", ":")).encode()).hexdigest()


class ChartFocusedAI(ComputerAI):
    """Fix normal call mix while retaining legal clock/endgame choices."""

    normal_weights = _OFFENSE_WEIGHTS

    def select_offense_with_clock_management(self, game: Any) -> tuple:
        decision = super().select_offense_with_clock_management(game)
        if self.last_mode is not None or decision[0] not in CHART_PLAY_TYPES:
            return decision
        if self._offense_rng is None:
            self._offense_rng = random.Random(f"chart-audit-offense:{random.getstate()!r}")
        selected = self._offense_rng.choices(_OFFENSE_PLAYS, weights=self.normal_weights, k=1)[0]
        return (selected, *decision[1:])

    def select_defense(self, game: Any) -> DefenseType:
        if self._defense_rng is None:
            self._defense_rng = random.Random(f"chart-audit-defense:{random.getstate()!r}")
        return self._defense_rng.choices(_DEFENSE_PLAYS, weights=_DEFENSE_WEIGHTS, k=1)[0]


def _factory(
    policy: str, *, attempt_end_zone_interception_returns: bool = False,
) -> Callable[[Any, bool], ComputerAI]:
    if not isinstance(attempt_end_zone_interception_returns, bool):
        raise ValueError("End-zone interception return audit option must be boolean")  # noqa: TRY004 - invalid argument value

    def create(game: Any, is_home: bool) -> ComputerAI:
        game.set_end_zone_interception_return(is_home, attempt_end_zone_interception_returns)
        if policy == "hard":
            return create_computer_ai("hard", game, is_home)
        if policy == "balanced":
            # Match the legacy default, including its lack of team analysis.
            return ComputerAI(aggression=.5, ai_behavior=game.season_rules.ai_behavior)
        ai = ChartFocusedAI(aggression=0.5, use_analysis=False,
                            ai_behavior=game.season_rules.ai_behavior)
        ai.normal_weights = _POLICY_WEIGHTS[policy]
        ai.set_team(game.state.home_chart if is_home else game.state.away_chart)
        return ai

    return create


def _count_errors(values: dict[str, Any]) -> list[str]:
    errors = []
    if values["offensive_plays"] != values["pass_attempts"] + values["rushing_attempts"] + values["sacks"]:
        errors.append("inconsistent play denominator")
    if values["completions"] + values["interceptions"] > values["pass_attempts"]:
        errors.append("impossible completion/interception denominator")
    if values["total_yards"] != values["rushing_yards"] + values["passing_yards"] - values["sack_yards"]:
        errors.append("inconsistent net yardage")
    if values["turnovers"] != values["interceptions"] + values["fumbles_lost"]:
        errors.append("inconsistent turnover count")
    return errors


def _game_receipt(game: Any, report: dict, away: str, home: str, seed: int) -> dict:
    state = game.state
    errors = []
    if not state.game_over or game.has_untimed_down():
        errors.append("incomplete or pending untimed down")
    periods = game.get_period_scores()
    for side in ("home", "away"):
        score = getattr(state, f"{side}_score")
        if sum(period[side] for period in periods) != score:
            errors.append(f"{side} period scores differ from final")
        if sum(play.points for play in state.scoring_plays
               if play.is_home_team == (side == "home")) != score:
            errors.append(f"{side} scoring log differs from final")
    for name, values in report["teams"].items():
        errors.extend(f"{name}: {reason}" for reason in _count_errors(values))
    if errors:
        raise RuntimeError(f"Invalid engine game: {away} at {home}, seed {seed}: {errors}")
    return {"away": away, "home": home, "seed": seed, "game_over": state.game_over,
            "untimed_down": game.has_untimed_down(), "home_score": state.home_score,
            "away_score": state.away_score, "teams": report["teams"],
            "home_end_zone_interception_return": game.home_end_zone_interception_return,
            "away_end_zone_interception_return": game.away_end_zone_interception_return}


def _run_season(task: tuple[str, list[tuple[str, str]], int, str, bool]) -> dict[str, Any]:
    directory, schedule, seed, policy, attempt_end_zone_interception_returns = task
    runtime = loaded_runtime_identity()
    before_engine = engine_fingerprint()
    team_totals: dict[str, TeamCalibrationTotals] = {}
    receipts = []
    original_random_state = random.getstate()
    try:
        for index, (away, home) in enumerate(schedule):
            game_seed = seed + index * 1009
            random.seed(game_seed)
            observer = EngineCalibrationObserver()
            selected: list[tuple] = []
            decisions: list[dict] = []

            def decision(game: Any, ai: Any, play: PlayType, defense: DefenseType,
                         observer: EngineCalibrationObserver = observer, selected: list = selected) -> None:
                observer.on_decision(game, ai, play, defense)
                state = game.state
                team = (state.home_chart if state.is_home_possession else state.away_chart).peripheral.short_name
                distance = "short" if state.yards_to_go <= 3 else "medium" if state.yards_to_go <= 7 else "long"
                key = (team, play.name, defense.name, state.down, distance, str(ai.last_mode or "normal"))
                selected[:] = [key]

            def result(game: Any, outcome: Any, observer: EngineCalibrationObserver = observer,
                       selected: list = selected, decisions: list = decisions) -> None:
                observer.on_result(game, outcome)
                retained = not (outcome.penalty_applied or outcome.result.replay_down
                                or (outcome.penalty_choice is not None and outcome.penalty_choice.offsetting))
                decisions.append({"situation": list(selected[0]),
                                  "result": outcome.result.result_type.name,
                                  "yards": outcome.yards_gained, "retained": retained,
                                  "initial_yards": outcome.result.yards,
                                  "qb_time": outcome.result.qb_scramble_dice > 0,
                                  "punt_snap_fumble": outcome.result.punt_snap_fumble,
                                  "field_goal_snap_fumble": outcome.result.field_goal_snap_fumble,
                                  "field_goal_made": bool(outcome.field_goal_made)})
                selected.clear()

            with contextlib.redirect_stdout(io.StringIO()):
                game = run_auto_game(
                    str(Path(directory) / away), str(Path(directory) / home),
                    ai_factory=_factory(policy, attempt_end_zone_interception_returns=attempt_end_zone_interception_returns),
                    on_decision=decision,
                    on_result=result, play_limit=750,
                )
            if game is None:
                raise RuntimeError(f"Missing engine game: {away} at {home}, seed {game_seed}")
            observer.finalize_game(game)
            report = observer.report()
            receipt = _game_receipt(game, report, away, home, game_seed)
            if any(receipt[f"{side}_end_zone_interception_return"] is not attempt_end_zone_interception_returns
                   for side in ("home", "away")):
                raise RuntimeError("Engine interception return policy differs from declared audit option")
            receipt["decision_results"] = decisions
            receipts.append(receipt)
            for name, values in report["teams"].items():
                total = team_totals.setdefault(name, TeamCalibrationTotals())
                for field in _RAW_FIELDS:
                    setattr(total, field, getattr(total, field) + values[field])
    finally:
        random.setstate(original_random_state)
    if runtime != loaded_runtime_identity() or before_engine != engine_fingerprint():
        raise RuntimeError("Engine or loaded runtime changed during worker execution")
    league = TeamCalibrationTotals(**{
        field: sum(getattr(team, field) for team in team_totals.values()) for field in _RAW_FIELDS
    }).to_dict()
    league["games"] = len(receipts)
    return {"league": league, "teams": {name: total.to_dict() for name, total in team_totals.items()},
            "game_receipts": receipts,
            "runtime_identity": runtime, "engine_fingerprint": before_engine,
            "attempt_end_zone_interception_returns": attempt_end_zone_interception_returns}


def _sampling_uncertainty(reports: list[dict]) -> dict:
    evidence = {}
    for label in ["league", *sorted(reports[0]["teams"])]:
        evidence[label] = {}
        for metric in REQUIRED_METRICS:
            values = [(report["league"] if label == "league" else report["teams"][label])[metric]
                      for report in reports]
            evidence[label][metric] = {
                "replications": len(values), "minimum": min(values), "maximum": max(values),
                "between_repetition_standard_error": (statistics.stdev(values) / math.sqrt(len(values))
                                                        if len(values) > 1 else None),
            }
    return evidence


def run_engine_audit(
    season_dir: Path, schedule: list[tuple[str, str]], *, repetitions: int,
    seed: int, policy: str = "chart-focused", workers: int = 1,
    attempt_end_zone_interception_returns: bool = False,
) -> dict[str, Any]:
    """Play independent deterministic repetitions of the supplied source schedule."""
    season_dir = Path(season_dir).resolve()
    if repetitions < 1 or workers < 1 or not schedule:
        raise ValueError("Positive repetitions/workers and a nonempty schedule are required")
    if policy not in _POLICIES:
        raise ValueError(f"Unsupported measurement policy: {policy}")
    if not isinstance(attempt_end_zone_interception_returns, bool):
        raise ValueError("End-zone interception return audit option must be boolean")  # noqa: TRY004 - invalid argument value
    for away, home in schedule:
        for team in (away, home):
            if not team or team in {".", ".."} or Path(team).name != team or "\\" in team:
                raise ValueError(f"Invalid team directory: {team!r}")
            if not (season_dir / team / "offense.csv").is_file():
                raise ValueError(f"Missing team charts: {team}")
        if away == home:
            raise ValueError("A team cannot play itself")
    runtime = loaded_runtime_identity()
    before_engine, before_charts = engine_fingerprint(), chart_fingerprint(season_dir)
    tasks = [(str(season_dir), schedule, seed + i * 1_000_003, policy, attempt_end_zone_interception_returns)
             for i in range(repetitions)]
    if workers == 1:
        reports = [_run_season(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            reports = list(pool.map(_run_season, tasks))
    if (runtime != loaded_runtime_identity()
            or any(report["runtime_identity"] != runtime or report["engine_fingerprint"] != before_engine
                   or report["attempt_end_zone_interception_returns"] is not attempt_end_zone_interception_returns
                   for report in reports)):
        raise RuntimeError("Worker loaded runtime differs from declared execution")
    if before_engine != engine_fingerprint() or before_charts != chart_fingerprint(season_dir):
        raise RuntimeError("Engine or chart inputs changed during audit")
    teams: dict[str, TeamCalibrationTotals] = {}
    for report in reports:
        for name, values in report["teams"].items():
            totals = teams.setdefault(name, TeamCalibrationTotals())
            for field in _RAW_FIELDS:
                setattr(totals, field, getattr(totals, field) + values[field])
    league = TeamCalibrationTotals(**{
        field: sum(getattr(team, field) for team in teams.values()) for field in _RAW_FIELDS
    }).to_dict()
    league["games"] = sum(report["league"]["games"] for report in reports)
    receipts = [receipt for report in reports for receipt in report["game_receipts"]]
    return {
        "league": league, "teams": {name: t.to_dict() for name, t in sorted(teams.items())},
        "game_receipts": receipts,
        "replications": [{"league": report["league"], "teams": report["teams"]} for report in reports],
        "uncertainty": _sampling_uncertainty(reports),
        **_decision_evidence(receipts),
        "metadata": {
            "policy": policy, "repetitions": repetitions, "seed": seed,
            "attempt_end_zone_interception_returns": attempt_end_zone_interception_returns,
            "seed_derivation": "master + repetition_index * 1000003 + game_index * 1009",
            "normal_offense_weights": _POLICY_WEIGHTS.get(policy),
            "normal_defense_weights": _DEFENSE_WEIGHTS if policy in _POLICY_WEIGHTS else None,
            "decision_schema": "team/play/defense/down/distance_band/mode-v1",
            "distance_bands": {"short": "1-3", "medium": "4-7", "long": "8+"},
            "schedule_hash": _schedule_hash(schedule),
            "engine_fingerprint": before_engine, "chart_fingerprint": before_charts,
            "runtime_identity": runtime,
            "worker_runtime_identities": [report["runtime_identity"] for report in reports],
            "team_names": {folder: load_team_chart(season_dir / folder).peripheral.short_name
                           for folder in sorted({team for pair in schedule for team in pair})},
        },
    }


def _decision_evidence(receipts: list[dict]) -> dict:
    """Reconstruct counts and comparable-situation repetition from ordered calls.

    Offensive repetition compares a team's down/distance/mode across its next
    appearance in that context, regardless of the selected defense. It resets
    between games. Defense remains explicit in the full call/outcome inventory.
    """
    calls, outcomes, longest = Counter(), Counter(), Counter()
    groups: dict[tuple, Counter] = defaultdict(Counter)
    for receipt in receipts:
        streaks = {}
        for call in receipt["decision_results"]:
            situation = tuple(call["situation"])
            team, play, _defense, down, distance, mode = situation
            calls[situation] += 1
            outcomes[(*situation, call["result"], call["yards"], call["retained"])] += 1
            key = (team, down, distance, mode)
            groups[key][play] += 1
            previous, count = streaks.get(key, (None, 0))
            count = count + 1 if previous == play else 1
            streaks[key] = play, count
            longest[key] = max(longest[key], count)
    situations = []
    for key, counts in sorted(groups.items()):
        total = counts.total()
        situations.append({
            "situation": list(key), "calls": total, "play_counts": dict(sorted(counts.items())),
            "play_shares": {play: count / total for play, count in sorted(counts.items())},
            "distinct_plays": len(counts), "largest_share": max(counts.values()) / total,
            "longest_streak": longest[key], "small_sample": total < 30,
        })
    return {
        "call_mix": [{"situation": list(key), "count": count} for key, count in sorted(calls.items())],
        "outcome_distributions": [{"situation": list(key), "count": count}
                                  for key, count in sorted(outcomes.items())],
        "comparable_situations": situations,
    }


def _decision_errors(receipt: dict, teams: set[str]) -> list[str]:
    """Validate typed selected-call receipts before reconstructing evidence."""
    decisions = receipt.get("decision_results")
    if not isinstance(decisions, list) or not decisions:
        return ["Missing ordered decision results"]
    errors = []
    for index, call in enumerate(decisions):
        try:
            team, play, defense, down, distance, mode = call["situation"]
            valid = (team in teams and play in PlayType.__members__ and defense in DefenseType.__members__
                     and type(down) is int and down in (1, 2, 3, 4)
                     and distance in {"short", "medium", "long"} and isinstance(mode, str) and bool(mode)
                     and call["result"] in ResultType.__members__ and type(call["yards"]) is int
                     and type(call["retained"]) is bool and type(call["initial_yards"]) is int
                     and type(call["qb_time"]) is bool and type(call["field_goal_made"]) is bool
                     and type(call["punt_snap_fumble"]) is bool
                     and type(call.get("field_goal_snap_fumble", False)) is bool
                     and (not call.get("field_goal_snap_fumble", False)
                          or (play == "FIELD_GOAL" and call["result"] == "FUMBLE"))
                     and (not call["punt_snap_fumble"] or (play == "PUNT" and call["result"] == "FUMBLE")))
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            errors.append(f"Invalid ordered decision: {index}")
    return errors


def _decision_count_errors(receipt: dict) -> list[str]:
    """Reconcile selected-call denominators against the finalized game receipt."""
    fields = ("offensive_plays", "rushing_attempts", "pass_attempts", "completions",
              "sacks", "field_goal_attempts", "field_goals_made")
    totals = {team: Counter(dict.fromkeys(fields, 0)) for team in receipt["teams"]}
    passes = {"SCREEN", "SHORT_PASS", "MEDIUM_PASS", "LONG_PASS", "TE_SHORT_LONG", "HAIL_MARY"}
    for call in receipt["decision_results"]:
        if not call["retained"]:
            continue
        team, play, *_ = call["situation"]
        count = totals[team]
        snap = call.get("field_goal_snap_fumble", False)
        if play == "FIELD_GOAL" and not snap:
            count["field_goal_attempts"] += 1
            count["field_goals_made"] += int(call["field_goal_made"])
        elif play not in {"PUNT", "KICKOFF"} or call["punt_snap_fumble"] or snap:
            count["offensive_plays"] += 1
            if play not in passes:
                count["rushing_attempts"] += 1
            else:
                result = call["result"]
                qt_fumble = result == "FUMBLE" and call["qb_time"]
                if (result == "SACK" or (result == "QB_SCRAMBLE" and call["yards"] < 0)
                        or (qt_fumble and call["initial_yards"] <= 0)):
                    count["sacks"] += 1
                elif result == "QB_SCRAMBLE" or qt_fumble:
                    count["rushing_attempts"] += 1
                else:
                    count["pass_attempts"] += 1
                    count["completions"] += int(result not in {"INCOMPLETE", "INTERCEPTION"})
    return [f"{team}: call totals differ from game receipt: {field}"
            for team, count in totals.items() for field in fields if count[field] != receipt["teams"][team][field]]


def validate_engine_report(
    report: dict[str, Any], contract: dict[str, Any], season_dir: Path, *,
    minimum_team_games: int = 1000, minimum_repetitions: int = 1, require_fit: bool = True,
) -> dict[str, Any]:
    """Reject stale/incomplete evidence and misses against predeclared tolerances."""
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    team_metrics: dict[str, Any] = {}
    maximum_team_errors = dict.fromkeys(REQUIRED_METRICS, 0.0)
    try:
        metadata = report["metadata"]
        runtime = loaded_runtime_identity()
        if (metadata.get("runtime_identity") != runtime
                or metadata.get("worker_runtime_identities") != [runtime] * metadata.get("repetitions", 0)):
            errors.append("Invalid loaded runtime identity")
        for key, actual in (("engine_fingerprint", engine_fingerprint()),
                            ("chart_fingerprint", chart_fingerprint(Path(season_dir)))):
            if metadata.get(key) != actual:
                errors.append(f"Stale {key}")
        if metadata.get("policy") not in _POLICIES:
            errors.append("Unknown measurement policy")
        attempt_returns = metadata.get("attempt_end_zone_interception_returns")
        if not isinstance(attempt_returns, bool):
            errors.append("Missing or invalid declared interception return policy")
        policy = metadata.get("policy")
        expected_offense = _POLICY_WEIGHTS.get(policy)
        expected_defense = _DEFENSE_WEIGHTS if policy in _POLICY_WEIGHTS else None
        for key, expected in (("normal_offense_weights", expected_offense),
                              ("normal_defense_weights", expected_defense)):
            actual = metadata.get(key)
            if key not in metadata or (list(actual) if isinstance(actual, (tuple, list)) else actual) != (
                list(expected) if expected is not None else None
            ):
                errors.append(f"Invalid declared policy: {key}")
        if (metadata.get("decision_schema") != "team/play/defense/down/distance_band/mode-v1"
                or metadata.get("distance_bands") != {"short": "1-3", "medium": "4-7", "long": "8+"}):
            errors.append("Invalid decision situation schema")
        if require_fit and metadata.get("policy") != "chart-focused":
            errors.append("Accuracy gate requires the declared chart-focused policy")
        schedule = [(p["away"], p["home"]) if isinstance(p, dict) else tuple(p)
                    for p in contract["schedule"]]
        if metadata.get("schedule_hash") != _schedule_hash(schedule):
            errors.append("Evidence schedule differs from source schedule")
        appearances = Counter(team for pair in schedule for team in pair)
        names = metadata["team_names"]
        if set(names) != set(appearances) or set(report["teams"]) != set(names.values()):
            errors.append("Evidence teams differ from source schedule")
        if len(names) != len(set(names.values())):
            errors.append("Duplicate engine team identifiers")
        if "teams" in contract and set(contract["teams"]) != set(names):
            errors.append("Incomplete team target inventory")
        repetitions = metadata["repetitions"]
        if not isinstance(repetitions, int) or repetitions < 1:
            errors.append("Invalid repetition sample")
        elif repetitions < minimum_repetitions:
            errors.append(f"Insufficient independent schedules ({repetitions} < {minimum_repetitions})")
        if report["league"]["games"] != len(schedule) * repetitions:
            errors.append("Incomplete scheduled game sample")
        for folder, short_name in names.items():
            count = report["teams"].get(short_name, {}).get("team_games", 0)
            if count != appearances[folder] * repetitions or count < minimum_team_games:
                errors.append(f"{folder}: incomplete team-game sample ({count})")
        receipts = report.get("game_receipts", [])
        if len(receipts) != len(schedule) * repetitions:
            errors.append("Incomplete individual game receipts")
        receipt_totals = {name: dict.fromkeys(_RAW_FIELDS, 0) for name in names.values()}
        reconstructed_replications = []
        repetition_totals: dict[str, TeamCalibrationTotals] = {}
        for index, receipt in enumerate(receipts):
            expected_pair = schedule[index % len(schedule)]
            expected_seed = metadata["seed"] + (index // len(schedule)) * 1_000_003 + (index % len(schedule)) * 1009
            if ((receipt.get("away"), receipt.get("home")) != expected_pair
                    or receipt.get("seed") != expected_seed
                    or receipt.get("game_over") is not True or receipt.get("untimed_down") is not False):
                errors.append(f"Invalid individual game receipt: {index}")
            if any(type(receipt.get(f"{side}_end_zone_interception_return")) is not bool
                   or receipt[f"{side}_end_zone_interception_return"] is not attempt_returns
                   for side in ("home", "away")):
                errors.append(f"Invalid individual game interception return policy: {index}")
            expected_names = {names[folder] for folder in expected_pair}
            decision_errors = _decision_errors(receipt, expected_names)
            errors.extend(f"game {index}: {reason}" for reason in decision_errors)
            if not decision_errors:
                errors.extend(f"game {index}: {reason}" for reason in _decision_count_errors(receipt))
            if set(receipt.get("teams", {})) != expected_names:
                errors.append(f"Invalid individual game teams: {index}")
            for side, folder in zip(("away", "home"), expected_pair):
                score = receipt[f"{side}_score"]
                if (type(score) is not int or score < 0
                        or score != receipt["teams"][names[folder]]["points"]):
                    errors.append(f"Invalid individual game score: {index} {side}")
            for name, values in receipt.get("teams", {}).items():
                errors.extend(f"game {index} {name}: {reason}" for reason in _count_errors(values))
                repetition_total = repetition_totals.setdefault(name, TeamCalibrationTotals())
                for field in _RAW_FIELDS:
                    receipt_totals[name][field] += values[field]
                    setattr(repetition_total, field, getattr(repetition_total, field) + values[field])
            if (index + 1) % len(schedule) == 0:
                league_total = TeamCalibrationTotals(**{
                    field: sum(getattr(total, field) for total in repetition_totals.values())
                    for field in _RAW_FIELDS
                }).to_dict()
                league_total["games"] = len(schedule)
                reconstructed_replications.append({
                    "league": league_total,
                    "teams": {name: total.to_dict() for name, total in repetition_totals.items()},
                })
                repetition_totals = {}
        if not any("decision" in error.lower() for error in errors):
            for key, expected in _decision_evidence(receipts).items():
                if report.get(key) != expected:
                    errors.append(f"Unreconciled call/decision evidence: {key}")
        if report.get("replications") != reconstructed_replications:
            errors.append("Unreconciled independent replication evidence")
        if (not reconstructed_replications
                or report.get("uncertainty") != _sampling_uncertainty(reconstructed_replications)):
            errors.append("Unreconciled sampling uncertainty evidence")
        for name, totals in receipt_totals.items():
            if any(totals[field] != report["teams"][name][field] for field in _RAW_FIELDS):
                errors.append(f"{name}: individual game totals differ from aggregate")
        for field in _RAW_FIELDS:
            observed = report["league"][field]
            expected = sum(team[field] for team in report["teams"].values())
            if not isinstance(observed, int) or observed < 0 or observed != expected:
                errors.append(f"Unreconciled league total: {field}")
        for label, values in [("league", report["league"]), *report["teams"].items()]:
            counts = [value for field, value in values.items()
                      if field in _RAW_FIELDS and not field.endswith("yards")]
            if any(type(value) is not int or value < 0 for value in counts):
                errors.append(f"{label}: invalid count denominator")
            if values["offensive_plays"] != (values["pass_attempts"]
                                              + values["rushing_attempts"] + values["sacks"]):
                errors.append(f"{label}: inconsistent play denominator")
            if values["completions"] + values["interceptions"] > values["pass_attempts"]:
                errors.append(f"{label}: impossible completion/interception denominator")
            derived = TeamCalibrationTotals(**{
                field: values[field] for field in _RAW_FIELDS
            }).to_dict()
            derived_names = (*REQUIRED_METRICS, *(key for key in derived
                              if key not in _RAW_FIELDS and key not in REQUIRED_METRICS))
            for name in derived_names:
                actual = values[name]
                if (isinstance(actual, bool) or not isinstance(actual, (int, float))
                        or not math.isfinite(actual) or not math.isclose(
                            actual, derived[name], rel_tol=1e-12, abs_tol=1e-12)):
                    errors.append(f"{label}: unreconciled derived metric: {name}")
        for folder, short_name in names.items():
            if not require_fit or "teams" not in contract:
                continue  # Small standalone diagnostics may declare league targets only.
            values = report["teams"][short_name]
            team_metrics[folder] = {}
            for name, tolerance in TEAM_TOLERANCES.items():
                target = float(contract["teams"][folder]["rates"][name])
                actual = values[name]
                difference = abs(actual - target)
                passed = math.isfinite(target) and math.isfinite(actual) and difference <= tolerance
                maximum_team_errors[name] = max(maximum_team_errors[name], difference)
                team_metrics[folder][name] = {
                    "observed": actual, "target": target, "absolute_error": difference,
                    "tolerance": tolerance, "passed": passed,
                }
                if not passed:
                    errors.append(f"{folder} {name}: {actual:.6f} differs from {target:.6f} "
                                  f"by more than {tolerance}")
        recalculated = TeamCalibrationTotals(**{
            field: report["league"][field] for field in _RAW_FIELDS
        }).to_dict()
        for name in REQUIRED_METRICS if require_fit else ():
            target = contract["targets"][name]
            actual = report["league"][name]
            value, tolerance = float(target["value"]), float(target["tolerance"])
            if not all(math.isfinite(v) for v in (actual, value, tolerance)) or tolerance <= 0:
                errors.append(f"Invalid metric/target: {name}")
                continue
            if not math.isclose(actual, recalculated[name], rel_tol=1e-12, abs_tol=1e-12):
                errors.append(f"Unreconciled derived metric: {name}")
            passed = abs(actual - value) <= tolerance
            metrics[name] = {"observed": actual, "target": value,
                             "tolerance": tolerance, "passed": passed}
            if not passed:
                errors.append(f"{name}: {actual:.6f} differs from {value:.6f} by more than {tolerance}")
    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
        errors.append(f"Invalid or incomplete engine evidence: {error}")
    return {"passed": not errors, "errors": errors, "metrics": metrics,
            "team_metrics": team_metrics, "maximum_team_errors": maximum_team_errors,
            "fit_required": require_fit}


def audit_observer_conformance() -> dict[str, Any]:
    """Cross-check measurement denominators against controlled real-engine events."""
    from dataclasses import replace
    from unittest.mock import patch

    from . import play_resolver
    from .chart_loader import DefenseChart
    from .chart_tactics_audit import controlled_offense
    from .game_engine import PaydirtGameEngine

    errors, checks = [], []
    cases = (
        ("QT", "0", (0, 0, 1, 0)),
        ("QT", "SACK 0", (0, 0, 0, 1)),
        ("QT", "F - 5", (0, 0, 0, 1)),
        ("QT", "F", (0, 0, 0, 1)),
        ("QT", "F + 5", (0, 0, 1, 0)),
        ("F + 5", "0", (1, 1, 0, 0)),
    )
    for primary, secondary, expected in cases:
        offense = controlled_offense(primary)
        offense.offense.qb_time = dict.fromkeys(range(10, 40), secondary)
        defense = DefenseChart({(formation, row): dict.fromkeys(range(1, 10), "0")
                                for formation in "ABCDEF" for row in range(1, 6)})
        defender = replace(offense, defense=defense,
                           peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position = 40
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
        with patch.object(play_resolver, "roll_chart_dice", lambda: (10, "observer control")), \
             patch.object(play_resolver, "roll_defense_dice", lambda: (1, 0, 1)):
            outcome = engine.run_play_with_penalty_procedure(PlayType.SHORT_PASS,
                                                           DefenseType.STANDARD)
        observer.on_result(engine, outcome)
        # One controlled event, not a claimed full game. Finalization only copies
        # the engine's authoritative box totals into the measurement record.
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = tuple(values[name] for name in
                       ("pass_attempts", "completions", "rushing_attempts", "sacks"))
        label = f"{primary}/{secondary}"
        checks.append({"case": label, "observed": actual, "expected": expected})
        if actual != expected or engine.state.home_stats.sacks != expected[3]:
            errors.append(f"observer {label}: pass/completion/rush/sack counts {actual}, expected {expected}")
    for made in (True, False):
        offense = controlled_offense("0")
        offense.special_teams.field_goal = dict.fromkeys(range(10, 40), "99" if made else "0")
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down = 80, 4
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.FIELD_GOAL, DefenseType.STANDARD)
        with patch.object(play_resolver, "roll_chart_dice", lambda: (10, "observer FG")):
            outcome = engine.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = (values["field_goal_attempts"], values["field_goals_made"])
        expected = (1, int(made))
        checks.append({"case": "FG/made" if made else "FG/missed", "observed": actual, "expected": expected})
        if actual != expected or outcome.field_goal_made != made:
            errors.append(f"observer field goal: {actual}, expected {expected}")
    for cell, snap_fumble in (("F - 10", True), ("40*", False)):
        offense = controlled_offense("0")
        offense.special_teams.punt = dict.fromkeys(range(10, 40), cell)
        offense.peripheral.fumble_recovered_range = (10, 31)
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 4, 5
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
        with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "punt"), (35, "recovery")]):
            outcome = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = tuple(values[name] for name in ("offensive_plays", "rushing_attempts", "sacks", "fumbles_lost"))
        expected = (1, 1, 0, 1) if snap_fumble else (0, 0, 0, 0)
        label = f"PUNT/{cell}"
        checks.append({"case": label, "observed": actual, "expected": expected})
        if (actual != expected or outcome.result.punt_snap_fumble != snap_fumble
                or engine.state.ball_position != (70 if snap_fumble else 20)
                or engine.state.is_home_possession or outcome.result.punt_return_dice
                or (snap_fumble and outcome.result.fumble_recovery_roll != 35)):
            errors.append(f"observer {label}: expected snap recovery/position and counts {expected}, got {actual}")
    for foul in ("OFF 5", "DEF 5"):
        for accept in (False, True):
            offense = controlled_offense("0")
            offense.special_teams.punt = {**dict.fromkeys(range(10, 40), "40*"), 10: foul, 11: "F - 10"}
            offense.peripheral.fumble_recovered_range = (10, 31)
            defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
            engine = PaydirtGameEngine(offense, defender)
            engine.state.is_home_possession = True
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 2, 8
            observer = EngineCalibrationObserver()
            observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
            dice = iter((10, 11, 35))
            label = f"PUNT/{foul}->F - 10/{'accept' if accept else 'decline'}"
            with patch("paydirt.game_engine.roll_chart_dice", side_effect=lambda dice=dice: (next(dice, 35), "punt foul")):
                pending = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
                if (not pending.pending_penalty_decision or not pending.result.punt_snap_fumble
                        or pending.result.fumble_recovery_roll or pending.result.turnover or engine.play_log
                        or engine.state.ball_position != 40 or not engine.state.is_home_possession):
                    checks.append({"case": label, "observed": False, "expected": True})
                    errors.append(f"observer {label}: missing or prematurely applied snap-fumble choice")
                    continue
                outcome = engine.apply_punt_penalty_decision(pending, accept_penalty=accept)
            observer.on_result(engine, outcome)
            observer.finalize_game(engine)
            values = observer.report()["teams"]["SYN"]
            actual = tuple(values[name] for name in ("offensive_plays", "rushing_attempts", "fumbles_lost"))
            expected = (0, 0, 0) if accept else (1, 1, 1)
            position = (35 if foul.startswith("OFF") else 45) if accept else 70
            checks.append({"case": label, "observed": actual, "expected": expected})
            if (actual != expected or engine.state.ball_position != position
                    or engine.state.is_home_possession != accept or outcome.pending_penalty_decision
                    or (accept and outcome.result.punt_snap_fumble)
                    or (not accept and outcome.result.fumble_recovery_roll != 35)):
                errors.append(f"observer {label}: wrong retained/erased fumble or counts {actual}, expected {expected}")
    for play in (PlayType.LINE_PLUNGE, PlayType.PUNT):
        for foul in ("DEF 5X", "DEF 15"):
            offense = controlled_offense("F - 10")
            offense.special_teams.punt = dict.fromkeys(range(10, 40), "F - 10")
            offense.special_teams.interception_return = {11: foul, 12: "0"}
            offense.peripheral.fumble_recovered_range = (10, 31)
            defense = DefenseChart({(formation, row): dict.fromkeys(range(1, 10), "0")
                                    for formation in "ABCDEF" for row in range(1, 6)})
            defender = replace(offense, defense=defense,
                               peripheral=replace(offense.peripheral, short_name="DEF"))
            engine = PaydirtGameEngine(offense, defender)
            engine.state.is_home_possession = True
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 4, 8
            observer = EngineCalibrationObserver()
            observer.on_decision(engine, None, play, DefenseType.STANDARD)
            resolver_dice = iter((10, 17))
            engine_dice = iter((10, 17, 11, 12) if play == PlayType.PUNT else (11, 12))
            with (patch.object(play_resolver, "roll_chart_dice",
                               side_effect=lambda dice=resolver_dice: (next(dice), "own recovery")),
                  patch.object(play_resolver, "roll_defense_dice", lambda: (1, 0, 1)),
                  patch("paydirt.game_engine.roll_chart_dice",
                        side_effect=lambda dice=engine_dice: (next(dice), "return penalty"))):
                outcome = engine.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
            observer.on_result(engine, outcome)
            observer.finalize_game(engine)
            values = observer.report()["teams"]["SYN"]
            actual = (values["offensive_plays"], values["rushing_attempts"],
                      engine.state.home_stats.first_downs, engine.state.down, engine.state.yards_to_go,
                      engine.state.ball_position, engine.state.is_home_possession,
                      outcome.first_down, outcome.turnover)
            expected = (1, 1, 1, 1, 10, 45 if foul == "DEF 15" else 35, True, True, False)
            label = f"{play.name}/{foul}/own-fumble-first-down"
            checks.append({"case": label, "observed": actual, "expected": expected})
            if actual != expected:
                errors.append(f"observer {label}: state/counts {actual}, expected {expected}")
    for kick_foul, label in (
        ("OFF 5", "PUNT/same-team-fouls/one-assessment"),
        ("DEF 5", "PUNT/opposite-team-fouls/offset-clock"),
        ("40", "PUNT/return-offset/next-call-preserved"),
    ):
        offense = controlled_offense("0")
        offense.special_teams.punt = {10: kick_foul, 11: "40"}
        offense.special_teams.punt_return = ({12: "OFF 10", 13: "DEF 15"} if kick_foul == "40"
                                            else {12: "DEF 15X", 13: "0"})
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 4, 8
        engine.state.quarter, engine.state.time_remaining = 2, 3 / 60
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
        dice = iter((10, 12, 13) if kick_foul == "40" else (10, 11, 12, 13))
        with (patch("paydirt.game_engine.roll_chart_dice", side_effect=lambda dice=dice: (next(dice), "punt fouls")),
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            outcome = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
            pending = outcome.pending_penalty_decision
            if pending:
                outcome = engine.apply_punt_penalty_decision(outcome, accept_penalty=False)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        same_team = kick_foul == "OFF 5"
        actual = (
            pending, outcome.result.replay_down, engine.state.is_home_possession,
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go,
            engine.state.home_stats.penalties, engine.state.home_stats.penalty_yards,
            engine.state.away_stats.penalties, values["offensive_plays"], values["rushing_attempts"],
            engine.state.quarter, engine.state.time_remaining, engine.has_untimed_down(),
            len(engine.play_log),
        )
        expected = ((True, False, False, 35, 1, 10, 1, 15, 0, 0, 0, 2, 0, True, 1)
                    if same_team else (False, True, True, 40, 4, 8, 0, 0, 0, 0, 0, 2, 0, True, 1))
        checks.append({"case": label, "observed": actual, "expected": expected})
        if actual != expected:
            errors.append(f"observer {label}: state/counts {actual}, expected {expected}")
    for kick, returned_foul, position, distance, recovery, label in (
        ("OFF 5", "OFF 15", 36, "37", 35, "PUNT/five-fifteen/receiver-catch"),
        ("OFF 15", "OFF 5", 10, "10", 20, "PUNT/five-fifteen/kicker-catch"),
    ):
        offense = controlled_offense("0")
        offense.special_teams.punt = {10: kick, 11: distance}
        offense.special_teams.punt_return = {12: returned_foul, 13: "F + 3"}
        offense.peripheral.fumble_recovered_range = (10, 31)
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = position, 4, 8
        engine.state.quarter, engine.state.time_remaining = 2, 3 / 60
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
        dice = iter((10, 11, 12, 13, recovery))
        with (patch("paydirt.game_engine.roll_chart_dice", side_effect=lambda dice=dice: (next(dice), "five-fifteen")),
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            outcome = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = (
            outcome.pending_penalty_decision, outcome.penalty_applied,
            engine.state.is_home_possession, engine.state.ball_position,
            engine.state.down, engine.state.yards_to_go,
            engine.state.home_stats.penalties, engine.state.home_stats.penalty_yards,
            engine.state.away_stats.penalties, engine.state.away_stats.penalty_yards,
            engine.state.home_stats.turnovers, engine.state.away_stats.turnovers,
            values["offensive_plays"], outcome.result.fumble_resolved,
            engine.state.quarter, engine.state.time_remaining, engine.has_untimed_down(),
        )
        expected = ((False, True, False, 14, 1, 10, 0, 0, 1, 13, 0, 0, 0, False, 3, 15, False)
                    if kick == "OFF 5"
                    else (False, True, False, 90, 1, 10, 1, 10, 0, 0, 0, 0, 0, False, 2, 0, True))
        checks.append({"case": label, "observed": actual, "expected": expected})
        if actual != expected:
            errors.append(f"observer {label}: state/counts {actual}, expected {expected}")
    for fouls, automatic, label in (
        (("DEF 15",), True, "PUNT/DEF 15/previous-first-down"),
        (("DEF 5X", "DEF 10"), False, "PUNT/DEF 5X->DEF 10/selected-rights"),
    ):
        offense = controlled_offense("0")
        offense.special_teams.punt = dict(enumerate((*fouls, "40"), start=10))
        offense.special_teams.punt_return = {20: "0"}
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 2, 20
        engine.state.quarter, engine.state.time_remaining = 2, 3 / 60
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
        dice = iter((*range(10, 11 + len(fouls)), 20))
        with (patch("paydirt.game_engine.roll_chart_dice", side_effect=lambda dice=dice: (next(dice), "selected foul")),
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            pending = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
            outcome = engine.apply_punt_penalty_decision(pending, accept_penalty=True)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = (
            outcome.first_down, engine.state.home_stats.first_downs,
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go,
            engine.state.away_stats.penalties, engine.state.away_stats.penalty_yards,
            values["offensive_plays"], engine.state.quarter, engine.state.time_remaining, engine.has_untimed_down(),
        )
        expected = ((True, 1, 55, 1, 10, 1, 15, 0, 2, 0, True) if automatic
                    else (False, 0, 50, 2, 10, 1, 10, 0, 2, 0, True))
        checks.append({"case": label, "observed": actual, "expected": expected})
        if actual != expected:
            errors.append(f"observer {label}: state/counts {actual}, expected {expected}")
    for foul, cell, accept in (
        ("OFF 5", "BK - 8", False), ("OFF 5", "BK - 8", True),
        ("DEF 5", "70", False), ("OFF 5", "40*", False), ("OFF 5", "40†", False),
    ):
        offense = controlled_offense("0")
        offense.special_teams.punt = {10: foul, 11: cell, 12: "40"}
        offense.special_teams.punt_return = {20: "0"}
        offense.peripheral.fumble_recovered_range = (10, 31)
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 40, 4, 8
        engine.state.quarter, engine.state.time_remaining = 2, 10
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, PlayType.PUNT, DefenseType.STANDARD)
        dice = iter((10, 11, 20))
        label = f"PUNT/{cell}/retained-{'accept' if accept else 'decline'}"
        with (patch("paydirt.game_engine.roll_chart_dice", side_effect=lambda dice=dice: (next(dice), "retained kick")) as rolls,
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            pending = engine.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
            valid_pending = (pending.pending_penalty_decision and rolls.call_count == 2
                             and engine.state.ball_position == 40 and not engine.play_log)
            outcome = engine.apply_punt_penalty_decision(pending, accept_penalty=accept)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = (
            bool(valid_pending), rolls.call_count, engine.state.is_home_possession,
            engine.state.ball_position, engine.state.down, engine.state.yards_to_go,
            engine.state.home_stats.penalties, engine.state.away_stats.penalties,
            values["offensive_plays"], outcome.result.punt_snap_fumble, outcome.result.punt_return_dice,
            outcome.result.raw_result, outcome.result.dice_roll, len(engine.play_log),
            foul in outcome.description, outcome.result.description == outcome.description,
            (outcome.result.result_type.value, asdict(outcome.clock_trace) if outcome.clock_trace else None)
            if cell.startswith("BK") and not accept else None,
        )
        expected = (
            True, 3 if cell.startswith("BK") and not accept else 2, accept,
            35 if accept else 68 if cell.startswith("BK") else 20,
            4 if accept else 1, 13 if accept else 10, int(accept), 0, 0, False, 0,
            foul if accept else cell, 0 if accept else 11, 1, True, True,
            ("blocked_kick", {"start_quarter": 2, "start_seconds": 600,
                              "end_quarter": 2, "end_seconds": 592,
                              "requested_seconds": 8, "charged_seconds": 8,
                              "period_ended": False, "note": ""})
            if cell.startswith("BK") and not accept else None,
        )
        checks.append({"case": label, "observed": actual, "expected": expected})
        if actual != expected:
            errors.append(f"observer {label}: state/counts {actual}, expected {expected}")
    for play, kind, yards, qt_roll in (
        (PlayType.SHORT_PASS, play_resolver.ResultType.YARDS, 5, 0),
        (PlayType.LINE_PLUNGE, play_resolver.ResultType.YARDS, 5, 0),
        (PlayType.SHORT_PASS, play_resolver.ResultType.SACK, -8, 10),
        (PlayType.SHORT_PASS, play_resolver.ResultType.FUMBLE, -8, 10),
    ):
        offense = controlled_offense("5")
        defender = replace(offense, peripheral=replace(offense.peripheral, short_name="DEF"))
        engine = PaydirtGameEngine(offense, defender)
        engine.state.is_home_possession = True
        engine.state.ball_position, engine.state.down = 40, 2
        observer = EngineCalibrationObserver()
        observer.on_decision(engine, None, play, DefenseType.STANDARD)
        provisional = play_resolver.PlayResult(kind, yards=yards, qb_scramble_dice=qt_roll)
        choice = play_resolver.PenaltyChoice(provisional, offsetting=True)
        with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
            outcome = engine.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
        observer.on_result(engine, outcome)
        observer.finalize_game(engine)
        values = observer.report()["teams"]["SYN"]
        actual = tuple(values[name] for name in
                       ("offensive_plays", "pass_attempts", "completions", "rushing_attempts", "sacks"))
        label = f"offsetting/{play.value}/{kind.value}"
        checks.append({"case": label, "observed": actual, "expected": (0, 0, 0, 0, 0)})
        if actual != (0, 0, 0, 0, 0) or (engine.state.ball_position, engine.state.down) != (40, 2):
            errors.append(f"observer {label}: nullified play must have no credited counts; got {actual}")
    return {"passed": not errors, "errors": errors, "checks": checks}
