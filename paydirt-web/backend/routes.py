from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml
import random
import uuid
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import load_team_chart
from paydirt.play_resolver import PlayType, DefenseType
from paydirt.computer_ai import ComputerAI

router = APIRouter()

SEASONS_DIR = Path(__file__).parent.parent.parent / 'seasons'

games: Dict[str, Dict[str, Any]] = {}


class Team(BaseModel):
    id: str
    name: str
    short_name: Optional[str] = None
    team_color: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PlayResult(BaseModel):
    result: str
    yards: int
    description: str
    turnover: bool = False
    scoring: bool = False
    new_ball_position: int
    new_down: int
    new_yards_to_go: int
    new_score_home: int
    new_score_away: int
    possession_changed: bool = False
    game_over: bool = False
    quarter_changed: bool = False
    half_changed: bool = False


class SeasonsResponse(BaseModel):
    seasons: List[str]


class TeamsResponse(BaseModel):
    teams: List[Team]


class NewGameRequest(BaseModel):
    player_team: str
    season: str
    play_as_home: bool = True
    opponent_team: Optional[str] = None


class GameStateResponse(BaseModel):
    game_id: str
    home_team: Team
    away_team: Team
    home_score: int
    away_score: int
    quarter: int
    time_remaining: int
    possession: str
    ball_position: int
    down: int
    yards_to_go: int
    game_over: bool
    home_timeouts: int = 3
    away_timeouts: int = 3
    player_offense: bool = True


class NewGameResponse(BaseModel):
    game_id: str
    game_state: GameStateResponse


class PlayRequest(BaseModel):
    game_id: str
    player_play: str


class CPUPlayResponse(BaseModel):
    cpu_play: str


class ExecutePlayResponse(BaseModel):
    player_play: str
    cpu_play: str
    dice_roll_offense: int
    dice_roll_defense: int
    result: PlayResult
    game_state: GameStateResponse


def load_team_info(season_dir: Path, team_id: str) -> Team:
    team_dir = season_dir / team_id
    team_info = {"id": team_id, "name": team_id}
    
    yaml_file = team_dir / "team.yaml"
    if yaml_file.exists():
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            if data:
                team_info["name"] = data.get("team_name", team_id)
                team_info["short_name"] = data.get("short_name")
                team_info["team_color"] = data.get("team_color")
                team_info["city"] = data.get("city")
                team_info["state"] = data.get("state")
    
    return Team(**team_info)


def game_state_to_response(game: Dict[str, Any]) -> GameStateResponse:
    return GameStateResponse(
        game_id=game["game_id"],
        home_team=game["home_team"],
        away_team=game["away_team"],
        home_score=game["engine"].state.home_score,
        away_score=game["engine"].state.away_score,
        quarter=game["engine"].state.quarter,
        time_remaining=int(game["engine"].state.time_remaining * 60),
        possession="home" if game["engine"].state.is_home_possession else "away",
        ball_position=game["engine"].state.ball_position,
        down=game["engine"].state.down,
        yards_to_go=game["engine"].state.yards_to_go,
        game_over=game["engine"].state.game_over,
        home_timeouts=game["engine"].state.home_timeouts,
        away_timeouts=game["engine"].state.away_timeouts,
        player_offense=game["player_offense"],
    )


def get_play_type_from_key(key: str) -> PlayType:
    play_map = {
        "1": PlayType.LINE_PLUNGE,
        "2": PlayType.OFF_TACKLE,
        "3": PlayType.END_RUN,
        "4": PlayType.DRAW,
        "5": PlayType.SCREEN,
        "6": PlayType.SHORT_PASS,
        "7": PlayType.MEDIUM_PASS,
        "8": PlayType.LONG_PASS,
        "9": PlayType.TE_SHORT_LONG,
        "Q": PlayType.QB_SNEAK,
        "K": PlayType.QB_KNEEL,
        "P": PlayType.PUNT,
        "F": PlayType.FIELD_GOAL,
        "S": PlayType.SPIKE_BALL,
    }
    return play_map.get(key.upper(), PlayType.LINE_PLUNGE)


def get_defense_type_from_key(key: str) -> DefenseType:
    defense_map = {
        "A": DefenseType.STANDARD,
        "B": DefenseType.SHORT_YARDAGE,
        "C": DefenseType.SPREAD,
        "D": DefenseType.SHORT_PASS,
        "E": DefenseType.LONG_PASS,
    }
    return defense_map.get(key.upper(), DefenseType.STANDARD)


@router.get("/api/seasons", response_model=SeasonsResponse)
async def get_seasons():
    if not SEASONS_DIR.exists():
        return {"seasons": []}
    
    seasons = [d.name for d in SEASONS_DIR.iterdir() if d.is_dir()]
    seasons.sort(reverse=True)
    return {"seasons": seasons}


@router.get("/api/teams", response_model=TeamsResponse)
async def get_teams(season: str):
    season_dir = SEASONS_DIR / season
    if not season_dir.exists():
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")
    
    teams = []
    for team_dir in sorted(season_dir.iterdir()):
        if team_dir.is_dir():
            teams.append(load_team_info(season_dir, team_dir.name))
    
    return {"teams": teams}


@router.post("/api/game/new", response_model=NewGameResponse)
async def new_game(request: NewGameRequest):
    season_dir = SEASONS_DIR / request.season
    if not season_dir.exists():
        raise HTTPException(status_code=404, detail=f"Season '{request.season}' not found")
    
    available_teams = [d.name for d in season_dir.iterdir() if d.is_dir()]
    if request.player_team not in available_teams:
        raise HTTPException(status_code=404, detail=f"Team '{request.player_team}' not found in season '{request.season}'")
    
    if request.opponent_team:
        if request.opponent_team not in available_teams:
            raise HTTPException(status_code=404, detail=f"Opponent team '{request.opponent_team}' not found")
        if request.opponent_team == request.player_team:
            raise HTTPException(status_code=400, detail="Player team and opponent team cannot be the same")
        cpu_team = request.opponent_team
    else:
        cpu_teams = [t for t in available_teams if t != request.player_team]
        cpu_team = random.choice(cpu_teams) if cpu_teams else request.player_team
    
    player_is_home = request.play_as_home
    player_offense = random.choice([True, False])
    
    player_team_id = request.player_team if player_is_home else cpu_team
    cpu_team_id = cpu_team if player_is_home else request.player_team
    
    home_team = load_team_info(season_dir, player_team_id if player_is_home else cpu_team_id)
    away_team = load_team_info(season_dir, cpu_team_id if player_is_home else player_team_id)
    
    home_chart = load_team_chart(str(season_dir / home_team.id))
    away_chart = load_team_chart(str(season_dir / away_team.id))
    
    game_id = f"game_{uuid.uuid4().hex[:8]}"
    
    engine = PaydirtGameEngine(home_chart, away_chart)
    
    game = {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "player_offense": player_offense,
        "player_team_id": player_team_id,
        "cpu_team_id": cpu_team_id,
        "engine": engine,
        "ai": ComputerAI(aggression=0.5),
        "created_at": datetime.now(),
        "season": request.season,
    }
    
    game["ai"].set_team(home_chart if home_team.id == cpu_team_id else away_chart)
    
    games[game_id] = game
    
    return NewGameResponse(
        game_id=game_id,
        game_state=game_state_to_response(game),
    )


@router.get("/api/game/state/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return game_state_to_response(games[game_id])


@router.post("/api/game/cpu-play", response_model=CPUPlayResponse)
async def get_cpu_play(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    
    if game["engine"].state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    cpu_is_offense = not game["player_offense"]
    
    if cpu_is_offense:
        cpu_play_type = game["ai"].select_offense(game["engine"])
        cpu_play = {
            PlayType.LINE_PLUNGE: "1",
            PlayType.OFF_TACKLE: "2",
            PlayType.END_RUN: "3",
            PlayType.DRAW: "4",
            PlayType.SCREEN: "5",
            PlayType.SHORT_PASS: "6",
            PlayType.MEDIUM_PASS: "7",
            PlayType.LONG_PASS: "8",
            PlayType.TE_SHORT_LONG: "9",
            PlayType.QB_SNEAK: "Q",
            PlayType.QB_KNEEL: "K",
            PlayType.PUNT: "P",
            PlayType.FIELD_GOAL: "F",
            PlayType.SPIKE_BALL: "S",
        }.get(cpu_play_type, "1")
    else:
        cpu_defense = game["ai"].select_defense(game["engine"])
        cpu_play = {
            DefenseType.STANDARD: "A",
            DefenseType.SHORT_YARDAGE: "B",
            DefenseType.SPREAD: "C",
            DefenseType.SHORT_PASS: "D",
            DefenseType.LONG_PASS: "E",
        }.get(cpu_defense, "A")
    
    return CPUPlayResponse(cpu_play=cpu_play)


@router.post("/api/game/execute", response_model=ExecutePlayResponse)
async def execute_play(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    if engine.state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    player_play = request.player_play.upper()
    player_offense = game["player_offense"]
    
    if player_offense:
        offense_play = get_play_type_from_key(player_play)
        defense_play = get_defense_type_from_key("A")
    else:
        offense_play = get_play_type_from_key("1")
        defense_play = get_defense_type_from_key(player_play)
    
    quarter_before = engine.state.quarter
    home_score_before = engine.state.home_score
    away_score_before = engine.state.away_score
    
    result = engine.run_play(offense_play, defense_play)
    
    quarter_changed = engine.state.quarter != quarter_before
    half_changed = quarter_before in [2, 4] and engine.state.quarter != quarter_before
    
    scoring = result.touchdown or result.field_goal_made or result.safety
    
    play_result = PlayResult(
        result=result.result.result_type.value,
        yards=result.yards_gained,
        description=result.description,
        turnover=result.turnover,
        scoring=scoring,
        new_ball_position=engine.state.ball_position,
        new_down=engine.state.down,
        new_yards_to_go=engine.state.yards_to_go,
        new_score_home=engine.state.home_score,
        new_score_away=engine.state.away_score,
        possession_changed=(
            result.turnover or 
            engine.state.home_score != home_score_before or 
            engine.state.away_score != away_score_before
        ),
        game_over=engine.state.game_over,
        quarter_changed=quarter_changed,
        half_changed=half_changed,
    )
    
    return ExecutePlayResponse(
        player_play=player_play,
        cpu_play="CPU",
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=play_result,
        game_state=game_state_to_response(game),
    )


@router.delete("/api/game/{game_id}")
async def delete_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    del games[game_id]
    return {"status": "deleted", "game_id": game_id}
