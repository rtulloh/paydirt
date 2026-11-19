"""Versioned portable session checkpoints using a closed, data-only type registry.

No modules or classes are selected by an import path from an input document.
Charts are references to locally validated catalog assets, never embedded data.
Unknown runtime objects fail export rather than producing incomplete saves.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import types
from collections import Counter, defaultdict, deque
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from paydirt import (
    ai_analysis,
    computer_ai,
    game_engine,
    game_state,
    penalty_handler,
    play_events,
    play_resolver,
    priority_chart,
    season_rules,
)

NESTED_LIST_FACTORY = ai_analysis.OpponentTendencyTracker().situation_results.default_factory

MAX_CHECKPOINT_BYTES = 8 * 1024 * 1024
MODULES = (ai_analysis, computer_ai, game_state, game_engine, penalty_handler, play_events,
           play_resolver, priority_chart, season_rules)
RECORDS = {f"{module.__name__}.{name}": cls for module in MODULES
           for name, cls in vars(module).items()
           if isinstance(cls, type) and cls.__module__ == module.__name__
           and (is_dataclass(cls) or issubclass(cls, Enum))}


# Engine-owned attributes attached to records outside their dataclass fields.
# Keep this closed and typed so pending decisions survive without accepting
# arbitrary checkpoint attributes.
RECORD_EXTRAS = {
    game_state.TeamStats: {'_turnover_breakdown_complete': bool, '_field_goal_stats': dict[str, int] | None, '_offensive_attempt_stats': dict[str, int] | None, '_extended_team_stats': dict[str, int] | None},
    game_state.PlayOutcome: {
        '_fg_distance_to_goal': int, '_fg_statistical_distance': int,
        '_fg_spot_of_hold': int, '_fg_ball_pos_before': int, '_fg_ytg_before': int,
    },
}

OBJECT_TYPES = {
    'paydirt.game_engine.PaydirtGameEngine', 'paydirt.computer_ai.ComputerAI',
    'paydirt.ai_analysis.OpponentModel', 'paydirt.ai_analysis.OpponentTendencyTracker',
    'paydirt.ai_analysis.TeamAnalyzer', 'paydirt.ai_analysis.OffenseAnalyzer',
    'paydirt.ai_analysis.DefenseAnalyzer', 'paydirt.offense_strategy.OffensiveStrategy',
}


def _matches(value: Any, annotation: Any) -> bool:
    """Strictly validate trusted source annotations without coercing save values."""
    if annotation is Any:
        return True
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        return any(_matches(value, option) for option in args)
    if annotation is float:
        return type(value) in (float, int) and math.isfinite(value)
    if annotation in (str, int, bool, type(None)):
        return type(value) is annotation
    if origin in (list, set, tuple) or annotation in (list, set, tuple):
        kind = origin or annotation
        if type(value) is not kind:
            return False
        if not args:
            return True
        if kind is tuple and (len(args) != 2 or args[-1] is not Ellipsis):
            return len(value) == len(args) and all(_matches(v, t) for v, t in zip(value, args))
        return all(_matches(v, args[0]) for v in value)
    if origin is dict or annotation is dict:
        return isinstance(value, dict) and (not args or all(
            _matches(k, args[0]) and _matches(v, args[1]) for k, v in value.items()))
    if isinstance(annotation, type):
        return type(value) is annotation
    raise ValueError('Unsupported checkpoint field annotation')


def _validate_record(cls: type, decoded: dict) -> None:
    hints = get_type_hints(cls, localns={"ReturnChain": game_engine.ReturnChain})
    if cls is game_state.GameState:
        hints['scoring_plays'] = list[game_state.ScoringPlay]
    if cls is game_state.TeamStats and '_field_goal_stats' in decoded:
        from paydirt.kicking_stats import validate_field_goal_stats
        validate_field_goal_stats(decoded['_field_goal_stats'])
    if cls is game_state.TeamStats and "_extended_team_stats" in decoded:
        from paydirt.team_stats import validate_extended_team_stats
        validate_extended_team_stats(decoded["_extended_team_stats"])
    if cls is game_state.TeamStats and "_offensive_attempt_stats" in decoded:
        from paydirt.offense_stats import validate_offensive_attempt_stats
        validate_offensive_attempt_stats(decoded["_offensive_attempt_stats"])
    hints.update(RECORD_EXTRAS.get(cls, {}))
    for name, value in decoded.items():
        # Existing special-team outcomes retain the numeric pre-kick coordinate.
        # Preserve those checkpoints exactly; other fields keep strict source types.
        if (cls is game_state.PlayOutcome and name == 'field_position_before'
                and type(value) is int and 0 <= value <= 100):
            continue
        annotation = hints[name]
        if not _matches(value, annotation):
            raise ValueError(f'Invalid checkpoint field type: {cls.__name__}.{name}')


def _validate_object(template: Any, decoded: dict) -> None:
    if type(template) is game_engine.PaydirtGameEngine:
        from paydirt.team_stats import validate_team_stats_context
        if decoded.get('_team_stats_depth', 0) != 0:
            raise ValueError('Cannot restore an in-flight team-stat capture')
        context = validate_team_stats_context(decoded.get('_team_stats_context', {}))
        pending = decoded.get('_last_play_outcome')
        if context and (context.get('pending') is not True or not (
                decoded.get('_pending_end_zone_interception')
                or getattr(pending, 'pending_penalty_decision', False)
                or getattr(pending, 'pending_end_zone_interception_return_decision', False))):
            raise ValueError('Team-stat capture has no pending engine choice')
    engine_hints = {
        'state': game_state.GameState, 'season_rules': season_rules.SeasonRules,
        'last_clock_trace': game_state.ClockTrace | None,
        'last_kickoff_context': dict | None,
        '_pending_post_score_action': str | None,
        '_pending_end_zone_interception': dict | None,
        '_pending_punt_state': dict, '_pending_kickoff_penalty_state': dict,
        '_last_play_outcome': game_state.PlayOutcome | None,
        'home_end_zone_interception_policy': str | None,
        'away_end_zone_interception_policy': str | None,
    }
    ai_hints = {
        'last_mode': str | None,
        'opponent_model': ai_analysis.OpponentModel | None,
        'team_analyzer': ai_analysis.TeamAnalyzer | None,
        '_offense_rng': random.Random | None,
        '_defense_rng': random.Random | None,
        '_decision_rng': random.Random | None,
    }
    for name, value in decoded.items():
        if type(template) is game_engine.PaydirtGameEngine and name in engine_hints:
            annotation = engine_hints[name]
        elif type(template) is computer_ai.ComputerAI and name in ai_hints:
            annotation = ai_hints[name]
        elif type(template) is computer_ai.ComputerAI and name == 'offense_strategy':
            from paydirt.offense_strategy import OffensiveStrategy
            annotation = OffensiveStrategy | None
        else:
            original = getattr(template, name)
            annotation = float if type(original) is float else type(original)
        if not _matches(value, annotation):
            raise ValueError(f'Invalid checkpoint object field: {type(template).__name__}.{name}')

def chart_identity(team: Any, directory: Path) -> dict:
    """Bind a portable catalog edition to all runtime chart/rule/roster inputs."""
    required = ('offense.csv', 'defense.csv', 'special.csv', 'team.yaml')
    hashes = {}
    for name in (*required, 'roster.json'):
        path = directory / name
        if path.is_symlink() or (name in required and not path.is_file()):
            raise ValueError('Chart inputs are missing or symlinked')
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    rules = directory.parent / f'{team.season}.yaml'
    if rules.is_symlink() or not rules.is_file():
        raise ValueError('Season rules are unavailable')
    hashes['rules'] = hashlib.sha256(rules.read_bytes()).hexdigest()
    return {'season': team.season, 'team_id': team.id, 'hashes': hashes}


class Codec:
    """Encode only registered records and copies of known, freshly built objects."""

    def __init__(self, game: dict) -> None:
        self.refs = {}
        engine = game['engine']
        for side in ('home', 'away'):
            chart = getattr(engine.state, f'{side}_chart')
            for suffix, obj in [('', chart), ('.offense', chart.offense),
                                ('.defense', chart.defense), ('.special', chart.special_teams)]:
                self.refs[side + suffix] = obj
        self.refs['rules'] = engine.season_rules
        # Templates have already passed normal application construction. Copying
        # one cannot invoke a user-selected constructor or arbitrary module import.
        self.objects = {}
        for obj in [engine, game['ai']]:
            self._templates(obj)

    def _templates(self, obj: Any) -> None:
        if type(obj) is random.Random:
            return
        if obj is None or isinstance(obj, (str, int, float, bool, Enum)):
            return
        if id(obj) in {id(v) for v in self.refs.values()}:
            return
        cls = type(obj)
        if cls in (dict, list, tuple, set, Counter, defaultdict, deque):
            values = obj.values() if isinstance(obj, dict) else obj
            for val in values:
                self._templates(val)
        elif hasattr(obj, '__dict__'):
            tag = f'{cls.__module__}.{cls.__name__}'
            if tag not in OBJECT_TYPES and tag not in RECORDS:
                raise ValueError(f'Unsupported checkpoint object: {cls.__name__}')
            if tag in self.objects:
                return
            self.objects[tag] = obj
            for val in vars(obj).values():
                self._templates(val)

    def encode(self, value: Any, depth: int = 0) -> Any:
        if depth > 100:
            raise ValueError('Checkpoint nesting is too deep')
        def enc(val: Any) -> Any:
            return self.encode(val, depth + 1)
        for name, obj in self.refs.items():
            if value is obj:
                return {'ref': name}
        if isinstance(value, Enum):
            return {'enum': f'{type(value).__module__}.{type(value).__name__}', 'name': value.name}
        if value is None or type(value) in (bool, int, str):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if type(value) is random.Random:
            return {'random_state': enc(value.getstate())}
        if isinstance(value, (dict, Counter, defaultdict)):
            factory = None
            if isinstance(value, defaultdict):
                factory = {list: 'list', int: 'int', dict: 'dict', float: 'float',
                           ai_analysis.SituationTendency: 'tendency'}.get(value.default_factory)
                if (factory is None and getattr(value.default_factory, '__code__', None)
                        is NESTED_LIST_FACTORY.__code__):
                    factory = 'nested-list'
                if factory is None:
                    raise ValueError('Unsupported default dictionary factory')
            pairs = [[enc(k), enc(v)] for k, v in value.items()]
            pairs.sort(key=lambda pair: json.dumps(pair[0], sort_keys=True))
            return {'mapping': pairs,
                    'kind': type(value).__name__, 'factory': factory}
        if isinstance(value, (list, tuple, set, deque)):
            return {'sequence': [enc(v) for v in value], 'kind': type(value).__name__}
        tag = f'{type(value).__module__}.{type(value).__name__}'
        if is_dataclass(value) and tag in RECORDS or tag in self.objects:
            return {'record': tag, 'attrs': {k: enc(v) for k, v in vars(value).items()}}
        raise ValueError(f'Unsupported checkpoint value: {type(value).__name__}')

    def decode(self, value: Any, depth: int = 0) -> Any:
        if depth > 100:
            raise ValueError('Checkpoint nesting is too deep')
        def dec(val: Any) -> Any:
            return self.decode(val, depth + 1)
        if value is None or type(value) in (bool, int, str):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if not isinstance(value, dict):
            raise TypeError('Invalid checkpoint value')
        if set(value) == {'random_state'}:
            state = dec(value['random_state'])
            if (type(state) is not tuple or len(state) != 3 or type(state[0]) is not int
                    or state[0] != 3 or type(state[1]) is not tuple or len(state[1]) != 625
                    or any(type(word) is not int or not 0 <= word <= 0xffffffff for word in state[1][:-1])
                    or type(state[1][-1]) is not int or not 0 <= state[1][-1] <= 624
                    or not (state[2] is None or type(state[2]) is float and math.isfinite(state[2]))):
                raise ValueError('Invalid checkpoint coaching RNG state')
            # Seed a closed stdlib type without reading or advancing the host's
            # gameplay stream. Never invoke a save-selected class/constructor.
            generator = random.Random(0)
            generator.setstate(state)
            return generator
        if set(value) == {'ref'}:
            return self.refs[value['ref']]
        if set(value) == {'enum', 'name'}:
            cls = RECORDS[value['enum']]
            if not issubclass(cls, Enum):
                raise ValueError('Invalid enum')
            return cls[value['name']]
        if set(value) == {'sequence', 'kind'}:
            constructors = {'list': list, 'tuple': tuple, 'set': set, 'deque': deque}
            return constructors[value['kind']](dec(v) for v in value['sequence'])
        if set(value) == {'mapping', 'kind', 'factory'}:
            pairs = [(dec(k), dec(v)) for k, v in value['mapping']]
            if len(dict(pairs)) != len(pairs):
                raise ValueError('Duplicate mapping key')
            if value['kind'] == 'defaultdict':
                factory = {'list': list, 'int': int, 'dict': dict, 'float': float,
                           'tendency': ai_analysis.SituationTendency,
                           'nested-list': NESTED_LIST_FACTORY}[value['factory']]
                return defaultdict(factory, pairs)
            return {'dict': dict, 'Counter': Counter}[value['kind']](dict(pairs))
        if set(value) == {'record', 'attrs'}:
            tag, attrs = value['record'], value['attrs']
            if not isinstance(attrs, dict) or any(not isinstance(k, str) for k in attrs):
                raise ValueError('Invalid record fields')
            cls = RECORDS.get(tag)
            if cls is not None and is_dataclass(cls):
                names = {f.name for f in fields(cls)}
                extra = set(RECORD_EXTRAS.get(cls, {}))
                if not names <= set(attrs) or not set(attrs) <= names | extra:
                    raise ValueError('Unknown record fields')
                decoded = {k: dec(v) for k, v in attrs.items()}
                _validate_record(cls, decoded)
                obj = cls(**{k: v for k, v in decoded.items() if k in names})
                for k in extra & decoded.keys():
                    setattr(obj, k, decoded[k])
                return obj
            template = self.objects[tag]
            expected = set(vars(template))
            optional = ({'_pending_punt_state', '_pending_kickoff_penalty_state', '_last_play_outcome'}
                        if tag == 'paydirt.game_engine.PaydirtGameEngine' else set())
            # These optional engine capture fields were added after version-1
            # checkpoints shipped. Old games retain unknown extended counters.
            defaults = ({'_team_stats_context': {}, '_team_stats_depth': 0}
                        if tag == 'paydirt.game_engine.PaydirtGameEngine' else {})
            if not expected - defaults.keys() <= set(attrs) or not set(attrs) <= expected | optional:
                raise ValueError(f'Incompatible runtime fields for {tag}: {set(attrs) ^ expected}')
            decoded = {**defaults, **{k: dec(v) for k, v in attrs.items()}}
            _validate_object(template, decoded)
            obj = copy.copy(template)
            obj.__dict__ = decoded
            return obj
        raise ValueError('Unknown checkpoint representation')


def export_checkpoint(game: dict, identities: dict, rules: dict) -> str:
    """Export full engine/AI/session state without machine-specific paths."""
    codec = Codec(game)
    excluded = {'game_id', 'engine', 'ai', 'home_team', 'away_team', 'created_at'}
    data = {'format': 'paydirt-session', 'version': 1, 'teams': identities, 'rules': rules,
            'engine': codec.encode(game['engine']), 'ai': codec.encode(game['ai']),
            'session': codec.encode({k: v for k, v in game.items() if k not in excluded})}
    text = json.dumps(data, allow_nan=False, separators=(',', ':'))
    if len(text.encode('utf-8')) > MAX_CHECKPOINT_BYTES:
        raise ValueError('Checkpoint exceeds size limit')
    return text


def parse_checkpoint(text: str) -> dict:
    """Reject malformed, duplicate-key, oversized and non-finite JSON inputs."""
    if len(text.encode('utf-8')) > MAX_CHECKPOINT_BYTES:
        raise ValueError('Checkpoint exceeds size limit')
    def pairs(items: list) -> dict:
        result = {}
        for key, val in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = val
        return result
    def reject_constant(_value: str) -> None:
        raise ValueError('Non-finite checkpoint number')
    data = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    if (not isinstance(data, dict) or set(data) != {'format', 'version', 'teams', 'rules', 'engine', 'ai', 'session'}
            or data['format'] != 'paydirt-session' or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['teams'], dict) or set(data['teams']) != {'home', 'away'}):
        raise ValueError('Unsupported checkpoint format')
    return data


def restore_checkpoint(data: dict, game: dict) -> dict:
    """Decode against a freshly built trusted session, before registration."""
    codec = Codec(game)
    # A hard AI provides templates for all supported analysis objects, even when
    # the saved game uses a different difficulty or an optional object is absent.
    hard = computer_ai.create_computer_ai('hard', game['engine'], cpu_is_home=not game['human_is_home'])
    codec._templates(hard)
    engine, ai, session = codec.decode(data['engine']), codec.decode(data['ai']), codec.decode(data['session'])
    if type(engine) is not type(game['engine']) or type(ai) is not type(game['ai']) or type(session) is not dict:
        raise ValueError('Invalid session objects')
    state = engine.state
    if (getattr(state, 'home_chart', None) is not codec.refs['home']
            or getattr(state, 'away_chart', None) is not codec.refs['away']
            or engine.season_rules is not codec.refs['rules']):
        raise ValueError('Engine chart/rule references differ from the bound editions')
    if (type(state) is not game_state.GameState or type(state.quarter) is not int
            or not 1 <= state.quarter <= 5 or type(state.down) is not int or not 1 <= state.down <= 4
            or not isinstance(state.time_remaining, (int, float)) or not 0 <= state.time_remaining <= 15
            or type(state.home_score) is not int or state.home_score < 0
            or type(state.away_score) is not int or state.away_score < 0
            or type(state.home_stats) is not game_state.TeamStats
            or type(state.away_stats) is not game_state.TeamStats):
        raise ValueError('Invalid engine state')
    if set(session) & {'game_id', 'engine', 'ai', 'home_team', 'away_team', 'created_at'}:
        raise ValueError('Reserved session key')
    if session.get('human_is_home') is not game['human_is_home']:
        raise ValueError('Invalid control side')
    game.update(session)
    game.update(engine=engine, ai=ai, created_at=datetime.now())
    return game
