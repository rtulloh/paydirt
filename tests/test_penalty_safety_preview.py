"""Penalty choices must preview an end-zone loss as a safety, not own one."""

from copy import deepcopy
import random
from unittest.mock import patch

import pytest

from paydirt.interactive_game import handle_penalty_decision
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home_offense", [False, True])
@pytest.mark.parametrize("down", [1, 4])
@pytest.mark.parametrize("position", [8, 9, 10], ids=["past-goal-line", "on-goal-line", "own-one-control"])
@pytest.mark.parametrize("accept_play", [False, True], ids=["accept-penalty", "decline-penalty"])
@pytest.mark.parametrize("qt", [False, True], ids=["run-loss", "qt-sack-overrides-int"])
def test_penalty_loss_preview_matches_retained_play(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    home_offense: bool, down: int, position: int, accept_play: bool, qt: bool,
) -> None:
    """Use real resolution with synthetic cells, including the reported INT/QT rolls."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home_offense
    state.quarter, state.time_remaining = 4, 373 / 60
    state.ball_position, state.down, state.yards_to_go = position, down, 10
    state.home_score, state.away_score = (5, 24) if home_offense else (24, 5)
    offense = state.possession_team
    defense = state.defense_team
    offense_name = offense.peripheral.short_name
    defense_name = defense.peripheral.short_name
    offense_stats = state.offense_stats
    play = PlayType.LONG_PASS if qt else PlayType.LINE_PLUNGE
    formation = DefenseType.BLITZ if qt else DefenseType.STANDARD
    column = offense.offense.long_pass if qt else offense.offense.line_plunge
    column.update({29: "OFF 15", 36: "INT 26" if qt else "-9"})
    offense.offense.qb_time[33] = "-9"
    defense.defense.modifiers.setdefault((formation.value, 1), {})[8 if qt else 1] = "QT" if qt else "0"
    rolls = [(29, "B2+W4+W5=29"), (36, "B3+W4+W2=36")]
    if qt:
        rolls.append((33, "B3+W1+W2=33"))

    with (
        patch("paydirt.play_resolver.random.choice", side_effect=lambda faces: faces[0]),
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=20),
    ):
        outcome = game.run_play_with_penalty_procedure(play, formation, no_huddle=True)
        assert outcome.pending_penalty_decision
        assert outcome.result.result_type == (ResultType.SACK if qt else ResultType.YARDS)
        assert outcome.result.yards == -9
        assert not outcome.result.turnover
        if qt:
            assert outcome.result.raw_result == "INT 26"
            assert outcome.result.qb_scramble_dice == 33
        before_state = deepcopy(state)
        before_result = deepcopy(outcome)
        before_rng = random.getstate()

        def choose(prompt: str) -> str:
            # Constructing/displaying previews must never simulate or apply a play.
            assert state == before_state
            assert outcome == before_result
            assert random.getstate() == before_rng
            assert dice.call_count == len(rolls)
            assert not game.play_log
            return "1" if accept_play else "2"

        monkeypatch.setattr("builtins.input", choose)
        final = handle_penalty_decision(game, outcome, is_human_offense=False, human_is_home=not home_offense)
        assert dice.call_count == len(rolls)

    output = capsys.readouterr().out
    summary = output.split("Play Result (if accepted, down counts):", 1)[1].split("may choose:", 1)[0]
    play_option = next(line for line in output.splitlines() if "[1] Accept PLAY result:" in line)
    would_be_safety = position <= 9
    if would_be_safety:
        for preview in (summary, play_option):
            assert "SAFETY" in preview
            assert defense_name in preview and "2 points" in preview
            assert offense_name in preview
            assert "2nd and 19" not in preview
            assert "TURNOVER ON DOWNS" not in preview
            assert "at own 1" not in preview
    else:
        assert "SAFETY" not in summary + play_option
        expected = "2nd and 19" if down == 1 else "TURNOVER ON DOWNS"
        assert f"Loss of 9 -> {expected} at own 1" in play_option

    assert final.safety is (accept_play and would_be_safety)
    assert final.penalty_applied is not accept_play
    assert not final.pending_penalty_decision
    assert len(game.play_log) == 1
    assert offense_stats.penalties == int(not accept_play)
    assert len(state.scoring_plays) == int(final.safety)
    assert state.home_score == ((5 if home_offense else 24) + (2 if final.safety and not home_offense else 0))
    assert state.away_score == ((24 if home_offense else 5) + (2 if final.safety and home_offense else 0))
    if final.safety:
        assert state.is_home_possession is home_offense  # Scored-on team takes the free kick.
        assert state.ball_position == 20
    elif not accept_play:
        assert state.is_home_possession is home_offense
        assert state.ball_position == position - position // 2
        assert state.down == down
        assert state.yards_to_go == 10 + position // 2


@pytest.mark.parametrize("home_offense", [False, True])
@pytest.mark.parametrize("raw,expected_type", [
    ("BLACK", ResultType.INCOMPLETE),
    ("INT -9", ResultType.INTERCEPTION),
    ("TD", ResultType.TOUCHDOWN),
])
def test_other_penalty_play_results_are_not_misidentified_as_safeties(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    home_offense: bool, raw: str, expected_type: ResultType,
) -> None:
    """A negative interception depth is not an offensive safety."""
    game = make_sample_game()
    state = game.state
    state.is_home_possession = home_offense
    state.quarter, state.time_remaining = 4, 373 / 60
    state.ball_position = 8
    state.possession_team.offense.long_pass.update({29: "OFF 15", 36: raw})
    state.defense_team.defense.modifiers.setdefault(("A", 1), {})[8] = "0"
    monkeypatch.setattr("builtins.input", lambda prompt: "1")
    with (
        patch("paydirt.play_resolver.random.choice", side_effect=lambda faces: faces[0]),
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[
            (29, "B2+W4+W5=29"), (36, "B3+W4+W2=36"),
        ]) as dice,
        patch("paydirt.game_engine.random.uniform", return_value=20),
    ):
        outcome = game.run_play_with_penalty_procedure(PlayType.LONG_PASS, DefenseType.STANDARD)
        assert outcome.pending_penalty_decision
        assert outcome.result.result_type == expected_type
        final = handle_penalty_decision(game, outcome, False, not home_offense)
        assert dice.call_count == 2
    assert "SAFETY" not in capsys.readouterr().out
    assert not final.safety
    assert final.touchdown is (raw != "BLACK")
