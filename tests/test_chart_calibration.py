from types import SimpleNamespace
from unittest.mock import patch

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome, TeamStats
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game


def _game(home_possession: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            is_home_possession=home_possession,
            home_chart=SimpleNamespace(peripheral=SimpleNamespace(short_name="HOM")),
            away_chart=SimpleNamespace(peripheral=SimpleNamespace(short_name="AWY")),
            home_stats=TeamStats(
                total_yards=350,
                rushing_yards=120,
                passing_yards=250,
                sacks=2,
                sack_yards=20,
                interceptions_thrown=1,
                fumbles_lost=1,
                turnovers=2,
            ),
            away_stats=TeamStats(
                total_yards=280,
                rushing_yards=100,
                passing_yards=195,
                sacks=3,
                sack_yards=15,
                interceptions_thrown=2,
                fumbles_lost=0,
                turnovers=2,
            ),
            home_score=27,
            away_score=17,
            game_over=True,
        )
    )


def _outcome(play_type: PlayType, result_type: ResultType, **changes) -> PlayOutcome:
    values = {
        "play_type": play_type,
        "defense_type": DefenseType.STANDARD,
        "result": PlayResult(result_type=result_type),
    }
    values.update(changes)
    return PlayOutcome(**values)


def test_observer_counts_resolved_passes_and_excludes_sacks_scrambles_and_penalties() -> None:
    observer = EngineCalibrationObserver()
    game = _game()

    expected = (
        (ResultType.YARDS, 1, 1),
        (ResultType.INCOMPLETE, 2, 1),
        (ResultType.INTERCEPTION, 3, 1),
        (ResultType.SACK, 3, 1),
        (ResultType.QB_SCRAMBLE, 3, 1),
    )
    for result_type, expected_attempts, expected_completions in expected:
        observer.on_decision(game, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
        observer.on_result(game, _outcome(PlayType.SHORT_PASS, result_type))
        totals = observer.team_totals("HOM")
        assert totals.pass_attempts == expected_attempts
        assert totals.completions == expected_completions

    observer.on_decision(game, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
    observer.on_result(
        game,
        _outcome(
            PlayType.SHORT_PASS,
            ResultType.YARDS,
            penalty_applied=True,
        ),
    )

    totals = observer.team_totals("HOM")
    assert totals.pass_attempts == 3
    assert totals.completions == 1
    assert totals.offensive_plays == 5


@pytest.mark.parametrize(
    "result_type,initial_yards,qt_dice,credited_yards,attempts,completions,rushes,sacks",
    [
        (ResultType.FUMBLE, -5, 10, -5, 0, 0, 0, 1),
        (ResultType.FUMBLE, 0, 10, 0, 0, 0, 0, 1),
        (ResultType.FUMBLE, 5, 10, 5, 0, 0, 1, 0),
        # Own recovery advance cannot turn the initial QB loss into a completion.
        (ResultType.FUMBLE, -5, 10, 5, 0, 0, 0, 1),
        (ResultType.FUMBLE, 5, 0, 5, 1, 1, 0, 0),
        (ResultType.FUMBLE, -5, 0, -5, 1, 1, 0, 0),
        (ResultType.QB_SCRAMBLE, -5, 10, -5, 0, 0, 0, 1),
        (ResultType.QB_SCRAMBLE, 5, 10, -1, 0, 0, 0, 1),
        (ResultType.QB_SCRAMBLE, -5, 10, 5, 0, 0, 1, 0),
        (ResultType.QB_SCRAMBLE, 0, 10, 0, 0, 0, 1, 0),
        (ResultType.QB_SCRAMBLE, 5, 10, 5, 0, 0, 1, 0),
        (ResultType.SACK, -5, 10, -5, 0, 0, 0, 1),
        (ResultType.YARDS, 5, 0, 5, 1, 1, 0, 0),
        (ResultType.INCOMPLETE, 0, 0, 0, 1, 0, 0, 0),
    ],
    ids=["qt-loss-fumble", "qt-zero-fumble", "qt-gain-fumble", "qt-recovery-advance",
        "pass-fumble", "negative-pass-fumble", "negative-scramble", "adjusted-scramble-loss",
        "adjusted-scramble-gain", "zero-scramble",
        "positive-scramble", "sack", "completion", "incomplete"],
)
def test_observer_attempt_denominators_conform_to_core_qt_classification(
    result_type: ResultType, initial_yards: int, qt_dice: int, credited_yards: int,
    attempts: int, completions: int, rushes: int, sacks: int,
) -> None:
    game = _game()
    game.state.home_stats = TeamStats()
    game.state.away_stats = TeamStats()
    result = PlayResult(result_type, yards=initial_yards, qb_scramble_dice=qt_dice)
    outcome = _outcome(PlayType.SHORT_PASS, result_type, result=result,
                       yards_gained=credited_yards)
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
    PaydirtGameEngine._record_scrimmage_yardage(
        game.state.home_stats, PlayType.SHORT_PASS, result, credited_yards, 40,
    )
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    totals = observer.report()["teams"]["HOM"]

    assert totals["pass_attempts"] == attempts
    assert totals["completions"] == completions
    assert totals["rushing_attempts"] == rushes
    assert totals["sacks"] == sacks
    assert totals["offensive_plays"] == attempts + rushes + sacks == 1
    for name in ("total_yards", "rushing_yards", "passing_yards", "sack_yards"):
        assert totals[name] == getattr(game.state.home_stats, name)


@pytest.mark.parametrize("play_type", [PlayType.SHORT_PASS, PlayType.LINE_PLUNGE])
@pytest.mark.parametrize("status", ["ordinary", "declined", "accepted", "replay", "offsetting"])
def test_observer_uses_finalized_penalty_flags_not_prose(
    play_type: PlayType, status: str,
) -> None:
    game = _game()
    observer = EngineCalibrationObserver()
    result = PlayResult(ResultType.YARDS, yards=4, replay_down=status == "replay")
    choice = PenaltyChoice(
        result,
        penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "Synthetic foul")]
            if status in {"declined", "accepted"} else [],
        offsetting=status == "offsetting",
    )
    outcome = _outcome(
        play_type, ResultType.YARDS, result=result, penalty_choice=choice,
        penalty_applied=status == "accepted",
        # Misleading prose deliberately proves classification uses flags only.
        description="Normal retained play" if status == "offsetting"
            else "Offsetting penalties - down replayed",
    )
    observer.on_decision(game, None, play_type, DefenseType.STANDARD)
    observer.on_result(game, outcome)
    totals = observer.team_totals("HOM")
    retained = int(status in {"ordinary", "declined"})
    assert totals.offensive_plays == retained
    assert totals.pass_attempts == (retained if play_type == PlayType.SHORT_PASS else 0)
    assert totals.completions == totals.pass_attempts
    assert totals.rushing_attempts == (retained if play_type == PlayType.LINE_PLUNGE else 0)


@pytest.mark.parametrize(
    "play_type,result_type,yards,qt_dice",
    [(PlayType.SHORT_PASS, ResultType.YARDS, 4, 0),
     (PlayType.LINE_PLUNGE, ResultType.YARDS, 4, 0),
     (PlayType.SHORT_PASS, ResultType.SACK, -8, 10),
     (PlayType.SHORT_PASS, ResultType.FUMBLE, -10, 26)],
    ids=["voided-completion", "voided-run", "voided-sack", "voided-qt-fumble"],
)
def test_real_engine_offsetting_plays_do_not_enter_observer_totals(
    play_type: PlayType, result_type: ResultType, yards: int, qt_dice: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 2, 10
    game.state.quarter, game.state.time_remaining = 2, 10
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, play_type, DefenseType.BLITZ)
    choice = PenaltyChoice(
        PlayResult(result_type, yards=yards, qb_scramble_dice=qt_dice), offsetting=True,
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        outcome = game.run_play_with_penalty_procedure(play_type, DefenseType.BLITZ)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    totals = observer.report()["teams"][game.state.home_chart.peripheral.short_name]

    assert outcome.penalty_choice.offsetting
    assert not outcome.penalty_applied and not outcome.result.replay_down
    assert (game.state.ball_position, game.state.down) == (40, 2)
    for field in ("offensive_plays", "pass_attempts", "completions", "rushing_attempts",
                  "sacks", "total_yards", "passing_yards", "rushing_yards"):
        assert totals[field] == 0


@pytest.mark.parametrize("accept_penalty", [False, True], ids=["declined", "accepted"])
def test_real_engine_penalty_decision_counts_only_retained_completion(
    accept_penalty: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 2, 10
    game.state.quarter, game.state.time_remaining = 2, 10
    observer = EngineCalibrationObserver()
    observer.on_decision(game, None, PlayType.SHORT_PASS, DefenseType.STANDARD)
    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, yards=4),
        penalty_options=[PenaltyOption("OFF", "OFF 5", 5, "Synthetic foul")],
        offended_team="defense",
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    outcome = game.apply_penalty_decision(pending, accept_play=not accept_penalty)
    observer.on_result(game, outcome)
    observer.finalize_game(game)
    totals = observer.report()["teams"][game.state.home_chart.peripheral.short_name]
    retained = int(not accept_penalty)
    assert outcome.penalty_applied is accept_penalty
    assert totals["offensive_plays"] == totals["pass_attempts"] == totals["completions"] == retained
    assert totals["passing_yards"] == 4 * retained


def test_observer_aggregates_authoritative_engine_box_score_metrics() -> None:
    observer = EngineCalibrationObserver()
    game = _game()

    observer.on_decision(game, None, PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    observer.on_result(game, _outcome(PlayType.LINE_PLUNGE, ResultType.YARDS))
    observer.finalize_game(game)

    report = observer.report()
    league = report["league"]
    home = report["teams"]["HOM"]

    assert league["games"] == 1
    assert league["team_games"] == 2
    assert league["points_per_team_game"] == pytest.approx(22.0)
    assert league["yards_per_team_game"] == pytest.approx(315.0)
    assert league["sacks_per_team_game"] == pytest.approx(2.5)
    assert league["turnovers_per_team_game"] == pytest.approx(2.0)
    assert home["points"] == 27
    assert home["passing_yards"] == 250
    assert home["sacks"] == 2
    assert home["interceptions"] == 1
    assert home["fumbles_lost"] == 1
    assert home["offensive_plays"] == 1


def test_observer_rejects_unpaired_callbacks() -> None:
    observer = EngineCalibrationObserver()
    game = _game()

    with pytest.raises(ValueError, match="without a selected play"):
        observer.on_result(game, _outcome(PlayType.LINE_PLUNGE, ResultType.YARDS))

    observer.on_decision(game, None, PlayType.LINE_PLUNGE, DefenseType.STANDARD)
    with pytest.raises(ValueError, match="already pending"):
        observer.on_decision(game, None, PlayType.DRAW, DefenseType.STANDARD)


def test_observer_counts_field_goal_attempts_and_makes() -> None:
    observer = EngineCalibrationObserver()
    game = _game()

    observer.on_decision(game, None, PlayType.FIELD_GOAL, DefenseType.STANDARD)
    observer.on_result(
        game,
        _outcome(PlayType.FIELD_GOAL, ResultType.YARDS, field_goal_made=True),
    )
    observer.on_decision(game, None, PlayType.FIELD_GOAL, DefenseType.STANDARD)
    observer.on_result(
        game,
        _outcome(PlayType.FIELD_GOAL, ResultType.YARDS, field_goal_made=False),
    )

    totals = observer.team_totals("HOM")
    assert totals.field_goal_attempts == 2
    assert totals.field_goals_made == 1
    assert totals.to_dict()["field_goal_rate"] == pytest.approx(0.5)
    assert totals.offensive_plays == 0


def test_observer_reports_rushing_attempts_and_yards_per_attempt() -> None:
    """Calibration should expose the rushing efficiency needed by the tuner."""
    observer = EngineCalibrationObserver()
    game = _game()

    for play_type in (PlayType.LINE_PLUNGE, PlayType.DRAW):
        observer.on_decision(game, None, play_type, DefenseType.STANDARD)
        observer.on_result(game, _outcome(play_type, ResultType.YARDS))
    observer.finalize_game(game)

    report = observer.report()
    league = report["league"]
    home = report["teams"]["HOM"]
    assert home["rushing_attempts"] == 2
    assert home["rushing_yards_per_attempt"] == pytest.approx(60.0)
    assert league["rushing_attempts"] == 2
