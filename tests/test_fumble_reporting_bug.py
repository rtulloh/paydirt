"""
Test to verify the fumble reporting bug fix.

The bug: When defense scores TD on fumble return, the display said
">>> TOUCHDOWN {off_team}!" where off_team is the team that was on offense
BEFORE the play, not the team that scored.

The fix: Added `scoring_team` field to PlayResult, set it in the game engine
when touchdowns are scored, and updated display_play_result to use it.
"""
import pytest
from unittest.mock import patch
from io import StringIO
import sys

from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import PlayType, DefenseType, PlayResult, ResultType
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart
import paydirt.interactive_game as ig


@pytest.fixture(autouse=True)
def reset_compact_mode():
    """Reset COMPACT_MODE to default before and after each test."""
    ig.COMPACT_MODE = False
    yield
    ig.COMPACT_MODE = False


def create_mock_chart(short_name: str, full_name: str) -> TeamChart:
    """Create a mock team chart for testing."""
    peripheral = PeripheralData(
        year=1983,
        team_name=full_name.split()[-1],
        team_nickname=full_name.split()[-1],
        power_rating=50,
        short_name=short_name
    )
    # Set fumble recovery range so defense can recover (roll 11-39 = lose fumble)
    peripheral.fumble_recovered_range = (1, 10)  # offense recovers on 1-10
    peripheral.fumble_lost_range = (11, 39)     # loses on 11-39

    offense_chart = OffenseChart(
        medium_pass={"39": "QT"},  # Roll 39 on Medium Pass = QT
    )
    defense_chart = DefenseChart()

    return TeamChart(
        peripheral=peripheral,
        offense=offense_chart,
        defense=defense_chart,
        special_teams=SpecialTeamsChart(),
        team_dir=""
    )


class TestFumbleReportingFix:
    """Tests to verify defensive fumble return TDs are correctly reported."""

    def test_defensive_fumble_td_correctly_attributed_to_defense(self):
        """
        Verify that when defense scores TD on fumble return,
        the display credits the defense, not the offense.

        The fix: display now uses outcome.result.scoring_team if available,
        otherwise falls back to the old off_team behavior.
        """
        from paydirt.interactive_game import display_play_result

        # Create mock charts - TB '83 (offense/home) vs CIN '83 (defense/away)
        home_chart = create_mock_chart("TB '83", "Tampa Bay Buccaneers")
        away_chart = create_mock_chart("CIN '83", "Cincinnati Bengals")

        # Create game with TB on offense (home possession)
        game = PaydirtGameEngine(home_chart, away_chart)

        # Set TB on offense (home possession)
        game.state.is_home_possession = True
        game.state.ball_position = 34  # TB 34-yard line
        game.state.down = 3
        game.state.yards_to_go = 13

        # Create a PlayResult with scoring_team set to CIN '83 (the defense)
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=0,
            description="",
            turnover=True,
            touchdown=True,
            raw_result="QT",
            dice_roll=39,
            defense_modifier="",
            scoring_team="CIN '83",  # Defense scored the TD
        )

        # Create outcome
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS,
            defense_type=DefenseType.LONG_PASS,
            result=result,
            yards_gained=0,
            turnover=True,
            touchdown=True,
            safety=False,
            first_down=False,
            field_position_before="TB 34",
            field_position_after="CIN 0",
            down_before=3,
            down_after=game.state.down,
            description="QB scramble FUMBLE at 0 yards (QT roll: ...)",
            transaction=None,
        )

        # Capture stdout to check the display output
        old_stdout = sys.stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            display_play_result(game, outcome, PlayType.MEDIUM_PASS, DefenseType.LONG_PASS, home_chart, True)
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()

        print(f"Output:\n{output}")

        # The fix should make the display correctly credit CIN '83
        has_correct_cin_td = ">>> TOUCHDOWN CIN '83!" in output
        has_buggy_tb_td = ">>> TOUCHDOWN TB '83!" in output

        assert has_correct_cin_td, (
            f"Fix should work: display should say '>>> TOUCHDOWN CIN '83!'\n"
            f"But output was:\n{output}"
        )
        assert not has_buggy_tb_td, (
            f"Fix should work: display should NOT say '>>> TOUCHDOWN TB '83!'\n"
            f"But output was:\n{output}"
        )