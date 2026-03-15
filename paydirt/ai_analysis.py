"""
AI Analysis module for studying team charts and opponent tendencies.

This module provides utilities for analyzing offense and defense charts to identify
best plays for different situations, ignoring penalties and turnovers.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from paydirt.chart_loader import OffenseChart, DefenseChart, TeamChart


@dataclass
class PlayOutcome:
    """A single play outcome result."""
    result: str
    yards: int
    is_positive: bool  # positive yardage
    is_first_down: bool  # results in first down
    is_negative: bool  # negative yardage
    is_zero: bool  # no gain
    is_black: bool  # incomplete pass
    is_fumble: bool
    is_interception: bool
    is_touchdown: bool
    is_penalty: bool
    is_breakaway: bool = False  # B - breakaway, requires second roll


@dataclass
class RollStats:
    """Statistics for a single die roll result."""
    result: str
    outcome: PlayOutcome


@dataclass
class PlayTypeStats:
    """Statistics for a play type across all relevant dice rolls."""
    play_type: str
    total_rolls: int = 0
    valid_rolls: int = 0  # excluding penalties and turnovers
    
    # Yards statistics (valid plays only)
    total_yards: int = 0
    avg_yards: float = 0.0
    max_yards: int = 0
    min_yards: int = 0
    
    # Success metrics (valid plays only)
    positive_plays: int = 0  # positive yardage
    first_downs: int = 0
    zero_plays: int = 0
    negative_plays: int = 0
    
    # Rates
    success_rate: float = 0.0  # % positive or first down
    first_down_rate: float = 0.0


@dataclass 
class SituationStats:
    """Statistics aggregated by down and distance."""
    down: int
    distance: int
    
    # Play type to stats mapping
    play_stats: dict[str, PlayTypeStats] = field(default_factory=dict)
    
    # Best play recommendations
    best_play_overall: Optional[str] = None
    best_run_play: Optional[str] = None
    best_pass_play: Optional[str] = None
    
    def get_best_plays(self, count: int = 3) -> list[tuple[str, float]]:
        """Return top plays by success rate."""
        plays = [(pt, stats.success_rate) for pt, stats in self.play_stats.items()]
        plays.sort(key=lambda x: x[1], reverse=True)
        return plays[:count]


class OffenseAnalyzer:
    """Analyzes an offense chart to find best plays for situations."""
    
    # Map column names to play types
    PLAY_TYPE_MAP = {
        'Line Plunge': 'run',
        'Off Tackle': 'run', 
        'End Run': 'run',
        'Draw': 'run',
        'Screen': 'pass',
        'Short': 'pass',
        'Med': 'pass',
        'Long': 'pass',
        'T/E S/L': 'pass',
        'B': 'breakaway',
        'QT': 'qb_trouble',
    }
    
    def __init__(self, offense_chart: OffenseChart):
        self.chart = offense_chart
        self._stats_cache: dict[str, PlayTypeStats] = {}
        
    def _parse_result(self, result: str) -> PlayOutcome:
        """Parse a result string into structured outcome."""
        result = result.strip()
        if not result:
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=True,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        result_upper = result.upper()
        
        # Check for penalty (OFF, DEF)
        if result_upper.startswith('OFF ') or result_upper.startswith('DEF '):
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=True
            )
        
        # Check for fumble
        if 'F' in result_upper and 'OF' not in result_upper:  # F, F + N, F - N
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=True,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        # Check for interception
        if 'INT' in result_upper:
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=False,
                is_interception=True,
                is_touchdown=False,
                is_penalty=False
            )
        
        # Check for BLACK/incomplete
        if result_upper == 'BLACK':
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=False,
                is_black=True,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        # Check for TD
        if result_upper == 'TD':
            return PlayOutcome(
                result=result,
                yards=100,  # TD = end of drive
                is_positive=True,
                is_first_down=True,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=True,
                is_penalty=False
            )
        
        # Check for TD in parentheses (defensive result)
        if result_upper == '(TD)':
            return PlayOutcome(
                result=result,
                yards=100,
                is_positive=True,
                is_first_down=True,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=True,
                is_penalty=False
            )
        
        # Try to parse as number
        # Handle parentheses (defensive modifier)
        parens_match = result_upper.strip('()')
        if parens_match.lstrip('-').isdigit():
            yards = int(parens_match)
            return PlayOutcome(
                result=result,
                yards=yards,
                is_positive=yards > 0,
                is_first_down=False,  # Can't determine first down from just dice roll
                is_negative=yards < 0,
                is_zero=yards == 0,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        # Try to parse regular number (possibly with asterisk)
        clean_result = result_upper.rstrip('*')
        if clean_result.lstrip('-').isdigit():
            yards = int(clean_result)
            return PlayOutcome(
                result=result,
                yards=yards,
                is_positive=yards > 0,
                is_first_down=False,
                is_negative=yards < 0,
                is_zero=yards == 0,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        # QT (quarterback trouble) - no yards specified
        if result_upper == 'QT':
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=True,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False
            )
        
        # B (breakaway) - requires second roll, treat as intangible
        if result_upper == 'B':
            return PlayOutcome(
                result=result,
                yards=0,
                is_positive=False,
                is_first_down=False,
                is_negative=False,
                is_zero=False,
                is_black=False,
                is_fumble=False,
                is_interception=False,
                is_touchdown=False,
                is_penalty=False,
                is_breakaway=True
            )
        
        # Default - unknown result
        return PlayOutcome(
            result=result,
            yards=0,
            is_positive=False,
            is_first_down=False,
            is_negative=False,
            is_zero=True,
            is_black=False,
            is_fumble=False,
            is_interception=False,
            is_touchdown=False,
            is_penalty=False
        )
    
    def _is_valid_play(self, outcome: PlayOutcome) -> bool:
        """Check if a play outcome is valid (not penalty, fumble, interception, or breakaway)."""
        return not (outcome.is_penalty or outcome.is_fumble or outcome.is_interception or outcome.is_breakaway)
    
    def analyze_play_type(self, play_column: str) -> PlayTypeStats:
        """Analyze a specific play type column."""
        if play_column in self._stats_cache:
            return self._stats_cache[play_column]
        
        # Get the dice roll results for this play type
        roll_results = getattr(self.chart, play_column.lower().replace(' ', '_').replace('/', '_'), {})
        if not roll_results:
            roll_results = self._get_chart_attribute(play_column)
        
        stats = PlayTypeStats(play_type=play_column)
        
        for dice_roll, result in roll_results.items():
            # Dice rolls in offense chart are 10-39
            if dice_roll < 10 or dice_roll > 39:
                continue
                
            stats.total_rolls += 1
            outcome = self._parse_result(result)
            
            if self._is_valid_play(outcome):
                stats.valid_rolls += 1
                stats.total_yards += outcome.yards
                stats.max_yards = max(stats.max_yards, outcome.yards)
                
                if stats.valid_rolls == 1:
                    stats.min_yards = outcome.yards
                else:
                    stats.min_yards = min(stats.min_yards, outcome.yards)
                
                if outcome.is_positive:
                    stats.positive_plays += 1
                elif outcome.is_negative:
                    stats.negative_plays += 1
                else:
                    stats.zero_plays += 1
        
        # Calculate rates
        if stats.valid_rolls > 0:
            stats.avg_yards = stats.total_yards / stats.valid_rolls
            # Success = positive yards OR (can't determine first down from dice roll alone)
            # For now, success = positive yardage
            stats.success_rate = (stats.positive_plays / stats.valid_rolls) * 100
            stats.first_down_rate = (stats.first_downs / stats.valid_rolls) * 100
        
        self._stats_cache[play_column] = stats
        return stats
    
    def _get_chart_attribute(self, play_column: str) -> dict:
        """Get chart attribute by play column name."""
        # Map play column names to chart attributes
        column_map = {
            'Line Plunge': 'line_plunge',
            'Off Tackle': 'off_tackle',
            'End Run': 'end_run',
            'Draw': 'draw',
            'Screen': 'screen',
            'Short': 'short_pass',
            'Med': 'medium_pass',
            'Long': 'long_pass',
            'T/E S/L': 'te_short_long',
            'B': 'breakaway',
            'QT': 'qb_time',
        }
        attr_name = column_map.get(play_column, play_column.lower().replace(' ', '_'))
        return getattr(self.chart, attr_name, {})
    
    def get_all_play_stats(self) -> dict[str, PlayTypeStats]:
        """Get statistics for all play types."""
        play_columns = [
            'Line Plunge', 'Off Tackle', 'End Run', 'Draw',
            'Screen', 'Short', 'Med', 'Long', 'T/E S/L', 'B', 'QT'
        ]
        
        result = {}
        for col in play_columns:
            stats = self.analyze_play_type(col)
            if stats.total_rolls > 0:
                result[col] = stats
        
        return result
    
    def get_best_play_for_downs(self, is_passing_down: bool, is_short_yardage: bool) -> str:
        """Get best play type for current down/distance situation."""
        all_stats = self.get_all_play_stats()
        
        if not all_stats:
            return 'Off Tackle'  # Default
        
        # Categorize plays
        run_plays = {k: v for k, v in all_stats.items() 
                     if self.PLAY_TYPE_MAP.get(k) == 'run'}
        pass_plays = {k: v for k, v in all_stats.items() 
                      if self.PLAY_TYPE_MAP.get(k) == 'pass'}
        
        # Determine what we need
        if is_short_yardage:
            # Need positive yardage, prefer runs
            candidates = run_plays if run_plays else pass_plays
        elif is_passing_down:
            # Need big yards, prefer passes
            candidates = pass_plays if pass_plays else run_plays
        else:
            # Balanced - go with higher success rate
            candidates = all_stats
        
        # Find best by success rate
        best = max(candidates.items(), key=lambda x: x[1].success_rate)
        return best[0]
    
    def get_top_plays(self, count: int = 5) -> list[tuple[str, PlayTypeStats]]:
        """Get top plays sorted by success rate."""
        all_stats = self.get_all_play_stats()
        plays = list(all_stats.items())
        plays.sort(key=lambda x: x[1].success_rate, reverse=True)
        return plays[:count]


class DefenseAnalyzer:
    """Analyzes a defense chart to identify strengths and weaknesses."""
    
    def __init__(self, defense_chart: DefenseChart):
        self.chart = defense_chart
    
    def get_formation_stats(self, formation: str) -> dict[int, PlayTypeStats]:
        """Get statistics for a specific formation."""
        stats = {}
        
        for sub_row in range(1, 6):
            key = (formation, sub_row)
            if key in self.chart.modifiers:
                modifiers = self.chart.modifiers[key]
                # Analyze what each dice column tends to produce
                # This is complex - for now return modifier counts
                stats[sub_row] = modifiers
        
        return stats
    
    def identify_weak_spots(self) -> list[tuple[str, int]]:
        """Identify formations/sub-rows that favor offense (low/negative modifiers)."""
        weak_spots = []
        
        for (formation, sub_row), modifiers in self.chart.modifiers.items():
            total_modifier = 0
            valid_count = 0
            
            for dice, mod in modifiers.items():
                if mod and mod.lstrip('(-').rstrip(')').isdigit():
                    total_modifier += int(mod.lstrip('(-').rstrip(')'))
                    valid_count += 1
            
            if valid_count > 0:
                avg = total_modifier / valid_count
                # Lower average = easier for offense
                weak_spots.append((formation, sub_row, avg))
        
        # Sort by average modifier (lowest first = weakest defense)
        weak_spots.sort(key=lambda x: x[2])
        return [(f, s) for f, s, _ in weak_spots]
    
    def identify_tough_spots(self) -> list[tuple[str, int]]:
        """Identify formations/sub-rows that favor defense."""
        weak = self.identify_weak_spots()
        all_spots = [(f, s) for f in 'ABCDEF' for s in range(1, 6)]
        
        tough = [s for s in all_spots if s not in weak]
        return tough


class TeamAnalyzer:
    """Complete team analyzer combining offense and defense."""
    
    def __init__(self, team_chart: TeamChart):
        self.team_chart = team_chart
        self.offense = OffenseAnalyzer(team_chart.offense)
        self.defense = DefenseAnalyzer(team_chart.defense)
    
    def get_offense_summary(self) -> dict:
        """Get summary of offense capabilities."""
        top_plays = self.offense.get_top_plays(5)
        
        return {
            'best_plays': [(p, s.success_rate, s.avg_yards) for p, s in top_plays],
            'total_play_types': len(self.offense.get_all_play_stats()),
        }
    
    def suggest_play(self, down: int, distance: int) -> dict:
        """Suggest best play for given situation."""
        is_passing_down = distance >= 7  # 3rd & 7+ or more
        is_short_yardage = distance <= 2
        
        best_play = self.offense.get_best_play_for_downs(is_passing_down, is_short_yardage)
        stats = self.offense.analyze_play_type(best_play)
        
        return {
            'recommended_play': best_play,
            'success_rate': stats.success_rate,
            'avg_yards': stats.avg_yards,
            'is_passing_down': is_passing_down,
            'is_short_yardage': is_short_yardage,
        }


def analyze_team(team_chart: TeamChart) -> TeamAnalyzer:
    """Create a team analyzer for the given team chart."""
    return TeamAnalyzer(team_chart)


# ============================================================
# PHASE 2: OPPONENT MODELING
# ============================================================


class PlayCategory(Enum):
    """Categories for play type classification."""
    RUN = "run"
    PASS = "pass"
    SPECIAL = "special"


class SituationType(Enum):
    """Situation categories for tendency tracking."""
    FIRST_DOWN = "first_down"  # 1st & any
    SECOND_SHORT = "second_short"  # 2nd & short (< 4)
    SECOND_MEDIUM = "second_medium"  # 2nd & medium (4-6)
    SECOND_LONG = "second_long"  # 2nd & 7+
    THIRD_SHORT = "third_short"  # 3rd & short (< 4)
    THIRD_MEDIUM = "third_medium"  # 3rd & medium (4-6)
    THIRD_LONG = "third_long"  # 3rd & 7+
    FOURTH_SHORT = "fourth_short"  # 4th & short
    FOURTH_LONG = "fourth_long"  # 4th & long


def get_situation_type(down: int, distance: int) -> SituationType:
    """Categorize a down/distance into a situation type."""
    if down == 1:
        return SituationType.FIRST_DOWN
    elif down == 2:
        if distance <= 3:
            return SituationType.SECOND_SHORT
        elif distance <= 6:
            return SituationType.SECOND_MEDIUM
        else:
            return SituationType.SECOND_LONG
    elif down == 3:
        if distance <= 3:
            return SituationType.THIRD_SHORT
        elif distance <= 6:
            return SituationType.THIRD_MEDIUM
        else:
            return SituationType.THIRD_LONG
    else:  # down 4
        if distance <= 3:
            return SituationType.FOURTH_SHORT
        else:
            return SituationType.FOURTH_LONG


def categorize_play(play_type: str) -> PlayCategory:
    """Categorize a play type as run, pass, or special."""
    run_keywords = ['Line Plunge', 'Off Tackle', 'End Run', 'Draw']
    pass_keywords = ['Screen', 'Short', 'Med', 'Long', 'T/E S/L']
    
    for keyword in run_keywords:
        if keyword in play_type:
            return PlayCategory.RUN
    for keyword in pass_keywords:
        if keyword in play_type:
            return PlayCategory.PASS
    return PlayCategory.SPECIAL


@dataclass
class SituationTendency:
    """Tendency statistics for a specific situation type."""
    situation: SituationType
    total_plays: int = 0
    run_plays: int = 0
    pass_plays: int = 0
    special_plays: int = 0
    
    @property
    def run_percentage(self) -> float:
        if self.total_plays == 0:
            return 50.0  # Default to balanced
        return (self.run_plays / self.total_plays) * 100
    
    @property
    def pass_percentage(self) -> float:
        if self.total_plays == 0:
            return 50.0
        return (self.pass_plays / self.total_plays) * 100


class OpponentTendencyTracker:
    """
    Tracks opponent tendencies to predict their play choices.
    
    Ignores penalties and turnovers - only tracks actual play outcomes.
    """
    
    def __init__(self):
        # Track plays by situation type
        self.situation_plays: dict[SituationType, list[PlayCategory]] = defaultdict(list)
        
        # Track recent plays for streak detection
        self.recent_plays: list[PlayCategory] = []
        self.max_recent_plays = 10  # Keep last 10 plays
        
        # Track results (for success rate calculation)
        self.situation_results: dict[SituationType, dict[PlayCategory, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
    
    def record_play(self, down: int, distance: int, play_type: str, 
                    yards_gained: int, is_pass: bool = None):
        """
        Record an opponent's play choice.
        
        Args:
            down: Down number (1-4)
            distance: Yards to go
            play_type: The play type they chose
            yards_gained: Yards gained (used to filter out big plays, not for tendency tracking)
            is_pass: Optional override for pass vs run classification
        """
        situation = get_situation_type(down, distance)
        
        # Categorize the play
        if is_pass is not None:
            category = PlayCategory.PASS if is_pass else PlayCategory.RUN
        else:
            category = categorize_play(play_type)
        
        # Record the play
        self.situation_plays[situation].append(category)
        self.recent_plays.append(category)
        
        # Keep only recent plays
        if len(self.recent_plays) > self.max_recent_plays:
            self.recent_plays.pop(0)
    
    def get_tendency(self, down: int, distance: int) -> SituationTendency:
        """Get tendency statistics for a specific down/distance."""
        situation = get_situation_type(down, distance)
        
        tendency = SituationTendency(situation=situation)
        plays = self.situation_plays.get(situation, [])
        
        tendency.total_plays = len(plays)
        tendency.run_plays = sum(1 for p in plays if p == PlayCategory.RUN)
        tendency.pass_plays = sum(1 for p in plays if p == PlayCategory.PASS)
        tendency.special_plays = sum(1 for p in plays if p == PlayCategory.SPECIAL)
        
        return tendency
    
    def predict_play(self, down: int, distance: int) -> PlayCategory:
        """
        Predict what the opponent will do in a given situation.
        
        Returns the most likely play category (RUN, PASS, or SPECIAL).
        """
        tendency = self.get_tendency(down, distance)
        
        # If we have no data, return balanced prediction
        if tendency.total_plays == 0:
            return PlayCategory.RUN  # Default assumption
        
        # Return the category with higher percentage
        if tendency.run_percentage >= tendency.pass_percentage:
            return PlayCategory.RUN
        else:
            return PlayCategory.PASS
    
    def get_streak(self) -> Optional[PlayCategory]:
        """Get the current streak of same play types."""
        if len(self.recent_plays) < 3:
            return None
        
        # Check last 3 plays
        last_three = self.recent_plays[-3:]
        if len(set(last_three)) == 1:
            return last_three[0]
        return None
    
    def get_defense_recommendation(self, down: int, distance: int) -> str:
        """
        Get a defense recommendation based on opponent tendencies.
        
        Returns a defense type recommendation (A-F).
        """
        tendency = self.get_tendency(down, distance)
        
        # If opponent runs a lot, use run defense (A, B)
        # If opponent passes a lot, use pass defense (D, E)
        if tendency.pass_percentage > 60:
            return "D"  # Short Pass defense
        elif tendency.pass_percentage > 40:
            return "C"  # Spread (balanced)
        elif tendency.run_percentage > 60:
            return "B"  # Short Yardage
        else:
            return "A"  # Standard
    
    def to_dict(self) -> dict:
        """
        Convert tracker state to JSON-serializable dict.
        
        Returns:
            Dict with situation_plays, recent_plays, and situation_results
        """
        # Convert situation_plays: SituationType -> list[PlayCategory]
        situation_plays_json = {}
        for situation, plays in self.situation_plays.items():
            situation_plays_json[situation.value] = [p.value for p in plays]
        
        # Convert recent_plays: list[PlayCategory]
        recent_plays_json = [p.value for p in self.recent_plays]
        
        # Convert situation_results: SituationType -> PlayCategory -> list[int]
        situation_results_json = {}
        for situation, results in self.situation_results.items():
            situation_results_json[situation.value] = {}
            for category, yards_list in results.items():
                situation_results_json[situation.value][category.value] = yards_list
        
        return {
            "situation_plays": situation_plays_json,
            "recent_plays": recent_plays_json,
            "situation_results": situation_results_json,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OpponentTendencyTracker':
        """
        Create tracker from JSON-serializable dict.
        
        Args:
            data: Dict from to_dict()
            
        Returns:
            New OpponentTendencyTracker instance with restored state
        """
        tracker = cls()
        
        # Restore situation_plays
        for situation_str, plays in data.get("situation_plays", {}).items():
            situation = SituationType(situation_str)
            tracker.situation_plays[situation] = [PlayCategory(p) for p in plays]
        
        # Restore recent_plays
        tracker.recent_plays = [PlayCategory(p) for p in data.get("recent_plays", [])]
        
        # Restore situation_results
        for situation_str, results in data.get("situation_results", {}).items():
            situation = SituationType(situation_str)
            tracker.situation_results[situation] = {}
            for category_str, yards_list in results.items():
                category = PlayCategory(category_str)
                tracker.situation_results[situation][category] = yards_list
        
        return tracker


class OpponentModel:
    """
    Complete opponent model combining tendencies with game state awareness.
    """
    
    def __init__(self):
        self.tracker = OpponentTendencyTracker()
        self.score_differential_history: list[int] = []
        self.is_protecting_lead: bool = False
        self.is_comeback_mode: bool = False
    
    def update_game_state(self, score_diff: int, quarter: int, time_remaining: float):
        """Update game state awareness."""
        self.score_differential_history.append(score_diff)
        
        # Determine game state
        if quarter >= 4 and time_remaining < 5.0:
            if score_diff > 0:
                self.is_protecting_lead = True
                self.is_comeback_mode = False
            elif score_diff < 0:
                self.is_comeback_mode = True
                self.is_protecting_lead = False
        else:
            self.is_protecting_lead = False
            self.is_comeback_mode = False
    
    def predict_defense(self, down: int, distance: int, score_diff: int,
                       quarter: int, time_remaining: float) -> str:
        """
        Predict the best defense to use against opponent.
        
        Considers both opponent tendencies and game state.
        """
        self.update_game_state(score_diff, quarter, time_remaining)
        
        # First, check game state overrides
        if self.is_protecting_lead:
            # They're likely to run - use run defense
            return "A"  # Standard/balanced
        elif self.is_comeback_mode:
            # They're likely to pass - use pass defense
            return "E"  # Long Pass
        
        # Otherwise, use tendency data
        return self.tracker.get_defense_recommendation(down, distance)
    
    def record_opponent_play(self, down: int, distance: int, play_type: str,
                            yards_gained: int, is_pass: bool = None):
        """Record an opponent's play for tendency tracking."""
        self.tracker.record_play(down, distance, play_type, yards_gained, is_pass)
    
    def to_dict(self) -> dict:
        """
        Convert opponent model to JSON-serializable dict.
        
        Returns:
            Dict with tracker data and game state awareness
        """
        return {
            "tracker": self.tracker.to_dict(),
            "score_differential_history": self.score_differential_history,
            "is_protecting_lead": self.is_protecting_lead,
            "is_comeback_mode": self.is_comeback_mode,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OpponentModel':
        """
        Create opponent model from JSON-serializable dict.
        
        Args:
            data: Dict from to_dict()
            
        Returns:
            New OpponentModel instance with restored state
        """
        model = cls()
        
        # Restore tracker
        if "tracker" in data:
            model.tracker = OpponentTendencyTracker.from_dict(data["tracker"])
        
        # Restore game state awareness
        model.score_differential_history = data.get("score_differential_history", [])
        model.is_protecting_lead = data.get("is_protecting_lead", False)
        model.is_comeback_mode = data.get("is_comeback_mode", False)
        
        return model


# ============================================================
# PHASE 4: EASY MODE HELPER
# ============================================================

class EasyModeHelper:
    """
    Helper for human player in easy mode.
    
    Provides:
    - Play suggestions with success rates
    - Explanations for why plays are recommended
    - Warning about opponent tendencies
    - "Tricky" play suggestions that might work unexpectedly
    """
    
    def __init__(self, team_chart: TeamChart):
        self.team_analyzer = TeamAnalyzer(team_chart)
        self.opponent_tracker = OpponentTendencyTracker()
        self._last_suggestion = None
    
    def suggest_offense_plays(self, down: int, distance: int, count: int = 3) -> list[dict]:
        """
        Get play suggestions for current situation.
        
        Returns list of dicts with:
        - play: play type name
        - success_rate: percentage chance of positive yards
        - avg_yards: average yards gained
        - is_pass: True if passing play
        """
        all_stats = self.team_analyzer.offense.get_all_play_stats()
        
        # Calculate success rate for each play type
        suggestions = []
        for play_type, stats in all_stats.items():
            # Skip breakaway (B) - not a callable play, it's a random result
            if play_type == 'B':
                continue
            if stats.valid_rolls > 0:
                suggestions.append({
                    'play': play_type,
                    'success_rate': stats.success_rate,
                    'avg_yards': stats.avg_yards,
                    'is_pass': self.team_analyzer.offense.PLAY_TYPE_MAP.get(play_type) == 'pass',
                })
        
        # Sort by success rate
        suggestions.sort(key=lambda x: x['success_rate'], reverse=True)
        return suggestions[:count]
    
    def suggest_defense(self, down: int, distance: int) -> str:
        """
        Get defense formation suggestion.
        
        Based on opponent tendencies if available.
        """
        return self.opponent_tracker.get_defense_recommendation(down, distance)
    
    def get_situation_tip(self, down: int, distance: int, quarter: int, 
                          time_remaining: float, score_diff: int) -> str:
        """
        Get a situational tip for the player.
        """
        tips = []
        
        # Time-based tips
        if quarter == 2 and time_remaining < 2.0:
            tips.append("Two-minute warning! Consider quick passes to stop clock.")
        elif quarter == 4 and time_remaining < 5.0:
            if score_diff > 0:
                tips.append("Protecting lead - runs are safer to kill clock.")
            elif score_diff < 0:
                tips.append("Hurry up! Need to score fast.")
        
        # Down-based tips
        if down == 3:
            if distance >= 7:
                tips.append("Third & long - passing is usually better.")
            elif distance <= 2:
                tips.append("Short yardage - power running is often best.")
        
        if down == 4:
            tips.append("Fourth down - consider punting or going for it.")
        
        # Add play suggestion
        suggestions = self.suggest_offense_plays(down, distance, 1)
        if suggestions:
            best = suggestions[0]
            tips.append(f"Recommended: {best['play']} ({best['success_rate']:.0f}% success)")
        
        return " | ".join(tips) if tips else ""
    
    def explain_play(self, play_type: str, down: int, distance: int) -> str:
        """
        Explain why a play type is good or bad for current situation.
        """
        stats = self.team_analyzer.offense.analyze_play_type(play_type)
        
        if stats.valid_rolls == 0:
            return f"{play_type}: Not enough data to analyze."
        
        play_category = self.team_analyzer.offense.PLAY_TYPE_MAP.get(play_type, "unknown")
        
        explanation = f"{play_type}: {stats.success_rate:.0f}% success, {stats.avg_yards:.1f} avg yards"
        
        # Add context based on situation
        if down == 3 and distance >= 7:
            if play_category == "pass":
                explanation += " - Good for third and long!"
            elif play_category == "run":
                explanation += " - Risky on third and long."
        elif down == 3 and distance <= 2:
            if play_category == "run":
                explanation += " - Good for short yardage!"
            elif play_category == "pass":
                explanation += " - Risky on short yardage."
        
        return explanation
    
    def warn_danger(self, down: int, distance: int) -> str:
        """
        Warn about dangerous opponent tendencies.
        """
        tendency = self.opponent_tracker.get_tendency(down, distance)
        
        if tendency.total_plays < 3:
            return ""  # Not enough data
        
        warnings = []
        
        if tendency.pass_percentage > 70:
            warnings.append(f"Warning: Opponent passes {tendency.pass_percentage:.0f}% on this situation!")
        
        streak = self.opponent_tracker.get_streak()
        if streak:
            streak_name = "passing" if streak == PlayCategory.PASS else "running"
            warnings.append(f"Note: Opponent has been {streak_name} consecutively.")
        
        return " ".join(warnings)


def create_easy_mode_helper(team_chart: TeamChart) -> EasyModeHelper:
    """Create an easy mode helper for a team."""
    return EasyModeHelper(team_chart)
