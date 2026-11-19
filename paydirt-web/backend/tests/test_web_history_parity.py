"""Canonical history preserves structured engine results and the snap clock."""
import random
from unittest.mock import patch

import pytest
import routes
from fastapi.testclient import TestClient
from main import app

from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType


@pytest.fixture
def client():
    identities = set(routes.games)
    rng = random.getstate()
    with TestClient(app) as value:
        yield value
    for identity in set(routes.games) - identities:
        routes.games.pop(identity)
    random.setstate(rng)


@pytest.mark.parametrize('interception', [False, True])
@pytest.mark.parametrize('field', ['timeRemaining', 'turnover', 'bigPlayFactor'])
def test_regular_history_preserves_snap_clock_and_structured_result(client, interception, field):
    created = client.post('/api/game/new', json={
        'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks', 'play_as_home': True,
    }).json()
    identity = created['game_id']
    game = routes.games[identity]
    game['is_kickoff'] = False
    engine = game['engine']
    engine.state.is_home_possession = True
    engine.state.quarter, engine.state.time_remaining = 1, 10 / 60
    engine.state.ball_position = 40
    resolved = PlayResult(
        result_type=ResultType.INTERCEPTION if interception else ResultType.YARDS,
        yards=0 if interception else 4, turnover=interception,
        raw_result='INT 0' if interception else '4',
    )
    before = client.get('/api/game/state/' + identity).json()
    with (patch('paydirt.game_engine.resolve_play_with_penalties', return_value=PenaltyChoice(play_result=resolved)),
          patch('paydirt.game_engine.random.uniform', return_value=30)):
        response = client.post('/api/game/execute', json={
            'game_id': identity, 'player_play': '6' if interception else '1', 'cpu_play': 'A',
        })
    assert response.status_code == 200, response.text
    body = response.json()
    entry = body['game_state']['play_history'][0]
    assert entry['quarter'] == before['quarter']
    expected = {'timeRemaining': before['time_remaining'],
        'turnover': body['result']['turnover'], 'bigPlayFactor': body['result']['big_play_factor']}
    assert entry[field] == expected[field]
    assert entry['ruleExplanation'] == body['result']['rule_explanation']
    assert entry['headline'] == body['result']['headline']
    assert entry['possession'] == before['possession']
    assert entry['lineOfScrimmage'] == before['ball_position']

def test_scoring_history_keeps_visible_score_marker(client):
    created = client.post('/api/game/new', json={'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks', 'play_as_home': True}).json()
    identity = created['game_id']
    game = routes.games[identity]
    game['is_kickoff'] = False
    game['engine'].state.is_home_possession = True
    game['engine'].state.ball_position = 94
    with patch('paydirt.game_engine.resolve_play_with_penalties',
               return_value=PenaltyChoice(play_result=PlayResult(result_type=ResultType.YARDS, yards=9))):
        response = client.post('/api/game/execute', json={'game_id': identity, 'player_play': '1', 'cpu_play': 'A'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['result']['touchdown'] is True
    assert body['game_state']['play_history'][0]['scoreChange'] == f"SCORE! {body['game_state']['home_score']}-{body['game_state']['away_score']}"

@pytest.mark.parametrize(('kind', 'expected_spot', 'kicking_home'), [
    ('normal', 35, True), ('receiving-foul', 45, True),
    ('kicking-foul', 25, True), ('safety', 20, True), ('halftime', 35, False),
])
def test_kickoff_history_uses_effective_engine_origin(client, kind, expected_spot, kicking_home):
    created = client.post('/api/game/new', json={'season': '2026', 'player_team': 'Ironclads',
        'opponent_team': 'Thunderhawks', 'play_as_home': True}).json()
    identity = created['game_id']
    game = routes.games[identity]
    engine = game['engine']
    engine.state.is_home_possession = True
    if kind in ('receiving-foul', 'kicking-foul'):
        engine.state.pending_kickoff_penalty_yards = 10
        engine.state.pending_kickoff_penalty_is_offense = kind == 'receiving-foul'
    if kind == 'safety':
        game['safety_free_kick'] = True
    if kind == 'halftime':
        engine.state.quarter, engine.state.time_remaining = 3, 15
        engine._last_play_start_quarter = 2
        engine._opening_kicking_home = True
    for chart in (engine.state.home_chart, engine.state.away_chart):
        chart.special_teams.kickoff = dict.fromkeys(range(10, 40), '65')
        chart.special_teams.kickoff_return = dict.fromkeys(range(10, 40), '0')
    response = client.post('/api/game/kickoff', json={'game_id': identity, 'kickoff_spot': 35})
    assert response.status_code == 200, response.text
    context = engine.last_kickoff_context
    assert context['spot'] == expected_spot
    assert context['kicking_home'] is kicking_home
    entry = response.json()['game_state']['play_history'][0]
    assert entry['lineOfScrimmage'] == context['spot']
    assert entry['ballPosition'] == context['spot']
    assert entry['fieldPosition'] == context['field_position']
    assert entry['possession'] == ('home' if kicking_home else 'away')
    assert entry['offenseTeam'] == (created['game_state']['home_team'] if kicking_home else created['game_state']['away_team'])['short_name']
