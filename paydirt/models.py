"""
Core game models for Paydirt football simulation.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PlayType(Enum):
    """Types of offensive plays available."""
    RUN_LEFT = "run_left"
    RUN_RIGHT = "run_right"
    RUN_MIDDLE = "run_middle"
    SHORT_PASS = "short_pass"
    MEDIUM_PASS = "medium_pass"
    LONG_PASS = "long_pass"
    SCREEN_PASS = "screen_pass"
    DRAW = "draw"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"


class DefenseType(Enum):
    """Types of defensive formations."""
    NORMAL = "normal"
    PREVENT = "prevent"
    BLITZ = "blitz"
    GOAL_LINE = "goal_line"


class PlayResult(Enum):
    """Possible outcomes of a play."""
    GAIN = "gain"
    LOSS = "loss"
    NO_GAIN = "no_gain"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"
    FUMBLE = "fumble"
    TOUCHDOWN = "touchdown"
    SACK = "sack"
    PENALTY_OFFENSE = "penalty_offense"
    PENALTY_DEFENSE = "penalty_defense"


@dataclass
class PlayOutcome:
    """Represents the outcome of a single play."""
    result: PlayResult
    yards: int = 0
    description: str = ""
    turnover: bool = False
    scoring: bool = False
    penalty_yards: int = 0


@dataclass
class TeamStats:
    """Tracks statistics for a team during the game."""
    first_downs: int = 0
    total_yards: int = 0
    rushing_yards: int = 0
    passing_yards: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    time_of_possession: float = 0.0
    third_down_attempts: int = 0
    third_down_conversions: int = 0


@dataclass
class Team:
    """Represents an NFL team with its characteristics."""
    name: str
    abbreviation: str
    # Team ratings affect dice roll outcomes (scale 1-10)
    rushing_offense: int = 5
    passing_offense: int = 5
    rushing_defense: int = 5
    passing_defense: int = 5
    special_teams: int = 5
    # Power rating used for home field advantage calculations
    power_rating: int = 50
    stats: TeamStats = field(default_factory=TeamStats)

    def reset_stats(self):
        """Reset game statistics."""
        self.stats = TeamStats()


@dataclass
class GameState:
    """Tracks the current state of the game."""
    home_team: Team
    away_team: Team
    home_score: int = 0
    away_score: int = 0
    quarter: int = 1
    time_remaining: float = 15.0  # Minutes remaining in quarter
    possession: Optional[Team] = None
    ball_position: int = 20  # Yard line (0-100, where 100 is opponent's end zone)
    down: int = 1
    yards_to_go: int = 10
    is_home_possession: bool = True
    play_clock: float = 40.0
    game_over: bool = False

    def __post_init__(self):
        """Initialize possession to away team (they receive kickoff)."""
        if self.possession is None:
            self.possession = self.away_team
            self.is_home_possession = False

    def switch_possession(self):
        """Switch possession between teams."""
        self.is_home_possession = not self.is_home_possession
        self.possession = self.home_team if self.is_home_possession else self.away_team
        # Ball position flips (e.g., own 20 becomes opponent's 80)
        self.ball_position = 100 - self.ball_position
        self.down = 1
        self.yards_to_go = 10

    def advance_ball(self, yards: int) -> bool:
        """
        Advance the ball by the given yards.
        Returns True if a first down was achieved or touchdown scored.
        """
        self.ball_position += yards

        # Check for touchdown
        if self.ball_position >= 100:
            self.ball_position = 100
            return True

        # Check for safety (ball in own end zone)
        if self.ball_position <= 0:
            self.ball_position = 0
            return False

        # Update yards to go
        self.yards_to_go -= yards

        # Check for first down
        if self.yards_to_go <= 0:
            self.down = 1
            self.yards_to_go = 10
            # Adjust if close to goal line
            if self.ball_position > 90:
                self.yards_to_go = 100 - self.ball_position
            return True

        return False

    def next_down(self):
        """Advance to the next down."""
        self.down += 1
        if self.down > 4:
            # Turnover on downs
            self.switch_possession()

    def get_field_position_description(self) -> str:
        """Get a human-readable description of field position."""
        from .utils import format_field_position
        return format_field_position(self.ball_position)

    def score_touchdown(self):
        """Record a touchdown for the team with possession."""
        if self.is_home_possession:
            self.home_score += 6
        else:
            self.away_score += 6

    def score_field_goal(self):
        """Record a field goal for the team with possession."""
        if self.is_home_possession:
            self.home_score += 3
        else:
            self.away_score += 3

    def score_extra_point(self):
        """Record an extra point for the team with possession."""
        if self.is_home_possession:
            self.home_score += 1
        else:
            self.away_score += 1

    def score_two_point_conversion(self):
        """Record a two-point conversion for the team with possession."""
        if self.is_home_possession:
            self.home_score += 2
        else:
            self.away_score += 2

    def score_safety(self):
        """Record a safety (2 points for the defense)."""
        if self.is_home_possession:
            self.away_score += 2
        else:
            self.home_score += 2

    def use_time(self, seconds: float):
        """Use game clock time."""
        minutes = seconds / 60.0
        self.time_remaining -= minutes

        if self.time_remaining <= 0:
            self.time_remaining = 0
            if self.quarter < 4:
                self.quarter += 1
                self.time_remaining = 15.0
            else:
                # Check for tie - would go to overtime
                if self.home_score != self.away_score:
                    self.game_over = True
