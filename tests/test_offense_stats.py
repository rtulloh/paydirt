"""Synthetic classification, legacy coverage, and NFL efficiency calculations."""
from types import SimpleNamespace

import pytest

from paydirt.offense_stats import (
    OFFENSIVE_ATTEMPT_FIELDS,
    efficiency,
    record_offensive_attempt,
    validate_offensive_attempt_stats,
)
from paydirt.play_resolver import PlayResult, PlayType, ResultType


@pytest.mark.parametrize('kind,yards,qt,play,key', [
    (ResultType.YARDS,0,0,PlayType.SHORT_PASS,'passing_completions'),
    (ResultType.INCOMPLETE,0,0,PlayType.SHORT_PASS,'passing_attempts'),
    (ResultType.INTERCEPTION,0,0,PlayType.SHORT_PASS,'passing_attempts'),
    (ResultType.QB_SCRAMBLE,5,0,PlayType.SHORT_PASS,'rushing_attempts'),
    (ResultType.FUMBLE,5,20,PlayType.SHORT_PASS,'rushing_attempts'),
    (ResultType.FUMBLE,5,0,PlayType.SHORT_PASS,'passing_completions'),
    (ResultType.YARDS,-2,0,PlayType.QB_KNEEL,'rushing_attempts'),
    (ResultType.INCOMPLETE,0,0,PlayType.SPIKE_BALL,'passing_attempts'),
])
def test_counter_classification(kind,yards,qt,play,key):
    stats=SimpleNamespace(_offensive_attempt_stats=dict.fromkeys(OFFENSIVE_ATTEMPT_FIELDS,0))
    result=PlayResult(result_type=kind,yards=yards,description='Synthetic',qb_scramble_dice=qt)
    record_offensive_attempt(stats,play,result)
    assert stats._offensive_attempt_stats[key]==1
    if key=='rushing_attempts': assert stats._offensive_attempt_stats['passing_attempts']==0


@pytest.mark.parametrize('kind,yards,qt,replay', [
    (ResultType.SACK,-5,0,False),(ResultType.QB_SCRAMBLE,-5,0,False),
    (ResultType.FUMBLE,-5,20,False),(ResultType.PASS_INTERFERENCE,10,0,False),
    (ResultType.PENALTY_OFFENSE,5,0,False),(ResultType.YARDS,5,0,True),
])
def test_sacks_fouls_replays_are_not_pass_or_rush_attempts(kind,yards,qt,replay):
    stats=SimpleNamespace(_offensive_attempt_stats=dict.fromkeys(OFFENSIVE_ATTEMPT_FIELDS,0))
    result=PlayResult(result_type=kind,yards=yards,description='Synthetic',qb_scramble_dice=qt,replay_down=replay)
    record_offensive_attempt(stats,PlayType.SHORT_PASS,result)
    assert not any(stats._offensive_attempt_stats.values())


def test_unknown_legacy_stats_stay_unknown_and_partial_fields_stay_partial():
    result=PlayResult(result_type=ResultType.YARDS,yards=5,description='Synthetic')
    legacy=SimpleNamespace(_offensive_attempt_stats=None)
    record_offensive_attempt(legacy,PlayType.SHORT_PASS,result,touchdown=True)
    assert legacy._offensive_attempt_stats is None
    partial=SimpleNamespace(_offensive_attempt_stats={'passing_attempts':0})
    record_offensive_attempt(partial,PlayType.SHORT_PASS,result,touchdown=True)
    assert partial._offensive_attempt_stats=={'passing_attempts':1}


@pytest.mark.parametrize('inputs,expected', [([10,10,200,3,0],158.3333333),([0,10,0,0,10],0)])
def test_nfl_rating_formula_and_component_clamps(inputs,expected):
    assert efficiency('passer_rating',inputs)==pytest.approx(expected)


@pytest.mark.parametrize('rate,inputs', [('passer_rating',[0,0,0,0,0]),('completion_percentage',[0,0]),('passing_yards_per_attempt',[0,0]),('rushing_yards_per_attempt',[0,0])])
def test_zero_attempt_rates_are_unknown(rate,inputs):
    assert efficiency(rate,inputs) is None


@pytest.mark.parametrize('value', [[], {'unknown':1}, {'passing_attempts':True}, {'passing_attempts':-1},
    {'passing_attempts':1,'passing_completions':2}, {'passing_attempts':1,'passing_touchdowns':2},
    {'passing_completions':1,'passing_touchdowns':2}])
def test_invalid_counter_shapes_or_impossible_totals(value):
    with pytest.raises(ValueError): validate_offensive_attempt_stats(value)


def test_optional_counter_validation():
    assert validate_offensive_attempt_stats(None) is None
    assert validate_offensive_attempt_stats({'passing_attempts':0})=={'passing_attempts':0}



def test_published_manning_2004_reference_rounds_to_121_1():
    assert round(efficiency('passer_rating',[336,497,4557,49,10]),1)==121.1


@pytest.mark.parametrize("kind,expected_touchdowns", [
    (ResultType.YARDS, 1),
    (ResultType.FUMBLE, 0),
])
def test_recovered_receiver_fumble_touchdown_is_not_a_passing_touchdown(kind, expected_touchdowns):
    stats = SimpleNamespace(_offensive_attempt_stats=dict.fromkeys(OFFENSIVE_ATTEMPT_FIELDS, 0))
    result = PlayResult(result_type=kind, yards=5, description="Synthetic")
    record_offensive_attempt(stats, PlayType.SHORT_PASS, result, touchdown=True)
    assert stats._offensive_attempt_stats == {
        "passing_attempts": 1, "passing_completions": 1,
        "passing_touchdowns": expected_touchdowns, "rushing_attempts": 0,
    }
