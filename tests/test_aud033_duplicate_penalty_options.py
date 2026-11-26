"""AUD-033: repeated chart fouls must not offer two identical penalty choices.

The offense rerolls after every penalty row, and each penalty row is appended
to the option list. When two offense rolls land on the same foul (the 2026-11-25
play test rolled ``DEF 5`` twice), the offended coach sees two byte-identical
options with the same enforced spot, down and first-down status. The reroll log
must keep every roll, but the enforceable list should carry the foul once.
"""

from unittest.mock import patch

import pytest

from paydirt.chart_loader import (
    DefenseChart,
    OffenseChart,
    PeripheralData,
    SpecialTeamsChart,
    TeamChart,
)
from paydirt.play_resolver import (
    DefenseType,
    PlayType,
    resolve_field_goal_with_penalties,
    resolve_play_with_penalties,
)


def _team_chart() -> TeamChart:
    """Synthetic chart; every chart lookup is patched in these tests."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name="Synthetic",
            team_nickname="Synthetic",
            power_rating=50,
            power_rating_variance=1,
            base_yardage_factor=100,
            reduced_yardage_factor=80,
            fumble_recovered_range=(0, 0),
            fumble_lost_range=(0, 0),
            special_defense="",
            short_name="SYN '83",
        ),
        offense=OffenseChart(line_plunge={10: "5"}, off_tackle={10: "4"}),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(
            interception_return={10: "5"},
            kickoff={},
            kickoff_return={},
            punt={},
            punt_return={},
            field_goal={},
            extra_point_no_good=[],
        ),
        team_dir="",
    )


def _scrimmage(offense_results, defense_result, *, rolls=None):
    """Resolve a scrimmage play with a scripted offense reroll sequence."""
    chart = _team_chart()
    rolls = rolls or [(20 + i, f"B2+W0+W{i}=2{i}") for i in range(len(offense_results))]
    with (
        patch("paydirt.play_resolver.roll_chart_dice") as roll,
        patch("paydirt.play_resolver.get_offense_result") as offense,
        patch("paydirt.play_resolver.get_defense_modifier") as defense,
    ):
        roll.side_effect = list(rolls)
        offense.side_effect = list(offense_results)
        defense.return_value = defense_result
        return resolve_play_with_penalties(
            chart, chart, PlayType.OFF_TACKLE, DefenseType.STANDARD,
        )


class TestScrimmageDuplicates:
    """The reported defect: the same foul rolled twice while rerolling."""

    def test_repeated_identical_defensive_foul_offers_one_option(self):
        """Two ``DEF 5`` rolls during the reroll must collapse to one choice."""
        result = _scrimmage(["DEF 5", "DEF 5", "8"], "3")

        assert result.offended_team == "offense"
        assert len(result.penalty_options) == 1
        option = result.penalty_options[0]
        assert (option.penalty_type, option.yards) == ("DEF", 5)
        assert option.auto_first_down is False

    def test_reroll_log_keeps_every_rolled_row(self):
        """The trace must still show both fouls even though the list deduped."""
        result = _scrimmage(["DEF 5", "DEF 5", "8"], "3")

        penalty_rolls = [entry for entry in result.reroll_log if "(penalty)" in entry]
        assert len(penalty_rolls) == 2
        assert all('DEF 5' in entry for entry in penalty_rolls)
        assert len(result.reroll_log) == 3

    def test_defensive_foul_matching_the_original_defense_row_collapses(self):
        """A rerolled foul identical to the defense chart's own row is one choice."""
        result = _scrimmage(["DEF 5", "8"], "DEF 5")

        assert result.offended_team == "offense"
        assert len(result.penalty_options) == 1

    def test_repeated_identical_offensive_foul_offers_one_option(self):
        """The same collapse applies when the defense is the offended team."""
        result = _scrimmage(["OFF 10", "OFF 10", "8"], "3")

        assert result.offended_team == "defense"
        assert len(result.penalty_options) == 1
        assert result.penalty_options[0].penalty_type == "OFF"


class TestDistinctFoulsArePreserved:
    """Controls: only indistinguishable options may be collapsed."""

    def test_different_yardage_stays_two_options(self):
        result = _scrimmage(["DEF 5", "DEF 15", "8"], "3")

        yardages = sorted(option.yards for option in result.penalty_options)
        assert yardages == [5, 15]

    def test_fifteen_yard_option_keeps_automatic_first_down(self):
        result = _scrimmage(["DEF 5", "DEF 15", "8"], "3")

        fifteen = next(option for option in result.penalty_options if option.yards == 15)
        five = next(option for option in result.penalty_options if option.yards == 5)
        assert fifteen.auto_first_down is True
        assert five.auto_first_down is False

    def test_same_yardage_with_first_down_modifier_stays_two_options(self):
        """An explicit first-down modifier is a different enforceable outcome."""
        result = _scrimmage(["DEF 5", "DEF 5X", "8"], "3")

        assert len(result.penalty_options) == 2
        assert sorted(option.auto_first_down for option in result.penalty_options) == [
            False, True,
        ]

    def test_offsetting_fouls_stay_distinct(self):
        """One offensive and one defensive foul must both remain available."""
        result = _scrimmage(["OFF 5", "8"], "DEF 5")

        assert result.offsetting is True
        assert {option.penalty_type for option in result.penalty_options} == {"OFF", "DEF"}
        assert len(result.penalty_options) == 2

    def test_pass_interference_is_never_collapsed_into_a_defensive_foul(self):
        result = _scrimmage(["DEF 5", "DEF 5", "PI 15"], "3")

        assert result.is_pass_interference is True
        types = sorted(option.penalty_type for option in result.penalty_options)
        assert types == ["DEF", "PI"]
        pi = next(option for option in result.penalty_options if option.penalty_type == "PI")
        assert pi.yards == 15


class TestFieldGoalDuplicates:
    """Field-goal charts build the same option list and need the same rule."""

    def test_repeated_identical_field_goal_foul_offers_one_option(self):
        special = SpecialTeamsChart(
            interception_return={10: "5"},
            kickoff={},
            kickoff_return={},
            punt={},
            punt_return={},
            field_goal={10: "DEF 5", 11: "DEF 5", 12: "35"},
            extra_point_no_good=[],
        )
        with patch("paydirt.play_resolver.roll_chart_dice") as roll:
            roll.side_effect = [(10, "B1+W0+W0=10"), (11, "B1+W0+W1=11"), (12, "B1+W1+W2=12")]
            result = resolve_field_goal_with_penalties(special)

        assert result.is_penalty is True
        assert result.offended_team == "offense"
        assert len(result.penalty_options) == 1
        assert len([entry for entry in result.reroll_log if "(penalty)" in entry]) == 2


class TestCliMenuNumbering:
    """The options preview must use the same numbers as the actual choices.

    Historically the "Penalty Options" block numbered the fouls from ``[1]``
    while the decision prompt numbered the same fouls from ``[2]``, with ``[1]``
    reserved for the play result. Two fouls therefore appeared as ``[1]``/``[2]``
    and then ``[2]``/``[3]``, and a duplicate pair as ``[1]``/``[2]`` twice over.
    """

    def _pending(self, options):
        from paydirt.game_engine import PlayOutcome
        from paydirt.play_resolver import (
            PenaltyChoice,
            PlayResult,
            ResultType,
        )
        from tests.game_fixtures import make_sample_game

        game = make_sample_game()
        game.state.is_home_possession = True
        game.state.ball_position, game.state.down, game.state.yards_to_go = 45, 2, 10
        result = PlayResult(
            ResultType.YARDS, yards=8, raw_result="8",
            description="8 yards [+8]",
        )
        choice = PenaltyChoice(
            play_result=result, penalty_options=list(options), offended_team="offense",
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=8,
            description=result.description,
            penalty_choice=choice,
            pending_penalty_decision=True,
        )
        return game, outcome

    def _menu(self, output: str):
        preview = [line.strip() for line in output.splitlines()
                   if line.strip().startswith("[") and "PLAY result" not in line
                   and "Accept PENALTY" not in line]
        choices = [line.strip() for line in output.splitlines()
                   if "Accept PENALTY" in line]
        return preview, choices

    @staticmethod
    def _options():
        from paydirt.play_resolver import PenaltyOption
        return [
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards"),
            PenaltyOption("DEF", "DEF 15", 15, "Defensive penalty, 15 yards",
                          auto_first_down=True),
        ]

    def test_preview_numbers_match_the_decision_numbers(self, monkeypatch, capsys):
        from paydirt import interactive_game as cli

        game, outcome = self._pending(self._options())
        monkeypatch.setattr("builtins.input", lambda *args: "1")
        cli.handle_penalty_decision(game, outcome, True, True)
        output = capsys.readouterr().out

        preview, choices = self._menu(output)
        assert len(preview) == len(choices) == 2
        assert preview[0].startswith("[2]") and preview[1].startswith("[3]")
        assert choices[0].startswith("[2] Accept PENALTY")
        assert choices[1].startswith("[3] Accept PENALTY")

    def test_duplicate_foul_appears_once_in_both_blocks(self, monkeypatch, capsys):
        from paydirt import interactive_game as cli
        from paydirt.play_resolver import PenaltyOption

        duplicate = [
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards"),
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards"),
        ]
        game, outcome = self._pending(duplicate)
        monkeypatch.setattr("builtins.input", lambda *args: "1")
        cli.handle_penalty_decision(game, outcome, True, True)
        output = capsys.readouterr().out

        preview, choices = self._menu(output)
        assert len(preview) == 1
        assert preview[0] == "[2] Defensive penalty, 5 yards"
        assert len(choices) == 1
        assert choices[0].startswith("[2] Accept PENALTY")


class TestCpuDecisionResolvability:
    """The deduplicated list must keep CPU indices valid after it shrinks.

    ``should_accept_penalty`` returns an index into
    ``outcome.penalty_choice.penalty_options``, not into its own filtered view.
    Collapsing repeats renumbers that list, so the index the CPU reports must
    still address the foul it chose - and applying it must enforce that foul.
    """

    def _pending(self, options):
        from paydirt.game_engine import PlayOutcome
        from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType
        from tests.game_fixtures import make_sample_game

        game = make_sample_game()
        game.state.is_home_possession = True
        game.state.ball_position, game.state.down, game.state.yards_to_go = 45, 2, 10
        result = PlayResult(
            ResultType.YARDS, yards=8, raw_result="8", description="8 yards [+8]",
        )
        choice = PenaltyChoice(
            play_result=result, penalty_options=list(options), offended_team="offense",
        )
        outcome = PlayOutcome(
            play_type=PlayType.OFF_TACKLE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=8,
            description=result.description,
            penalty_choice=choice,
            pending_penalty_decision=True,
        )
        return game, outcome

    def test_deduped_list_keeps_the_cpu_choice_resolvable(self):
        from paydirt.computer_ai import ComputerAI
        from paydirt.play_resolver import PenaltyOption

        options = [
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards"),
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty, 5 yards"),
            PenaltyOption("DEF", "DEF 15", 15, "Defensive penalty, 15 yards",
                          auto_first_down=True),
        ]
        game, outcome = self._pending(options)

        accept_play, index = ComputerAI().should_accept_penalty(
            outcome, is_human_offense=False, human_is_home=True, game=game,
        )
        assert accept_play is False
        assert index is not None
        chosen = outcome.penalty_choice.penalty_options[index]
        assert chosen.yards == 15 and chosen.auto_first_down is True

        before = (game.state.ball_position, game.state.down)
        applied = game.apply_penalty_decision(outcome, accept_play, index)
        assert applied.penalty_applied
        # A DEF foul is charged to the defense and moves the offense forward.
        assert game.state.defense_stats.penalties == 1
        assert game.state.defense_stats.penalty_yards == 15
        assert game.state.ball_position == before[0] + 15
