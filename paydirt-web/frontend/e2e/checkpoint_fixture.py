"""Synthetic recovery situations installed only by the isolated browser server."""

from unittest.mock import patch

import routes
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from paydirt.play_resolver import PenaltyChoice, PlayResult, ResultType


class RecoveryFixtureRequest(BaseModel):
    game_id: str
    kind: str


def install_checkpoint_fixture(app: FastAPI) -> None:
    @app.post('/api/test/checkpoint-fixture')
    async def configure_recovery(request: RecoveryFixtureRequest) -> dict:
        if request.game_id not in routes.games:
            raise HTTPException(status_code=404, detail='Game not found')
        game = routes.games[request.game_id]
        engine = game['engine']
        state = engine.state
        if request.kind == 'kickoff-stale-try':
            if engine.pending_post_score_action() != 'try':
                raise HTTPException(status_code=400, detail='Fixture requires an engine-owned try')
            # Reproduce the old API's lost flag and pre-try placement, without
            # changing the engine-owned score, clock, possession or statistics.
            game['pending_pat'] = False
            state.ball_position, state.down, state.yards_to_go = 99, 1, 10
            response = routes.game_state_to_response(game)
            return {'game_state': response.model_dump()}
        game['is_kickoff'] = False
        state.is_home_possession = True
        state.quarter, state.time_remaining = 2, 3
        state.ball_position, state.down, state.yards_to_go = 40, 1, 10
        if request.kind in ('label-offense', 'label-defense', 'help-offense', 'help-defense'):
            offense = request.kind.endswith('offense')
            state.is_home_possession = game['human_is_home'] == offense
            state.quarter, state.time_remaining = 1, 15
            state.ball_position, state.down, state.yards_to_go = 20, 1, 10
            if request.kind.startswith('help-'):
                state.quarter, state.time_remaining = 2, 41 / 60
                state.ball_position, state.down, state.yards_to_go = 77, 3, 9
                state.home_timeouts, state.away_timeouts = 3, 1
                game['play_history'] = [
                    {'quarter': 2, 'timeRemaining': 41, 'description': 'Synthetic first-half play'},
                    {'quarter': 3, 'timeRemaining': 900, 'description': 'Synthetic second-half play'},
                ]
        elif request.kind == 'kickoff-fumble-td':
            # The real engine resolves a return fumble in the receiver's end zone.
            # Every dice row has the same synthetic outcome; no gameplay RNG patch.
            state.is_home_possession = game['human_is_home']
            state.quarter, state.time_remaining = 2, 3
            game['is_kickoff'] = True
            game['pending_pat'] = False
            kicker, receiver = state.possession_team, state.defense_team
            kicker.special_teams.kickoff = dict.fromkeys(range(10, 40), '74')
            receiver.special_teams.kickoff_return = dict.fromkeys(range(10, 40), 'F + 3')
            receiver.peripheral.fumble_recovered_range = (0, 0)
        elif request.kind == 'pending-try':
            state.is_home_possession = game['human_is_home']
            state.quarter, state.time_remaining = 2, 20 / 60
            state.home_timeouts, state.away_timeouts = 1, 2
            engine._score_touchdown()
            engine.setup_for_pat()
            game['pending_pat'] = True
        elif request.kind == 'field-goal-penalty':
            from paydirt.play_resolver import FieldGoalResult, PenaltyOption
            state.is_home_possession = False
            state.quarter, state.time_remaining = 2, 9 / 60
            state.ball_position, state.down, state.yards_to_go = 83, 2, 10
            result = FieldGoalResult(
                dice_roll=11, dice_desc='Synthetic kick', raw_result='1', chart_yards=1,
                is_penalty=True, penalty_options=[PenaltyOption('OFF', 'OFF 5', 5, 'Synthetic FG foul')],
                offsetting=False, offended_team='defense', reroll_log=[])
            with patch('paydirt.game_engine.resolve_field_goal_with_penalties', return_value=result):
                await routes.execute_play(routes.PlayRequest(
                    game_id=request.game_id, player_play='A', cpu_play='F'))
        elif request.kind == 'post-punt':
            import random
            state.is_home_possession = False
            state.quarter, state.time_remaining = 1, 14
            state.ball_position, state.down, state.yards_to_go = 11, 4, 7
            prior_random = random.getstate()
            try:
                random.seed(8306)
                await routes.execute_play(routes.PlayRequest(
                    game_id=request.game_id, player_play='A', cpu_play='P'))
            finally:
                random.setstate(prior_random)
        elif request.kind in ('recorded-final', 'corrected-final'):
            state.quarter, state.time_remaining, state.game_over = 4, 0, True
            state.home_score = 24 if request.kind == 'corrected-final' else 21
            state.away_score = 14
            state.home_stats.total_yards = 420 if request.kind == 'corrected-final' else 310
            state.home_stats.rushing_yards = 180 if request.kind == 'corrected-final' else 120
            game['pending_pat'] = False
        elif request.kind == 'halftime':
            state.quarter, state.time_remaining = 3, 15
            engine._last_play_start_quarter = 2
            engine.prepare_second_half_kickoff()
            game['is_kickoff'] = True
        elif request.kind in ('penalty', 'penalty-final', 'interception', 'expired-try'):
            if request.kind == 'interception':
                state.is_home_possession = False
                state.ball_position = 90
                result = PlayResult(result_type=ResultType.INTERCEPTION, yards=14, turnover=True, raw_result='INT 14')
            else:
                result = PlayResult(result_type=ResultType.YARDS, yards=9 if request.kind == 'expired-try' else 4)
            if request.kind == 'expired-try':
                state.quarter, state.time_remaining = 4, 10 / 60
                state.two_minute_warning_called = True
                state.home_score, state.away_score = 21, 14
                state.ball_position, state.down, state.yards_to_go = 94, 2, 6
            choice = PenaltyChoice(play_result=result)
            if request.kind in ('penalty', 'penalty-final'):
                from paydirt.play_resolver import PenaltyOption
                choice.offended_team = 'offense'
                choice.penalty_options = [PenaltyOption(penalty_type='D', raw_result='D 5', yards=5, description='Synthetic defensive foul')]
                if request.kind == 'penalty-final':
                    state.quarter, state.time_remaining = 4, 1 / 60
                    state.home_score, state.away_score = 21, 20
                    state.is_home_possession = False
                    state.ball_position, state.down, state.yards_to_go = 40, 4, 10
                    choice.offended_team = 'defense'
                    choice.penalty_options = [PenaltyOption('OFF', 'OFF 5', 5, 'Synthetic offensive foul')]

            with (patch('paydirt.game_engine.resolve_play_with_penalties', return_value=choice),
                  patch('paydirt.game_engine.random.uniform', return_value=30)):
                await routes.execute_play(routes.PlayRequest(
                    game_id=request.game_id,
                    player_play='A' if request.kind in ('interception', 'penalty-final') else '1',
                    cpu_play='6' if request.kind == 'interception' else '1' if request.kind == 'penalty-final' else 'A',
                ))
        else:
            raise HTTPException(status_code=400, detail='Unknown recovery fixture')
        response = routes.game_state_to_response(game)
        return {'game_state': response.model_dump(), 'pending_result': routes._restored_pending_result(engine)}
