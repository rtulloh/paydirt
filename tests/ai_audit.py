"""Testing-only AI configuration, evidence collection, and balance reporting.

Uses the production auto-game loop; never resolves plays or writes standings.
Random isolation is serial/in-process, not thread-safe. No chart cells or narrative
logs are exported. Reports are local developer evidence, not usage quotas.
"""

from collections import Counter, defaultdict
import contextlib
from dataclasses import asdict, dataclass
import hashlib
import io
import platform
import random
from typing import Iterable
from unittest.mock import patch

from paydirt.auto_game import run_auto_game
from paydirt.computer_ai import ComputerAI, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.offense_strategy import situation_key
from paydirt.play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType
from tests.run_full_season import validate_game


DIFFICULTIES = ("easy", "medium", "hard", "balanced")


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
        with patch.object(PaydirtGameEngine, "kickoff", guarded_kickoff), contextlib.redirect_stdout(output):
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
        limits = {
            "Auto-game play limit reached before game completion",
            "Auto-game penalty decision limit reached",
            "Auto-game scoring/kickoff sequence limit reached",
        }
        reason = "play/sequence limit reached" if str(error) in limits else "game or evidence validation failed"
        record["error"] = f"{type(error).__name__}: {reason}"
    finally:
        random.setstate(original_random)
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
            "games": games, "summary": {
                "games": len(games), "passed": sum(g["status"] == "passed" for g in games),
                "failed": sum(g["status"] != "passed" for g in games), "calls": all_calls,
                "balance_calls": completed_calls, "situations": situations, "warnings": warnings,
            }}
