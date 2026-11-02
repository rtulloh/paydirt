from types import SimpleNamespace

import pytest

from paydirt.chart_calibration import EngineCalibrationObserver
from paydirt.game_state import PlayOutcome, TeamStats
from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType


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
