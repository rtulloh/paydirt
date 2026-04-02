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
from pathlib import Path
from unittest.mock import patch
import pytest

from paydirt.save_game import save_game, load_game
from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import load_team_chart


# Check if 1972 season data exists for skipif markers
_seasons_dir = Path(__file__).parent.parent / "seasons"
_has_1972_jets = (_seasons_dir / "1972" / "Jets").exists()
requires_1972_jets = pytest.mark.skipif(
    not _has_1972_jets, reason="1972/Jets season data not available"
)


@pytest.fixture
def game():
    """Create a game engine with real 2026 team charts (save/load needs valid paths)."""
    home_chart = load_team_chart("seasons/2026/Ironclads")
    away_chart = load_team_chart("seasons/2026/Thunderhawks")
    return PaydirtGameEngine(home_chart, away_chart)


@pytest.fixture
def temp_save_file():
    """Create a temporary save file path."""
    fd, path = tempfile.mkstemp(suffix=".json")
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
        assert loaded_game.state.is_home_possession is False, (
            "After home team scores and kicks, away team should receive"
        )

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
        assert loaded_game.state.is_home_possession is True, (
            "After away team scores and kicks, home team should receive"
        )

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
        assert loaded_game.state.is_home_possession is False, (
            "BUF scored but got the ball back (consecutive possessions bug)"
        )


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
        assert loaded_game.state.is_home_possession is False, (
            "After home gives up safety and kicks, away should receive"
        )

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
        assert loaded_game.state.is_home_possession is True, (
            "After away gives up safety and kicks, home should receive"
        )


class TestResumeWithActualSaveFile:
    """Test using the actual save file format from the reported bug."""

    def test_pending_td_from_save_data(self, temp_save_file):
        """Reproduce the exact bug: away @ home, home has pending TD at ball_position=100."""
        save_data = {
            "version": 1,
            "saved_at": "2026-03-13T19:55:46.865616",
            "away_team_path": "seasons/2026/Thunderhawks",
            "home_team_path": "seasons/2026/Ironclads",
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
            "home_stats": {
                "first_downs": 0,
                "total_yards": 0,
                "rushing_yards": 0,
                "passing_yards": 0,
                "turnovers": 0,
                "penalties": 0,
                "penalty_yards": 0,
                "sacks": 0,
                "sack_yards": 0,
                "interceptions_thrown": 0,
                "fumbles_lost": 0,
            },
            "away_stats": {
                "first_downs": 0,
                "total_yards": 0,
                "rushing_yards": 0,
                "passing_yards": 0,
                "turnovers": 0,
                "penalties": 0,
                "penalty_yards": 0,
                "sacks": 0,
                "sack_yards": 0,
                "interceptions_thrown": 0,
                "fumbles_lost": 0,
            },
            "scoring_plays": [],
        }
        with open(temp_save_file, "w") as f:
            json.dump(save_data, f)

        loaded_game, human_is_away, human_is_home, pending_score = load_game(temp_save_file)

        assert pending_score == "touchdown"
        assert human_is_away is True
        assert human_is_home is False

        # Home (Ironclads) has possession at ball_position=100 → home scored
        scoring_team_is_home = loaded_game.state.is_home_possession
        assert scoring_team_is_home is True

        # Process TD + PAT
        loaded_game.state.home_score += 6
        loaded_game.attempt_extra_point()

        # Scoring team kicks
        kicking_home = scoring_team_is_home  # True → home kicks
        loaded_game.kickoff(kicking_home=kicking_home)

        # Away (Thunderhawks/human) should receive, NOT kick
        assert loaded_game.state.is_home_possession is False, (
            "BUG REGRESSION: Jets (human) kicked instead of receiving after BUF TD"
        )

        # Human is away, so human should NOT be kicking
        is_human_kicking = kicking_home == human_is_home
        assert is_human_kicking is False, (
            "BUG REGRESSION: Human was asked to kick after opponent scored"
        )


class TestScoringSummaryLogging:
    """Tests for logging TD and Safety to scoring_plays when resuming with pending score.

    These tests verify the fix for the scoring summary mismatch bug where
    pending TDs/safeties weren't logged to scoring_plays, causing the
    scoring summary to not match the final score.
    """

    @patch("paydirt.game_engine.roll_chart_dice")
    def test_pending_td_logs_to_scoring_plays(self, mock_dice, game, temp_save_file):
        """Pending TD should be logged to scoring_plays so it appears in summary."""
        # Mock dice roll to ensure PAT succeeds (roll 25 is not in no_good_rolls for either team)
        mock_dice.return_value = (25, "Roll: 25")

        game.state.ball_position = 100  # TD
        game.state.is_home_possession = True  # Home team scored
        game.state.home_score = 20
        game.state.away_score = 17
        game.state.quarter = 4
        game.state.time_remaining = 5.0
        save_game(game, filepath=temp_save_file)

        loaded_game, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "touchdown"

        # Simulate the FIXED resume logic - log TD to scoring_plays
        from paydirt.game_state import ScoringPlay

        scoring_team_is_home = loaded_game.state.is_home_possession

        if scoring_team_is_home:
            loaded_game.state.home_score += 6
            loaded_game.state.scoring_plays.append(
                ScoringPlay(
                    quarter=loaded_game.state.quarter,
                    time_remaining=loaded_game.state.time_remaining,
                    team=loaded_game.state.home_chart.peripheral.short_name,
                    is_home_team=True,
                    play_type="TD",
                    description="Touchdown",
                    points=6,
                )
            )
            team_name = loaded_game.state.home_chart.peripheral.short_name
        else:
            loaded_game.state.away_score += 6
            loaded_game.state.scoring_plays.append(
                ScoringPlay(
                    quarter=loaded_game.state.quarter,
                    time_remaining=loaded_game.state.time_remaining,
                    team=loaded_game.state.away_chart.peripheral.short_name,
                    is_home_team=False,
                    play_type="TD",
                    description="Touchdown",
                    points=6,
                )
            )
            team_name = loaded_game.state.away_chart.peripheral.short_name

        # Now add PAT (mocked to succeed)
        loaded_game.attempt_extra_point()

        # Verify scoring_plays has both TD and PAT
        assert len(loaded_game.state.scoring_plays) == 2

        td_play = loaded_game.state.scoring_plays[0]
        assert td_play.play_type == "TD"
        assert td_play.points == 6
        assert td_play.team == team_name

    def test_pending_safety_logs_to_scoring_plays(self, game, temp_save_file):
        """Pending safety should be logged to scoring_plays so it appears in summary."""
        game.state.ball_position = 0  # Safety
        game.state.is_home_possession = True  # Home team was on offense, gave up safety
        game.state.home_score = 10
        game.state.away_score = 14
        game.state.quarter = 3
        game.state.time_remaining = 7.0
        save_game(game, filepath=temp_save_file)

        loaded_game, _, _, pending_score = load_game(temp_save_file)
        assert pending_score == "safety"

        # Simulate the FIXED resume logic - log safety to scoring_plays
        from paydirt.game_state import ScoringPlay

        # Safety: defense (away) scores
        if loaded_game.state.is_home_possession:
            loaded_game.state.away_score += 2
            loaded_game.state.scoring_plays.append(
                ScoringPlay(
                    quarter=loaded_game.state.quarter,
                    time_remaining=loaded_game.state.time_remaining,
                    team=loaded_game.state.away_chart.peripheral.short_name,
                    is_home_team=False,
                    play_type="Safety",
                    description="Safety",
                    points=2,
                )
            )
        else:
            loaded_game.state.home_score += 2
            loaded_game.state.scoring_plays.append(
                ScoringPlay(
                    quarter=loaded_game.state.quarter,
                    time_remaining=loaded_game.state.time_remaining,
                    team=loaded_game.state.home_chart.peripheral.short_name,
                    is_home_team=True,
                    play_type="Safety",
                    description="Safety",
                    points=2,
                )
            )

        # Verify scoring_plays has the safety
        assert len(loaded_game.state.scoring_plays) == 1

        safety_play = loaded_game.state.scoring_plays[0]
        assert safety_play.play_type == "Safety"
        assert safety_play.points == 2

    @patch("paydirt.game_engine.roll_chart_dice")
    def test_pending_td_and_pat_can_be_combined(self, mock_dice, game, temp_save_file):
        """TD + PAT should be combinable in scoring summary (same team, consecutive)."""
        # Mock dice roll to ensure PAT succeeds (roll 25 is not in no_good_rolls for either team)
        mock_dice.return_value = (25, "Roll: 25")

        game.state.ball_position = 100
        game.state.is_home_possession = True
        game.state.home_score = 20
        game.state.away_score = 17
        game.state.quarter = 4
        game.state.time_remaining = 5.0
        save_game(game, filepath=temp_save_file)

        loaded_game, _, _, pending_score = load_game(temp_save_file)

        # Log TD (the fix)
        from paydirt.game_state import ScoringPlay

        loaded_game.state.home_score += 6
        loaded_game.state.scoring_plays.append(
            ScoringPlay(
                quarter=loaded_game.state.quarter,
                time_remaining=loaded_game.state.time_remaining,
                team=loaded_game.state.home_chart.peripheral.short_name,
                is_home_team=True,
                play_type="TD",
                description="Touchdown",
                points=6,
            )
        )

        # Add PAT (mocked to succeed)
        loaded_game.attempt_extra_point()

        # Now test combining logic (from interactive_game.py scoring summary)
        combined_plays = []
        i = 0
        while i < len(loaded_game.state.scoring_plays):
            play = loaded_game.state.scoring_plays[i]
            if play.play_type == "TD" and i + 1 < len(loaded_game.state.scoring_plays):
                next_play = loaded_game.state.scoring_plays[i + 1]
                if (
                    next_play.play_type in ["PAT", "2PT"]
                    and next_play.is_home_team == play.is_home_team
                ):
                    combined_plays.append(
                        {"points": play.points + next_play.points, "is_home": play.is_home_team}
                    )
                    i += 2
                    continue
            i += 1

        # Should have 1 combined entry with 7 points
        assert len(combined_plays) == 1
        assert combined_plays[0]["points"] == 7
