"""
Test to verify the fumble reporting bug fix.

The bug: When defense scores TD on fumble return, the display said
">>> TOUCHDOWN {off_team}!" where off_team is the team that was on offense
BEFORE the play, not the team that scored.

The fix: Added `scoring_team` field to PlayResult, set it in the game engine
when touchdowns are scored, and updated display_play_result to use it.
"""
import sys
from io import StringIO
from unittest.mock import patch

import pytest

import paydirt.interactive_game as ig
from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType


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
        has_correct_cin_td = "FUMBLE RETURN TOUCHDOWN CIN '83!" in output
        has_buggy_tb_td = "TOUCHDOWN TB '83!" in output

        assert has_correct_cin_td, (
            "Display should credit the defense in the single fumble-return announcement\n"
            f"But output was:\n{output}"
        )
        assert not has_buggy_tb_td, (
            f"Fix should work: display should NOT say '>>> TOUCHDOWN TB '83!'\n"
            f"But output was:\n{output}"
        )

@pytest.mark.parametrize("offense_is_home", [False, True])
@pytest.mark.parametrize("fumble_yards", [-5, -6], ids=["goal-line", "in-end-zone"])
@pytest.mark.parametrize("compact", [False, True], ids=["full-cli", "compact-cli"])
@pytest.mark.parametrize("use_penalty_procedure", [False, True], ids=["direct", "penalty-procedure"])
def test_end_zone_defensive_recovery_sets_scoring_team(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    offense_is_home: bool,
    fumble_yards: int,
    compact: bool,
    use_penalty_procedure: bool,
) -> None:
    """Real engine recovery metadata must credit the defense in either CLI mode."""
    home = create_mock_chart("TB '83", "Tampa Bay Buccaneers")
    away = create_mock_chart("CIN '83", "Cincinnati Bengals")
    game = PaydirtGameEngine(home, away)
    game.state.is_home_possession = offense_is_home
    game.state.ball_position = 5
    game.state.down = 2
    game.state.yards_to_go = 10
    offense = game.state.possession_team
    defense = game.state.defense_team
    result = PlayResult(
        result_type=ResultType.FUMBLE, yards=fumble_yards,
        raw_result="F", description="FUMBLE!",
    )
    run_play = game.run_play_with_penalty_procedure if use_penalty_procedure else game.run_play
    with (
        patch("paydirt.game_engine.resolve_play", return_value=result),
        patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(30, "Recovery: 30")),
    ):
        outcome = run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)

    assert outcome.touchdown
    assert outcome.turnover
    assert not outcome.safety
    assert (game.state.home_score, game.state.away_score) == (
        (0, 6) if offense_is_home else (6, 0)
    )
    assert game.state.is_home_possession == (not offense_is_home)
    assert game.state.ball_position == 97
    assert game.state.scoring_plays[-1].team == defense.peripheral.short_name
    assert outcome.result.scoring_team == defense.peripheral.short_name

    monkeypatch.setattr(ig, "COMPACT_MODE", compact)
    ig.display_play_result(
        game, outcome, PlayType.LINE_PLUNGE, DefenseType.STANDARD,
        offense, offense_is_home,
    )
    output = capsys.readouterr().out
    assert "SCOOP AND SCORE!" not in output
    assert "RETURNED FOR TD" not in output
    assert (f"{defense.peripheral.short_name} recovers the fumble in "
            f"{offense.peripheral.short_name}'s end zone. TOUCHDOWN!") in output
    assert output.upper().count("TOUCHDOWN") == 1
    assert f"TOUCHDOWN {offense.peripheral.short_name}!" not in output
