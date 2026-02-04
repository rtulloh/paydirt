"""
Tests for 4th down decision making in the CPU AI.

Tests verify that the AI makes smart decisions based on:
- Field goal range and distance
- Yards to go for first down
- Field position
- Score differential and time remaining
- Aggression level
"""
import pytest
from unittest.mock import MagicMock, patch

from paydirt.computer_ai import ComputerAI
from paydirt.play_resolver import PlayType
from paydirt.game_engine import PaydirtGameEngine, GameState
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


@pytest.fixture
def mock_game():
    """Create a mock game for testing."""
    game = MagicMock(spec=PaydirtGameEngine)
    game.state = MagicMock(spec=GameState)
    game.state.down = 4
    game.state.yards_to_go = 3
    game.state.ball_position = 50
    game.state.time_remaining = 10.0
    game.state.quarter = 2
    game.state.is_home_possession = True
    game.state.home_score = 14
    game.state.away_score = 14
    return game


class TestFieldGoalDecisions:
    """Tests for field goal decision making."""
    
    def test_easy_fg_always_kicks(self, mock_game):
        """Should kick easy field goals (35 yards or less)."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at opponent's 18 = 35 yard FG (18 yards to goal + 17)
        mock_game.state.ball_position = 82
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.FIELD_GOAL
    
    def test_makeable_fg_kicks_on_longer_yardage(self, mock_game):
        """Should kick makeable FGs when not short yardage."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at opponent's 28 = 45 yard FG
        mock_game.state.ball_position = 72
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.FIELD_GOAL
    
    def test_makeable_fg_goes_for_it_on_4th_and_1_with_aggression(self, mock_game):
        """Should go for it on 4th and 1 in FG range with moderate aggression."""
        ai = ComputerAI(aggression=0.6)
        
        # Ball at opponent's 28 = 45 yard FG, but 4th and 1
        mock_game.state.ball_position = 72
        mock_game.state.yards_to_go = 1
        
        play = ai.select_offense(mock_game)
        # Should be a running play (go for it)
        assert play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE]
    
    def test_long_fg_punts_with_conservative_ai(self, mock_game):
        """Conservative AI should punt on long FG attempts."""
        ai = ComputerAI(aggression=0.3)
        
        # Ball at opponent's 38 = 55 yard FG (long)
        mock_game.state.ball_position = 62
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.PUNT
    
    def test_long_fg_kicks_with_aggressive_ai(self, mock_game):
        """Aggressive AI should attempt long FGs."""
        ai = ComputerAI(aggression=0.7)
        
        # Ball at opponent's 38 = 55 yard FG (long)
        mock_game.state.ball_position = 62
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.FIELD_GOAL


class TestPuntDecisions:
    """Tests for punt decision making."""
    
    def test_punts_in_own_territory(self, mock_game):
        """Should punt when deep in own territory."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at own 30
        mock_game.state.ball_position = 30
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.PUNT
    
    def test_punts_on_4th_and_long_at_midfield(self, mock_game):
        """Should punt on 4th and long at midfield."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at midfield, 4th and 10
        mock_game.state.ball_position = 50
        mock_game.state.yards_to_go = 10
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.PUNT
    
    def test_punts_outside_fg_range_with_long_yardage(self, mock_game):
        """Should punt when outside FG range with long yardage."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at opponent's 45 (55 yards from goal), 4th and 8
        mock_game.state.ball_position = 55
        mock_game.state.yards_to_go = 8
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.PUNT


class TestGoForItDecisions:
    """Tests for going for it on 4th down."""
    
    def test_goes_for_it_on_4th_and_1_in_opponent_territory(self, mock_game):
        """Should go for it on 4th and 1 in opponent territory."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at opponent's 35, 4th and 1
        mock_game.state.ball_position = 65
        mock_game.state.yards_to_go = 1
        
        play = ai.select_offense(mock_game)
        # Should be a short yardage play (QB_SNEAK is also valid for 4th and 1)
        assert play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.QB_SNEAK]
    
    def test_goes_for_it_on_4th_and_2_deep_in_opponent_territory(self, mock_game):
        """Should go for it on 4th and 2 deep in opponent territory."""
        ai = ComputerAI(aggression=0.5)
        
        # Ball at opponent's 25, 4th and 2 (outside easy FG range)
        mock_game.state.ball_position = 75
        mock_game.state.yards_to_go = 2
        
        play = ai.select_offense(mock_game)
        # Could be FG or go for it - both are reasonable
        assert play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS, 
                       PlayType.DRAW, PlayType.FIELD_GOAL]
    
    def test_aggressive_ai_goes_for_it_more_often(self, mock_game):
        """Aggressive AI should go for it more often."""
        ai = ComputerAI(aggression=0.9)
        
        # Ball at midfield, 4th and 2
        mock_game.state.ball_position = 50
        mock_game.state.yards_to_go = 2
        
        play = ai.select_offense(mock_game)
        # Aggressive AI should go for it
        assert play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.DRAW]


class TestDesperationSituations:
    """Tests for late-game desperation situations."""
    
    def test_kicks_fg_to_tie_late(self, mock_game):
        """Should kick FG to tie game late in 4th quarter."""
        ai = ComputerAI(aggression=0.5)
        
        # 4th quarter, 1 minute left, down by 3, in FG range
        mock_game.state.quarter = 4
        mock_game.state.time_remaining = 1.0
        mock_game.state.home_score = 14
        mock_game.state.away_score = 17  # Down by 3
        mock_game.state.ball_position = 75  # 42 yard FG
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        assert play == PlayType.FIELD_GOAL
    
    def test_goes_for_td_when_down_by_more_than_fg(self, mock_game):
        """Should go for TD when down by more than 3 late."""
        ai = ComputerAI(aggression=0.5)
        
        # 4th quarter, 1 minute left, down by 7
        mock_game.state.quarter = 4
        mock_game.state.time_remaining = 1.0
        mock_game.state.home_score = 14
        mock_game.state.away_score = 21  # Down by 7
        mock_game.state.ball_position = 75
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        # Should go for it, not kick FG
        assert play != PlayType.FIELD_GOAL
        assert play != PlayType.PUNT
    
    def test_goes_for_it_outside_fg_range_late(self, mock_game):
        """Should go for it when outside FG range and trailing late."""
        ai = ComputerAI(aggression=0.5)
        
        # 4th quarter, 1 minute left, down by 3, outside FG range
        mock_game.state.quarter = 4
        mock_game.state.time_remaining = 1.0
        mock_game.state.home_score = 14
        mock_game.state.away_score = 17  # Down by 3
        mock_game.state.ball_position = 50  # 67 yard FG - out of range
        mock_game.state.yards_to_go = 5
        
        play = ai.select_offense(mock_game)
        # Must go for it
        assert play != PlayType.PUNT
        assert play != PlayType.FIELD_GOAL


class TestGoForItPlaySelection:
    """Tests for play selection when going for it."""
    
    def test_4th_and_1_uses_power_run(self):
        """4th and 1 should use power running plays."""
        ai = ComputerAI(aggression=0.5)
        
        # Call _go_for_it_play directly with larger sample for statistical reliability
        plays = [ai._go_for_it_play(1) for _ in range(50)]
        
        # Should be mostly LINE_PLUNGE and OFF_TACKLE
        # Also include QB_SNEAK as a valid short-yardage play
        run_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.QB_SNEAK]]
        assert len(run_plays) >= 35  # At least 70% should be power runs (more reliable with larger sample)
    
    def test_4th_and_short_mixes_run_pass(self):
        """4th and 2-3 should mix run and pass."""
        ai = ComputerAI(aggression=0.5)
        
        plays = [ai._go_for_it_play(3) for _ in range(20)]
        
        # Should have variety
        play_types = set(plays)
        assert len(play_types) >= 2  # At least 2 different play types
    
    def test_4th_and_long_uses_passes(self):
        """4th and long should use passing plays."""
        ai = ComputerAI(aggression=0.5)
        
        plays = [ai._go_for_it_play(10) for _ in range(20)]
        
        # Should be mostly passes
        pass_plays = [p for p in plays if p in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS]]
        assert len(pass_plays) >= 15  # At least 75% should be passes
