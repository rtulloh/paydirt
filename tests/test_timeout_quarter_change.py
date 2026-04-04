"""
Tests for _should_apply_timeout_after_play to verify quarter-change behavior.
"""

import pytest
from unittest.mock import MagicMock, patch

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType, PlayResult, ResultType
from paydirt.models import PlayOutcome
from paydirt.chart_loader import (
    TeamChart,
    PeripheralData,
    OffenseChart,
    DefenseChart,
    SpecialTeamsChart,
)


def create_mock_chart(short_name: str = "TEST", year: int = 1983) -> TeamChart:
    """Create a minimal mock TeamChart for testing."""
    return TeamChart(
        peripheral=PeripheralData(
            year=year,
            team_name="Test Team",
            team_nickname="Testers",
            power_rating=50,
            short_name=short_name,
        ),
        offense=MagicMock(spec=OffenseChart),
        defense=MagicMock(spec=DefenseChart),
        special_teams=MagicMock(spec=SpecialTeamsChart),
    )


@pytest.fixture
def game():
    """Create a game engine for testing."""
    home_chart = create_mock_chart("HOME")
    away_chart = create_mock_chart("AWAY")
    return PaydirtGameEngine(home_chart, away_chart)


class TestShouldApplyTimeoutAfterPlayQuarterChange:
    """
    Tests for _should_apply_timeout_after_play when quarter changes during play.

    This reproduces the bug where:
    - Time before play: 0.2 minutes (12 seconds) in Q2
    - Play uses ~30 seconds, causing quarter to advance to Q3
    - Time after play: 15.0 minutes (new quarter)
    - play_seconds calculation: (0.2 - 15.0) * 60 = -888 seconds
    - -888 <= 10 is TRUE, so timeout is incorrectly skipped

    FIX: Now passes quarter_before_play to detect quarter changes.
    """

    def test_timeout_applies_when_quarter_changes(self, game):
        """
        When quarter changes during play, timeout SHOULD be applied.

        This test verifies the fix: when quarter changes, timeout applies.
        """
        # Set up Q2 with 12 seconds remaining
        game.state.quarter = 3  # Set to new quarter to test comparison
        game.state.time_remaining = 0.2  # 12 seconds

        # Create a mock outcome (not incomplete, not OOB)
        outcome = MagicMock()
        outcome.result = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        outcome.touchdown = False
        outcome.turnover = False

        # Simulate what happens when quarter changes:
        # quarter_before = 2, quarter_after = 3 (game.state.quarter)
        quarter_before = 2
        play_seconds = (0.2 - 15.0) * 60  # = -888 seconds (but now we detect quarter change)

        # After fix: should apply because quarter changed
        should_apply, skip_msg = game._should_apply_timeout_after_play(
            outcome, play_seconds, quarter_before
        )

        print(f"quarter_before: {quarter_before}, quarter_after: {game.state.quarter}")
        print(f"play_seconds: {play_seconds}")
        print(f"should_apply: {should_apply}")
        print(f"skip_msg: {skip_msg}")

        # FIXED: Timeout should now apply when quarter changed
        assert should_apply is True, "Timeout should apply when quarter changed"
        assert skip_msg == ""

    def test_timeout_not_skipped_when_quarter_changes_but_should_be(self, game):
        """
        Verify that timeout IS applied when quarter changed.

        The fix: if quarter changed during play, apply timeout.
        """
        # Set up Q3 (new quarter)
        game.state.quarter = 3
        game.state.time_remaining = 15.0

        outcome = MagicMock()
        outcome.result = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        outcome.touchdown = False
        outcome.turnover = False

        # Quarter changed: before=2, after=3
        quarter_before = 2
        play_seconds = (0.2 - 15.0) * 60  # = -888

        should_apply, _ = game._should_apply_timeout_after_play(
            outcome, play_seconds, quarter_before
        )

        # With fix: should apply because quarter changed
        print(f"Fixed behavior: should_apply={should_apply}")
        assert should_apply is True

    def test_timeout_not_skipped_normal_case(self, game):
        """
        Verify timeout NOT skipped in normal case (no quarter change).
        """
        game.state.quarter = 2
        game.state.time_remaining = 10.0  # 10 seconds remaining

        outcome = MagicMock()
        outcome.result = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        outcome.touchdown = False
        outcome.turnover = False

        # Normal case: 30 seconds used, no quarter change
        quarter_before = 2
        play_seconds = 30.0

        should_apply, skip_msg = game._should_apply_timeout_after_play(
            outcome, play_seconds, quarter_before
        )

        # 30 > 10, so timeout should apply
        assert should_apply is True
        assert skip_msg == ""

    def test_timeout_skipped_short_play(self, game):
        """
        Verify timeout IS skipped when play uses <= 10 seconds.
        """
        game.state.quarter = 2
        game.state.time_remaining = 10.0

        outcome = MagicMock()
        outcome.result = MagicMock()
        outcome.result.result_type = ResultType.YARDS
        outcome.result.out_of_bounds = False
        outcome.touchdown = False
        outcome.turnover = False

        # Short play: 8 seconds used
        quarter_before = 2
        play_seconds = 8.0

        should_apply, skip_msg = game._should_apply_timeout_after_play(
            outcome, play_seconds, quarter_before
        )

        # 8 <= 10, so timeout should be skipped
        assert should_apply is False
        assert "no time would be saved" in skip_msg
