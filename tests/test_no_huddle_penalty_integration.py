"""
Integration tests for No Huddle penalty handling through resolve_penalty and the game engine.

These tests verify the full pipeline:
  roll_no_huddle_penalty_yardage → resolve_penalty → game engine run_play

Covers the complete No Huddle Penalty Chart matrix:

  +----------------+----------------+----------------+----------+------------+
  | PENALTY        | OFF=S          | DEF=S          | OFF=R    | DEF=R      |
  | YARDAGE        |                |                |          |            |
  +----------------+----------------+----------------+----------+------------+
  | 5 yards        | 10-11 (FS*)    | 10-14 OFF 5    | 10+      | --         |
  |                | 12-29          | 15-24 DEF 5    |          |            |
  +----------------+----------------+----------------+----------+------------+
  | 5Y yards       | --             | 25-29++        | --       | 11-16++    |
  +----------------+----------------+----------------+----------+------------+
  | 5X yards       | --             | 30-35**        | --       | 17-19**    |
  +----------------+----------------+----------------+----------+------------+
  | 10 yards       | 30-36          | --             | 11-34    | --         |
  +----------------+----------------+----------------+----------+------------+
  | 15 yards       | 37-39          | 36-39**++      | 35-39    | 20-39**++  |
  +----------------+----------------+----------------+----------+------------+
  *   No Penalty - Bad Snap (F-13 punt, F-7 FG, F-2 all other plays)
  **  Automatic first down
  +   Prior to the change of possession
  ++  Marked from end of any gain or previous spot (Off. Player's Choice)
"""
import pytest
from unittest.mock import patch, MagicMock

from paydirt.penalty_handler import (
    PenaltyType, PenaltyResult, resolve_penalty
)
from paydirt.play_resolver import PlayType, DefenseType, ResultType, PlayResult
from paydirt.game_engine import PaydirtGameEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def game():
    """Create a game engine with mock team charts."""
    home_chart = MagicMock()
    away_chart = MagicMock()

    home_chart.peripheral = MagicMock()
    home_chart.peripheral.team_name = "Home Team"
    home_chart.peripheral.short_name = "HOM"
    home_chart.peripheral.fumble_recovered_range = (10, 15)
    away_chart.peripheral = MagicMock()
    away_chart.peripheral.team_name = "Away Team"
    away_chart.peripheral.short_name = "AWY"
    away_chart.peripheral.fumble_recovered_range = (10, 15)

    game = PaydirtGameEngine(home_chart, away_chart)
    return game


def _make_off_penalty_result(raw="OFF S"):
    """Helper to create an offensive penalty PlayResult."""
    return PlayResult(
        result_type=ResultType.PENALTY_OFFENSE,
        yards=0,
        description="Offensive penalty",
        raw_result=raw,
    )


def _make_def_penalty_result(raw="DEF S"):
    """Helper to create a defensive penalty PlayResult."""
    return PlayResult(
        result_type=ResultType.PENALTY_DEFENSE,
        yards=0,
        description="Defensive penalty",
        raw_result=raw,
    )


# ===========================================================================
# Part 1: resolve_penalty integration (penalty_handler level)
# ===========================================================================

class TestResolvePenaltyNoHuddle_OFF_S:
    """resolve_penalty with no_huddle=True for OFF=S penalties."""

    @pytest.mark.parametrize("roll,play_type,expected_fumble_yards", [
        (10, "normal", -2),
        (11, "normal", -2),
        (10, "punt", -13),
        (11, "punt", -13),
        (10, "field_goal", -7),
        (11, "field_goal", -7),
    ])
    def test_bad_snap_returns_immediately(self, roll, play_type, expected_fumble_yards):
        """Rolls 10-11: bad snap returns immediately with is_bad_snap=True and correct fumble yards."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True, play_type=play_type
            )

        assert result.is_bad_snap is True
        assert result.fumble_yards == expected_fumble_yards
        assert "BAD SNAP" in result.description
        # Position unchanged — caller handles fumble
        assert new_pos == 50
        assert new_down == 2
        assert new_ytg == 10
        assert first_down is False

    @pytest.mark.parametrize("roll", [12, 20, 29])
    def test_12_29_is_5_yards(self, roll):
        """Rolls 12-29: 5-yard offensive penalty, ball moves back 5."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.is_bad_snap is False
        assert result.is_false_start is False
        assert result.yards == 5
        assert new_pos == 45  # 50 - 5
        assert new_down == 2  # Repeat down
        assert new_ytg == 15  # 10 + 5
        assert first_down is False

    @pytest.mark.parametrize("roll", [30, 33, 36])
    def test_30_36_is_10_yards(self, roll):
        """Rolls 30-36: 10-yard offensive penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=1,
                no_huddle=True
            )

        assert result.yards == 10
        assert new_pos == 40  # 50 - 10
        assert new_ytg == 20  # 10 + 10

    @pytest.mark.parametrize("roll", [37, 38, 39])
    def test_37_39_is_15_yards(self, roll):
        """Rolls 37-39: 15-yard offensive penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=1,
                no_huddle=True
            )

        assert result.yards == 15
        assert new_pos == 35  # 50 - 15


class TestResolvePenaltyNoHuddle_DEF_S:
    """resolve_penalty with no_huddle=True for DEF=S penalties."""

    @pytest.mark.parametrize("roll", [10, 11, 12, 13, 14])
    def test_false_start_flips_to_off_5(self, roll):
        """Rolls 10-14: false start — DEF penalty becomes OFF 5 penalty."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.is_false_start is True
        assert result.penalty_type == PenaltyType.OFFENSIVE_S  # Flipped
        assert result.yards == 5
        assert "FALSE START" in result.description
        # Applied as offensive penalty: ball goes back, repeat down
        assert new_pos == 45  # 50 - 5
        assert new_down == 2  # Repeat down
        assert new_ytg == 15  # 10 + 5
        assert first_down is False

    @pytest.mark.parametrize("roll", [15, 20, 24])
    def test_15_24_is_def_5(self, roll):
        """Rolls 15-24: normal DEF 5 yards."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.is_false_start is False
        assert result.yards == 5
        assert new_pos == 55  # 50 + 5
        assert new_ytg == 5  # 10 - 5
        assert new_down == 2

    @pytest.mark.parametrize("roll", [25, 27, 29])
    def test_25_29_is_5y(self, roll):
        """Rolls 25-29: 5Y yards (mark from end of gain)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.yards == 5
        assert result.mark_from_end_of_gain is True
        assert result.automatic_first_down is False

    @pytest.mark.parametrize("roll", [30, 33, 35])
    def test_30_35_is_5x_auto_first_down(self, roll):
        """Rolls 30-35: 5X (auto first down + mark from gain)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=50, yards_to_go=10, down=3,
                no_huddle=True
            )

        assert result.yards == 5
        assert result.automatic_first_down is True
        assert result.mark_from_end_of_gain is True
        assert first_down is True
        assert new_down == 1
        assert new_ytg == 10

    @pytest.mark.parametrize("roll", [36, 37, 39])
    def test_36_39_is_15_auto_first_down(self, roll):
        """Rolls 36-39: 15 yards + auto first down + mark from gain."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=50, yards_to_go=10, down=3,
                no_huddle=True
            )

        assert result.yards == 15
        assert result.automatic_first_down is True
        assert result.mark_from_end_of_gain is True
        assert first_down is True
        assert new_pos == 65  # 50 + 15
        assert new_down == 1


class TestResolvePenaltyNoHuddle_OFF_R:
    """resolve_penalty with no_huddle=True for OFF=R penalties."""

    def test_roll_10_is_5_yards(self):
        """Roll 10: 5 yards (prior to change of possession)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF R", ball_position=50, yards_to_go=10, down=1,
                no_huddle=True
            )

        assert result.yards == 5
        assert new_pos == 45  # OFF penalty = ball back

    @pytest.mark.parametrize("roll", [11, 20, 34])
    def test_11_34_is_10_yards(self, roll):
        """Rolls 11-34: 10 yards."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF R", ball_position=50, yards_to_go=10, down=1,
                no_huddle=True
            )

        assert result.yards == 10
        assert new_pos == 40

    @pytest.mark.parametrize("roll", [35, 37, 39])
    def test_35_39_is_15_yards(self, roll):
        """Rolls 35-39: 15 yards."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF R", ball_position=50, yards_to_go=10, down=1,
                no_huddle=True
            )

        assert result.yards == 15
        assert new_pos == 35


class TestResolvePenaltyNoHuddle_DEF_R:
    """resolve_penalty with no_huddle=True for DEF=R penalties."""

    def test_roll_10_is_5_yards_no_auto_fd(self):
        """Roll 10: 5 yards (-- in table), no auto first down."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF R", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.yards == 5
        assert result.mark_from_end_of_gain is True
        assert result.automatic_first_down is False

    @pytest.mark.parametrize("roll", [11, 14, 16])
    def test_11_16_is_5y(self, roll):
        """Rolls 11-16: 5Y (mark from gain, no auto first down)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF R", ball_position=50, yards_to_go=10, down=2,
                no_huddle=True
            )

        assert result.yards == 5
        assert result.mark_from_end_of_gain is True
        assert result.automatic_first_down is False

    @pytest.mark.parametrize("roll", [17, 18, 19])
    def test_17_19_is_5x_auto_first_down(self, roll):
        """Rolls 17-19: 5X (auto first down + mark from gain)."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF R", ball_position=50, yards_to_go=10, down=3,
                no_huddle=True
            )

        assert result.yards == 5
        assert result.automatic_first_down is True
        assert first_down is True
        assert new_down == 1

    @pytest.mark.parametrize("roll", [20, 30, 39])
    def test_20_39_is_15_auto_first_down(self, roll):
        """Rolls 20-39: 15 yards + auto first down + mark from gain."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF R", ball_position=50, yards_to_go=10, down=3,
                no_huddle=True
            )

        assert result.yards == 15
        assert result.automatic_first_down is True
        assert first_down is True
        assert new_pos == 65  # 50 + 15


# ===========================================================================
# Part 2: resolve_penalty edge cases
# ===========================================================================

class TestResolvePenaltyNoHuddleEdgeCases:
    """Edge cases for no-huddle penalty resolution."""

    def test_half_distance_rule_applies_to_no_huddle(self):
        """Half-distance rule should still apply to no-huddle penalties."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(38, "dice=38")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=8, yards_to_go=10, down=1,
                no_huddle=True
            )

        # 15-yard penalty at the 8 should be half-distance (4 yards)
        assert new_pos == 4  # 8 - 4
        assert "half-distance" in result.description

    def test_false_start_half_distance(self):
        """False start (OFF 5) should apply half-distance when close to own goal."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(12, "dice=12")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "DEF S", ball_position=3, yards_to_go=10, down=1,
                no_huddle=True
            )

        # False start 5 yards at the 3 → half-distance = 1 yard
        assert result.is_false_start is True
        assert new_pos == 2  # 3 - 1

    def test_no_huddle_false_does_not_use_nh_chart(self):
        """When no_huddle=False, resolve_penalty uses normal chart, not no-huddle."""
        with patch('paydirt.penalty_handler.roll_penalty_yardage') as mock_normal:
            mock_normal.return_value = PenaltyResult(
                penalty_type=PenaltyType.OFFENSIVE_S,
                yards=5,
                description="Normal penalty",
                dice_roll=15,
            )
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=1,
                no_huddle=False
            )

        mock_normal.assert_called_once()
        assert result.is_bad_snap is False

    def test_chart_yards_overrides_no_huddle(self):
        """When chart_yards is provided, no_huddle is bypassed (explicit yardage)."""
        with patch('paydirt.penalty_handler.roll_no_huddle_penalty_yardage') as mock_nh:
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=50, yards_to_go=10, down=1,
                chart_yards=10, no_huddle=True
            )

        # chart_yards takes priority — no-huddle chart should not be called
        mock_nh.assert_not_called()
        assert result.yards == 10

    def test_bad_snap_preserves_ball_position(self):
        """Bad snap should NOT move the ball — the caller handles the fumble."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            result, new_pos, new_down, new_ytg, first_down = resolve_penalty(
                "OFF S", ball_position=75, yards_to_go=7, down=3,
                no_huddle=True, play_type="normal"
            )

        assert result.is_bad_snap is True
        assert new_pos == 75  # Unchanged
        assert new_down == 3  # Unchanged
        assert new_ytg == 7   # Unchanged


# ===========================================================================
# Part 3: Game engine integration
# ===========================================================================

class TestGameEngineNoHuddleBadSnap:
    """Game engine run_play with no_huddle=True + offensive penalty → bad snap."""

    def test_bad_snap_triggers_fumble_handling(self, game):
        """OFF penalty + no_huddle + roll 10-11 should trigger fumble handling."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        off_penalty = _make_off_penalty_result("OFF S")

        with patch('paydirt.game_engine.resolve_play', return_value=off_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")), \
             patch('paydirt.game_engine.roll_chart_dice', return_value=(12, "dice=12")):
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=True
            )

        assert "BAD SNAP" in outcome.description

    def test_bad_snap_punt_fumble_yards_at_resolve_level(self):
        """Bad snap on punt uses F-13 — tested at resolve_penalty level.
        
        Note: Punt/FG plays use _handle_punt/_handle_field_goal which bypass
        run_play's PENALTY_OFFENSE block. Bad snap punt/FG yardage is verified
        in TestResolvePenaltyNoHuddle_OFF_S.test_bad_snap_returns_immediately.
        """
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            result, _, _, _, _ = resolve_penalty(
                "OFF S", ball_position=30, no_huddle=True, play_type="punt"
            )

        assert result.is_bad_snap is True
        assert result.fumble_yards == -13

    def test_bad_snap_fg_fumble_yards_at_resolve_level(self):
        """Bad snap on FG uses F-7 — tested at resolve_penalty level.
        
        Note: Punt/FG plays use _handle_punt/_handle_field_goal which bypass
        run_play's PENALTY_OFFENSE block. Bad snap punt/FG yardage is verified
        in TestResolvePenaltyNoHuddle_OFF_S.test_bad_snap_returns_immediately.
        """
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            result, _, _, _, _ = resolve_penalty(
                "OFF S", ball_position=80, no_huddle=True, play_type="field_goal"
            )

        assert result.is_bad_snap is True
        assert result.fumble_yards == -7


class TestGameEngineNoHuddleFalseStart:
    """Game engine run_play with no_huddle=True + defensive penalty → false start."""

    def test_false_start_flips_to_offensive_penalty(self, game):
        """DEF penalty + no_huddle + roll 10-14 should become OFF 5 (false start)."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        def_penalty = _make_def_penalty_result("DEF S")

        with patch('paydirt.game_engine.resolve_play', return_value=def_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(12, "dice=12")):
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=True
            )

        assert "FALSE START" in outcome.description
        # Ball should move BACK (offensive penalty)
        assert game.state.ball_position == 45  # 50 - 5
        # Repeat the down
        assert game.state.down == 2
        # Yards to go increases
        assert game.state.yards_to_go == 13  # 8 + 5
        # Counted as offensive penalty
        assert game.state.offense_stats.penalties == 1
        assert game.state.defense_stats.penalties == 0

    def test_false_start_yards_reported_negative(self, game):
        """False start should report negative yards (offensive penalty direction)."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        def_penalty = _make_def_penalty_result("DEF S")

        with patch('paydirt.game_engine.resolve_play', return_value=def_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(10, "dice=10")):
            outcome = game.run_play(
                PlayType.LINE_PLUNGE, DefenseType.STANDARD,
                no_huddle=True
            )

        assert outcome.yards_gained == -5


class TestGameEngineNoHuddleNormalPenalties:
    """Game engine run_play with no_huddle=True + normal penalty ranges."""

    def test_off_s_normal_penalty_no_huddle(self, game):
        """OFF penalty + no_huddle + roll 20 → normal 5-yard offensive penalty."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        off_penalty = _make_off_penalty_result("OFF S")

        with patch('paydirt.game_engine.resolve_play', return_value=off_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(20, "dice=20")):
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=True
            )

        assert game.state.ball_position == 45  # 50 - 5
        assert game.state.offense_stats.penalties == 1
        assert outcome.yards_gained == -5

    def test_def_s_normal_penalty_no_huddle(self, game):
        """DEF penalty + no_huddle + roll 20 → normal 5-yard defensive penalty."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 2
        game.state.yards_to_go = 8
        game.state.is_home_possession = True

        def_penalty = _make_def_penalty_result("DEF S")

        with patch('paydirt.game_engine.resolve_play', return_value=def_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(20, "dice=20")):
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=True
            )

        assert game.state.ball_position == 55  # 50 + 5
        assert game.state.defense_stats.penalties == 1
        assert outcome.yards_gained == 5

    def test_def_s_auto_first_down_no_huddle(self, game):
        """DEF penalty + no_huddle + roll 32 → 5X auto first down."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 3
        game.state.yards_to_go = 12
        game.state.is_home_possession = True

        def_penalty = _make_def_penalty_result("DEF S")

        with patch('paydirt.game_engine.resolve_play', return_value=def_penalty), \
             patch('paydirt.penalty_handler.roll_chart_dice', return_value=(32, "dice=32")):
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=True
            )

        assert game.state.down == 1
        assert game.state.yards_to_go == 10
        assert outcome.first_down is True

    def test_no_huddle_false_means_normal_chart(self, game):
        """When no_huddle=False, penalty uses normal chart (no bad snap/false start)."""
        game.state.quarter = 2
        game.state.time_remaining = 5.0
        game.state.ball_position = 50
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.is_home_possession = True

        off_penalty = _make_off_penalty_result("OFF S")

        with patch('paydirt.game_engine.resolve_play', return_value=off_penalty), \
             patch('paydirt.penalty_handler.roll_penalty_yardage') as mock_normal:
            mock_normal.return_value = PenaltyResult(
                penalty_type=PenaltyType.OFFENSIVE_S,
                yards=5,
                description="Normal 5-yard penalty",
                dice_roll=15,
            )
            outcome = game.run_play(
                PlayType.SHORT_PASS, DefenseType.STANDARD,
                no_huddle=False
            )

        mock_normal.assert_called_once()
        assert "BAD SNAP" not in outcome.description
        assert "FALSE START" not in outcome.description


# ===========================================================================
# Part 4: Boundary dice roll coverage
# ===========================================================================

class TestNoHuddleBoundaryRolls:
    """Test boundary dice rolls where ranges change for each penalty type."""

    @pytest.mark.parametrize("roll,expected_bad_snap", [
        (10, True),   # Start of bad snap range
        (11, True),   # End of bad snap range
        (12, False),  # First roll AFTER bad snap → normal 5 yd
    ])
    def test_off_s_bad_snap_boundary(self, roll, expected_bad_snap):
        """OFF=S boundary: 10-11 bad snap, 12+ normal."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "OFF S", ball_position=50, no_huddle=True
            )

        assert result.is_bad_snap is expected_bad_snap

    @pytest.mark.parametrize("roll,expected_false_start", [
        (10, True),   # Start of false start range
        (14, True),   # End of false start range
        (15, False),  # First roll AFTER false start → normal DEF 5
    ])
    def test_def_s_false_start_boundary(self, roll, expected_false_start):
        """DEF=S boundary: 10-14 false start, 15+ normal."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "DEF S", ball_position=50, no_huddle=True
            )

        assert result.is_false_start is expected_false_start

    @pytest.mark.parametrize("roll,expected_yards", [
        (29, 5),   # Last 5-yard roll
        (30, 10),  # First 10-yard roll
        (36, 10),  # Last 10-yard roll
        (37, 15),  # First 15-yard roll
    ])
    def test_off_s_yardage_boundaries(self, roll, expected_yards):
        """OFF=S yardage boundaries: 12-29=5yd, 30-36=10yd, 37-39=15yd."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "OFF S", ball_position=50, no_huddle=True
            )

        assert result.yards == expected_yards

    @pytest.mark.parametrize("roll,expected_yards,expected_auto_fd", [
        (24, 5, False),   # Last DEF 5 roll
        (25, 5, False),   # First 5Y roll (mark from gain, no auto FD)
        (29, 5, False),   # Last 5Y roll
        (30, 5, True),    # First 5X roll (auto first down)
        (35, 5, True),    # Last 5X roll
        (36, 15, True),   # First 15-yard roll
    ])
    def test_def_s_yardage_boundaries(self, roll, expected_yards, expected_auto_fd):
        """DEF=S yardage boundaries: 15-24=5, 25-29=5Y, 30-35=5X, 36-39=15."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "DEF S", ball_position=50, no_huddle=True
            )

        assert result.yards == expected_yards
        assert result.automatic_first_down is expected_auto_fd

    @pytest.mark.parametrize("roll,expected_yards", [
        (10, 5),   # Single roll for 5 yards
        (11, 10),  # First 10-yard roll
        (34, 10),  # Last 10-yard roll
        (35, 15),  # First 15-yard roll
    ])
    def test_off_r_yardage_boundaries(self, roll, expected_yards):
        """OFF=R yardage boundaries: 10=5, 11-34=10, 35-39=15."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "OFF R", ball_position=50, no_huddle=True
            )

        assert result.yards == expected_yards

    @pytest.mark.parametrize("roll,expected_yards,expected_auto_fd", [
        (10, 5, False),   # Roll 10: --, 5 yards
        (11, 5, False),   # First 5Y roll
        (16, 5, False),   # Last 5Y roll
        (17, 5, True),    # First 5X roll
        (19, 5, True),    # Last 5X roll
        (20, 15, True),   # First 15-yard roll
        (39, 15, True),   # Last 15-yard roll
    ])
    def test_def_r_yardage_boundaries(self, roll, expected_yards, expected_auto_fd):
        """DEF=R yardage boundaries: 10=--, 11-16=5Y, 17-19=5X, 20-39=15."""
        with patch('paydirt.penalty_handler.roll_chart_dice', return_value=(roll, f"dice={roll}")):
            result, _, _, _, _ = resolve_penalty(
                "DEF R", ball_position=50, no_huddle=True
            )

        assert result.yards == expected_yards
        assert result.automatic_first_down is expected_auto_fd
