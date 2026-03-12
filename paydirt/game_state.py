"""
Game state dataclasses for the Paydirt game engine.
"""
from dataclasses import dataclass, field
from typing import Optional

from .chart_loader import TeamChart
from .utils import format_field_position, format_field_position_with_team
from .play_resolver import PlayType, DefenseType, PlayResult, PenaltyChoice
from .play_events import PlayTransaction


@dataclass
class ScoringPlay:
    """Record of a scoring play."""
    quarter: int
    time_remaining: float
    team: str  # Team short name
    is_home_team: bool  # True if home team scored, False if away team
    play_type: str  # "TD", "FG", "PAT", "2PT", "Safety", "Def TD", "Def 2PT"
    description: str
    points: int


@dataclass
class TeamStats:
    """Game statistics for a team."""
    first_downs: int = 0
    total_yards: int = 0
    rushing_yards: int = 0
    passing_yards: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    sacks: int = 0
    sack_yards: int = 0
    interceptions_thrown: int = 0
    fumbles_lost: int = 0


@dataclass
class GameState:
    """Current state of the game."""
    home_chart: TeamChart
    away_chart: TeamChart
    home_score: int = 0
    away_score: int = 0
    quarter: int = 1
    time_remaining: float = 15.0  # minutes in quarter
    is_home_possession: bool = False  # Away receives opening kickoff
    ball_position: int = 20  # Yard line (0=own goal, 100=opponent's goal)
    down: int = 1
    yards_to_go: int = 10
    game_over: bool = False
    home_stats: TeamStats = field(default_factory=TeamStats)
    away_stats: TeamStats = field(default_factory=TeamStats)
    # Timeouts: 3 per half for each team
    home_timeouts: int = 3
    away_timeouts: int = 3
    # 2-minute warning tracking
    two_minute_warning_called: bool = False
    # Scoring log
    scoring_plays: list = field(default_factory=list)
    # Overtime tracking
    is_overtime: bool = False
    ot_period: int = 0  # Current OT period (1, 2, etc.)
    ot_first_possession_complete: bool = False
    ot_first_possession_scored: bool = False
    ot_first_possession_was_td: bool = False
    ot_coin_toss_winner_is_home: bool = False  # Who won the OT coin toss
    is_playoff: bool = False  # Is this a playoff game?
    # Untimed down tracking (defensive penalty at 0:00)
    untimed_down_pending: bool = False  # True if an untimed down must be played
    # Pending penalty to apply to next kickoff (e.g., when TD scored on return with penalty)
    pending_kickoff_penalty_yards: int = 0
    pending_kickoff_penalty_is_offense: bool = False  # True = offense committed penalty, False = defense

    @property
    def possession_team(self) -> TeamChart:
        return self.home_chart if self.is_home_possession else self.away_chart

    @property
    def defense_team(self) -> TeamChart:
        return self.away_chart if self.is_home_possession else self.home_chart

    @property
    def offense_stats(self) -> TeamStats:
        return self.home_stats if self.is_home_possession else self.away_stats

    @property
    def defense_stats(self) -> TeamStats:
        return self.away_stats if self.is_home_possession else self.home_stats

    def field_position_str(self) -> str:
        """Get human-readable field position with correct team context."""
        off_team = self.possession_team.peripheral.short_name
        def_team = self.defense_team.peripheral.short_name
        return format_field_position_with_team(self.ball_position, off_team, def_team)

    def switch_possession(self):
        """Switch possession between teams."""
        self.is_home_possession = not self.is_home_possession
        self.ball_position = 100 - self.ball_position
        self.down = 1
        self.yards_to_go = 10

    @property
    def offense_timeouts(self) -> int:
        """Get timeouts remaining for offense."""
        return self.home_timeouts if self.is_home_possession else self.away_timeouts

    @property
    def defense_timeouts(self) -> int:
        """Get timeouts remaining for defense."""
        return self.away_timeouts if self.is_home_possession else self.home_timeouts

    def use_timeout(self, is_home: bool) -> bool:
        """
        Use a timeout for the specified team.
        Returns True if timeout was available and used, False otherwise.
        """
        if is_home:
            if self.home_timeouts > 0:
                self.home_timeouts -= 1
                return True
        else:
            if self.away_timeouts > 0:
                self.away_timeouts -= 1
                return True
        return False

    def reset_timeouts_for_half(self):
        """Reset timeouts to 3 for each team at start of second half."""
        self.home_timeouts = 3
        self.away_timeouts = 3
        self.two_minute_warning_called = False

    def advance_ball(self, yards: int) -> bool:
        """
        Advance the ball. Returns True if first down achieved.
        """
        self.ball_position += yards

        # Clamp to valid range
        if self.ball_position > 100:
            self.ball_position = 100
        elif self.ball_position < 0:
            self.ball_position = 0

        # Check for touchdown first (ball at or past goal line)
        if self.ball_position >= 100:
            # Touchdown - don't update yards_to_go, it will be reset after score
            return True

        self.yards_to_go -= yards

        if self.yards_to_go <= 0:
            self.down = 1
            self.yards_to_go = min(10, 100 - self.ball_position)
            return True

        return False

    def next_down(self):
        """Advance to next down. Returns True if turnover on downs."""
        self.down += 1
        if self.down > 4:
            self.switch_possession()
            return True
        return False


@dataclass
class PlayOutcome:
    """Complete outcome of a play for the game."""
    play_type: PlayType
    defense_type: DefenseType
    result: PlayResult
    yards_gained: int = 0
    turnover: bool = False
    touchdown: bool = False
    safety: bool = False
    first_down: bool = False
    field_goal_made: bool = False
    field_position_before: str = ""
    field_position_after: str = ""
    down_before: int = 1
    down_after: int = 1
    description: str = ""
    # Penalty choice information - when a penalty occurs, offended team gets a choice
    penalty_choice: Optional[PenaltyChoice] = None
    # Whether this outcome requires a penalty decision from the user
    pending_penalty_decision: bool = False
    # Whether a penalty was accepted (vs play result)
    penalty_applied: bool = False
    # Transaction-based event chain (new architecture)
    transaction: Optional[PlayTransaction] = None
