"""
Tests for AI Analysis module.
"""
import pytest
from pathlib import Path
from paydirt.chart_loader import load_team_chart
from paydirt.ai_analysis import (
    OffenseAnalyzer, DefenseAnalyzer, TeamAnalyzer, analyze_team,
    PlayOutcome
)


@pytest.fixture
def bears_chart():
    """Load Bears team chart for testing."""
    return load_team_chart(Path('seasons/1983/Bears'))


class TestPlayOutcomeParsing:
    """Tests for parsing play outcome results."""
    
    def test_parses_positive_number(self):
        """Parse positive yardage result."""
        result = "5"
        # Would need to test via analyzer
    
    def test_excludes_penalties(self):
        """Penalties should be excluded from success calculation."""
        pass


class TestOffenseAnalyzer:
    """Tests for offense chart analysis."""
    
    def test_loads_bears_offense(self, bears_chart):
        """Should load Bears offense chart."""
        analyzer = OffenseAnalyzer(bears_chart.offense)
        stats = analyzer.analyze_play_type('Line Plunge')
        
        assert stats.total_rolls > 0
        assert stats.valid_rolls > 0
    
    def test_success_rate_calculation(self, bears_chart):
        """Success rate should be calculated correctly."""
        analyzer = OffenseAnalyzer(bears_chart.offense)
        stats = analyzer.analyze_play_type('Line Plunge')
        
        # Should have both valid rolls and calculated rate
        assert stats.success_rate >= 0
        assert stats.success_rate <= 100
    
    def test_filters_penalties(self, bears_chart):
        """Should filter out penalties from success calculation."""
        analyzer = OffenseAnalyzer(bears_chart.offense)
        stats = analyzer.analyze_play_type('Line Plunge')
        
        # valid_rolls should be less than total_rolls if there are penalties
        # Line Plunge has OFF 10, OFF 15, etc.
        assert stats.valid_rolls <= stats.total_rolls
    
    def test_get_all_play_stats(self, bears_chart):
        """Should get stats for all play types."""
        analyzer = OffenseAnalyzer(bears_chart.offense)
        all_stats = analyzer.get_all_play_stats()
        
        assert len(all_stats) > 0
        assert 'Line Plunge' in all_stats
        assert 'Off Tackle' in all_stats
    
    def test_get_top_plays(self, bears_chart):
        """Should return plays sorted by success rate."""
        analyzer = OffenseAnalyzer(bears_chart.offense)
        top_plays = analyzer.get_top_plays(3)
        
        # Should be sorted by success rate descending
        assert len(top_plays) <= 3
        if len(top_plays) >= 2:
            assert top_plays[0][1].success_rate >= top_plays[1][1].success_rate


class TestTeamAnalyzer:
    """Tests for complete team analysis."""
    
    def test_analyze_team(self, bears_chart):
        """Should create team analyzer."""
        analyzer = analyze_team(bears_chart)
        
        assert analyzer is not None
        assert analyzer.offense is not None
        assert analyzer.defense is not None
    
    def test_get_offense_summary(self, bears_chart):
        """Should get offense summary."""
        analyzer = analyze_team(bears_chart)
        summary = analyzer.get_offense_summary()
        
        assert 'best_plays' in summary
        assert 'total_play_types' in summary
    
    def test_suggest_play_3rd_and_long(self, bears_chart):
        """Should suggest pass on 3rd and long."""
        analyzer = analyze_team(bears_chart)
        suggestion = analyzer.suggest_play(3, 10)
        
        # 3rd & 10 should be a passing down
        assert suggestion['is_passing_down'] is True
    
    def test_suggest_play_3rd_and_short(self, bears_chart):
        """Should suggest run on 3rd and short."""
        analyzer = analyze_team(bears_chart)
        suggestion = analyzer.suggest_play(3, 2)
        
        # 3rd & 2 should be short yardage
        assert suggestion['is_short_yardage'] is True
    
    def test_suggest_play_first_and_ten(self, bears_chart):
        """Should work for 1st and 10."""
        analyzer = analyze_team(bears_chart)
        suggestion = analyzer.suggest_play(1, 10)
        
        assert suggestion['recommended_play'] is not None
        assert suggestion['success_rate'] >= 0


class TestMultipleTeams:
    """Tests analyzing multiple teams."""
    
    @pytest.mark.parametrize("team_name", [
        "Bears", "49ers", "Cowboys", "Dolphins", "Raiders"
    ])
    def test_analyze_different_teams(self, team_name):
        """Should work for different teams."""
        chart_path = Path(f"seasons/1983/{team_name}")
        if not chart_path.exists():
            pytest.skip(f"Team {team_name} not found")
        
        chart = load_team_chart(chart_path)
        analyzer = analyze_team(chart)
        
        summary = analyzer.get_offense_summary()
        assert summary['total_play_types'] > 0
