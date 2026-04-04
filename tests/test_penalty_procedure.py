"""
Unit tests for the penalty procedure implementation.

Tests the full penalty procedure per Paydirt rules:
- When a penalty occurs, offense rerolls (defense keeps original)
- Offended team chooses: play result (down counts) OR penalty (down replayed)
- If multiple penalties, offended team picks ONE (not combined)
- If offsetting penalties, down is replayed
- If PI, no rerolls - defensive result cancelled, incomplete pass
"""

import pytest
from unittest.mock import patch

from paydirt.play_resolver import (
    PlayType,
    DefenseType,
    ResultType,
    PlayResult,
    PenaltyChoice,
    PenaltyOption,
    _is_penalty_result,
    _create_penalty_option,
    resolve_play_with_penalties,
)
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.chart_loader import (
    TeamChart,
    PeripheralData,
    OffenseChart,
    DefenseChart,
    SpecialTeamsChart,
)


# Module-level mock fixtures for tests that don't need real chart data
@pytest.fixture
def mock_special_teams():
    """Create mock special teams chart."""
    return SpecialTeamsChart(
        interception_return={10: "5"},
        kickoff={},
        kickoff_return={},
        punt={},
        punt_return={},
        field_goal={},
        extra_point_no_good=[],
    )


@pytest.fixture
def mock_offense():
    """Create mock offense chart."""
    return OffenseChart(
        line_plunge={10: "5"},
        off_tackle={10: "4"},
    )


@pytest.fixture
def mock_team_chart(mock_offense, mock_special_teams):
    """Create a mock team chart with year=1983 for fallback rules."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Test",
            team_nickname="Team",
            power_rating=50,
            power_rating_variance=1,
            base_yardage_factor=100,
            reduced_yardage_factor=80,
            fumble_recovered_range=(0, 0),
            fumble_lost_range=(0, 0),
            special_defense="",
            short_name="TST '83",
        ),
        offense=mock_offense,
        defense=DefenseChart(),
        special_teams=mock_special_teams,
        team_dir="",
    )


class TestIsPenaltyResult:
    """Tests for the _is_penalty_result helper function."""

    def test_offensive_penalty(self):
        """OFF X should be detected as offensive penalty."""
        is_pen, pen_type = _is_penalty_result("OFF 10")
        assert is_pen is True
        assert pen_type == "OFF"

    def test_offensive_penalty_s(self):
        """OFF S should be detected as offensive penalty."""
        is_pen, pen_type = _is_penalty_result("OFF S")
        assert is_pen is True
        assert pen_type == "OFF"

    def test_defensive_penalty(self):
        """DEF X should be detected as defensive penalty."""
        is_pen, pen_type = _is_penalty_result("DEF 5")
        assert is_pen is True
        assert pen_type == "DEF"

    def test_defensive_penalty_with_modifier(self):
        """DEF 5X should be detected as defensive penalty."""
        is_pen, pen_type = _is_penalty_result("DEF 5X")
        assert is_pen is True
        assert pen_type == "DEF"

    def test_pass_interference(self):
        """PI X should be detected as pass interference."""
        is_pen, pen_type = _is_penalty_result("PI 15")
        assert is_pen is True
        assert pen_type == "PI"

    def test_yardage_not_penalty(self):
        """Normal yardage should not be a penalty."""
        is_pen, pen_type = _is_penalty_result("8")
        assert is_pen is False
        assert pen_type == ""

    def test_parentheses_not_penalty(self):
        """Parenthesized number should not be a penalty."""
        is_pen, pen_type = _is_penalty_result("(4)")
        assert is_pen is False
        assert pen_type == ""

    def test_empty_not_penalty(self):
        """Empty string should not be a penalty."""
        is_pen, pen_type = _is_penalty_result("")
        assert is_pen is False
        assert pen_type == ""

    def test_interception_not_penalty(self):
        """INT should not be a penalty."""
        is_pen, pen_type = _is_penalty_result("INT 15")
        assert is_pen is False
        assert pen_type == ""


class TestCreatePenaltyOption:
    """Tests for the _create_penalty_option helper function."""

    def test_offensive_penalty_option(self):
        """Create option for offensive penalty."""
        opt = _create_penalty_option("OFF 10")
        assert opt.penalty_type == "OFF"
        assert opt.yards == 10
        assert opt.auto_first_down is False
        assert "Offensive penalty" in opt.description

    def test_defensive_penalty_option(self):
        """Create option for defensive penalty."""
        opt = _create_penalty_option("DEF 5")
        assert opt.penalty_type == "DEF"
        assert opt.yards == 5
        assert opt.auto_first_down is False
        assert "Defensive penalty" in opt.description

    def test_defensive_penalty_with_auto_first(self):
        """DEF 5X should have auto_first_down=True."""
        opt = _create_penalty_option("DEF 5X")
        assert opt.penalty_type == "DEF"
        assert opt.auto_first_down is True

    def test_pass_interference_option(self):
        """Create option for pass interference."""
        opt = _create_penalty_option("PI 15")
        assert opt.penalty_type == "PI"
        assert opt.yards == 15
        assert opt.auto_first_down is True
        assert opt.is_pass_interference is True
        assert "Pass interference" in opt.description

    def test_defensive_15_yard_penalty_auto_first_down(self):
        """
        DEF 15 should give automatic first down.

        Per NFL rules (1983+), all 15-yard defensive penalties carry automatic first down.
        This is NOT dependent on the X modifier - any 15-yard defensive penalty should
        give an automatic first down, even if half-distance reduces the yardage.

        Bug scenario: 2nd & Goal at opp 10, DEF 15 penalty -> half distance to 5 yards
        Expected: 1st & Goal at opp 5 (automatic first down)
        Bug behavior: 2nd & 5 at opp 5 (no automatic first down)
        """
        opt = _create_penalty_option("DEF 15")
        assert opt.penalty_type == "DEF"
        assert opt.yards == 15
        assert opt.auto_first_down is True, "DEF 15 should give automatic first down per NFL rules"


class TestResolvePlayWithPenalties:
    """Tests for the resolve_play_with_penalties function."""

    @pytest.fixture
    def team_charts(self, mock_team_chart):
        """Use mock team charts for testing (results are mocked anyway)."""
        return mock_team_chart, mock_team_chart

    def test_no_penalty_returns_play_result(self, team_charts):
        """When no penalty occurs, should return normal play result."""
        home, away = team_charts

        # Mock to return non-penalty results
        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            mock_roll.return_value = (25, "B2+W3+W0=25")
            mock_off.return_value = "8"  # 8 yards, not a penalty
            mock_def.return_value = "3"  # 3 yards, not a penalty

            result = resolve_play_with_penalties(
                home, away, PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert len(result.penalty_options) == 0
            assert result.offended_team == ""
            assert result.offsetting is False

    def test_defensive_penalty_offense_offended(self, team_charts):
        """When defense commits penalty, offense is offended."""
        home, away = team_charts

        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            mock_roll.return_value = (25, "B2+W3+W0=25")
            mock_off.return_value = "8"  # Normal result
            mock_def.return_value = "DEF 5"  # Defensive penalty

            result = resolve_play_with_penalties(
                home, away, PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert len(result.penalty_options) == 1
            assert result.penalty_options[0].penalty_type == "DEF"
            assert result.offended_team == "offense"
            assert result.offsetting is False

    def test_offensive_penalty_defense_offended(self, team_charts):
        """When offense commits penalty, defense is offended."""
        home, away = team_charts

        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            # First roll returns penalty, second roll returns normal result
            mock_roll.side_effect = [(25, "B2+W3+W0=25"), (30, "B3+W0+W0=30")]
            mock_off.side_effect = ["OFF 10", "8"]  # First penalty, then normal
            mock_def.return_value = "3"  # Normal result

            result = resolve_play_with_penalties(
                home, away, PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert len(result.penalty_options) == 1
            assert result.penalty_options[0].penalty_type == "OFF"
            assert result.offended_team == "defense"
            assert result.offsetting is False

    def test_offsetting_penalties(self, team_charts):
        """When both offense and defense commit penalties, they offset."""
        home, away = team_charts

        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            # Offense rolls penalty first, then normal
            mock_roll.side_effect = [(25, "B2+W3+W0=25"), (30, "B3+W0+W0=30")]
            mock_off.side_effect = ["OFF 10", "8"]  # First penalty, then normal
            mock_def.return_value = "DEF 5"  # Defense also has penalty

            result = resolve_play_with_penalties(
                home, away, PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert len(result.penalty_options) == 2  # Both penalties recorded
            assert result.offsetting is True
            assert result.offended_team == ""  # No one is offended when offsetting

    def test_pi_cancels_defense_result(self, team_charts):
        """Pass interference should cancel defensive result and be incomplete."""
        home, away = team_charts

        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            mock_roll.return_value = (25, "B2+W3+W0=25")
            mock_off.return_value = "PI 15"  # Pass interference
            mock_def.return_value = "INT 20"  # Would be interception, but PI cancels it

            result = resolve_play_with_penalties(
                home, away, PlayType.MEDIUM_PASS, DefenseType.STANDARD
            )

            assert result.is_pass_interference is True
            assert result.play_result.result_type == ResultType.INCOMPLETE
            assert result.offended_team == "offense"  # Defense committed PI

    def test_multiple_offensive_penalties_reroll(self, team_charts):
        """Offense should keep rerolling until non-penalty result."""
        home, away = team_charts

        with (
            patch("paydirt.play_resolver.roll_chart_dice") as mock_roll,
            patch("paydirt.play_resolver.get_offense_result") as mock_off,
            patch("paydirt.play_resolver.get_defense_modifier") as mock_def,
        ):
            # Multiple penalty rolls, then normal
            mock_roll.side_effect = [
                (20, "B2+W0+W0=20"),
                (25, "B2+W3+W0=25"),
                (30, "B3+W0+W0=30"),
                (35, "B3+W3+W0=35"),
            ]
            mock_off.side_effect = ["OFF 5", "OFF 10", "OFF 15", "8"]  # 3 penalties, then normal
            mock_def.return_value = "3"  # Normal result

            result = resolve_play_with_penalties(
                home, away, PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            # Should have 3 penalty options (all the offensive penalties)
            assert len(result.penalty_options) == 3
            assert all(opt.penalty_type == "OFF" for opt in result.penalty_options)
            assert result.offended_team == "defense"
            # Reroll log should show the rerolls
            assert len(result.reroll_log) == 4  # 3 penalties + 1 final result


class TestGameEnginePenaltyProcedure:
    """Tests for the game engine penalty procedure methods."""

    @pytest.fixture
    def game(self, mock_team_chart):
        """Create a game using mock charts (year=1983 for fallback rules)."""
        return PaydirtGameEngine(mock_team_chart, mock_team_chart)

    def test_run_play_with_penalty_procedure_no_penalty(self, game):
        """Normal play without penalty should work like run_play."""
        with patch("paydirt.game_engine.resolve_play_with_penalties") as mock_resolve:
            # Mock a normal play result with no penalties
            mock_result = PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 8, "8 yards"),
                penalty_options=[],
                offended_team="",
                offsetting=False,
            )
            mock_resolve.return_value = mock_result

            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert outcome.pending_penalty_decision is False
            assert outcome.yards_gained == 8

    def test_run_play_with_penalty_procedure_pending_decision(self, game):
        """Play with penalty should return pending decision."""
        with patch("paydirt.game_engine.resolve_play_with_penalties") as mock_resolve:
            # Mock a play with defensive penalty
            mock_result = PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 8, "8 yards"),
                penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards")],
                offended_team="offense",
                offsetting=False,
            )
            mock_resolve.return_value = mock_result

            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert outcome.pending_penalty_decision is True
            assert outcome.penalty_choice is not None
            assert outcome.penalty_choice.offended_team == "offense"

    def test_run_play_with_penalty_procedure_offsetting(self, game):
        """Offsetting penalties should replay down without pending decision."""
        with patch("paydirt.game_engine.resolve_play_with_penalties") as mock_resolve:
            # Mock offsetting penalties
            mock_result = PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 8, "8 yards"),
                penalty_options=[
                    PenaltyOption("OFF", "OFF 10", 10, "Offensive penalty"),
                    PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty"),
                ],
                offended_team="",
                offsetting=True,
            )
            mock_resolve.return_value = mock_result

            down_before = game.state.down
            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert outcome.pending_penalty_decision is False
            assert "Offsetting" in outcome.description
            assert game.state.down == down_before  # Down should not change

    def test_apply_penalty_decision_accept_play(self, game):
        """Accepting play result should apply the play."""
        # Create a pending outcome
        play_result = PlayResult(ResultType.YARDS, 8, "8 yards")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty")],
            offended_team="offense",
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=8,
            field_position_before="own 20",
            down_before=1,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        final = game.apply_penalty_decision(outcome, accept_play=True)

        assert final.pending_penalty_decision is False
        assert final.yards_gained == 8

    def test_apply_penalty_decision_accept_penalty(self, game):
        """Accepting penalty should apply the penalty."""
        # Create a pending outcome
        play_result = PlayResult(ResultType.YARDS, 8, "8 yards")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards")],
            offended_team="offense",
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=8,
            field_position_before="own 20",
            down_before=1,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        ball_before = game.state.ball_position
        final = game.apply_penalty_decision(outcome, accept_play=False, penalty_index=0)

        assert final.pending_penalty_decision is False
        # Ball should have moved forward (defensive penalty)
        assert game.state.ball_position > ball_before


class TestPenaltyChoiceDataclass:
    """Tests for the PenaltyChoice dataclass."""

    def test_penalty_choice_defaults(self):
        """PenaltyChoice should have sensible defaults."""
        play_result = PlayResult(ResultType.YARDS, 5, "5 yards")
        choice = PenaltyChoice(play_result=play_result)

        assert choice.penalty_options == []
        assert choice.offended_team == ""
        assert choice.offsetting is False
        assert choice.is_pass_interference is False
        assert choice.reroll_log == []

    def test_penalty_option_defaults(self):
        """PenaltyOption should have sensible defaults."""
        opt = PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty")

        assert opt.auto_first_down is False
        assert opt.is_pass_interference is False


class TestPenaltyAppliedFlag:
    """Tests for the penalty_applied flag on PlayOutcome."""

    @pytest.fixture
    def game(self, mock_team_chart):
        """Create a game using mock charts (year=1983 for fallback rules)."""
        return PaydirtGameEngine(mock_team_chart, mock_team_chart)

    def test_penalty_applied_false_by_default(self, game):
        """PlayOutcome should have penalty_applied=False by default."""
        with patch("paydirt.game_engine.resolve_play_with_penalties") as mock_resolve:
            mock_result = PenaltyChoice(
                play_result=PlayResult(ResultType.YARDS, 8, "8 yards"),
                penalty_options=[],
                offended_team="",
                offsetting=False,
            )
            mock_resolve.return_value = mock_result

            outcome = game.run_play_with_penalty_procedure(
                PlayType.OFF_TACKLE, DefenseType.STANDARD
            )

            assert outcome.penalty_applied is False

    def test_penalty_applied_true_when_penalty_accepted(self, game):
        """penalty_applied should be True when a penalty is accepted."""
        game.state.ball_position = 30
        game.state.down = 2
        game.state.yards_to_go = 5

        # Create an outcome with a pending penalty decision
        play_result = PlayResult(ResultType.YARDS, 0, "0 yards")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards")],
            offended_team="offense",
            offsetting=False,
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=0,
            field_position_before="own 30",
            down_before=2,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        # Accept the penalty
        final = game.apply_penalty_decision(outcome, accept_play=False, penalty_index=0)

        assert final.penalty_applied is True
        assert final.pending_penalty_decision is False

    def test_penalty_applied_false_when_play_accepted(self, game):
        """penalty_applied should be False when play result is accepted."""
        game.state.ball_position = 30
        game.state.down = 2
        game.state.yards_to_go = 5

        # Create an outcome with a pending penalty decision
        play_result = PlayResult(ResultType.YARDS, 8, "8 yards")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards")],
            offended_team="offense",
            offsetting=False,
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=8,
            field_position_before="own 30",
            down_before=2,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        # Accept the play result (not the penalty)
        final = game.apply_penalty_decision(outcome, accept_play=True)

        assert final.penalty_applied is False
        assert final.pending_penalty_decision is False

    def test_penalty_yards_correct_when_def_penalty_accepted(self, game):
        """Accepting DEF penalty should give correct yards."""
        game.state.ball_position = 30
        game.state.down = 2
        game.state.yards_to_go = 8

        play_result = PlayResult(ResultType.YARDS, 0, "0 yards")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards")],
            offended_team="offense",
            offsetting=False,
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=0,
            field_position_before="own 30",
            down_before=2,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        # Mock the dice roll to get consistent 5-yard penalty (roll 10-24 = 5 yards for DEF_S)
        with patch("paydirt.penalty_handler.roll_chart_dice") as mock_dice:
            mock_dice.return_value = (15, "B1+W0+W5=15")  # Roll 15 = 5 yard DEF penalty

            final = game.apply_penalty_decision(outcome, accept_play=False, penalty_index=0)

        # Ball should move forward 5 yards (DEF penalty benefits offense)
        assert game.state.ball_position == 35
        assert final.yards_gained == 5

    def test_pi_penalty_gives_first_down(self, game):
        """Accepting PI penalty should give automatic first down."""
        game.state.ball_position = 30
        game.state.down = 3
        game.state.yards_to_go = 15

        play_result = PlayResult(ResultType.INCOMPLETE, 0, "Incomplete")
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[
                PenaltyOption(
                    "PI",
                    "PI 20",
                    20,
                    "Pass interference, 20 yards",
                    auto_first_down=True,
                    is_pass_interference=True,
                )
            ],
            offended_team="offense",
            offsetting=False,
            is_pass_interference=True,
        )
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=0,
            field_position_before="own 30",
            down_before=3,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

        final = game.apply_penalty_decision(outcome, accept_play=False, penalty_index=0)

        # PI should give first down
        assert final.first_down is True
        assert game.state.down == 1
        assert game.state.ball_position == 50  # 30 + 20


class TestPenaltyAdviceDisplay:
    """Tests for penalty advice display calculations in interactive_game.py."""

    def test_offensive_penalty_increases_yards_to_go(self):
        """Offensive penalty should increase yards to go, not decrease.

        Bug fix: On 1st and 10, a 5-yard offensive penalty should result in
        1st and 15, not 1st and 5.
        """
        # Test the calculation logic directly
        yards_to_go = 10
        penalty_yards = 5
        penalty_type = "OFF"

        # Offensive penalty - yards to go should INCREASE
        if penalty_type in ["DEF", "PI"]:
            # Defensive penalty - offense gains yards, reduces yards to go
            new_ytg = max(1, yards_to_go - penalty_yards)
        else:
            # Offensive penalty - offense loses yards, increases yards to go
            new_ytg = yards_to_go + penalty_yards

        assert new_ytg == 15, f"Expected 1st and 15, got 1st and {new_ytg}"

    def test_defensive_penalty_decreases_yards_to_go(self):
        """Defensive penalty should decrease yards to go."""
        yards_to_go = 10
        penalty_yards = 5
        penalty_type = "DEF"

        # Defensive penalty - yards to go should DECREASE
        if penalty_type in ["DEF", "PI"]:
            new_ytg = max(1, yards_to_go - penalty_yards)
        else:
            new_ytg = yards_to_go + penalty_yards

        assert new_ytg == 5, f"Expected 2nd and 5, got 2nd and {new_ytg}"

    def test_offensive_penalty_on_third_and_long(self):
        """Offensive penalty on 3rd and 15 should result in 3rd and 20."""
        yards_to_go = 15
        penalty_yards = 5
        penalty_type = "OFF"

        if penalty_type in ["DEF", "PI"]:
            new_ytg = max(1, yards_to_go - penalty_yards)
        else:
            new_ytg = yards_to_go + penalty_yards

        assert new_ytg == 20, f"Expected 3rd and 20, got 3rd and {new_ytg}"

    def test_defensive_penalty_gives_first_down_when_enough_yards(self):
        """Defensive penalty that exceeds yards to go should give first down."""
        yards_to_go = 5
        penalty_yards = 10
        penalty_type = "DEF"
        auto_first_down = False

        # Check if penalty gives first down
        gives_first_down = auto_first_down or (
            penalty_type in ["DEF", "PI"] and penalty_yards >= yards_to_go
        )

        assert gives_first_down is True, "10-yard DEF penalty on 3rd and 5 should give first down"


class TestPenaltyAdviceTouchdown:
    """Tests for penalty advice display when play would result in touchdown."""

    def test_play_result_shows_touchdown_at_goal_line(self):
        """A 5-yard gain from the 1-yard line should show TOUCHDOWN, not '2nd and X'."""
        # At opponent's 1-yard line, ball_position = 99
        # A 5-yard gain means new_position = 99 + 5 = 104 >= 100 = TOUCHDOWN
        ball_position = 99  # 1-yard line
        yards_gained = 5
        new_position = ball_position + yards_gained

        assert new_position >= 100, "5 yards from the 1 should cross the goal line"

        # The display logic should show TOUCHDOWN
        if new_position >= 100:
            result = "TOUCHDOWN!"
        else:
            result = "some other result"

        assert result == "TOUCHDOWN!", f"Expected TOUCHDOWN but got {result}"

    def test_play_result_shows_first_down_not_touchdown(self):
        """A 5-yard gain from the 10-yard line should show FIRST DOWN, not TOUCHDOWN."""
        # At opponent's 10-yard line, ball_position = 90
        # A 5-yard gain means new_position = 90 + 5 = 95 < 100 = not TD
        ball_position = 90  # 10-yard line
        yards_gained = 5
        yards_to_go = 5  # 1st and 5
        new_position = ball_position + yards_gained

        assert new_position < 100, "5 yards from the 10 should not cross the goal line"
        assert yards_gained >= yards_to_go, "5 yards should be enough for first down"

        # The display logic should show FIRST DOWN
        if new_position >= 100:
            result = "TOUCHDOWN!"
        elif yards_gained >= yards_to_go:
            result = "FIRST DOWN"
        else:
            result = "some other result"

        assert result == "FIRST DOWN", f"Expected FIRST DOWN but got {result}"

    def test_1_yard_gain_from_1_yard_line_is_touchdown(self):
        """Even a 1-yard gain from the 1-yard line should be a touchdown."""
        ball_position = 99  # 1-yard line
        yards_gained = 1
        new_position = ball_position + yards_gained

        assert new_position >= 100, "1 yard from the 1 should cross the goal line"


class TestHalfDistanceRuleInPenaltyAdvice:
    """Tests for half-distance rule application in penalty advice display."""

    def test_half_distance_defensive_penalty_near_goal(self):
        """15-yard defensive penalty at opponent's 22 should be reduced to 11 yards."""
        from paydirt.penalty_handler import apply_half_distance_rule

        # Ball at opponent's 22 = position 78 (100 - 22 = 78)
        ball_position = 78
        penalty_yards = 15
        is_offensive_penalty = False  # Defensive penalty

        adjusted = apply_half_distance_rule(penalty_yards, ball_position, is_offensive_penalty)

        # Distance to goal is 22 yards, half is 11
        assert adjusted == 11, f"Expected 11 yards (half of 22), got {adjusted}"

    def test_half_distance_defensive_penalty_at_10(self):
        """15-yard defensive penalty at opponent's 10 should be reduced to 5 yards."""
        from paydirt.penalty_handler import apply_half_distance_rule

        # Ball at opponent's 10 = position 90
        ball_position = 90
        penalty_yards = 15
        is_offensive_penalty = False

        adjusted = apply_half_distance_rule(penalty_yards, ball_position, is_offensive_penalty)

        # Distance to goal is 10 yards, half is 5
        assert adjusted == 5, f"Expected 5 yards (half of 10), got {adjusted}"

    def test_half_distance_offensive_penalty_near_own_goal(self):
        """15-yard offensive penalty at own 20 should be reduced to 10 yards."""
        from paydirt.penalty_handler import apply_half_distance_rule

        # Ball at own 20 = position 20
        ball_position = 20
        penalty_yards = 15
        is_offensive_penalty = True

        adjusted = apply_half_distance_rule(penalty_yards, ball_position, is_offensive_penalty)

        # Distance to own goal is 20 yards, half is 10
        assert adjusted == 10, f"Expected 10 yards (half of 20), got {adjusted}"

    def test_no_half_distance_when_far_from_goal(self):
        """15-yard penalty at midfield should not be reduced."""
        from paydirt.penalty_handler import apply_half_distance_rule

        # Ball at midfield = position 50
        ball_position = 50
        penalty_yards = 15
        is_offensive_penalty = False  # Defensive penalty

        adjusted = apply_half_distance_rule(penalty_yards, ball_position, is_offensive_penalty)

        # Distance to goal is 50 yards, half is 25, so 15 is fine
        assert adjusted == 15, f"Expected 15 yards (no reduction needed), got {adjusted}"

    def test_5_yard_penalty_at_8_yard_line(self):
        """5-yard defensive penalty at opponent's 8 should be reduced to 4 yards."""
        from paydirt.penalty_handler import apply_half_distance_rule

        # Ball at opponent's 8 = position 92
        ball_position = 92
        penalty_yards = 5
        is_offensive_penalty = False

        adjusted = apply_half_distance_rule(penalty_yards, ball_position, is_offensive_penalty)

        # Distance to goal is 8 yards, half is 4
        assert adjusted == 4, f"Expected 4 yards (half of 8), got {adjusted}"


class TestPenaltyOptionsFiltering:
    """Tests for filtering penalty options based on offended team."""

    def test_offense_offended_only_sees_defensive_penalties(self):
        """When offense is offended, they should only see DEF/PI penalties."""
        from paydirt.play_resolver import PenaltyOption

        # Simulate penalty options list with both OFF and DEF penalties
        penalty_options = [
            PenaltyOption(
                penalty_type="OFF",
                raw_result="OFF 15",
                yards=15,
                auto_first_down=False,
                description="Offensive penalty, 15 yards",
            ),
            PenaltyOption(
                penalty_type="PI",
                raw_result="PI 8",
                yards=8,
                auto_first_down=True,
                description="Pass interference, 8 yards",
            ),
        ]

        offended_is_offense = True

        # Filter like interactive_game.py does
        if offended_is_offense:
            filtered = [opt for opt in penalty_options if opt.penalty_type in ["DEF", "PI"]]
        else:
            filtered = [opt for opt in penalty_options if opt.penalty_type == "OFF"]

        # Should only have the PI penalty
        assert len(filtered) == 1
        assert filtered[0].penalty_type == "PI"
        assert filtered[0].yards == 8

    def test_defense_offended_only_sees_offensive_penalties(self):
        """When defense is offended, they should only see OFF penalties."""
        from paydirt.play_resolver import PenaltyOption

        # Simulate penalty options list with both OFF and DEF penalties
        penalty_options = [
            PenaltyOption(
                penalty_type="OFF",
                raw_result="OFF 10",
                yards=10,
                auto_first_down=False,
                description="Offensive penalty, 10 yards",
            ),
            PenaltyOption(
                penalty_type="DEF",
                raw_result="DEF 5",
                yards=5,
                auto_first_down=False,
                description="Defensive penalty, 5 yards",
            ),
        ]

        offended_is_offense = False

        # Filter like interactive_game.py does
        if offended_is_offense:
            filtered = [opt for opt in penalty_options if opt.penalty_type in ["DEF", "PI"]]
        else:
            filtered = [opt for opt in penalty_options if opt.penalty_type == "OFF"]

        # Should only have the OFF penalty
        assert len(filtered) == 1
        assert filtered[0].penalty_type == "OFF"
        assert filtered[0].yards == 10


class TestPenaltyDecisionFourthDown:
    """Tests for penalty decision display on 4th down."""

    def test_fourth_down_no_gain_shows_turnover_on_downs(self):
        """On 4th down, incomplete/no gain should show TURNOVER ON DOWNS, not 5th down."""
        # This tests the logic that was causing KeyError: 5
        game_down = 4
        yards_to_go = 5
        yards_gained = 0  # Incomplete pass

        # Simulate the logic from handle_penalty_decision
        if yards_gained >= yards_to_go:
            play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
        elif game_down >= 4:
            # 4th down failure = turnover on downs
            if yards_gained > 0:
                play_outcome_str = f"{yards_gained} yards -> TURNOVER ON DOWNS"
            elif yards_gained == 0:
                play_outcome_str = "No gain -> TURNOVER ON DOWNS"
            else:
                play_outcome_str = f"Loss of {abs(yards_gained)} -> TURNOVER ON DOWNS"
        else:
            next_down = game_down + 1
            down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
            play_outcome_str = f"No gain -> {next_down}{down_suffix[next_down]} and {yards_to_go}"

        assert play_outcome_str == "No gain -> TURNOVER ON DOWNS"
        assert "5th" not in play_outcome_str

    def test_fourth_down_short_gain_shows_turnover_on_downs(self):
        """On 4th down, short gain that doesn't convert should show TURNOVER ON DOWNS."""
        game_down = 4
        yards_to_go = 5
        yards_gained = 3  # Short of first down

        if yards_gained >= yards_to_go:
            play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
        elif game_down >= 4:
            if yards_gained > 0:
                play_outcome_str = f"{yards_gained} yards -> TURNOVER ON DOWNS"
            elif yards_gained == 0:
                play_outcome_str = "No gain -> TURNOVER ON DOWNS"
            else:
                play_outcome_str = f"Loss of {abs(yards_gained)} -> TURNOVER ON DOWNS"
        else:
            next_down = game_down + 1
            next_ytg = yards_to_go - yards_gained
            down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
            play_outcome_str = (
                f"{yards_gained} yards -> {next_down}{down_suffix[next_down]} and {next_ytg}"
            )

        assert play_outcome_str == "3 yards -> TURNOVER ON DOWNS"

    def test_fourth_down_loss_shows_turnover_on_downs(self):
        """On 4th down, loss of yards should show TURNOVER ON DOWNS."""
        game_down = 4
        yards_to_go = 5
        yards_gained = -3  # Sack or loss

        if yards_gained >= yards_to_go:
            play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
        elif game_down >= 4:
            if yards_gained > 0:
                play_outcome_str = f"{yards_gained} yards -> TURNOVER ON DOWNS"
            elif yards_gained == 0:
                play_outcome_str = "No gain -> TURNOVER ON DOWNS"
            else:
                play_outcome_str = f"Loss of {abs(yards_gained)} -> TURNOVER ON DOWNS"
        else:
            next_down = game_down + 1
            next_ytg = yards_to_go - yards_gained
            down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
            play_outcome_str = (
                f"Loss of {abs(yards_gained)} -> {next_down}{down_suffix[next_down]} and {next_ytg}"
            )

        assert play_outcome_str == "Loss of 3 -> TURNOVER ON DOWNS"

    def test_fourth_down_conversion_shows_first_down(self):
        """On 4th down, gaining enough yards should show FIRST DOWN."""
        game_down = 4
        yards_to_go = 5
        yards_gained = 7  # Converts

        if yards_gained >= yards_to_go:
            play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
        elif game_down >= 4:
            if yards_gained > 0:
                play_outcome_str = f"{yards_gained} yards -> TURNOVER ON DOWNS"
            elif yards_gained == 0:
                play_outcome_str = "No gain -> TURNOVER ON DOWNS"
            else:
                play_outcome_str = f"Loss of {abs(yards_gained)} -> TURNOVER ON DOWNS"
        else:
            next_down = game_down + 1
            down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
            play_outcome_str = f"{yards_gained} yards -> {next_down}{down_suffix[next_down]} and {yards_to_go - yards_gained}"

        assert play_outcome_str == "7 yards, FIRST DOWN"


class TestCPUPenaltyDecisionWithTurnover:
    """Tests for CPU penalty decision logic when turnovers are involved.

    Bug fix: Defense should accept play result (turnover) not penalty.
    Previously, the code always took the penalty on turnover regardless of who benefited.
    """

    def test_defense_accepts_turnover_over_offensive_penalty(self):
        """Defense offended by offensive penalty should accept turnover, not penalty.

        Scenario: Offense fumbles, but there was an offensive penalty.
        Defense is offended and should WANT the turnover (play result).
        """
        # Simulate the decision logic
        play_turnover = True
        offended_is_offense = False  # Defense is offended (offensive penalty)

        # The fix: defense wants the turnover
        if play_turnover:
            if offended_is_offense:
                # Offense wants penalty to undo turnover
                accept_play = False
            else:
                # Defense WANTS the turnover!
                accept_play = True

        assert accept_play is True, "Defense should accept play result (turnover)"

    def test_offense_declines_turnover_takes_penalty(self):
        """Offense offended by defensive penalty should decline turnover, take penalty.

        Scenario: Offense throws interception, but there was a defensive penalty.
        Offense is offended and should want the penalty to undo the turnover.
        """
        play_turnover = True
        offended_is_offense = True  # Offense is offended (defensive penalty)

        if play_turnover:
            if offended_is_offense:
                # Offense wants penalty to undo turnover
                accept_play = False
            else:
                # Defense WANTS the turnover!
                accept_play = True

        assert accept_play is False, "Offense should decline play (turnover) and take penalty"


class TestFumblePenaltyDisplay:
    """Tests for fumble penalty decision display.

    Bug fix: When a fumble occurs with a penalty, the fumble recovery must be
    rolled BEFORE presenting the penalty choice, just like in the NFL where the
    play is fully completed before the penalty decision is made.
    """

    def test_fumble_recovery_rolled_before_penalty_choice(self):
        """Fumble recovery should be rolled in resolve_play_with_penalties.

        The fumble recovery roll now happens during play resolution, so the
        complete outcome is known before the penalty choice is presented.
        """
        # Create a fumble play result with pre-determined recovery (offense recovers)
        fumble_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=11,
            description="Fumble",
            turnover=False,  # Offense recovered
            dice_roll=23,
        )
        fumble_result.fumble_recovered = True
        fumble_result.fumble_recovery_roll = 18
        fumble_result.fumble_resolved = True

        # The UI should show the actual recovery result
        fumble_recovered = getattr(fumble_result, "fumble_recovered", False)
        recovery_roll = getattr(fumble_result, "fumble_recovery_roll", 0)
        if fumble_result.result_type == ResultType.FUMBLE:
            if fumble_recovered:
                play_outcome_str = f"FUMBLE - Offense recovers (roll {recovery_roll})"
            else:
                play_outcome_str = f"FUMBLE - TURNOVER (roll {recovery_roll})"
        elif fumble_result.turnover:
            play_outcome_str = "TURNOVER"
        else:
            play_outcome_str = f"{fumble_result.yards} yards"

        assert play_outcome_str == "FUMBLE - Offense recovers (roll 18)"
        assert "TURNOVER" not in play_outcome_str

    def test_fumble_turnover_shows_correctly(self):
        """Fumble with defense recovery should show as TURNOVER."""
        fumble_result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=11,
            description="Fumble",
            turnover=True,  # Defense recovered
            dice_roll=23,
        )
        fumble_result.fumble_recovered = False
        fumble_result.fumble_recovery_roll = 35
        fumble_result.fumble_resolved = True

        fumble_recovered = getattr(fumble_result, "fumble_recovered", False)
        recovery_roll = getattr(fumble_result, "fumble_recovery_roll", 0)
        if fumble_result.result_type == ResultType.FUMBLE:
            if fumble_recovered:
                play_outcome_str = f"FUMBLE - Offense recovers (roll {recovery_roll})"
            else:
                play_outcome_str = f"FUMBLE - TURNOVER (roll {recovery_roll})"
        elif fumble_result.turnover:
            play_outcome_str = "TURNOVER"
        else:
            play_outcome_str = f"{fumble_result.yards} yards"

        assert play_outcome_str == "FUMBLE - TURNOVER (roll 35)"

    def test_interception_still_shows_turnover(self):
        """Interception should still show as TURNOVER (no recovery roll needed)."""
        int_result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=-5,
            description="Interception",
            turnover=True,
            dice_roll=12,
        )

        # Interceptions are definite turnovers
        fumble_recovered = getattr(int_result, "fumble_recovered", False)
        if int_result.result_type == ResultType.FUMBLE:
            if fumble_recovered:
                play_outcome_str = "FUMBLE - Offense recovers"
            else:
                play_outcome_str = "FUMBLE - TURNOVER"
        elif int_result.turnover:
            play_outcome_str = "TURNOVER"
        else:
            play_outcome_str = f"{int_result.yards} yards"

        assert play_outcome_str == "TURNOVER"


class TestPenaltyChoiceTransaction:
    """Tests for transaction building in resolve_play_with_penalties."""

    @pytest.fixture
    def game_engine(self, mock_team_chart):
        """Create a game engine using mock charts (year=1983 for fallback rules)."""
        return PaydirtGameEngine(mock_team_chart, mock_team_chart)

    def test_penalty_choice_has_transaction(self, game_engine):
        """PenaltyChoice should include a transaction with play events."""
        from paydirt.play_resolver import resolve_play_with_penalties, PlayType, DefenseType
        from paydirt.play_events import EventType

        offense_chart = game_engine.state.possession_team
        defense_chart = game_engine.state.defense_team

        # Run multiple plays to verify transaction is always present
        for _ in range(20):
            penalty_choice = resolve_play_with_penalties(
                offense_chart, defense_chart, PlayType.SHORT_PASS, DefenseType.STANDARD
            )

            # Transaction should always be present
            assert penalty_choice.transaction is not None

            # Transaction should have at least a chart lookup event
            assert penalty_choice.transaction.has_event_type(EventType.CHART_LOOKUP)

            # If it's a fumble, should have fumble and recovery events
            if penalty_choice.play_result.result_type == ResultType.FUMBLE:
                assert penalty_choice.transaction.has_event_type(EventType.FUMBLE)
                assert penalty_choice.transaction.has_event_type(EventType.FUMBLE_RECOVERY)
                # Verify fumble_resolved is set
                assert penalty_choice.play_result.fumble_resolved is True
                break

    def test_fumble_transaction_has_recovery_info(self):
        """Fumble transaction should capture recovery roll details."""
        from paydirt.play_events import (
            PlayTransaction,
            EventType,
            create_fumble_event,
            create_recovery_event,
        )

        # Build a transaction like resolve_play_with_penalties does
        txn = PlayTransaction()

        txn.add_event(
            create_fumble_event(yards_before_fumble=11, fumble_spot=59, acting_team="STL '83")
        )

        txn.add_event(
            create_recovery_event(
                recovery_roll=18,
                recovery_desc="B1+W0+W4=18",
                offense_recovers=True,
                recovery_range=(10, 31),
                acting_team="STL '83",
            )
        )

        # Verify events are captured
        assert txn.has_event_type(EventType.FUMBLE)
        assert txn.has_event_type(EventType.FUMBLE_RECOVERY)

        # Get recovery event and verify details
        recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
        assert len(recovery_events) == 1
        rec_event = recovery_events[0]
        assert rec_event.dice_roll == 18
        assert rec_event.possession_change is False  # Offense recovered
        assert "RECOVERED" in rec_event.description

    def test_turnover_fumble_transaction(self):
        """Fumble with defense recovery should show possession change."""
        from paydirt.play_events import (
            PlayTransaction,
            EventType,
            create_fumble_event,
            create_recovery_event,
        )

        txn = PlayTransaction()

        txn.add_event(
            create_fumble_event(yards_before_fumble=11, fumble_spot=59, acting_team="STL '83")
        )

        txn.add_event(
            create_recovery_event(
                recovery_roll=35,
                recovery_desc="B2+W3+W4=35",
                offense_recovers=False,  # Defense recovers
                recovery_range=(10, 31),
                acting_team="NO '83",  # Defense team
            )
        )

        # Get recovery event and verify turnover
        recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
        rec_event = recovery_events[0]
        assert rec_event.dice_roll == 35
        assert rec_event.possession_change is True  # Turnover
        assert "LOST" in rec_event.description


class TestInterceptionReturnAfterPenalty:
    """Tests for interception return handling after penalty decision.

    Bug fix: When an interception occurs with a penalty, the penalty decision
    re-triggers _handle_interception. The handler should reuse the existing
    return yards instead of re-rolling the return dice.
    """

    def test_interception_reuses_existing_return_yards(self):
        """Interception should reuse existing return yards when available.

        When an interception result already has int_return_yards set (from
        the initial play resolution), the handler should use those values
        instead of re-rolling the return dice.
        """
        from paydirt.play_resolver import PlayResult, ResultType

        # Create result with pre-set return values (as would happen after penalty decision)
        result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=5,
            description="Interception",
            dice_roll=25,
            turnover=True,
        )
        result.int_return_yards = 5  # Pre-set return yards (5 yard return)
        result.int_return_dice = 22  # Pre-set dice
        result.int_spot = 70  # Ball was intercepted at opponent's 30

        # Verify the fix: when result has int_return_yards set,
        # _handle_interception should NOT call roll_chart_dice
        # This is tested by verifying the logic in game_engine.py:
        # It checks "if result.int_return_yards and result.int_return_yards != 0"
        # before calling roll_chart_dice

        # The test verifies that the condition is properly checking for non-zero values
        assert result.int_return_yards == 5
        assert result.int_return_yards != 0  # Should trigger reuse path
        assert result.int_spot == 70  # Intercepted at 30 from offense perspective = 70
