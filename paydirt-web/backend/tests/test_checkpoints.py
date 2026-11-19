"""Portable sessions preserve engine state rather than reconstructing display text."""
import json
import shutil
from pathlib import Path

import pytest
import routes
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    before = set(routes.games)
    with TestClient(app) as value:
        yield value
    for key in set(routes.games) - before:
        routes.games.pop(key, None)


def new_game(client, **extra):
    response = client.post('/api/game/new', json={
        'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks', **extra,
    })
    assert response.status_code == 200, response.text
    return response.json()['game_id']


@pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard'])
def test_checkpoint_restores_full_session_after_registry_loss(client, difficulty):
    game_id = new_game(client, difficulty=difficulty)
    game = routes.games[game_id]
    game['engine'].state.home_score = 17
    game['engine'].state.home_stats.sacks = 3
    game['engine'].state.time_remaining = 3.25
    game['pending_pat'] = True
    game['play_history'] = [{'description': 'not authoritative touchdown prose'}]
    response = client.post(f'/api/game/checkpoint/{game_id}')
    assert response.status_code == 200
    checkpoint = response.json()['checkpoint']
    assert isinstance(checkpoint, str)
    assert str(Path.cwd()) not in checkpoint
    routes.games.pop(game_id)
    restored = client.post('/api/game/restore', json={'checkpoint': checkpoint})
    assert restored.status_code == 200, restored.text
    data = restored.json()
    resumed = routes.games[data['game_id']]
    assert resumed['engine'].state.home_score == 17
    assert resumed['engine'].state.home_stats.sacks == 3
    assert resumed['engine'].state.time_remaining == 3.25
    assert resumed['pending_pat'] is True
    assert data['play_history'] == game['play_history']
    assert data['difficulty'] == difficulty
    # Export -> restore -> export retains canonical payload, aside from session ID/time.
    second = client.post(f"/api/game/checkpoint/{data['game_id']}").json()['checkpoint']
    assert json.loads(second) == json.loads(checkpoint)


def test_checkpoint_corruption_is_atomic(client):
    game_id = new_game(client)
    before = set(routes.games)
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200
    data = json.loads(exported.json()['checkpoint'])
    data['teams']['home']['hashes']['offense.csv'] = '0' * 64
    response = client.post('/api/game/restore', json={'checkpoint': json.dumps(data)})
    assert response.status_code == 400
    assert set(routes.games) == before


@pytest.mark.parametrize('payload', ['{}', 'null', '{', '{"version":999}', 'NaN'])
def test_invalid_checkpoint_rejected_without_mutation(client, payload):
    before = set(routes.games)
    response = client.post('/api/game/restore', json={'checkpoint': payload})
    assert response.status_code == 400
    assert set(routes.games) == before


def test_cross_year_same_franchise_preserves_control_and_rules(client, tmp_path, monkeypatch):
    source = Path(routes.SEASONS_DIR) / '2026'
    for year in ['2030', '2031']:
        dest = tmp_path / year
        shutil.copytree(source, dest)
        rules = dest / '2026.yaml'
        (dest / f'{year}.yaml').write_text(rules.read_text().replace('2026', year))
        rules.unlink()
    monkeypatch.setattr(routes, 'get_all_season_paths', lambda: [tmp_path])
    response = client.post('/api/game/new', json={
        'season': '2030', 'player_season': '2030', 'opponent_season': '2031',
        'player_team': 'Ironclads', 'opponent_team': 'Ironclads', 'play_as_home': False,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    state = data['game_state']
    assert state['human_is_home'] is False
    assert state['home_team']['edition_id'] == '2031/Ironclads'
    assert state['away_team']['edition_id'] == '2030/Ironclads'
    assert state['season'] == '2031'
    assert routes.games[data['game_id']]['engine'].season_rules.season == 2031
    exported = client.post(f"/api/game/checkpoint/{data['game_id']}")
    assert exported.status_code == 200
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    assert restored.json()['game_state']['human_is_home'] is False
    assert restored.json()['game_state']['away_team']['edition_id'] == '2030/Ironclads'


def test_ordinary_same_year_control_still_works(client):
    game_id = new_game(client, play_as_home=False)
    assert routes.games[game_id]['home_team'].id == 'Thunderhawks'


def test_missing_required_state_field_is_rejected(client):
    game_id = new_game(client)
    payload = json.loads(client.post(f'/api/game/checkpoint/{game_id}').json()['checkpoint'])
    del payload['engine']['attrs']['state']['attrs']['home_score']
    before = set(routes.games)
    response = client.post('/api/game/restore', json={'checkpoint': json.dumps(payload)})
    assert response.status_code == 400
    assert set(routes.games) == before


def test_pending_interception_checkpoint_continues_decision(client):
    from unittest.mock import patch

    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType
    game_id = new_game(client, player_end_zone_interception_policy='ask')
    engine = routes.games[game_id]['engine']
    engine.state.is_home_possession = False
    engine.state.ball_position = 90
    result = PlayResult(result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result='INT 14')
    with patch('paydirt.game_engine.resolve_play_with_penalties', return_value=PenaltyChoice(play_result=result)):
        played = client.post('/api/game/execute', json={'game_id': game_id, 'player_play': 'A', 'cpu_play': '6'})
    assert played.status_code == 200
    assert played.json()['result']['pending_end_zone_interception_return_decision']
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    resumed = routes.games[restored.json()['game_id']]['engine']
    pending = restored.json()['pending_result']
    assert pending['pending_end_zone_interception_return_decision'] is True
    assert pending['int_catch_depth'] == played.json()['result']['int_catch_depth']
    assert pending['int_return_team'] == played.json()['result']['int_return_team']
    assert resumed.has_pending_end_zone_interception
    assert resumed.state.is_home_possession is False
    original = engine.apply_end_zone_interception_return_decision(engine._last_play_outcome, False)
    continued = resumed.apply_end_zone_interception_return_decision(resumed._last_play_outcome, False)
    assert continued.description == original.description
    assert resumed.state.ball_position == engine.state.ball_position
    assert resumed.state.is_home_possession == engine.state.is_home_possession


def test_checkpoint_cannot_replace_bound_chart_with_other_side(client):
    game_id = new_game(client)
    data = json.loads(client.post(f'/api/game/checkpoint/{game_id}').json()['checkpoint'])
    data['engine']['attrs']['state']['attrs']['home_chart'] = {'ref': 'away'}
    response = client.post('/api/game/restore', json={'checkpoint': json.dumps(data)})
    assert response.status_code == 400


def test_worker_checkpoint_transport_matches_http(client):
    import asyncio

    from browser_bridge import dispatch_json
    game_id = new_game(client, difficulty='hard')
    exported = json.loads(asyncio.run(dispatch_json(json.dumps({
        'method': 'POST', 'path': f'/api/game/checkpoint/{game_id}',
    }))))
    assert exported['status'] == 200
    restored = json.loads(asyncio.run(dispatch_json(json.dumps({
        'method': 'POST', 'path': '/api/game/restore',
        'body': json.dumps(exported['body']),
    }))))
    assert restored['status'] == 200
    assert restored['body']['game_state']['home_team']['edition_id'] == '2026/Ironclads'


@pytest.mark.parametrize('field,value', [('untimed_down_pending', 'false'), ('is_playoff', 1),
                                         ('scoring_plays', {'bad': True})])
def test_checkpoint_rejects_wrong_engine_field_types(client, field, value):
    game_id = new_game(client)
    data = json.loads(client.post(f'/api/game/checkpoint/{game_id}').json()['checkpoint'])
    data['engine']['attrs']['state']['attrs'][field] = value
    before = set(routes.games)
    response = client.post('/api/game/restore', json={'checkpoint': json.dumps(data)})
    assert response.status_code == 400
    assert set(routes.games) == before


def test_checkpoint_serializes_retained_return_chain(client):
    from paydirt.game_engine import ReturnChain
    from paydirt.play_resolver import PlayResult, ResultType
    game_id = new_game(client)
    result = PlayResult(result_type=ResultType.YARDS, yards=4)
    result.int_return_chain = ReturnChain(first_roll=26, first_cell="4", possession_home=True, spot=24)
    routes.games[game_id]['return_chain_test'] = result
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    retained = routes.games[restored.json()['game_id']]['return_chain_test']
    assert type(retained.int_return_chain) is ReturnChain


def test_checkpoint_never_embeds_unbound_chart_objects(client):
    import copy
    game_id = new_game(client, difficulty='hard')
    game = routes.games[game_id]
    game['ai'].team_analyzer = copy.deepcopy(game['ai'].team_analyzer)
    response = client.post(f'/api/game/checkpoint/{game_id}')
    assert response.status_code == 400
    assert 'offense.csv' not in response.text
    assert str(Path.cwd()) not in response.text


def test_checkpoint_response_exposes_effective_rules_year(client, tmp_path, monkeypatch):
    game_id = new_game(client)
    rules_dir = tmp_path / '2030'
    rules_dir.mkdir()
    (rules_dir / '2030.yaml').write_text((Path(routes.SEASONS_DIR) / '2026' / '2026.yaml').read_text().replace('2026', '2030'))
    monkeypatch.setattr(routes, 'get_all_season_paths', lambda: [tmp_path, Path(routes.SEASONS_DIR)])
    routes.games[game_id]['engine'].season_rules = routes.load_season_rules(rules_dir)
    response = client.get(f'/api/game/state/{game_id}')
    assert response.json()['rules_season'] == '2030'
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200
    assert restored.json()['game_state']['rules_season'] == '2030'


def test_restore_exposes_authoritative_pending_penalty_preview(client):
    from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType
    game_id = new_game(client)
    engine = routes.games[game_id]['engine']
    from paydirt.game_state import PlayOutcome
    from paydirt.play_resolver import DefenseType, PlayType
    outcome = PlayOutcome(play_type=next(iter(PlayType)), defense_type=next(iter(DefenseType)),
        result=PlayResult(result_type=ResultType.YARDS, yards=4), yards_gained=4, description='Synthetic retained play')
    outcome.pending_penalty_decision = True
    outcome.penalty_choice = PenaltyChoice(play_result=PlayResult(result_type=ResultType.YARDS, yards=4), offended_team='offense',
        penalty_options=[PenaltyOption(penalty_type='D', raw_result='D 5', yards=5, description='Synthetic foul')])
    engine._last_play_outcome = outcome
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    pending = restored.json()['pending_result']
    assert pending['pending_penalty_decision'] is True
    assert pending['description'] == 'Synthetic retained play'
    assert pending['penalty_choice']['offended_team'] == 'offense'
    assert pending['penalty_choice']['penalty_options'][0]['yards'] == 5


def test_restore_without_pending_choice_has_no_pending_result(client):
    game_id = new_game(client)
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200
    assert restored.json()['pending_result'] is None


def test_punt_checkpoint_restores_numeric_preplay_position_and_next_offense(client):
    import random
    game_id = new_game(client)
    game = routes.games[game_id]
    state = game['engine'].state
    state.is_home_possession = False
    state.ball_position = 11
    state.down = 4
    state.yards_to_go = 7
    random_state = random.getstate()
    try:
        random.seed(8306)
        played = client.post('/api/game/execute', json={
            'game_id': game_id, 'player_play': 'A', 'cpu_play': 'P'})
    finally:
        random.setstate(random_state)
    assert played.status_code == 200, played.text
    assert not played.json()['result'].get('pending_penalty_decision')
    assert played.json()['game_state']['player_offense'] is True
    assert game['engine'].play_log[-1].field_position_before == 11
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    assert restored.json()['game_state']['player_offense'] is True
    assert restored.json()['game_state']['down'] == 1
    resumed = routes.games[restored.json()['game_id']]
    assert resumed['engine'].play_log[-1].field_position_before == 11
    assert resumed['engine'].state.ball_position == state.ball_position


@pytest.mark.parametrize('position', [0, 11, 100, -1, 101, True, 11.5, None, {}])
def test_legacy_numeric_outcome_positions_are_bounded_and_not_coerced(client, position):
    from paydirt.game_state import DefenseType, PlayOutcome, PlayType
    from paydirt.play_resolver import PlayResult, ResultType
    game_id = new_game(client)
    outcome = PlayOutcome(play_type=PlayType.PUNT, defense_type=DefenseType.STANDARD,
                          result=PlayResult(result_type=ResultType.YARDS),
                          field_position_before=position)
    routes.games[game_id]['engine'].play_log.append(outcome)
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    before = set(routes.games)
    restored = client.post('/api/game/restore', json=exported.json())
    valid = type(position) is int and 0 <= position <= 100
    assert restored.status_code == (200 if valid else 400), restored.text
    if not valid:
        assert set(routes.games) == before


@pytest.mark.parametrize('chart_yards', [1, 45])
@pytest.mark.parametrize('accept', [False, True])
def test_pending_field_goal_penalty_checkpoint_preserves_decision_context(client, chart_yards, accept):
    from unittest.mock import patch

    from paydirt.play_resolver import FieldGoalResult, PenaltyOption
    game_id = new_game(client)
    engine = routes.games[game_id]['engine']
    state = engine.state
    state.is_home_possession = False
    state.ball_position, state.down, state.yards_to_go = 83, 2, 10
    state.quarter, state.time_remaining = 2, 9 / 60
    result = FieldGoalResult(dice_roll=15, dice_desc='synthetic roll', raw_result=str(chart_yards),
                            chart_yards=chart_yards, is_penalty=True,
                            penalty_options=[PenaltyOption('OFF', 'OFF 5', 5, 'Synthetic foul')],
                            offsetting=False, offended_team='defense', reroll_log=[])
    with patch('paydirt.game_engine.resolve_field_goal_with_penalties', return_value=result):
        played = client.post('/api/game/execute', json={
            'game_id':game_id, 'player_play':'A', 'cpu_play':'F'})
    assert played.status_code == 200, played.text
    assert played.json()['result']['pending_penalty_decision'] is True
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    assert exported.status_code == 200, exported.text
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 200, restored.text
    assert restored.json()['pending_result']['pending_penalty_decision'] is True
    resumed = routes.games[restored.json()['game_id']]['engine']
    for field in ['_fg_distance_to_goal', '_fg_statistical_distance', '_fg_spot_of_hold',
                  '_fg_ball_pos_before', '_fg_ytg_before']:
        assert getattr(resumed._last_play_outcome, field) == getattr(engine._last_play_outcome, field)
    with patch('paydirt.game_engine.random.uniform', return_value=5):
        responses = [client.post('/api/game/penalty-decision', json={
            'game_id':identity,'accept_penalty':accept,'penalty_index':0})
            for identity in [game_id, restored.json()['game_id']]]
    for response in responses:
        assert response.status_code == 200, response.text
        assert not response.json()['result'].get('pending_penalty_decision')
    for key in ['home_score','away_score','time_remaining','field_position','down','yards_to_go','possession']:
        assert responses[0].json()['game_state'][key] == responses[1].json()['game_state'][key]


@pytest.mark.parametrize('field', ['_fg_distance_to_goal','_fg_statistical_distance',
                                  '_fg_spot_of_hold','_fg_ball_pos_before','_fg_ytg_before'])
@pytest.mark.parametrize('value', [True, 3.5, '17', None, {}])
def test_checkpoint_field_goal_context_rejects_noninteger_values(client, field, value):
    from paydirt.game_state import DefenseType, PlayOutcome, PlayType
    from paydirt.play_resolver import PlayResult, ResultType
    game_id = new_game(client)
    outcome = PlayOutcome(play_type=PlayType.FIELD_GOAL, defense_type=DefenseType.STANDARD,
                          result=PlayResult(result_type=ResultType.YARDS))
    setattr(outcome, field, value)
    routes.games[game_id]['engine'].play_log.append(outcome)
    exported = client.post(f'/api/game/checkpoint/{game_id}')
    before = set(routes.games)
    restored = client.post('/api/game/restore', json=exported.json())
    assert restored.status_code == 400
    assert set(routes.games) == before



def test_kicking_checkpoint_counts_and_absent_legacy_coverage(client):
    game_id = new_game(client)
    stats = routes.games[game_id]['engine'].state.home_stats
    stats._offensive_attempt_stats['passing_attempts'] = 3
    stats._offensive_attempt_stats['passing_completions'] = 2
    stats._field_goal_stats['field_goals_attempted'] = 1
    stats._field_goal_stats['field_goals_30_39_attempted'] = 1
    checkpoint = client.post(f'/api/game/checkpoint/{game_id}').json()['checkpoint']
    response = client.post('/api/game/restore', json={'checkpoint': checkpoint})
    assert response.status_code == 200, response.text
    restored = routes.games[response.json()['game_id']]['engine']
    assert restored.state.home_stats._field_goal_stats == stats._field_goal_stats
    assert restored.state.home_stats._offensive_attempt_stats == stats._offensive_attempt_stats
    data = json.loads(checkpoint)
    def remove_extra(value):
        if isinstance(value, dict):
            if value.get('record') == 'paydirt.game_state.TeamStats':
                value['attrs'].pop('_field_goal_stats', None)
                value['attrs'].pop('_offensive_attempt_stats', None)
            for child in value.values(): remove_extra(child)
        elif isinstance(value, list):
            for child in value: remove_extra(child)
    remove_extra(data)
    legacy = client.post('/api/game/restore', json={'checkpoint': json.dumps(data)})
    assert legacy.status_code == 200, legacy.text
    assert routes.games[legacy.json()['game_id']]['engine'].state.home_stats._field_goal_stats is None
    assert routes.games[legacy.json()['game_id']]['engine'].state.home_stats._offensive_attempt_stats is None



def test_checkpoint_rejects_impossible_kicking_counters_atomically(client):
    game_id = new_game(client)
    routes.games[game_id]['engine'].state.home_stats._field_goal_stats = {
        'field_goals_attempted': 1, 'field_goals_made': 2}
    checkpoint = client.post(f'/api/game/checkpoint/{game_id}').json()['checkpoint']
    before = set(routes.games)
    response = client.post('/api/game/restore', json={'checkpoint': checkpoint})
    assert response.status_code == 400
    assert set(routes.games) == before


def test_extended_stats_checkpoint_roundtrip_partial_unknown_and_invalid_atomic(client):
    game_id = new_game(client)
    expected = {"longest_rush": 31, "third_down_attempts": 4, "third_down_conversions": 2}
    routes.games[game_id]["engine"].state.home_stats._extended_team_stats = expected
    saved = client.post(f"/api/game/checkpoint/{game_id}")
    assert saved.status_code == 200, saved.text
    raw = json.loads(saved.json()["checkpoint"])
    restored = client.post("/api/game/restore", json={"checkpoint": json.dumps(raw)})
    assert restored.status_code == 200, restored.text
    assert routes.games[restored.json()["game_id"]]["engine"].state.home_stats._extended_team_stats == expected
    attrs = raw["engine"]["attrs"]["state"]["attrs"]["home_stats"]["attrs"]
    attrs.pop("_extended_team_stats")
    raw["engine"]["attrs"].pop("_team_stats_context")
    raw["engine"]["attrs"].pop("_team_stats_depth")
    legacy = client.post("/api/game/restore", json={"checkpoint": json.dumps(raw)})
    assert legacy.status_code == 200, legacy.text
    assert routes.games[legacy.json()["game_id"]]["engine"].state.home_stats._extended_team_stats is None
    attrs["_extended_team_stats"] = {"mapping": [["third_down_attempts", 1], ["third_down_conversions", 2]], "kind": "dict", "factory": None}
    before = set(routes.games)
    rejected = client.post("/api/game/restore", json={"checkpoint": json.dumps(raw)})
    assert rejected.status_code == 400
    assert set(routes.games) == before


def test_checkpoint_rejects_in_flight_extended_stats_capture_depth(client):
    identity = new_game(client)
    raw = json.loads(client.post(f"/api/game/checkpoint/{identity}").json()["checkpoint"])
    raw["engine"]["attrs"]["_team_stats_depth"] = 1
    before = set(routes.games)
    rejected = client.post("/api/game/restore", json={"checkpoint": json.dumps(raw)})
    assert rejected.status_code == 400
    assert set(routes.games) == before


@pytest.mark.parametrize("context", [
    {"home": "away"},
    {"home": True, "ball": -1, "down": 1, "first_downs": 0, "passing_yards": 0, "rushing_yards": 0, "pending": True},
    {"home": True, "ball": 50, "down": 0, "first_downs": 0, "passing_yards": 0, "rushing_yards": 0, "pending": True},
    {"home": True, "ball": 50, "down": 1, "first_downs": 0, "passing_yards": 0, "rushing_yards": 0, "pending": True, "unknown": 0},
    {"home": True, "ball": 50, "down": 1, "first_downs": 0, "passing_yards": 0, "rushing_yards": 0, "pending": True, "return": {"home": True, "yards": "ten", "touchdown": False, "cancelled": False}},
])
def test_checkpoint_rejects_malformed_extended_capture_context_atomically(client, context):
    identity = new_game(client)
    routes.games[identity]["engine"]._team_stats_context = context
    checkpoint = client.post(f"/api/game/checkpoint/{identity}").json()["checkpoint"]
    before = set(routes.games)
    response = client.post("/api/game/restore", json={"checkpoint": checkpoint})
    assert response.status_code == 400
    assert set(routes.games) == before


def test_checkpoint_rejects_valid_capture_context_without_pending_engine_choice(client):
    identity = new_game(client)
    routes.games[identity]["engine"]._team_stats_context = {
        "home": True, "ball": 50, "down": 1, "first_downs": 0,
        "passing_yards": 0, "rushing_yards": 0, "pending": True}
    checkpoint = client.post(f"/api/game/checkpoint/{identity}").json()["checkpoint"]
    before = set(routes.games)
    response = client.post("/api/game/restore", json={"checkpoint": checkpoint})
    assert response.status_code == 400
    assert "no pending engine choice" in response.json()["detail"]
    assert set(routes.games) == before
