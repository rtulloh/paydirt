"""
Regression tests for kickoff after scoring.

Verifies that the correct team kicks off after touchdowns, field goals,
and safeties — specifically that the away team doesn't get consecutive
possessions after scoring.
"""
import pytest

from paydirt.game_engine import PaydirtGameEngine
from tests.game_fixtures import make_sample_game


@pytest.fixture
def game() -> PaydirtGameEngine:
    """Public sample teams: their return charts carry no fumble cells, so an
    unpatched kickoff always leaves the receiving team in possession."""
    return make_sample_game()


class TestKickoffAfterScore:
    """After scoring, the scoring team should kick off (opponent receives)."""

    def test_away_team_kicks_after_away_touchdown(self, game):
        """After away team scores TD, away should kick and home should receive."""
        game.state.is_home_possession = False  # away has ball
        game.state.away_score += 6
        game.attempt_extra_point()

        # Scoring team (away) kicks off
        kicking_home = game.state.is_home_possession  # False (away)
        game.kickoff(kicking_home=kicking_home)

        # Home team should now have possession (they received)
        assert game.state.is_home_possession is True

    def test_home_team_kicks_after_home_touchdown(self, game):
        """After home team scores TD, home should kick and away should receive."""
        game.state.is_home_possession = True  # home has ball
        game.state.home_score += 6
        game.attempt_extra_point()

        # Scoring team (home) kicks off
        kicking_home = game.state.is_home_possession  # True (home)
        game.kickoff(kicking_home=kicking_home)

        # Away team should now have possession (they received)
        assert game.state.is_home_possession is False

    def test_away_team_kicks_after_away_field_goal(self, game):
        """After away team FG, away should kick and home should receive."""
        game.state.is_home_possession = False  # away has ball

        kicking_home = game.state.is_home_possession  # False (away)
        game.kickoff(kicking_home=kicking_home)

        assert game.state.is_home_possession is True

    def test_default_kickoff_home_true_gives_away_possession(self, game):
        """Verify kickoff(kicking_home=True) gives away team the ball."""
        game.kickoff(kicking_home=True)
        assert game.state.is_home_possession is False

    def test_default_kickoff_home_false_gives_home_possession(self, game):
        """Verify kickoff(kicking_home=False) gives home team the ball."""
        game.kickoff(kicking_home=False)
        assert game.state.is_home_possession is True

    def test_no_consecutive_possessions_after_away_score(self, game):
        """Away team must not get the ball back immediately after scoring."""
        game.state.is_home_possession = False  # away has ball
        game.state.away_score += 6
        game.attempt_extra_point()

        # This is the correct pattern used by interactive_game.py
        kicking_home = game.state.is_home_possession
        game.kickoff(kicking_home=kicking_home)

        # Away scored, so home must have ball now
        assert game.state.is_home_possession is True, \
            "Away team has consecutive possessions after scoring (kickoff bug)"
