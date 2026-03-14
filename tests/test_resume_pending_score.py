"""
Regression tests for resuming a game with a pending score.

Verifies that after loading a save file with a pending touchdown or safety,
the correct team kicks off. Specifically tests the bug where a manual
possession flip caused the non-scoring team to kick off instead of the
scoring team.
"""
import os
import json
import tempfile
import pytest

from paydirt.save_game import save_game, load_game
from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import load_team_chart


@pytest.fixture
def game():
    """Create a game engine with real team charts (away=Jets, home=Bills)."""
    home_chart = load_team_chart("seasons/1972/Bills")
    away_chart = load_team_chart("seasons/1972/Jets")
    return PaydirtGameEngine(home_chart, away_chart)


@pytest.fixture
def temp_save_file():
    """Create a temporary save file path."""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestResumePendingTouchdown:
    """Tests for resuming a game with a pending touchdown."""

    def test_load_detects_pending_touchdown(self, game, temp_save_file):
        """ball_position >= 100 should be detected as pending touchdown."""
        game.state.ball_position = 100
        game.state.is_home_possession = True
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        _, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "touchdown"

    def test_home_team_scores_td_then_home_kicks(self, game, temp_save_file):
        """When home team has a pending TD, home should kick off after PAT."""
        game.state.ball_position = 100
        game.state.is_home_possession = True
        game.state.home_score = 17
        game.state.away_score = 35
        game.state.quarter = 4
        game.state.time_remaining = 10.0
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        loaded_game, human_is_away, human_is_home, pending_score = load_game(temp_save_file)
        assert pending_score == "touchdown"

        # Simulate the resume logic from interactive_game.py
        scoring_team_is_home = loaded_game.state.is_home_possession  # True (home/Bills)
        assert scoring_team_is_home is True

        # Add TD + PAT (mirroring resume_game)
        loaded_game.state.home_score += 6
        loaded_game.attempt_extra_point()

        # The fix: kicking_home = scoring_team_is_home (not flipped possession)
        kicking_home = scoring_team_is_home
        assert kicking_home is True, "Home team scored, home team should kick"

        # Execute kickoff
        loaded_game.kickoff(kicking_home=kicking_home)

        # After kickoff, away team (Jets) should have the ball
        assert loaded_game.state.is_home_possession is False, \
            "After home team scores and kicks, away team should receive"

    def test_away_team_scores_td_then_away_kicks(self, game, temp_save_file):
        """When away team has a pending TD, away should kick off after PAT."""
        game.state.ball_position = 100
        game.state.is_home_possession = False  # Away team (Jets) scored
        game.state.away_score = 28
        game.state.home_score = 10
        game.state.quarter = 3
        game.state.time_remaining = 5.0
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        loaded_game, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "touchdown"

        scoring_team_is_home = loaded_game.state.is_home_possession  # False (away/Jets)
        assert scoring_team_is_home is False

        loaded_game.state.away_score += 6
        loaded_game.attempt_extra_point()

        kicking_home = scoring_team_is_home
        assert kicking_home is False, "Away team scored, away team should kick"

        loaded_game.kickoff(kicking_home=kicking_home)

        # After kickoff, home team (Bills) should have the ball
        assert loaded_game.state.is_home_possession is True, \
            "After away team scores and kicks, home team should receive"

    def test_no_consecutive_possessions_after_pending_td(self, game, temp_save_file):
        """Scoring team must not get the ball back after their own pending TD.

        This is the exact bug from the save file: BUF (home) scores a TD,
        but Jets (away/human) were asked to kick instead of BUF.
        """
        game.state.ball_position = 100
        game.state.is_home_possession = True  # BUF (home) scored
        game.state.home_score = 17
        game.state.away_score = 35
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        loaded_game, _, _, pending_score = load_game(temp_save_file)

        # Reproduce the resume flow
        scoring_team_is_home = loaded_game.state.is_home_possession
        loaded_game.state.home_score += 6
        loaded_game.attempt_extra_point()

        # Use scoring_team_is_home (the fix), NOT flipped possession
        kicking_home = scoring_team_is_home
        loaded_game.kickoff(kicking_home=kicking_home)

        # BUF scored → BUF kicks → Jets receive
        assert loaded_game.state.is_home_possession is False, \
            "BUF scored but got the ball back (consecutive possessions bug)"


class TestResumePendingSafety:
    """Tests for resuming a game with a pending safety."""

    def test_load_detects_pending_safety(self, game, temp_save_file):
        """ball_position <= 0 should be detected as pending safety."""
        game.state.ball_position = 0
        save_game(game, filepath=temp_save_file)

        _, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "safety"

    def test_home_offense_gives_up_safety_then_home_kicks(self, game, temp_save_file):
        """When home team gives up a safety, home (offense) does the free kick."""
        game.state.ball_position = 0
        game.state.is_home_possession = True  # Home was on offense, gave up safety
        game.state.home_score = 10
        game.state.away_score = 7
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        loaded_game, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "safety"

        # Safety: defense (away) scores 2 points
        loaded_game.state.away_score += 2

        # The team that gave up the safety (home/offense) kicks the free kick
        kicking_home = loaded_game.state.is_home_possession  # True (home was offense)
        assert kicking_home is True, "Home gave up safety, home should kick free kick"

        loaded_game.safety_free_kick()

        # Away team should receive the free kick
        assert loaded_game.state.is_home_possession is False, \
            "After home gives up safety and kicks, away should receive"

    def test_away_offense_gives_up_safety_then_away_kicks(self, game, temp_save_file):
        """When away team gives up a safety, away (offense) does the free kick."""
        game.state.ball_position = 0
        game.state.is_home_possession = False  # Away was on offense, gave up safety
        game.state.home_score = 3
        game.state.away_score = 14
        save_game(game, filepath=temp_save_file, human_is_away=True, human_is_home=False)

        loaded_game, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "safety"

        # Safety: defense (home) scores 2 points
        loaded_game.state.home_score += 2

        # The team that gave up the safety (away/offense) kicks
        kicking_home = loaded_game.state.is_home_possession  # False (away was offense)
        assert kicking_home is False, "Away gave up safety, away should kick free kick"

        loaded_game.safety_free_kick()

        # Home team should receive the free kick
        assert loaded_game.state.is_home_possession is True, \
            "After away gives up safety and kicks, home should receive"


class TestResumeWithActualSaveFile:
    """Test using the actual save file format from the reported bug."""

    def test_pending_td_from_save_data(self, temp_save_file):
        """Reproduce the exact bug: Jets @ Bills, BUF has pending TD at ball_position=100."""
        save_data = {
            "version": 1,
            "saved_at": "2026-03-13T19:55:46.865616",
            "away_team_path": "seasons/1972/Jets",
            "home_team_path": "seasons/1972/Bills",
            "human_is_away": True,
            "human_is_home": False,
            "home_score": 17,
            "away_score": 35,
            "quarter": 4,
            "time_remaining": 10.78,
            "is_home_possession": True,
            "ball_position": 100,
            "down": 2,
            "yards_to_go": 3,
            "game_over": False,
            "home_timeouts": 3,
            "away_timeouts": 3,
            "two_minute_warning_called": False,
            "is_overtime": False,
            "ot_period": 0,
            "ot_first_possession_complete": False,
            "ot_first_possession_scored": False,
            "ot_first_possession_was_td": False,
            "ot_coin_toss_winner_is_home": False,
            "is_playoff": False,
            "untimed_down_pending": False,
            "home_stats": {"first_downs": 0, "total_yards": 0, "rushing_yards": 0,
                           "passing_yards": 0, "turnovers": 0, "penalties": 0,
                           "penalty_yards": 0, "sacks": 0, "sack_yards": 0,
                           "interceptions_thrown": 0, "fumbles_lost": 0},
            "away_stats": {"first_downs": 0, "total_yards": 0, "rushing_yards": 0,
                           "passing_yards": 0, "turnovers": 0, "penalties": 0,
                           "penalty_yards": 0, "sacks": 0, "sack_yards": 0,
                           "interceptions_thrown": 0, "fumbles_lost": 0},
            "scoring_plays": [],
        }
        with open(temp_save_file, 'w') as f:
            json.dump(save_data, f)

        loaded_game, human_is_away, human_is_home, pending_score = load_game(temp_save_file)

        assert pending_score == "touchdown"
        assert human_is_away is True
        assert human_is_home is False

        # BUF (home) has possession at ball_position=100 → BUF scored
        scoring_team_is_home = loaded_game.state.is_home_possession
        assert scoring_team_is_home is True

        # Process TD + PAT
        loaded_game.state.home_score += 6
        loaded_game.attempt_extra_point()

        # Scoring team kicks
        kicking_home = scoring_team_is_home  # True → BUF kicks
        loaded_game.kickoff(kicking_home=kicking_home)

        # Jets (away/human) should receive, NOT kick
        assert loaded_game.state.is_home_possession is False, \
            "BUG REGRESSION: Jets (human) kicked instead of receiving after BUF TD"

        # Human is away, so human should NOT be kicking
        is_human_kicking = (kicking_home == human_is_home)
        assert is_human_kicking is False, \
            "BUG REGRESSION: Human was asked to kick after opponent scored"
