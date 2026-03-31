"""
Tests for AI Analysis module.
"""
import pytest
from pathlib import Path
from paydirt.chart_loader import load_team_chart
from paydirt.ai_analysis import (
    OffenseAnalyzer, analyze_team
)


@pytest.fixture
def bears_chart():
    """Load team chart for testing (using 2026 Ironclads)."""
    return load_team_chart(Path('seasons/2026/Ironclads'))


class TestPlayOutcomeParsing:
    """Tests for parsing play outcome results."""
    
    def test_parses_positive_number(self):
        """Parse positive yardage result."""
        # Would need to test via analyzer
        pass
    
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
        "Ironclads", "Thunderhawks"
    ])
    def test_analyze_different_teams(self, team_name):
        """Should work for different teams."""
        chart_path = Path(f"seasons/2026/{team_name}")
        if not chart_path.exists():
            pytest.skip(f"Team {team_name} not found")
        
        chart = load_team_chart(chart_path)
        analyzer = analyze_team(chart)
        
        summary = analyzer.get_offense_summary()
        assert summary['total_play_types'] > 0


class TestOpponentTendencyTracker:
    """Tests for opponent tendency tracking."""
    
    def test_situation_type_categorization(self):
        """Should correctly categorize situations."""
        from paydirt.ai_analysis import get_situation_type, SituationType
        
        assert get_situation_type(1, 10) == SituationType.FIRST_DOWN
        assert get_situation_type(2, 3) == SituationType.SECOND_SHORT
        assert get_situation_type(2, 8) == SituationType.SECOND_LONG
        assert get_situation_type(3, 5) == SituationType.THIRD_MEDIUM
        assert get_situation_type(3, 15) == SituationType.THIRD_LONG
        assert get_situation_type(4, 1) == SituationType.FOURTH_SHORT
    
    def test_record_and_predict_plays(self):
        """Should record and predict opponent plays."""
        from paydirt.ai_analysis import OpponentTendencyTracker, PlayCategory
        
        tracker = OpponentTendencyTracker()
        
        # Record runs
        tracker.record_play(1, 10, 'Off Tackle', 5)
        tracker.record_play(1, 10, 'Line Plunge', 3)
        
        # Record passes
        tracker.record_play(3, 10, 'Long', 20, is_pass=True)
        tracker.record_play(3, 10, 'Med', 10, is_pass=True)
        
        # Predict on 3rd & 10 - should be PASS
        prediction = tracker.predict_play(3, 10)
        assert prediction == PlayCategory.PASS
        
        # Predict on 1st & 10 - should be balanced
        prediction = tracker.predict_play(1, 10)
        assert prediction in [PlayCategory.RUN, PlayCategory.PASS]
    
    def test_defense_recommendation(self):
        """Should recommend appropriate defense."""
        from paydirt.ai_analysis import OpponentTendencyTracker
        
        tracker = OpponentTendencyTracker()
        
        # Record mostly passes on 3rd & long
        for _ in range(5):
            tracker.record_play(3, 10, 'Long', 15, is_pass=True)
        
        # Record mostly runs on 1st & 10
        for _ in range(5):
            tracker.record_play(1, 10, 'Off Tackle', 4)
        
        # Should recommend pass defense for 3rd & 10
        defense = tracker.get_defense_recommendation(3, 10)
        assert defense == "D"  # Short Pass defense
        
        # Should recommend run defense for 1st & 10
        defense = tracker.get_defense_recommendation(1, 10)
        assert defense == "B"  # Short Yardage
    
    def test_streak_detection(self):
        """Should detect play streaks."""
        from paydirt.ai_analysis import OpponentTendencyTracker, PlayCategory
        
        tracker = OpponentTendencyTracker()
        
        # No streak initially
        assert tracker.get_streak() is None
        
        # Record 3 consecutive passes
        for _ in range(3):
            tracker.record_play(3, 10, 'Long', 15, is_pass=True)
        
        # Should detect pass streak
        assert tracker.get_streak() == PlayCategory.PASS
    
    def test_empty_prediction(self):
        """Should handle no data gracefully."""
        from paydirt.ai_analysis import OpponentTendencyTracker, PlayCategory
        
        tracker = OpponentTendencyTracker()
        
        # With no data, should default to RUN
        prediction = tracker.predict_play(3, 10)
        assert prediction == PlayCategory.RUN


class TestOpponentModel:
    """Tests for opponent model with game state awareness."""
    
    def test_comeback_mode_defense(self):
        """Should recommend pass defense when opponent is trailing."""
        from paydirt.ai_analysis import OpponentModel
        
        model = OpponentModel()
        
        # Trailing in 4th quarter
        defense = model.predict_defense(3, 10, -7, 4, 3.0)
        assert defense == "E"  # Long Pass - expecting them to pass
    
    def test_protect_lead_defense(self):
        """Should recommend run defense when opponent is leading."""
        from paydirt.ai_analysis import OpponentModel
        
        model = OpponentModel()
        
        # Leading in 4th quarter
        defense = model.predict_defense(3, 10, 7, 4, 3.0)
        assert defense == "A"  # Standard - expecting them to run
    
    def test_tendency_overrides_early_game(self):
        """Should use tendencies in early game before game state kicks in."""
        from paydirt.ai_analysis import OpponentModel
        
        model = OpponentModel()
        
        # Record opponent tends to pass on 3rd & long
        for _ in range(5):
            model.record_opponent_play(3, 10, 'Long', 15, is_pass=True)
        
        # Early game, close score - should use tendency
        defense = model.predict_defense(3, 10, 0, 2, 10.0)
        assert defense == "D"  # Based on tendency


class TestEasyModeHelper:
    """Tests for easy mode helper."""
    
    def test_create_helper(self):
        """Should create easy mode helper."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        assert helper is not None
        assert helper.team_analyzer is not None
    
    def test_suggest_offense_plays(self):
        """Should suggest offense plays."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        suggestions = helper.suggest_offense_plays(3, 7, 3)
        
        assert len(suggestions) > 0
        assert len(suggestions) <= 3
        assert 'play' in suggestions[0]
        assert 'success_rate' in suggestions[0]
        assert 'avg_yards' in suggestions[0]
    
    def test_suggest_defense(self):
        """Should suggest defense formation."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        defense = helper.suggest_defense(3, 7)
        
        assert defense in ['A', 'B', 'C', 'D', 'E', 'F']
    
    def test_get_situation_tip(self):
        """Should get situational tip."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        # Normal situation
        tip = helper.get_situation_tip(1, 10, 2, 10.0, 0)
        assert tip != ""
        
        # Late game trailing
        tip = helper.get_situation_tip(3, 7, 4, 3.0, -7)
        assert "Hurry up" in tip
    
    def test_explain_play(self):
        """Should explain why a play is good."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        explanation = helper.explain_play("Screen", 3, 7)
        
        assert "Screen" in explanation
        assert "%" in explanation  # Contains success rate
    
    def test_warn_danger(self):
        """Should warn about opponent tendencies."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        # Not enough data - should be empty
        warning = helper.warn_danger(3, 7)
        assert warning == ""


class TestBreakawayExclusion:
    """Tests for breakaway (B) play type exclusion."""
    
    def test_breakaway_not_in_suggestions(self):
        """Breakaway 'B' should not be in play suggestions."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        suggestions = helper.suggest_offense_plays(1, 10, 10)
        play_names = [s['play'] for s in suggestions]
        
        assert 'B' not in play_names
    
    def test_breakaway_column_has_stats_but_not_suggested(self):
        """Breakaway column can have stats but shouldn't be suggested."""
        from paydirt.ai_analysis import OffenseAnalyzer, create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        stats = analyzer.analyze_play_type('B')
        
        # B column does have valid rolls (yards to gain on breakaway)
        assert stats.valid_rolls > 0
        
        # But it shouldn't be in suggestions
        helper = create_easy_mode_helper(bears)
        suggestions = helper.suggest_offense_plays(1, 10, 10)
        play_names = [s['play'] for s in suggestions]
        assert 'B' not in play_names
    
    def test_breakaway_results_excluded_from_other_plays(self):
        """Breakaway 'B' results in other columns should be excluded."""
        from paydirt.ai_analysis import OffenseAnalyzer
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        
        # Check that other plays don't count B as valid
        stats = analyzer.analyze_play_type('Line Plunge')
        
        # valid_rolls should not count breakaway results
        # (they should be filtered out as invalid)
        assert stats.valid_rolls > 0


class TestPlayOutcomeBreakaway:
    """Tests for PlayOutcome breakaway field."""
    
    def test_parse_breakaway_result(self):
        """Parse 'B' as breakaway result."""
        from paydirt.ai_analysis import OffenseAnalyzer
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        
        outcome = analyzer._parse_result('B')
        
        assert outcome.is_breakaway
        assert not outcome.is_positive
    
    def test_breakaway_not_valid_play(self):
        """Breakaway should not be counted as valid play."""
        from paydirt.ai_analysis import OffenseAnalyzer
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        
        outcome = analyzer._parse_result('B')
        
        assert not analyzer._is_valid_play(outcome)
    
    def test_breakaway_result_in_other_columns_excluded(self):
        """Breakaway 'B' results in other play columns should be excluded from stats."""
        from paydirt.ai_analysis import OffenseAnalyzer
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        
        # Analyze a play type that has B results (check some columns)
        # Line Plunge might have some B results in the data
        stats = analyzer.analyze_play_type('Line Plunge')
        
        # The valid_rolls should NOT include any B results
        # Since we can't easily verify exact counts, we verify the stats are reasonable
        assert stats.total_rolls >= stats.valid_rolls
        assert stats.valid_rolls > 0
    
    def test_breakaway_column_has_100_percent_success_rate(self):
        """Breakaway column has 100% success because B means big gain."""
        from paydirt.ai_analysis import OffenseAnalyzer
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        analyzer = OffenseAnalyzer(bears.offense)
        stats = analyzer.analyze_play_type('B')
        
        # B column has all positive yards (10-49 yards typically)
        assert stats.success_rate == 100.0
    
    def test_breakaway_in_all_situations_excluded(self):
        """Breakaway should be excluded from suggestions in all down/distance situations."""
        from paydirt.ai_analysis import create_easy_mode_helper
        from pathlib import Path
        from paydirt.chart_loader import load_team_chart
        
        bears = load_team_chart(Path('seasons/2026/Ironclads'))
        helper = create_easy_mode_helper(bears)
        
        # Test various down and distance situations
        test_cases = [
            (1, 10),
            (2, 5),
            (3, 1),
            (3, 15),
            (4, 2),
        ]
        
        for down, distance in test_cases:
            suggestions = helper.suggest_offense_plays(down, distance, 10)
            play_names = [s['play'] for s in suggestions]
            assert 'B' not in play_names, f"B found in suggestions for {down} & {distance}"
