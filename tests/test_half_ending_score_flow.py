"""Half-ending and clock-expiring scores through the complete CLI loops.

Synthetic public-team games; kicks are recorded by a stand-in kickoff so each
test can assert exactly which kicks happened, in which period, and by whom.
"""

from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


class StopSession(Exception):
    """Stop before the next scrimmage play without saving anything."""


def prepared_game(scorer_home: bool, quarter: int, seconds: float, *, safety: bool = False,
                  home_score: int = 0, away_score: int = 0):
    game = make_sample_game()
    game.state.is_home_possession = scorer_home if not safety else not scorer_home
    game.state.quarter, game.state.time_remaining = quarter, seconds / 60
    game.state.two_minute_warning_called = True
    game.state.home_score, game.state.away_score = home_score, away_score
    if safety:
        game.state.ball_position, game.state.down, game.state.yards_to_go = 3, 2, 8
    else:
        game.state.ball_position, game.state.down, game.state.yards_to_go = 94, 2, 6
    game.state.possession_team.special_teams.extra_point_no_good = []
    return game


def drive(monkeypatch: pytest.MonkeyPatch, game, *, resumed: bool, result: PlayResult,
          play_seconds: float = 30, pat_roll: int = 26) -> dict:
    """Run one CLI loop through the first scrimmage play until the next snap."""
    record = {"kicks": [], "halves": [], "statuses": 0}
    ai = Mock(use_analysis=False)
    ai.select_offense_with_clock_management.return_value = (
        PlayType.LINE_PLUNGE, False, False, False, 0, False)
    ai.select_defense.return_value = DefenseType.STANDARD
    ai.should_call_timeout_on_defense.return_value = False
    ai.should_call_timeout_on_offense.return_value = False
    ai.should_call_timeout.return_value = False
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=[game.state.home_chart, game.state.away_chart]))
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, False, True, None))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: dict(
        saved_at="synthetic", away_team="AWAY", home_team="HOME",
        away_score=game.state.away_score, home_score=game.state.home_score,
        quarter=game.state.quarter, time_remaining=game.state.time_remaining))
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_play_result", lambda *args: None)
    monkeypatch.setattr(cli, "display_box_score", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args:
                        (PlayType.LINE_PLUNGE, False, False, False, False, False))
    monkeypatch.setattr(cli, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)

    def answer(prompt: str = "") -> str:
        if "2nd half kickoff" in prompt:
            record["halves"].append(round(game.state.time_remaining * 60, 3))
        return ""

    def status(*args: object) -> None:
        record["statuses"] += 1
        if record["statuses"] > 1:
            raise StopSession

    def kickoff(*, kicking_home: bool, kickoff_spot: int = 35) -> PlayOutcome:
        opening = not resumed and not record["kicks"]
        record["kicks"].append(dict(
            quarter=game.state.quarter, after_halftime_prompt=bool(record["halves"]),
            opening=opening, kicking_home=kicking_home, spot=kickoff_spot,
            clock=round(game.state.time_remaining * 60, 3)))
        if not opening:
            game._use_time(7.5)
            game.state.is_home_possession = not kicking_home
            game.state.ball_position = 27
            game.state.down, game.state.yards_to_go = 1, 10
        return PlayOutcome(PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
                           description="Synthetic kickoff")

    played = []
    original_play = game.run_play_with_penalty_procedure

    def play(*args, **kwargs) -> PlayOutcome:
        if played:
            return original_play(*args, **kwargs)
        played.append(True)
        with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
              patch("paydirt.game_engine.random.uniform", return_value=play_seconds)):
            return original_play(*args, **kwargs)

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(cli, "display_game_status", status)
    monkeypatch.setattr(game, "kickoff", kickoff)
    monkeypatch.setattr(game, "run_play_with_penalty_procedure", play)
    record["stopped"] = False
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(pat_roll, "Try")):
        try:
            if resumed:
                cli.resume_game("synthetic.save")
            else:
                cli.run_interactive_game()
        except StopSession:
            record["stopped"] = True
    record["real_kicks"] = [kick for kick in record["kicks"] if not kick["opening"]]
    return record


TOUCHDOWN = PlayResult(ResultType.YARDS, yards=9, raw_result="9", description="Synthetic score")
SAFETY = PlayResult(ResultType.SACK, yards=-5, raw_result="-5", description="Synthetic sack")


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("scorer_home", [False, True])
def test_half_ending_touchdown_waits_for_the_second_half_kickoff(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, scorer_home: bool,
) -> None:
    game = prepared_game(scorer_home, 2, 20)
    record = drive(monkeypatch, game, resumed=resumed, result=TOUCHDOWN)
    assert record["stopped"]
    assert [(k["quarter"], k["after_halftime_prompt"]) for k in record["real_kicks"]] == [(3, True)], (
        "Only the scheduled second-half kickoff may follow a half-ending touchdown")
    assert record["halves"] == [900]
    if not resumed:
        # Human (home) kicked to open after losing the toss; the away side opens the second half.
        assert record["real_kicks"][0]["kicking_home"] is False
    assert (game.state.home_score, game.state.away_score) == ((7, 0) if scorer_home else (0, 7))
    assert [play.play_type for play in game.state.scoring_plays] == ["TD", "PAT"]
    assert game.state.quarter == 3
    assert game.state.time_remaining * 60 == pytest.approx(892.5)


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("quarter,seconds,expect_kick_quarter", [(1, 20, 2), (3, 20, 4), (2, 60, 2)],
                         ids=["q1-expires", "q3-expires", "time-remains"])
def test_touchdowns_elsewhere_still_kick_off(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, quarter: int, seconds: int, expect_kick_quarter: int,
) -> None:
    game = prepared_game(True, quarter, seconds)
    record = drive(monkeypatch, game, resumed=resumed, result=TOUCHDOWN)
    assert [(k["quarter"], k["after_halftime_prompt"], k["kicking_home"]) for k in record["real_kicks"]] == [
        (expect_kick_quarter, False, True)]
    assert not record["halves"]
    assert game.state.home_score == 7


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("conceding_home", [False, True])
def test_half_ending_safety_has_no_free_kick(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, conceding_home: bool,
) -> None:
    game = prepared_game(not conceding_home, 2, 3, safety=True)
    record = drive(monkeypatch, game, resumed=resumed, result=SAFETY)
    assert [(k["quarter"], k["after_halftime_prompt"], k["spot"]) for k in record["real_kicks"]] == [(3, True, 35)]
    assert record["halves"] == [900]
    assert (game.state.home_score, game.state.away_score) == ((0, 2) if conceding_home else (2, 0))
    assert game.state.quarter == 3
    assert game.state.time_remaining * 60 == pytest.approx(892.5)


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("quarter,seconds,expect_kick_quarter", [(1, 3, 2), (2, 60, 2)],
                         ids=["q1-expires", "time-remains"])
def test_safeties_elsewhere_still_free_kick_from_the_20(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, quarter: int, seconds: int, expect_kick_quarter: int,
) -> None:
    game = prepared_game(False, quarter, seconds, safety=True)
    record = drive(monkeypatch, game, resumed=resumed, result=SAFETY)
    assert [(k["quarter"], k["spot"], k["kicking_home"]) for k in record["real_kicks"]] == [
        (expect_kick_quarter, 20, True)]
    assert not record["halves"]
    assert game.state.away_score == 2


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
@pytest.mark.parametrize("scorer_home", [False, True])
@pytest.mark.parametrize("pat_good", [True, False], ids=["pat-good", "pat-missed"])
def test_clock_expiring_touchdown_still_gets_its_try(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, scorer_home: bool, pat_good: bool,
) -> None:
    game = prepared_game(scorer_home, 4, 10, home_score=14 if scorer_home else 21,
                         away_score=21 if scorer_home else 14)
    game.state.possession_team.special_teams.extra_point_no_good = [] if pat_good else [26]
    record = drive(monkeypatch, game, resumed=resumed, result=TOUCHDOWN)
    assert [play.play_type for play in game.state.scoring_plays] == (["TD", "PAT"] if pat_good else ["TD"])
    scorer = game.state.home_score if scorer_home else game.state.away_score
    assert scorer == (21 if pat_good else 20)
    if pat_good:
        assert game.state.is_overtime and not game.state.game_over
        assert record["stopped"]
        assert [(k["quarter"], k["after_halftime_prompt"]) for k in record["real_kicks"]] == [(5, False)]
    else:
        assert game.state.game_over and not record["stopped"]
        assert record["real_kicks"] == []


@pytest.mark.parametrize("resumed", [False, True], ids=["new", "resumed"])
def test_clock_expiring_touchdown_while_leading_still_kicks_the_point(
    monkeypatch: pytest.MonkeyPatch, resumed: bool,
) -> None:
    game = prepared_game(True, 4, 10, home_score=21, away_score=14)
    record = drive(monkeypatch, game, resumed=resumed, result=TOUCHDOWN)
    assert [play.play_type for play in game.state.scoring_plays] == ["TD", "PAT"]
    assert (game.state.home_score, game.state.away_score) == (28, 14)
    assert game.state.game_over and not record["stopped"]
    assert record["real_kicks"] == []
