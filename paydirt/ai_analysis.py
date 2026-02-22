"""
AI Analysis module for studying team charts and opponent tendencies.

This module provides utilities for analyzing offense and defense charts to identify
best plays for different situations, ignoring penalties and turnovers.
"""
from dataclasses import dataclass, field
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
        """Check if a play outcome is valid (not penalty, fumble, or interception)."""
        return not (outcome.is_penalty or outcome.is_fumble or outcome.is_interception)
    
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
