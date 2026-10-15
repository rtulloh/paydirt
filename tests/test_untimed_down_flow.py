"""Regressions for consuming, renewing, and completing untimed downs."""

import random
from unittest.mock import Mock

import pytest

from paydirt import interactive_game as cli
from tests.game_fixtures import make_sample_game
from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)


@pytest.fixture
def game() -> PaydirtGameEngine:
    return make_sample_game()


def prepare_untimed_down(game: PaydirtGameEngine, quarter: int = 4) -> None:
    game.state.quarter = quarter
    game.state.time_remaining = 0
    game.state.untimed_down_pending = True
    game.state.home_score = 0
    game.state.away_score = 7 if quarter <= 4 else 0
    game.state.is_home_possession = True
    game.state.ball_position = 40
    if quarter == 5:
        game.state.is_overtime = True
        game.state.ot_period = 1


def penalty_choice(penalty_type: str) -> PenaltyChoice:
    return PenaltyChoice(
        PlayResult(ResultType.INCOMPLETE, description="Pass incomplete"),
        penalty_options=[PenaltyOption(
            penalty_type, f"{penalty_type} 5", 5, "Defensive penalty", True,
        )],
        offended_team="offense",
    )


@pytest.mark.parametrize("quarter", [2, 4, 5])
@pytest.mark.parametrize("procedure", [False, True])
def test_clean_untimed_down_finishes_period_in_engine(game, monkeypatch, quarter, procedure) -> None:
    prepare_untimed_down(game, quarter)
    monkeypatch.setattr("paydirt.game_engine.resolve_play", lambda *args: PlayResult(ResultType.YARDS, yards=4))
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4),
    ))
    run = game.run_play_with_penalty_procedure if procedure else game.run_play
    run(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert not game.has_untimed_down()
    assert game.state.ball_position == 44
    if quarter == 2:
        assert game.state.quarter == 3
        assert game.state.time_remaining == 15
        assert not game.state.game_over
    else:
        assert game.state.game_over
        assert game.state.time_remaining == 0


@pytest.mark.parametrize("penalty_type", ["DEF", "PI"])
@pytest.mark.parametrize("repeats", [1, 3])
def test_each_accepted_defensive_penalty_renews_untimed_down(game, monkeypatch, penalty_type, repeats) -> None:
    prepare_untimed_down(game)
    choices = [penalty_choice(penalty_type) for _ in range(repeats)]
    choices.append(PenaltyChoice(PlayResult(ResultType.YARDS, yards=4)))
    resolver = Mock(side_effect=choices)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", resolver)
    for _ in range(repeats):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
        assert outcome.pending_penalty_decision
        assert not game.state.game_over
        outcome = game.apply_penalty_decision(outcome, accept_play=False)
        assert game.has_untimed_down()
        assert not game.state.game_over
        assert game.state.time_remaining == 0
    game.run_play_with_penalty_procedure(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert resolver.call_count == repeats + 1
    assert game.state.ball_position == 40 + 5 * repeats + 4
    assert not game.has_untimed_down()
    assert game.state.game_over


def test_declined_defensive_penalty_does_not_extend_untimed_down(game, monkeypatch) -> None:
    prepare_untimed_down(game)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: penalty_choice("DEF"))
    outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    game.apply_penalty_decision(outcome, accept_play=True)
    assert not game.has_untimed_down()
    assert game.state.game_over
    assert game.state.ball_position == 40


@pytest.mark.parametrize("entry_point", ["resume", "new"])
@pytest.mark.parametrize("penalties", [0, 1, 3])
def test_cli_does_not_discard_replacement_untimed_down(game, monkeypatch, capsys, entry_point, penalties) -> None:
    prepare_untimed_down(game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(cli, "_offer_record_to_standings", lambda **kwargs: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, False, False,
    ))
    monkeypatch.setattr(cli, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    monkeypatch.setattr(cli, "handle_penalty_decision", lambda engine, outcome, *args: (
        engine.apply_penalty_decision(outcome, accept_play=False)
    ))
    choices = [penalty_choice("PI") for _ in range(penalties)]
    choices.append(PenaltyChoice(PlayResult(ResultType.YARDS, yards=4)))
    resolver = Mock(side_effect=choices)
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", resolver)
    if entry_point == "resume":
        monkeypatch.setattr(cli, "get_save_info", lambda _: {
            "saved_at": "test", "away_team": "OAK", "home_team": "PHI",
            "away_score": 7, "home_score": 0, "quarter": 4, "time_remaining": 0,
        })
        monkeypatch.setattr(cli, "load_game", lambda _: (game, False, True, None))
        cli.resume_game("test-save.json", compact=True)
    else:
        charts = iter([game.state.home_chart, game.state.away_chart])
        monkeypatch.setattr(cli, "select_team", lambda *args, **kwargs: next(charts))
        monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
        monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)

        def opening_kickoff(*args, **kwargs) -> PlayOutcome:
            prepare_untimed_down(game)
            return PlayOutcome(
                PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
                description="Opening kickoff",
            )

        monkeypatch.setattr(game, "kickoff", opening_kickoff)
        cli.run_interactive_game(compact=True)
    assert resolver.call_count == penalties + 1
    assert game.state.ball_position == 40 + 5 * penalties + 4
    assert game.state.game_over
    assert not game.has_untimed_down()
    assert "FINAL" in capsys.readouterr().out


def run_seeded_cli_game(monkeypatch, away: str, home: str, seed: int) -> PaydirtGameEngine:
    """Run unmodified game rules/dice with AI supplying human choices; never save standings."""
    random_state = random.getstate()
    random.seed(seed)
    engines = []
    ai = ComputerAI(aggression=0.5)
    choices = 0
    prompts = 0

    def make_engine(*args) -> PaydirtGameEngine:
        engine = PaydirtGameEngine(*args)
        engines.append(engine)
        return engine

    def offense(engine, *args) -> tuple:
        nonlocal choices
        choices += 1
        assert choices < 1000, "Excessive plays"
        play, oob, no_huddle, short_drop, coffin, spike = ai.select_offense_with_clock_management(engine)
        return play, no_huddle, oob, False, False, spike

    def defense(engine, *args) -> tuple:
        nonlocal choices
        choices += 1
        assert choices < 1000, "Excessive plays"
        return ai.select_defense(engine), False

    def answer(prompt: str = "") -> str:
        nonlocal prompts
        prompts += 1
        assert prompts < 1500, f"Repeated prompt: {prompt}"
        return "1" if "1 for play" in prompt or "penalty number" in prompt else ""

    try:
        with monkeypatch.context() as context:
            context.setattr(cli, "PaydirtGameEngine", make_engine)
            context.setattr(cli, "get_human_offense_play", offense)
            context.setattr(cli, "get_human_defense_play", defense)
            context.setattr(cli, "_offer_record_to_standings", lambda **kwargs: None)
            context.setattr(cli, "clear_screen", lambda: None)
            context.setattr(cli, "COMPACT_MODE", True)
            context.setattr(cli, "AI_HELPER_ENABLED", False)
            context.setattr("builtins.input", answer)
            cli.run_interactive_game(
                home_team=home if "/" in home else f"2026/{home}",
                away_team=away if "/" in away else f"2026/{away}",
                compact=True,
            )
        return engines[0]
    finally:
        random.setstate(random_state)


@pytest.mark.parametrize("away,home,seed", [
    ("Ironclads", "Thunderhawks", 19831104),
    ("Thunderhawks", "Ironclads", 19831603),
])
def test_sample_full_games_end_in_engine(monkeypatch, capsys, away, home, seed) -> None:
    game = run_seeded_cli_game(monkeypatch, away, home, seed)
    output = capsys.readouterr().out
    # Historical untimed-down reproductions live in the local season runner.
    assert "FINAL" in output
    assert game.state.game_over
    assert not game.has_untimed_down()
    assert game.state.time_remaining == 0
    assert sum(p["home"] for p in game.get_period_scores()) == game.state.home_score
    assert sum(p["away"] for p in game.get_period_scores()) == game.state.away_score


@pytest.mark.parametrize("play_type", [PlayType.QB_KNEEL, PlayType.SPIKE_BALL])
@pytest.mark.parametrize("procedure", [False, True])
def test_special_play_consumes_untimed_down(game, play_type, procedure) -> None:
    prepare_untimed_down(game)
    run = game.run_play_with_penalty_procedure if procedure else game.run_play
    run(play_type, DefenseType.STANDARD)
    assert not game.has_untimed_down()
    assert game.state.game_over


def test_offsetting_penalties_replay_untimed_down(game, monkeypatch) -> None:
    prepare_untimed_down(game)
    resolver = Mock(side_effect=[
        PenaltyChoice(PlayResult(ResultType.INCOMPLETE), offsetting=True),
        PenaltyChoice(PlayResult(ResultType.YARDS, yards=4)),
    ])
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", resolver)
    game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.has_untimed_down()
    assert not game.state.game_over
    assert game.state.ball_position == 40
    game.run_play_with_penalty_procedure(PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    assert not game.has_untimed_down()
    assert game.state.game_over


def test_offensive_penalty_does_not_renew_untimed_down(game, monkeypatch) -> None:
    prepare_untimed_down(game)
    choice = penalty_choice("OFF")
    choice.offended_team = "defense"
    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", lambda *args: choice)
    outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    game.apply_penalty_decision(outcome, accept_play=False)
    assert not game.has_untimed_down()
    assert game.state.game_over


@pytest.mark.parametrize("pending", [False, True])
@pytest.mark.parametrize("result_type", [ResultType.YARDS, ResultType.INCOMPLETE])
def test_clean_hail_mary_does_not_award_phantom_untimed_down(game, monkeypatch, pending, result_type) -> None:
    prepare_untimed_down(game)
    game.state.untimed_down_pending = pending
    game.state.time_remaining = 0 if pending else 0.02
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (16, "Roll16"))
    monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: PlayResult(
        result_type, yards=4 if result_type == ResultType.YARDS else 0,
    ))
    game.run_play_with_penalty_procedure(PlayType.HAIL_MARY, DefenseType.STANDARD)
    assert game.state.game_over
    assert not game.has_untimed_down()


def test_hail_mary_pass_interference_renews_untimed_down(game, monkeypatch) -> None:
    prepare_untimed_down(game)
    monkeypatch.setattr("paydirt.game_engine.roll_chart_dice", lambda: (16, "Roll16"))
    monkeypatch.setattr("paydirt.game_engine.resolve_hail_mary", lambda *args: PlayResult(
        ResultType.PASS_INTERFERENCE, yards=5, description="Pass interference",
    ))
    game.run_play_with_penalty_procedure(PlayType.HAIL_MARY, DefenseType.STANDARD)
    assert game.has_untimed_down()
    assert not game.state.game_over
    assert game.state.ball_position == 45
