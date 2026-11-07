"""Synthetic setup only; real API and engine resolve every browser try."""

from copy import deepcopy
from dataclasses import asdict

import routes
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from paydirt.game_state import ScoringPlay


class TryFixtureRequest(BaseModel):
    game_id: str
    cell: str = "2"
    eligible: bool = True


def install_try_fixture(app: FastAPI) -> None:
    """Install fixture setup in an isolated test service, never the product API."""
    @app.post("/api/test/two-point-fixture")
    async def configure_try(request: TryFixtureRequest) -> dict:
        if request.game_id not in routes.games:
            raise HTTPException(status_code=404, detail="Game not found")
        game = routes.games[request.game_id]
        engine = game["engine"]
        state = engine.state
        if not game.get("pending_pat"):
            raise HTTPException(status_code=400, detail="Fixture requires a saved pending try")
        state.possession_team.offense.line_plunge = dict.fromkeys(range(10, 40), request.cell)
        state.defense_team.defense.modifiers = {}
        state.possession_team.peripheral.fumble_recovered_range = (10, 10)
        state.defense_team.special_teams.interception_return = dict.fromkeys(range(10, 40), "0")
        for chart in (state.home_chart, state.away_chart):
            chart.special_teams.kickoff = dict.fromkeys(range(10, 40), "60")
            chart.special_teams.kickoff_return = dict.fromkeys(range(10, 40), "20")
        engine.season_rules.two_point_conversion = request.eligible
        if not state.scoring_plays:
            state.scoring_plays.append(ScoringPlay(
                quarter=state.quarter, time_remaining=state.time_remaining,
                team=state.possession_team.peripheral.short_name,
                is_home_team=state.is_home_possession, play_type="TD", description="Synthetic setup touchdown", points=6,
            ))
        return {
            "game_state": routes.game_state_to_response(game).model_dump(),
            "accounting": deepcopy({
                "home": asdict(state.home_stats), "away": asdict(state.away_stats),
                "play_log_count": len(engine.play_log), "call_history": engine.offensive_call_history,
            }),
        }

    @app.get("/api/test/two-point-accounting/{game_id}")
    async def accounting(game_id: str) -> dict:
        if game_id not in routes.games:
            raise HTTPException(status_code=404, detail="Game not found")
        engine = routes.games[game_id]["engine"]
        return {
            "home": asdict(engine.state.home_stats), "away": asdict(engine.state.away_stats),
            "play_log_count": len(engine.play_log), "call_history": engine.offensive_call_history,
            "scoring_plays": [asdict(score) for score in engine.state.scoring_plays],
            "clock_trace": asdict(engine.last_clock_trace) if engine.last_clock_trace else None,
        }
