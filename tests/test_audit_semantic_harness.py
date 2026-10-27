"""Inject semantically wrong, total-preserving evidence into audit checks."""

import random
from copy import deepcopy
from types import SimpleNamespace

import pytest

from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
)
from tests.game_fixtures import make_sample_game
from tests.run_full_season import validate_game


def test_period_audit_rejects_a_conversion_shift_even_when_totals_match() -> None:
    game = make_sample_game()
    game.state.game_over = True
    game.state.home_score = 7
    game.state.scoring_plays = [
        SimpleNamespace(points=6, is_home_team=True, play_type="TD", quarter=1),
        SimpleNamespace(points=1, is_home_team=True, play_type="PAT", quarter=2),
    ]
    with pytest.raises(ValueError, match="conversion period"):
        validate_game(game, "FINAL")


@pytest.mark.parametrize("accept", [False, True])
@pytest.mark.parametrize("cpu_offense", [False, True])
def test_penalty_audit_has_an_independent_scoring_side_oracle(accept: bool, cpu_offense: bool) -> None:
    from tests.semantic_audit import SemanticAudit

    result = PlayResult(ResultType.TOUCHDOWN, touchdown=True)
    option = PenaltyOption("DEF" if cpu_offense else "OFF", "DEF 5" if cpu_offense else "OFF 10", 5, "Penalty")
    pending = PlayOutcome(play_type=PlayType.SHORT_PASS, defense_type=DefenseType.STANDARD,
                          result=result, touchdown=True,
                          penalty_choice=PenaltyChoice(result, penalty_options=[option],
                              offended_team="offense" if cpu_offense else "defense"))
    audit = SemanticAudit()
    if accept != cpu_offense:
        with pytest.raises(ValueError, match="scoring-side"):
            audit.penalty(pending, (accept, 0))
    else:
        audit.penalty(pending, (accept, 0))
        assert audit.report()["covered"]["scoring_penalty_choice"] == 1


@pytest.mark.parametrize("wrong_action", [False, True])
def test_scramble_audit_rejects_pass_narration(wrong_action: bool) -> None:
    from tests.semantic_audit import SemanticAudit

    game = make_sample_game()
    game.state.home_score = 6
    result = PlayResult(ResultType.QB_SCRAMBLE, yards=18)
    text = "QB pass complete to Receiver for 18 yards. TOUCHDOWN" if wrong_action else "QB scrambled for 18 yards. TOUCHDOWN"
    outcome = PlayOutcome(play_type=PlayType.TE_SHORT_LONG, defense_type=DefenseType.STANDARD,
                          result=result, yards_gained=18, touchdown=True, description=text)
    audit = SemanticAudit()
    before, rng = deepcopy(game.state), random.getstate()
    if wrong_action:
        with pytest.raises(ValueError, match="scramble"):
            audit.result(game, outcome)
    else:
        audit.result(game, outcome)
        assert audit.report()["covered"]["qb_scramble_td"] == 1
    assert game.state == before and random.getstate() == rng


def test_missing_events_are_explicit_not_success_or_random_game_failure() -> None:
    from tests.semantic_audit import SemanticAudit

    report = SemanticAudit().report()
    assert report["covered"]["qb_scramble_td"] == 0
    assert "qb_scramble_td" in report["unexercised"]


@pytest.mark.parametrize("play", [PlayType.PUNT, PlayType.KICKOFF, PlayType.FIELD_GOAL])
def test_scrimmage_recovery_oracle_does_not_invent_special_teams_requirements(play: PlayType) -> None:
    from tests.semantic_audit import SemanticAudit

    game = make_sample_game()
    result = PlayResult(ResultType.FUMBLE, fumble_recovered=True,
                        description="Returner fumbles; kicking team recovers")
    outcome = PlayOutcome(play_type=play, defense_type=DefenseType.STANDARD, result=result)
    audit = SemanticAudit()
    audit.result(game, outcome)
    assert audit.report()["covered"]["fumble_at_spot"] == 0


def test_scrimmage_spot_wording_oracle_excludes_scoring_safeties() -> None:
    from tests.semantic_audit import SemanticAudit

    game = make_sample_game()
    result = PlayResult(ResultType.FUMBLE, fumble_recovered=True,
                        description="Fumble in own end zone - SAFETY")
    outcome = PlayOutcome(play_type=PlayType.END_RUN, defense_type=DefenseType.STANDARD,
                          result=result, safety=True, yards_gained=-10)
    audit = SemanticAudit()
    audit.result(game, outcome)
    assert audit.report()["covered"]["fumble_at_spot"] == 0


@pytest.mark.parametrize("defect", [None, "passing-stat", "scorer"])
@pytest.mark.parametrize("home", [False, True])
def test_scramble_audit_checks_credited_stats_and_scoring_team(defect: str, home: bool) -> None:
    from tests.semantic_audit import SemanticAudit

    game = make_sample_game()
    game.state.is_home_possession, game.state.ball_position = home, 90
    audit = SemanticAudit()
    audit.before(game)
    game.state.offense_stats.rushing_yards = 0 if defect == "passing-stat" else 10
    game.state.offense_stats.passing_yards = 10 if defect == "passing-stat" else 0
    game.state.scoring_plays = [SimpleNamespace(play_type="TD", is_home_team=not home if defect == "scorer" else home)]
    result = PlayResult(ResultType.QB_SCRAMBLE, yards=18)
    outcome = PlayOutcome(play_type=PlayType.TE_SHORT_LONG, defense_type=DefenseType.STANDARD,
                          result=result, yards_gained=18, touchdown=True,
                          description="QB scrambled for 18 yards. TOUCHDOWN")
    if defect:
        with pytest.raises(ValueError, match="scramble"):
            audit.result(game, outcome)
    else:
        audit.result(game, outcome)
        assert audit.report()["covered"]["qb_scramble_td_accounting"] == 1
