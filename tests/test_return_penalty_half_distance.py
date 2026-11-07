"""Return fouls may not exceed half the distance to the actual offender's goal."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("spot", [1, 2, 9, 10, 11, 17, 26, 27, 29, 30, 31, 40, 80, 90, 99])
@pytest.mark.parametrize("yards", [5, 15, 40])
@pytest.mark.parametrize("returner_foul", [False, True])
def test_return_assessment_never_exceeds_offenders_half_distance(
    spot: int, yards: int, returner_foul: bool,
) -> None:
    game = make_sample_game()
    final, assessed, wiped = game._enforce_return_penalty(spot, yards, returner_foul)
    distance = spot if returner_foul else 100 - spot
    expected_assessment = min(yards, distance // 2)
    expected_final = spot - expected_assessment if returner_foul else spot + expected_assessment
    assert (final, assessed, wiped) == (expected_final, expected_assessment, False)
    assert 1 <= final <= 99
    assert assessed <= distance / 2


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("catch,assessment,final", [(27, 13, 14), (26, 13, 13), (29, 14, 15), (1, 0, 1)])
@pytest.mark.parametrize("kick_foul", [False, True])
def test_punt_return_and_legacy_catch_assess_actual_half_distance(
    home: bool, catch: int, assessment: int, final: int, kick_foul: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 20, 4, 8
    game.state.possession_team.special_teams.punt = {10: "OFF 5" if kick_foul else str(80 - catch),
                                                 11: str(80 - catch)}
    game.state.defense_team.special_teams.punt_return = {12: "OFF 15", 13: "0"}
    dice = [10, *([11] if kick_foul else []), 12, 13]
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == len(dice)
    assert not outcome.pending_penalty_decision and not outcome.result.replay_down
    assert game.state.is_home_possession is not home
    assert game.state.ball_position == final
    assert (game.state.down, game.state.yards_to_go) == (1, 10)
    assert (game.state.offense_stats.penalties, game.state.offense_stats.penalty_yards) == (1, assessment)
    assert game.state.defense_stats.penalties == 0
    assert outcome.penalty_applied and not outcome.touchdown and not outcome.safety


@pytest.mark.parametrize("returner_foul", [False, True])
def test_return_score_boundary_control(returner_foul: bool) -> None:
    game = make_sample_game()
    assert game._enforce_return_penalty(100, 15, returner_foul) == (
        (85, 15, True) if returner_foul else (100, 0, False)
    )


def test_gate_rejects_oversized_returner_half_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    def old_rule(game: PaydirtGameEngine, position: int, penalty_yards: int) -> int:
        return max(1, position // 2) if position - penalty_yards < 1 else penalty_yards

    monkeypatch.setattr(PaydirtGameEngine, "_apply_half_the_distance", old_rule)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("PUNT/five-fifteen/receiver-catch" in error for error in report["errors"])
