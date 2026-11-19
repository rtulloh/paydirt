"""Synthetic optional field-goal coverage and validation contracts."""
from types import SimpleNamespace

import pytest

from paydirt.kicking_stats import (
    empty_field_goal_stats,
    record_field_goal,
    validate_field_goal_stats,
)


@pytest.mark.parametrize('value', [[], {'wrong': 1}, {'field_goals_made': True},
    {'field_goals_attempted': -1}, {'field_goals_made': 2, 'field_goals_attempted': 1},
    {'field_goals_made': 0, 'field_goals_20_29_made': 1},
    {**empty_field_goal_stats(), 'field_goals_made': 1, 'field_goals_attempted': 1}])
def test_reject_invalid_or_inconsistent_counters(value):
    with pytest.raises(ValueError): validate_field_goal_stats(value)


def test_legacy_coverage_cannot_be_fabricated_by_continuation():
    legacy = SimpleNamespace(_field_goal_stats=None)
    record_field_goal(legacy, 42, True)
    assert legacy._field_goal_stats is None
    assert validate_field_goal_stats(None) is None


def test_partial_counter_mapping_retains_unknown_fields():
    partial = SimpleNamespace(_field_goal_stats={'field_goals_attempted': 1})
    record_field_goal(partial, 42, True)
    assert partial._field_goal_stats == {'field_goals_attempted': 2}
    assert validate_field_goal_stats(partial._field_goal_stats) == partial._field_goal_stats
