"""Run/pass learning counts selections, not every action that is not a pass."""

from copy import deepcopy

import pytest

from paydirt.ai_analysis import OpponentModel, OpponentTendencyTracker, PlayCategory
from paydirt.play_resolver import CHART_PLAY_TYPES, PlayType, is_passing_play


@pytest.mark.parametrize("play", [PlayType.PUNT, PlayType.FIELD_GOAL, PlayType.KICKOFF,
                                 PlayType.QB_KNEEL, PlayType.SPIKE_BALL])
@pytest.mark.parametrize("override", [None, False, True])
def test_special_actions_do_not_change_tendencies_or_streaks(play: PlayType, override: bool) -> None:
    tracker = OpponentTendencyTracker()
    for _ in range(3):
        tracker.record_play(1, 10, "short_pass", 6, is_pass=True)
    before = deepcopy(tracker.to_dict())
    tracker.record_play(4, 10, play.value, 0, is_pass=override)
    assert tracker.to_dict() == before
    assert tracker.get_streak() == PlayCategory.PASS


@pytest.mark.parametrize("play", [*CHART_PLAY_TYPES, PlayType.QB_SNEAK, PlayType.HAIL_MARY])
@pytest.mark.parametrize("display_name", [False, True])
def test_actual_run_pass_calls_work_without_a_boolean_override(play: PlayType, display_name: bool) -> None:
    tracker = OpponentTendencyTracker()
    name = play.value.replace("_", " ").title() if display_name else play.value
    tracker.record_play(3, 2, name, 2)
    tendency = tracker.get_tendency(3, 2)
    assert tendency.total_plays == 1
    assert tendency.pass_plays == int(is_passing_play(play))
    assert tendency.run_plays == int(not is_passing_play(play))
    assert tendency.special_plays == 0


def test_mixed_matchup_accounting_excludes_two_punts_and_field_goal() -> None:
    model = OpponentModel()
    for _ in range(32):
        model.record_opponent_play(1, 10, "off_tackle", 4, is_pass=False)
    for _ in range(26):
        model.record_opponent_play(2, 6, "medium_pass", 7, is_pass=True)
    for play in (PlayType.PUNT, PlayType.PUNT, PlayType.FIELD_GOAL):
        model.record_opponent_play(4, 6, play.value, 0, is_pass=False)
    totals = [model.tracker.get_tendency(down, distance) for down, distance in ((1, 10), (2, 6), (4, 6))]
    assert sum(t.total_plays for t in totals) == 58
    assert sum(t.run_plays for t in totals) == 32
    assert sum(t.pass_plays for t in totals) == 26
    assert model.tracker.get_streak() == PlayCategory.PASS
    restored = OpponentModel.from_dict(model.to_dict())
    assert restored.tracker.to_dict() == model.tracker.to_dict()


@pytest.mark.parametrize("name", ["RUN", "PASS", "Long", "Med", "Short", "T/E S/L"])
def test_legacy_primary_names_still_count(name: str) -> None:
    tracker = OpponentTendencyTracker()
    tracker.record_play(1, 10, name, 5)
    tendency = tracker.get_tendency(1, 10)
    assert tendency.total_plays == 1
    assert tendency.special_plays == 0


@pytest.mark.parametrize("name", ["unknown", "breakaway", "qb_time", "", "Long Kickoff"])
def test_unknown_and_secondary_actions_are_not_guessed_from_substrings(name: str) -> None:
    tracker = OpponentTendencyTracker()
    tracker.record_play(1, 10, name, 0, is_pass=False)
    assert tracker.to_dict() == OpponentTendencyTracker().to_dict()
