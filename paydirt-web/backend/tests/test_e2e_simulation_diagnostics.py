"""Synthetic test-only simulation diagnostics, without a running API."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE = Path(__file__).resolve().parents[2] / 'frontend/e2e/simulation_diagnostics.py'
spec = importlib.util.spec_from_file_location('simulation_diagnostics', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def engine(final=True):
    return SimpleNamespace(state=SimpleNamespace(game_over=final, quarter=4, time_remaining=0,
        home_score=14, away_score=7, is_playoff=False), has_untimed_down=lambda:False,
        pending_post_score_action=lambda:None, has_pending_end_zone_interception=False)


def test_nonfinal_diagnostic_retains_replay_rng_and_same_result(capsys):
    import random
    before = random.getstate()
    result = engine(False)
    wrapped = module.instrument_simulation(lambda *args, **kwargs:result)
    assert wrapped('away', 'home') is result
    record = json.loads(capsys.readouterr().err)
    assert record['kind'] == 'e2e-campaign-final-diagnostic'
    assert record['rng_state'] == json.loads(json.dumps(before))
    assert record['flags']['game_over'] is False
    assert random.getstate() == before


def test_legal_final_emits_nothing_and_preserves_result(capsys):
    result = engine()
    assert module.instrument_simulation(lambda:result)() is result
    assert capsys.readouterr().err == ''


@pytest.mark.parametrize("condition", ["missing", "untimed", "post_score", "end_zone", "tied_playoff"])
def test_each_legal_final_rejection_is_observed(capsys, condition):
    result = None if condition == "missing" else engine()
    if condition == "untimed":
        result.has_untimed_down = lambda: True
    elif condition == "post_score":
        result.pending_post_score_action = lambda: "try"
    elif condition == "end_zone":
        result.has_pending_end_zone_interception = True
    elif condition == "tied_playoff":
        result.state.away_score = result.state.home_score
    assert module.instrument_simulation(lambda **kwargs:result)(is_playoff=True) is result
    assert json.loads(capsys.readouterr().err)['kind'] == 'e2e-campaign-final-diagnostic'
