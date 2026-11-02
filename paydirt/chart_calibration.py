"""Observe resolved engine games for statistical chart calibration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .game_state import PlayOutcome, TeamStats
from .play_resolver import DefenseType, PlayType, ResultType

_PASS_PLAY_TYPES = {
    PlayType.SCREEN,
    PlayType.SHORT_PASS,
    PlayType.MEDIUM_PASS,
    PlayType.LONG_PASS,
    PlayType.TE_SHORT_LONG,
    PlayType.HAIL_MARY,
}
_NON_SCRIMMAGE_PLAY_TYPES = {
    PlayType.PUNT,
    PlayType.FIELD_GOAL,
    PlayType.KICKOFF,
}


@dataclass
class TeamCalibrationTotals:
    """Engine observations accumulated for one team across completed games."""

    team_games: int = 0
    points: int = 0
    offensive_plays: int = 0
    rushing_attempts: int = 0
    pass_attempts: int = 0
    completions: int = 0
    total_yards: int = 0
    rushing_yards: int = 0
    passing_yards: int = 0
    sack_yards: int = 0
    sacks: int = 0
    interceptions: int = 0
    fumbles_lost: int = 0
    turnovers: int = 0
    field_goal_attempts: int = 0
    field_goals_made: int = 0

    def add_box_score(self, stats: TeamStats, points: int) -> None:
        """Add authoritative final engine totals from one team-game."""
        self.team_games += 1
        self.points += points
        self.total_yards += stats.total_yards
        self.rushing_yards += stats.rushing_yards
        self.passing_yards += stats.passing_yards
        self.sack_yards += stats.sack_yards
        self.sacks += stats.sacks
        self.interceptions += stats.interceptions_thrown
        self.fumbles_lost += stats.fumbles_lost
        self.turnovers += stats.turnovers

    def to_dict(self) -> dict[str, int | float]:
        """Return counts plus derived rates used by calibration reports."""
        values: dict[str, int | float] = asdict(self)
        values["completion_rate"] = _ratio(self.completions, self.pass_attempts)
        values["rushing_yards_per_attempt"] = _ratio(
            self.rushing_yards, self.rushing_attempts
        )
        values["yards_per_pass_attempt"] = _ratio(
            self.passing_yards, self.pass_attempts
        )
        values["sack_rate"] = _ratio(self.sacks, self.pass_attempts + self.sacks)
        values["interception_rate"] = _ratio(
            self.interceptions, self.pass_attempts
        )
        values["fumble_loss_rate_per_play"] = _ratio(
            self.fumbles_lost, self.offensive_plays
        )
        values["plays_per_team_game"] = _ratio(
            self.offensive_plays, self.team_games
        )
        values["points_per_team_game"] = _ratio(self.points, self.team_games)
        values["field_goal_rate"] = _ratio(
            self.field_goals_made, self.field_goal_attempts
        )
        return values


def _ratio(numerator: int, denominator: int) -> float:
    """Return a safe ratio for report-only derived metrics."""
    return numerator / denominator if denominator else 0.0


class EngineCalibrationObserver:
    """Pair auto-game decision/result callbacks and aggregate final box scores."""

    def __init__(self) -> None:
        """Initialize an empty observer with no pending selected play."""
        self._teams: dict[str, TeamCalibrationTotals] = {}
        self._pending: tuple[str, PlayType] | None = None
        self._games = 0

    def team_totals(self, team: str) -> TeamCalibrationTotals:
        """Return the mutable accumulation record for one short team name."""
        return self._teams.setdefault(team, TeamCalibrationTotals())

    def on_decision(
        self,
        game: Any,
        _ai: Any,
        play_type: PlayType,
        _defense_type: DefenseType,
    ) -> None:
        """Record the offense and call selected immediately before engine execution."""
        if self._pending is not None:
            raise ValueError("A calibration play is already pending")
        state = game.state
        chart = state.home_chart if state.is_home_possession else state.away_chart
        self._pending = (chart.peripheral.short_name, play_type)

    def on_result(self, _game: Any, outcome: PlayOutcome) -> None:
        """Classify one finalized selected call after the engine resolves penalties."""
        if self._pending is None:
            raise ValueError("Calibration result arrived without a selected play")
        team, selected_play = self._pending
        self._pending = None
        if selected_play != outcome.play_type:
            raise ValueError("Calibration result does not match the selected play")
        if outcome.penalty_applied or outcome.result.replay_down:
            return
        totals = self.team_totals(team)
        if selected_play == PlayType.FIELD_GOAL:
            totals.field_goal_attempts += 1
            totals.field_goals_made += int(outcome.field_goal_made)
            return
        if selected_play in _NON_SCRIMMAGE_PLAY_TYPES:
            return
        totals.offensive_plays += 1
        if selected_play not in _PASS_PLAY_TYPES:
            totals.rushing_attempts += 1
            return
        result_type = outcome.result.result_type
        if result_type == ResultType.QB_SCRAMBLE:
            totals.rushing_attempts += 1
            return
        if result_type == ResultType.SACK:
            return
        totals.pass_attempts += 1
        if result_type not in {ResultType.INCOMPLETE, ResultType.INTERCEPTION}:
            totals.completions += 1

    def finalize_game(self, game: Any) -> None:
        """Add final scores and engine-owned team statistics for one completed game."""
        if self._pending is not None:
            raise ValueError("Cannot finalize calibration with a pending play")
        state = game.state
        home = state.home_chart.peripheral.short_name
        away = state.away_chart.peripheral.short_name
        self.team_totals(home).add_box_score(state.home_stats, state.home_score)
        self.team_totals(away).add_box_score(state.away_stats, state.away_score)
        self._games += 1

    def report(self) -> dict[str, Any]:
        """Return per-team and league totals with derived calibration rates."""
        league = TeamCalibrationTotals()
        for totals in self._teams.values():
            for name in TeamCalibrationTotals.__dataclass_fields__:
                setattr(league, name, getattr(league, name) + getattr(totals, name))
        league_report = league.to_dict()
        league_report["games"] = self._games
        league_report["yards_per_team_game"] = _ratio(
            league.total_yards, league.team_games
        )
        league_report["sacks_per_team_game"] = _ratio(league.sacks, league.team_games)
        league_report["turnovers_per_team_game"] = _ratio(
            league.turnovers, league.team_games
        )
        return {
            "league": league_report,
            "teams": {
                team: totals.to_dict() for team, totals in sorted(self._teams.items())
            },
        }
