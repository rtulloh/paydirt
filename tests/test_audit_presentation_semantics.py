"""Outcome semantics and complete display paths use independent expectations."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt import commentary
from paydirt import interactive_game as cli
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
@pytest.mark.parametrize("yards", [-3, 0, 4, 12])
def test_recovery_at_spot_does_not_invent_a_post_recovery_advance(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, view: str, yards: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 27
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    result = PlayResult(ResultType.FUMBLE, yards=yards, raw_result=f"F {yards:+d}", description="FUMBLE!")
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(24, "Recovery at spot")) as dice):
        outcome = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    dice.assert_called_once()
    assert game.state.ball_position == 27 + yards
    assert outcome.yards_gained == yards and outcome.result.fumble_return_yards == 0
    assert game.state.offense_stats.rushing_yards == yards
    if view == "legacy-compact":
        outcome.transaction = None
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, PlayType.OFF_TACKLE, DefenseType.STANDARD, game.state.home_chart, home)
    output = capsys.readouterr().out
    assert outcome.result.rule_explanation
    assert outcome.result.rule_explanation in output
    assert f"{yards} yards before fumble" in output
    assert "at the spot" in output
    assert "advanced" not in output.lower()
    assert output.upper().count("FIRST DOWN") == int(yards == 12)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full", "formatter", "penalty-choice"])
@pytest.mark.parametrize("incomplete", [False, True])
def test_incomplete_is_distinct_from_completed_no_gain(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, view: str, incomplete: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 65, 2, 11
    result = PlayResult(ResultType.INCOMPLETE if incomplete else ResultType.YARDS,
                        raw_result="9" if incomplete else "0",
                        defense_modifier="BLACK" if incomplete else "",
                        description="Incomplete pass" if incomplete else "Completed pass for no gain")
    options = [PenaltyOption("DEF", "DEF 5X", 5, "Defensive penalty, 5 yards", auto_first_down=True)] if view == "penalty-choice" else []
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
            result, penalty_options=options, offended_team="offense")):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.SPREAD)
    if view == "penalty-choice":
        monkeypatch.setattr("builtins.input", lambda *args: "1")
        cli.handle_penalty_decision(game, outcome, True, home)
        text = next(line for line in capsys.readouterr().out.splitlines() if "[1] Accept PLAY result:" in line)
    else:
        if view == "legacy-compact":
            outcome.transaction = None
        if view == "formatter":
            text = ResultFormatter("OFF", "DEF").format(outcome).headline
        else:
            monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
            cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.SPREAD, game.state.home_chart, home)
            output = capsys.readouterr().out
            text = next(line for line in output.splitlines() if line.startswith("►") or "RESULT:" in line)
    assert ("incomplete" in text.lower()) is incomplete
    assert ("no gain" in text.lower()) is not incomplete
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (65, 3, 11)


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("home", [False, True])
def test_pi_first_down_explained_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, compact: bool, home: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    option = PenaltyOption("PI", "PI 5", 5, "Pass interference", auto_first_down=True, is_pass_interference=True)
    result = PlayResult(ResultType.INCOMPLETE, description="Pass interference - incomplete pass")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
            result, penalty_options=[option], offended_team="offense")):
        pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    outcome = game.apply_penalty_decision(pending, accept_play=False)
    assert outcome.first_down and game.state.down == 1
    before = deepcopy(game.state)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.STANDARD, game.state.home_chart, home)
    text = capsys.readouterr().out
    assert text.upper().count("FIRST DOWN") == 1
    assert "pass interference" in text.lower()
    assert game.state == before


@pytest.mark.parametrize("index", range(max(len(commentary.BIG_RUN_CALLS), len(commentary.BREAKAWAY_CALLS))))
@pytest.mark.parametrize("touchdown", [False, True])
def test_every_breakaway_template_respects_final_outcome(
    monkeypatch: pytest.MonkeyPatch, index: int, touchdown: bool,
) -> None:
    def choose(options: list) -> object:
        return options[index % len(options)]

    monkeypatch.setattr(commentary._NARRATION_RANDOM, "choice", choose)
    roster = commentary.TeamRoster(qb=["QB"], rb=["Runner"])
    text = commentary.Commentary(roster, roster, "OFF", "DEF").generate(
        PlayType.END_RUN, ResultType.BREAKAWAY, 13, is_breakaway=True, is_touchdown=touchdown)
    if not touchdown:
        assert "nobody" not in text.lower()
        assert "all the way" not in text.lower()
        assert "touchdown" not in text.lower()
    else:
        assert any(marker in text.upper() for marker in ["TOUCHDOWN", "SCORE", "SIX POINTS"])


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("offensive_foul", [False, True])
def test_nine_plus_defensive_black_resolves_incomplete_not_no_gain(home: bool, offensive_foul: bool) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 65, 2, 11
    game.state.possession_team.offense.short_pass[26] = "9"
    game.state.possession_team.offense.short_pass[27] = "OFF 10"
    game.state.defense_team.defense.modifiers[("C", 2)] = {column: "BLACK" for column in range(10)}
    rolls = [(27, "Synthetic foul"), (26, "Synthetic reroll")] if offensive_foul else [(26, "Synthetic pass")]
    with (patch("paydirt.play_resolver.random.choice", side_effect=[2, 0]),
          patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls) as dice):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.SPREAD)
    assert dice.call_count == (2 if offensive_foul else 1)
    assert outcome.result.result_type == ResultType.INCOMPLETE
    assert outcome.result.raw_result == "9" and outcome.result.defense_modifier == "BLACK"
    assert outcome.result.yards == 0
    if offensive_foul:
        assert outcome.pending_penalty_decision
        with patch("paydirt.game_engine.resolve_play_with_penalties") as reroll:
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
        reroll.assert_not_called()
    assert len(game.play_log) == 1
    assert game.state.offense_stats.total_yards == 0
    assert game.state.offense_stats.passing_yards == 0
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (65, 3, 11)
