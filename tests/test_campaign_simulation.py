"""Campaign simulation uses real engine orchestration and preserves caller RNG."""
import random
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SAMPLES = Path(__file__).resolve().parents[1] / 'seasons' / '2026'


def test_auto_game_import_does_not_load_cli_ui():
    result = subprocess.run([sys.executable, '-c',
        "import sys; import paydirt.auto_game; assert 'paydirt.interactive_game' not in sys.modules"],
        text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_campaign_simulates_legal_final_and_retains_caller_rng():
    from paydirt.campaign_simulation import simulate_game
    before = random.getstate()
    engine = simulate_game(SAMPLES / 'Ironclads', SAMPLES / 'Thunderhawks', SAMPLES, seed=883)
    assert random.getstate() == before
    assert engine.state.game_over
    assert engine.season_rules.season == 2026
    assert engine.state.home_chart.team_dir.endswith('Ironclads')
    assert engine.state.away_chart.team_dir.endswith('Thunderhawks')
    assert engine.pending_post_score_action() is None
    assert not engine.has_pending_end_zone_interception
    assert not engine.has_untimed_down()


def test_campaign_simulation_restores_rng_after_failure():
    from paydirt.campaign_simulation import simulate_game
    before = random.getstate()
    with pytest.raises(RuntimeError, match='play limit'):
        simulate_game(SAMPLES / 'Ironclads', SAMPLES / 'Thunderhawks', SAMPLES, seed=883, play_limit=1)
    assert random.getstate() == before


def test_campaign_rules_override_is_used_before_first_play(tmp_path):
    from paydirt.campaign_simulation import simulate_game
    rules = (SAMPLES / '2026.yaml').read_text().replace('2026', '2030')
    directory = tmp_path / '2030'
    directory.mkdir()
    (directory / '2030.yaml').write_text(rules)
    engine = simulate_game(SAMPLES / 'Ironclads', SAMPLES / 'Thunderhawks', directory, seed=884)
    assert engine.season_rules.season == 2030


def test_campaign_rejects_nonfinal_engine():
    from paydirt.campaign_simulation import simulate_game
    from paydirt.chart_loader import load_team_chart
    from paydirt.game_engine import PaydirtGameEngine
    engine = PaydirtGameEngine(load_team_chart(SAMPLES / 'Ironclads'), load_team_chart(SAMPLES / 'Thunderhawks'))
    with (patch('paydirt.campaign_simulation.run_auto_game', return_value=engine),
          pytest.raises(RuntimeError, match='legal final')):
        simulate_game(SAMPLES / 'Ironclads', SAMPLES / 'Thunderhawks', SAMPLES)


@pytest.mark.parametrize('seed', [-1, True, '1'])
def test_campaign_rejects_invalid_seed(seed):
    from paydirt.campaign_simulation import simulate_game
    with pytest.raises(ValueError, match='seed'):
        simulate_game(SAMPLES / 'Ironclads', SAMPLES / 'Thunderhawks', SAMPLES, seed=seed)
