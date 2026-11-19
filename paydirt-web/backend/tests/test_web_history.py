"""Acknowledged game actions retain authoritative display history in checkpoints."""
import asyncio
import json
import random
from unittest.mock import patch

import pytest
import routes
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    before = set(routes.games)
    rng = random.getstate()
    random.seed(8306)
    with TestClient(app) as value:
        yield value
    for identity in set(routes.games) - before:
        routes.games.pop(identity, None)
    random.setstate(rng)


def test_kickoff_history_survives_checkpoint_registry_loss(client):
    created = client.post('/api/game/new', json={'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks', 'play_as_home': False}).json()
    identity = created['game_id']
    assert client.post('/api/game/coin-toss', json={'game_id': identity,
        'player_won': True, 'player_kicks': True}).status_code == 200
    before = client.get('/api/game/state/' + identity).json()
    kicked = client.post('/api/game/kickoff', json={'game_id': identity}).json()
    history = kicked['game_state'].get('play_history', [])
    assert len(history) == 1
    entry = history[0]
    assert entry['description'] == kicked['result']['description']
    assert entry['possession'] == before['possession']
    assert entry['humanIsHome'] is False
    assert entry['fieldPosition'] == routes.games[identity]['engine'].last_kickoff_context['field_position']
    assert entry['newFieldPosition'] == kicked['game_state']['field_position']
    assert entry['offenseDice'] == kicked['dice_details']['offense']
    checkpoint = client.post('/api/game/checkpoint/' + identity).json()
    routes.games.pop(identity)
    restored = client.post('/api/game/restore', json=checkpoint).json()
    assert restored['play_history'] == history
    assert restored['game_state']['play_history'] == history
    assert client.get('/api/game/state/' + restored['game_id']).json()['play_history'] == history


def test_rejected_action_and_read_operations_do_not_create_history(client):
    created = client.post('/api/game/new', json={'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks'}).json()
    identity = created['game_id']
    assert client.post('/api/game/extra-point', json={'game_id': identity}).status_code == 400
    assert client.get('/api/game/state/' + identity).status_code == 200
    assert routes.games[identity].get('play_history', []) == []


@pytest.mark.parametrize('play', ['1', 'P', 'F'])
def test_ordinary_and_special_plays_use_preplay_identity(client, play):
    data = client.post('/api/game/new', json={'season':'2026','player_team':'Ironclads',
        'opponent_team':'Thunderhawks'}).json()
    identity = data['game_id']
    engine = routes.games[identity]['engine']
    engine.state.is_home_possession = routes.games[identity]['human_is_home']
    routes.games[identity]['is_kickoff'] = False
    engine.state.ball_position = 60
    engine.state.down = 4 if play in {'P','F'} else 1
    before = client.get('/api/game/state/' + identity).json()
    response = client.post('/api/game/execute', json={'game_id':identity,'player_play':play,'cpu_play':'A'})
    assert response.status_code == 200, response.text
    result = response.json()
    if result['result']['pending_penalty_decision']:
        assert result['game_state']['play_history'] == []
        response = client.post('/api/game/penalty-decision',json={
            'game_id':identity,'accept_penalty':False,'penalty_index':0})
        assert response.status_code == 200, response.text
        result = response.json()
    entry = result['game_state']['play_history'][0]
    assert entry['offensePlay'] == play
    assert entry['possession'] == before['possession']
    assert entry['lineOfScrimmage'] == 60
    assert entry['description'] == result['result']['description']


def test_try_history_and_worker_share_acknowledgement_boundary(client):
    from browser_bridge import dispatch_json
    data = client.post('/api/game/new', json={'season':'2026','player_team':'Ironclads',
        'opponent_team':'Thunderhawks'}).json()
    identity = data['game_id']
    game = routes.games[identity]
    game['pending_pat'] = True
    game['engine'].state.is_home_possession = True
    game['engine'].state.home_score = 6
    response = json.loads(asyncio.run(dispatch_json(json.dumps({'method':'POST',
        'path':'/api/game/extra-point','body':{'game_id':identity}}))))
    assert response['status'] == 200, response
    entry = response['body']['game_state']['play_history'][0]
    assert entry['offensePlay'] == 'XP'
    assert entry['description'] == response['body']['description']
    assert entry['possession'] == 'home'
    assert client.get('/api/game/state/' + identity).json()['play_history'] == [entry]


def test_pending_interception_survives_checkpoint_and_logs_once_when_resolved(client):
    from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType
    data = client.post('/api/game/new', json={'season':'2026','player_team':'Ironclads',
        'opponent_team':'Thunderhawks','player_end_zone_interception_policy':'ask'}).json()
    identity = data['game_id']
    engine = routes.games[identity]['engine']
    engine.state.is_home_possession = False
    engine.state.ball_position = 90
    result = PlayResult(result_type=ResultType.INTERCEPTION,yards=14,turnover=True,raw_result='INT 14')
    with patch('paydirt.game_engine.resolve_play_with_penalties',return_value=PenaltyChoice(play_result=result)):
        played = client.post('/api/game/execute',json={'game_id':identity,'player_play':'A','cpu_play':'6'}).json()
    assert played['result']['pending_end_zone_interception_return_decision']
    assert played['game_state']['play_history'] == []
    checkpoint = client.post('/api/game/checkpoint/' + identity).json()
    routes.games.pop(identity)
    restored = client.post('/api/game/restore',json=checkpoint).json()
    resolved = client.post('/api/game/end-zone-interception-decision',json={
        'game_id':restored['game_id'],'attempt_return':False})
    assert resolved.status_code == 200, resolved.text
    history = resolved.json()['game_state']['play_history']
    assert len(history) == 1
    assert history[0]['lineOfScrimmage'] == 90
    assert history[0]['possession'] == 'away'
    assert history[0]['offensePlay'] == '6'
    assert history[0]['description'] == resolved.json()['result']['description']


@pytest.mark.parametrize('accept', [True, False])
def test_pending_penalty_logs_only_resolved_decision_and_original_preplay_state(client, accept):
    from paydirt.play_resolver import PenaltyChoice, PenaltyOption, PlayResult, ResultType
    data = client.post('/api/game/new',json={'season':'2026','player_team':'Ironclads',
        'opponent_team':'Thunderhawks','play_as_home':True}).json()
    identity = data['game_id']
    game = routes.games[identity]
    game['is_kickoff'] = False
    engine = game['engine']
    engine.state.is_home_possession = False
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 77, 3, 9
    choice = PenaltyChoice(PlayResult(ResultType.INCOMPLETE,description='Synthetic engine incomplete'),
        [PenaltyOption('OFF','OFF 5',5,'Offensive penalty, 5 yards')],offended_team='defense')
    with patch('paydirt.game_engine.resolve_play_with_penalties',return_value=choice):
        played = client.post('/api/game/execute',json={'game_id':identity,'player_play':'A','cpu_play':'6'})
    assert played.status_code == 200, played.text
    assert played.json()['result']['pending_penalty_decision']
    assert played.json()['game_state']['play_history'] == []
    checkpoint = client.post('/api/game/checkpoint/' + identity).json()
    routes.games.pop(identity)
    restored = client.post('/api/game/restore',json=checkpoint).json()
    decided = client.post('/api/game/penalty-decision',json={'game_id':restored['game_id'],
        'accept_penalty':accept,'penalty_index':0})
    assert decided.status_code == 200, decided.text
    history = decided.json()['game_state']['play_history']
    assert len(history) == 1
    assert history[0]['lineOfScrimmage'] == 77
    assert history[0]['down'] == 3
    assert history[0]['yardsToGo'] == 9
    assert history[0]['possession'] == 'away'
    assert history[0]['description'] == decided.json()['result']['description']
