"""
Tests for team strength analysis used in offensive play recommendations.

The analyze_team_strength function examines a team's offensive chart to determine
if they favor running or passing, which influences the default play suggestion.
"""

from paydirt.chart_loader import OffenseChart
from paydirt.interactive_game import analyze_team_strength


class TestAnalyzeTeamStrength:
    """Tests for the analyze_team_strength function."""
    
    def test_run_heavy_team(self):
        """Team with strong running chart should return 'run'."""
        offense = OffenseChart(
            # Strong running plays - lots of positive yardage
            line_plunge={10: "3", 11: "4", 12: "5", 13: "B", 14: "6", 15: "3"},
            off_tackle={10: "5", 11: "6", 12: "B", 13: "7", 14: "4", 15: "5"},
            end_run={10: "6", 11: "7", 12: "B", 13: "8", 14: "5", 15: "6"},
            draw={10: "4", 11: "5", 12: "6", 13: "B", 14: "3", 15: "4"},
            # Weak passing plays - lots of negatives and turnovers
            screen={10: "-2", 11: "INT 5", 12: "0", 13: "SK", 14: "-1", 15: "2"},
            short_pass={10: "INT 10", 11: "-3", 12: "SK", 13: "0", 14: "2", 15: "INT 5"},
            medium_pass={10: "SK", 11: "INT 15", 12: "-2", 13: "0", 14: "3", 15: "SK"},
            long_pass={10: "INT 20", 11: "SK", 12: "INT 10", 13: "-5", 14: "0", 15: "INT 5"},
            te_short_long={10: "INT 5", 11: "SK", 12: "0", 13: "-2", 14: "2", 15: "INT 10"},
        )
        
        result = analyze_team_strength(offense)
        assert result == 'run', f"Expected 'run' for run-heavy team, got '{result}'"
    
    def test_pass_heavy_team(self):
        """Team with strong passing chart should return 'pass'."""
        offense = OffenseChart(
            # Weak running plays
            line_plunge={10: "-2", 11: "F + 3", 12: "0", 13: "1", 14: "-1", 15: "F - 2"},
            off_tackle={10: "F + 2", 11: "-3", 12: "0", 13: "1", 14: "F - 1", 15: "-2"},
            end_run={10: "-1", 11: "F + 5", 12: "0", 13: "2", 14: "-2", 15: "F - 3"},
            draw={10: "F + 1", 11: "-2", 12: "0", 13: "1", 14: "F - 2", 15: "-1"},
            # Strong passing plays - lots of positive yardage
            screen={10: "5", 11: "8", 12: "B", 13: "10", 14: "6", 15: "7"},
            short_pass={10: "8", 11: "10", 12: "B", 13: "12", 14: "7", 15: "9"},
            medium_pass={10: "12", 11: "15", 12: "B", 13: "18", 14: "10", 15: "14"},
            long_pass={10: "20", 11: "25", 12: "B", 13: "30", 14: "18", 15: "22"},
            te_short_long={10: "10", 11: "12", 12: "B", 13: "15", 14: "8", 15: "11"},
        )
        
        result = analyze_team_strength(offense)
        assert result == 'pass', f"Expected 'pass' for pass-heavy team, got '{result}'"
    
    def test_balanced_team(self):
        """Team with similar run/pass effectiveness should return 'balanced'."""
        offense = OffenseChart(
            # Moderate running plays
            line_plunge={10: "3", 11: "4", 12: "2", 13: "5", 14: "3", 15: "4"},
            off_tackle={10: "4", 11: "5", 12: "3", 13: "6", 14: "4", 15: "5"},
            end_run={10: "5", 11: "6", 12: "4", 13: "7", 14: "5", 15: "6"},
            draw={10: "3", 11: "4", 12: "2", 13: "5", 14: "3", 15: "4"},
            # Moderate passing plays (similar effectiveness)
            screen={10: "4", 11: "5", 12: "3", 13: "6", 14: "4", 15: "5"},
            short_pass={10: "5", 11: "6", 12: "4", 13: "7", 14: "5", 15: "6"},
            medium_pass={10: "6", 11: "7", 12: "5", 13: "8", 14: "6", 15: "7"},
            long_pass={10: "8", 11: "10", 12: "6", 13: "12", 14: "8", 15: "10"},
            te_short_long={10: "5", 11: "6", 12: "4", 13: "7", 14: "5", 15: "6"},
        )
        
        result = analyze_team_strength(offense)
        assert result == 'balanced', f"Expected 'balanced' for balanced team, got '{result}'"
    
    def test_breakaways_count_extra(self):
        """Breakaway results (B) should count as extra positive."""
        offense = OffenseChart(
            # Running plays with breakaways
            line_plunge={10: "B", 11: "B", 12: "B", 13: "B", 14: "B", 15: "B"},
            off_tackle={10: "B", 11: "B", 12: "B", 13: "B", 14: "B", 15: "B"},
            end_run={10: "B", 11: "B", 12: "B", 13: "B", 14: "B", 15: "B"},
            draw={10: "B", 11: "B", 12: "B", 13: "B", 14: "B", 15: "B"},
            # Passing plays with no breakaways
            screen={10: "5", 11: "5", 12: "5", 13: "5", 14: "5", 15: "5"},
            short_pass={10: "5", 11: "5", 12: "5", 13: "5", 14: "5", 15: "5"},
            medium_pass={10: "5", 11: "5", 12: "5", 13: "5", 14: "5", 15: "5"},
            long_pass={10: "5", 11: "5", 12: "5", 13: "5", 14: "5", 15: "5"},
            te_short_long={10: "5", 11: "5", 12: "5", 13: "5", 14: "5", 15: "5"},
        )
        
        result = analyze_team_strength(offense)
        # Breakaways count double, so run should dominate
        assert result == 'run', f"Expected 'run' for team with running breakaways, got '{result}'"
    
    def test_turnovers_not_counted_as_positive(self):
        """Fumbles and interceptions should not count as positive results."""
        offense = OffenseChart(
            # Running plays with fumbles
            line_plunge={10: "F + 3", 11: "F - 2", 12: "F + 5", 13: "F - 1", 14: "F + 2", 15: "F - 3"},
            off_tackle={10: "F + 2", 11: "F - 1", 12: "F + 4", 13: "F - 2", 14: "F + 3", 15: "F - 1"},
            end_run={10: "F + 5", 11: "F - 3", 12: "F + 6", 13: "F - 2", 14: "F + 4", 15: "F - 1"},
            draw={10: "F + 1", 11: "F - 2", 12: "F + 3", 13: "F - 1", 14: "F + 2", 15: "F - 3"},
            # Passing plays with positive yardage
            screen={10: "5", 11: "6", 12: "7", 13: "8", 14: "5", 15: "6"},
            short_pass={10: "6", 11: "7", 12: "8", 13: "9", 14: "6", 15: "7"},
            medium_pass={10: "8", 11: "9", 12: "10", 13: "11", 14: "8", 15: "9"},
            long_pass={10: "12", 11: "14", 12: "16", 13: "18", 14: "12", 15: "14"},
            te_short_long={10: "7", 11: "8", 12: "9", 13: "10", 14: "7", 15: "8"},
        )
        
        result = analyze_team_strength(offense)
        # Fumbles don't count, so pass should dominate
        assert result == 'pass', f"Expected 'pass' when run plays are all fumbles, got '{result}'"
    
    def test_variable_yardage_counts_as_positive(self):
        """Variable yardage results (DS, T1, etc.) should count as positive."""
        offense = OffenseChart(
            # Running plays with variable yardage
            line_plunge={10: "DS", 11: "T1", 12: "T2", 13: "DS", 14: "T1", 15: "DS"},
            off_tackle={10: "T1", 11: "DS", 12: "T2", 13: "T1", 14: "DS", 15: "T1"},
            end_run={10: "DS", 11: "T2", 12: "T1", 13: "DS", 14: "T2", 15: "DS"},
            draw={10: "T1", 11: "DS", 12: "T1", 13: "T2", 14: "DS", 15: "T1"},
            # Passing plays with negative/zero
            screen={10: "0", 11: "-1", 12: "0", 13: "-2", 14: "0", 15: "-1"},
            short_pass={10: "-1", 11: "0", 12: "-2", 13: "0", 14: "-1", 15: "0"},
            medium_pass={10: "0", 11: "-2", 12: "0", 13: "-1", 14: "0", 15: "-2"},
            long_pass={10: "-2", 11: "0", 12: "-1", 13: "0", 14: "-2", 15: "0"},
            te_short_long={10: "0", 11: "-1", 12: "0", 13: "-2", 14: "0", 15: "-1"},
        )
        
        result = analyze_team_strength(offense)
        assert result == 'run', f"Expected 'run' for team with variable yardage runs, got '{result}'"
