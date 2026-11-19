"""Lazy coaching RNGs are portable state, never arbitrary runtime objects."""
import json
import random

import pytest
import routes
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def session():
    baseline = set(routes.games)
    global_state = random.getstate()
    with TestClient(app) as client:
        response = client.post('/api/game/new', json={'season':'2026','player_team':'Ironclads',
            'opponent_team':'Thunderhawks','difficulty':'medium'})
        assert response.status_code == 200
        identity = response.json()['game_id']
        game = routes.games[identity]
        engine, ai = game['engine'], game['ai']
        # These are real coach decisions that lazily allocate independent RNGs.
        engine.state.quarter, engine.state.time_remaining = 2, 1
        engine.state.is_home_possession = not game['human_is_home']
        ai.select_offense(engine)
        ai.select_two_point_defense(engine)
        engine.state.down, engine.state.ball_position = 4, 65
        engine.state.time_remaining = 5
        ai.select_offense(engine)
        yield client, identity, game
    for key in set(routes.games) - baseline:
        routes.games.pop(key, None)
    random.setstate(global_state)


def test_real_lazy_coaching_streams_roundtrip_without_changing_global_rng(session):
    client, identity, game = session
    ai = game['ai']
    assert all(type(getattr(ai,name)) is random.Random for name in
        ('_offense_rng','_defense_rng','_decision_rng'))
    global_state = random.getstate()
    exported = client.post('/api/game/checkpoint/' + identity)
    assert exported.status_code == 200, exported.text
    assert random.getstate() == global_state
    restored = client.post('/api/game/restore',json=exported.json())
    assert restored.status_code == 200, restored.text
    assert random.getstate() == global_state
    resumed = routes.games[restored.json()['game_id']]
    for name in ('_offense_rng','_defense_rng','_decision_rng'):
        original, saved = getattr(ai,name), getattr(resumed['ai'],name)
        assert original is not saved
        assert original.getstate() == saved.getstate()
        assert [original.random() for _ in range(8)] == [saved.random() for _ in range(8)]
    # Continue actual coaching calls from the same engine situation and stream.
    for current in (game['engine'], resumed['engine']):
        current.state.down = 1
        current.state.time_remaining = 1
    assert [ai.select_offense(game['engine']) for _ in range(5)] == [
        resumed['ai'].select_offense(resumed['engine']) for _ in range(5)]


@pytest.mark.parametrize('kind',['subclass','arbitrary'])
def test_checkpoint_rejects_rng_subclasses_and_arbitrary_objects(session,kind):
    client,identity,game = session
    class UntrustedRandom(random.Random):
        pass
    game['ai']._offense_rng = UntrustedRandom(1) if kind == 'subclass' else object()
    response = client.post('/api/game/checkpoint/' + identity)
    assert response.status_code == 400


@pytest.mark.parametrize('state',[(4,tuple([0]*624+[0]),None),
    (3,tuple([0]*624+[True]),None),(3,tuple([0]*624+[625]),None),
    (3,tuple([-1]*624+[0]),None),(3,tuple([0]*624+[0]),'not a gaussian')])
def test_invalid_rng_payload_is_atomic_and_preserves_global_rng(session,state):
    from checkpoints import Codec
    client,identity,game = session
    exported = client.post('/api/game/checkpoint/' + identity)
    assert exported.status_code == 200, exported.text
    data = json.loads(exported.json()['checkpoint'])
    data['ai']['attrs']['_offense_rng'] = {'random_state':Codec(game).encode(state)}
    before, global_state = set(routes.games), random.getstate()
    response = client.post('/api/game/restore',json={'checkpoint':json.dumps(data)})
    assert response.status_code == 400, response.text
    assert set(routes.games) == before
    assert random.getstate() == global_state
