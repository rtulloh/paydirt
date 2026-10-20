"""Interception-return chart penalties, fumbles and recovery rolls (RULE-015, RULE-016).

The Int. Return chart is used by interception returns, fumble advances
(recovery 17–19 for the offense, 37–39 for the defense) and blocked-kick
returns. OFF/DEF cells reroll and are assessed automatically against the end
of the return (rule-book example: intercepted at own 13, OFF 10 then 52-yard
return → 13 + 52 - 10 = own 55). Fumble cells use the returning team's
recovery roll. Recovery 39 on an ordinary fumble is a chart return, not an
automatic touchdown; 19/39 stay automatic only on blocked kicks.
Public 2026 charts with explicit synthetic cells; recovery range (10, 27).
"""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


def rolls(*values):
    return [(value, f"Roll{value}") for value in values]


def game_with_return_chart(cells: dict, returning_home: bool) -> object:
    """Home has the ball; the away team (returning on an INT) or home (fumble advance) owns the cells."""
    game = make_sample_game()
    game.state.is_home_possession = True
    chart = game.state.home_chart if returning_home else game.state.away_chart
    chart.special_teams.interception_return.clear()
    chart.special_teams.interception_return.update(cells)
    chart.peripheral.fumble_recovered_range = (10, 27)
    game.state.home_chart.peripheral.fumble_recovered_range = (10, 27)
    return game


def run(game, mocked_result: PlayResult, *dice):
    with (patch("paydirt.game_engine.resolve_play", return_value=mocked_result),
          patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(*dice)) as mock,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.run_play(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert mock.call_count == len(dice), "every listed roll is consumed and no other"
    return outcome


def interception(depth: int = 7) -> PlayResult:
    return PlayResult(result_type=ResultType.INTERCEPTION, yards=depth, turnover=True,
                      raw_result=f"INT {depth}", dice_roll=10)


def fumble(yards: int = 3) -> PlayResult:
    return PlayResult(result_type=ResultType.FUMBLE, yards=yards, turnover=True,
                      raw_result=f"F + {yards}", dice_roll=10)


class TestInterceptionReturns:
    def setup_method(self):
        # Intercepted 7 yards past the 80 → away team's own 13, as in the rule book.
        self.start = 80

    def test_rule_book_example_off_10_then_52_yard_return(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "52"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20)
        assert outcome.pending_penalty_decision is False
        assert game.state.is_home_possession is False
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (55, 1, 10)
        assert outcome.turnover is True
        assert outcome.touchdown is False
        assert (game.state.away_stats.penalties, game.state.away_stats.penalty_yards) == (1, 10)
        assert 'Ret:35→"OFF 10"' in outcome.description
        assert 'Ret reroll:20→"52"' in outcome.description
        assert outcome.result.int_return_dice == 35
        assert outcome.result.int_return_yards == 42  # Net of the penalty.

    def test_def_foul_on_the_return_adds_yards(self) -> None:
        game = game_with_return_chart({35: "DEF 15", 20: "20"}, returning_home=False)
        game.state.ball_position = self.start
        run(game, interception(), 35, 20)
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 48  # 13 + 20 + 15
        assert (game.state.home_stats.penalties, game.state.home_stats.penalty_yards) == (1, 15)
        assert game.state.away_stats.penalties == 0

    def test_off_foul_wipes_out_a_return_touchdown(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "TD"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20)
        assert outcome.touchdown is False
        assert game.state.away_score == 0
        assert game.state.ball_position == 90
        assert game.state.is_home_possession is False

    def test_def_foul_leaves_a_return_touchdown_standing(self) -> None:
        game = game_with_return_chart({35: "DEF 15", 20: "TD"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20)
        assert outcome.touchdown is True
        assert game.state.away_score == 6

    def test_def_foul_near_the_goal_is_half_the_distance(self) -> None:
        game = game_with_return_chart({35: "DEF 15", 20: "82"}, returning_home=False)  # 13 + 82 = 95
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20)
        assert outcome.touchdown is False
        assert game.state.ball_position == 97

    def test_offsetting_fouls_nullify_the_play_and_replay_the_down(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "DEF 15"}, returning_home=False)
        game.state.ball_position = self.start
        game.state.down, game.state.yards_to_go = 2, 7
        time_before = game.state.time_remaining
        outcome = run(game, interception(), 35, 20)
        assert game.state.is_home_possession is True, "the interception is erased"
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (80, 2, 7)
        assert outcome.turnover is False
        assert game.state.home_stats.turnovers == 0
        assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
        assert "OFFSETTING" in outcome.description.upper()
        assert round((time_before - game.state.time_remaining) * 60) == 10

    def test_same_type_rerolls_take_the_larger_penalty(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 36: "OFF 15", 20: "52"}, returning_home=False)
        game.state.ball_position = self.start
        run(game, interception(), 35, 36, 20)
        assert game.state.ball_position == 50  # 13 + 52 - 15

    def test_fumble_on_the_return_recovered_by_the_returner(self) -> None:
        game = game_with_return_chart({35: "F + 29"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20)  # Recovery 20 → recovered.
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 42  # 13 + 29
        assert "FUMBLE" in outcome.description.upper()
        assert game.state.away_stats.fumbles_lost == 0

    def test_fumble_on_the_return_recovered_by_the_original_offense(self) -> None:
        game = game_with_return_chart({35: "F + 29"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 30)  # Recovery 30 → lost.
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 58  # 100 - 42
        assert (game.state.down, game.state.yards_to_go) == (1, 10)
        assert game.state.away_stats.fumbles_lost == 1
        assert game.state.away_stats.turnovers == 1
        assert game.state.home_stats.turnovers == 1  # The interception still counts.
        assert "FUMBLE" in outcome.description.upper() and "R:30" in outcome.description

    def test_fumble_after_a_penalty_recovered_by_the_returner_is_assessed(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "F + 29"}, returning_home=False)
        game.state.ball_position = self.start
        run(game, interception(), 35, 20, 20)
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 32  # 13 + 29 - 10
        assert game.state.away_stats.penalties == 1

    def test_fumble_after_a_penalty_recovered_by_the_original_offense_keeps_the_recovery(self) -> None:
        # The recovering team's natural choice is applied: keep the ball, penalty declined.
        game = game_with_return_chart({35: "OFF 10", 20: "F + 29"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 35, 20, 30)
        assert outcome.pending_penalty_decision is False
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 58
        assert game.state.away_stats.penalties == 0
        assert "declined" in outcome.description.lower()

    def test_unparseable_cell_is_a_zero_yard_return_and_shown_raw(self) -> None:
        game = game_with_return_chart({30: "`"}, returning_home=False)
        game.state.ball_position = self.start
        outcome = run(game, interception(), 30)
        assert game.state.ball_position == 13
        assert 'Ret:30→"`"' in outcome.description


class TestFumbleAdvances:
    def test_offense_recovery_17_with_off_foul_is_assessed(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "20"}, returning_home=True)
        game.state.ball_position = 50
        outcome = run(game, fumble(3), 17, 35, 20)  # Fumble at 53, advance 20, back 10.
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 63
        assert outcome.result.fumble_recovered is True
        assert (game.state.home_stats.penalties, game.state.home_stats.penalty_yards) == (1, 10)
        assert 'Ret:35→"OFF 10"' in outcome.description and 'Ret reroll:20→"20"' in outcome.description

    def test_defense_recovery_37_with_def_foul_adds_yards(self) -> None:
        game = game_with_return_chart({35: "DEF 15", 20: "20"}, returning_home=False)
        game.state.ball_position = 50
        run(game, fumble(3), 37, 35, 20)  # Lost at 53 → away's 47; advance 20 + 15.
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 82
        assert (game.state.home_stats.penalties, game.state.home_stats.penalty_yards) == (1, 15)

    def test_recovery_39_is_a_chart_return_not_an_automatic_touchdown(self) -> None:
        game = game_with_return_chart({14: "20"}, returning_home=False)
        game.state.ball_position = 50
        outcome = run(game, fumble(3), 39, 14)
        assert outcome.touchdown is False
        assert game.state.away_score == 0
        assert game.state.is_home_possession is False
        assert game.state.ball_position == 67  # 47 + 20
        assert outcome.result.fumble_return_yards == 20

    def test_recovery_39_with_a_td_cell_scores(self) -> None:
        game = game_with_return_chart({14: "TD"}, returning_home=False)
        game.state.ball_position = 50
        outcome = run(game, fumble(3), 39, 14)
        assert outcome.touchdown is True
        assert game.state.away_score == 6

    def test_recovery_39_with_a_return_fumble_recovered_by_the_offense(self) -> None:
        game = game_with_return_chart({14: "F + 8"}, returning_home=False)
        game.state.ball_position = 50
        run(game, fumble(3), 39, 14, 30)  # Away fumbles at its 55; home recovers.
        assert game.state.is_home_possession is True
        assert game.state.ball_position == 45


class TestBlockedKickReturns:
    @pytest.fixture
    def blocked_fg(self):
        from tests.test_field_goal import create_fg_result
        return create_fg_result(14, "BK -8", is_blocked=True)

    def test_blocked_fg_defense_return_penalty_is_assessed(self, blocked_fg) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "20"}, returning_home=False)
        game.state.ball_position = 75
        with (patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=blocked_fg),
              patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(37, 35, 20)) as mock,
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
        assert mock.call_count == 3
        assert game.state.is_home_possession is False
        # Block spot 75 - 7 - 8 = 60 → defense's 40; +20 return, -10 penalty.
        assert game.state.ball_position == 50
        assert game.state.away_stats.penalties == 1
        assert "blocked" in outcome.description.lower()

    def test_blocked_fg_recovery_39_is_still_an_automatic_touchdown(self, blocked_fg) -> None:
        game = game_with_return_chart({14: "0"}, returning_home=False)
        game.state.ball_position = 75
        with (patch("paydirt.game_engine.resolve_field_goal_with_penalties", return_value=blocked_fg),
              patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(39, 14)),
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
        assert outcome.touchdown is True
        assert game.state.away_score == 6


class TestOffsettingOnOtherReturns:
    def test_fumble_advance_offsetting_fouls_replay_the_down(self) -> None:
        game = game_with_return_chart({35: "OFF 10", 20: "DEF 15"}, returning_home=True)
        game.state.ball_position = 50
        game.state.down, game.state.yards_to_go = 3, 4
        time_before = game.state.time_remaining
        outcome = run(game, fumble(3), 17, 35, 20)
        assert game.state.is_home_possession is True
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (50, 3, 4)
        assert outcome.turnover is False and outcome.first_down is False
        assert "OFFSETTING" in outcome.description.upper()
        assert round((time_before - game.state.time_remaining) * 60) == 10

    def test_blocked_fg_return_offsetting_fouls_replay_the_down(self) -> None:
        from tests.test_field_goal import create_fg_result
        game = game_with_return_chart({35: "OFF 10", 20: "DEF 15"}, returning_home=False)
        game.state.ball_position = 75
        game.state.down, game.state.yards_to_go = 4, 6
        with (patch("paydirt.game_engine.resolve_field_goal_with_penalties",
                    return_value=create_fg_result(14, "BK -8", is_blocked=True)),
              patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls(37, 35, 20)),
              patch("paydirt.game_engine.random.uniform", return_value=8)):
            outcome = game.run_play(PlayType.FIELD_GOAL, None)
        assert game.state.is_home_possession is True
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (75, 4, 6)
        assert outcome.turnover is False
        assert "OFFSETTING" in outcome.description.upper()
