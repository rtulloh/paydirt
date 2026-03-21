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
from paydirt.result_formatter import ResultFormatter
from paydirt.commentary import load_roster_from_file

router = APIRouter()

SEASONS_DIR = Path(__file__).parent.parent.parent / 'seasons'

games: Dict[str, Dict[str, Any]] = {}


@router.get("/api/health")
async def health_check():
    return {"status": "ok"}


class Team(BaseModel):
    id: str
    name: str
    short_name: Optional[str] = None
    team_color: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PenaltyOptionModel(BaseModel):
    penalty_type: str
    raw_result: str
    yards: int
    description: str
    auto_first_down: bool = False
    is_pass_interference: bool = False


class PenaltyChoiceModel(BaseModel):
    penalty_options: List[PenaltyOptionModel]
    offended_team: str
    offsetting: bool = False
    is_pass_interference: bool = False
    reroll_log: List[str] = []


class PlayResult(BaseModel):
    result: str
    yards: int
    description: str
    turnover: bool = False
    scoring: bool = False
    touchdown: bool = False
    new_ball_position: int
    new_down: int
    new_yards_to_go: int
    new_score_home: int
    new_score_away: int
    possession_changed: bool = False
    game_over: bool = False
    quarter_changed: bool = False
    half_changed: bool = False
    pending_penalty_decision: bool = False
    penalty_choice: Optional[PenaltyChoiceModel] = None
    play_type: Optional[str] = None
    
    headline: Optional[str] = None
    commentary: Optional[str] = None
    big_play_factor: int = 0
    big_play_type: str = "normal"
    is_gain: bool = False
    is_stuffed: bool = False
    is_big_play: bool = False
    is_explosive: bool = False
    is_interception: bool = False
    is_fumble: bool = False
    is_first_down: bool = False
    is_safety: bool = False
    is_sack: bool = False
    is_breakaway: bool = False


class ExtraPointResponse(BaseModel):
    success: bool
    description: str
    new_score_home: int
    new_score_away: int


class PATChoiceResponse(BaseModel):
    can_go_for_two: bool
    cpu_should_go_for_two: bool
    scoring_team_is_player: bool


class SeasonsResponse(BaseModel):
    seasons: List[str]


class TeamsResponse(BaseModel):
    teams: List[Team]


class NewGameRequest(BaseModel):
    player_team: str
    season: str
    play_as_home: bool = True
    opponent_team: Optional[str] = None
    difficulty: str = "medium"


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
    difficulty: str = "medium"
    human_team_id: Optional[str] = None
    cpu_team_id: Optional[str] = None
    human_is_home: Optional[bool] = None


class NewGameResponse(BaseModel):
    game_id: str
    game_state: GameStateResponse
    difficulty: str = "medium"


class PlayRequest(BaseModel):
    game_id: str
    player_play: str
    cpu_play: Optional[str] = None


class CPUPlayResponse(BaseModel):
    cpu_play: str


class ExecutePlayResponse(BaseModel):
    player_play: str
    cpu_play: str
    dice_roll_offense: int
    dice_roll_defense: int
    dice_details: Optional[Dict[str, Any]] = None  # Full dice breakdown
    result: PlayResult
    game_state: GameStateResponse


def parse_dice_from_description(description: str) -> Dict[str, Any]:
    """Parse dice values from play description like 'B1+W4+W3=17 [Off: B1+W1+W4=15, Def: R2+G1=3]'"""
    import re
    dice_info = {
        "offense": {"black": 0, "white1": 0, "white2": 0, "total": 0},
        "defense": {"red": 0, "green": 0, "total": 0}
    }
    
    offense_match = re.search(r'\[Off:\s*B(\d)\+W(\d)\+W(\d)=(\d+)', description)
    if offense_match:
        dice_info["offense"] = {
            "black": int(offense_match.group(1)),
            "white1": int(offense_match.group(2)),
            "white2": int(offense_match.group(3)),
            "total": int(offense_match.group(4))
        }
    
    defense_match = re.search(r'Def:\s*R(\d)\+G(\d)=(\d+)', description)
    if defense_match:
        dice_info["defense"] = {
            "red": int(defense_match.group(1)),
            "green": int(defense_match.group(2)),
            "total": int(defense_match.group(3))
        }
    
    return dice_info


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
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = game["engine"].state.is_home_possession
    player_offense = human_is_home == is_home_possession
    response = GameStateResponse(
        game_id=game["game_id"],
        home_team=game["home_team"],
        away_team=game["away_team"],
        home_score=game["engine"].state.home_score,
        away_score=game["engine"].state.away_score,
        quarter=game["engine"].state.quarter,
        time_remaining=int(game["engine"].state.time_remaining * 60),
        possession="home" if is_home_possession else "away",
        ball_position=game["engine"].state.ball_position,
        down=game["engine"].state.down,
        yards_to_go=game["engine"].state.yards_to_go,
        game_over=game["engine"].state.game_over,
        home_timeouts=game["engine"].state.home_timeouts,
        away_timeouts=game["engine"].state.away_timeouts,
        player_offense=player_offense,
        human_team_id=game.get("player_team_id"),
        cpu_team_id=game.get("cpu_team_id"),
        human_is_home=human_is_home,
    )
    return response


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
        player_team_id = request.player_team
        cpu_team_id = request.opponent_team
        player_is_home = request.play_as_home
        human_plays_offense = random.choice([True, False])
        if player_is_home:
            home_id = player_team_id
            away_id = cpu_team_id
        else:
            home_id = cpu_team_id
            away_id = player_team_id
    else:
        cpu_teams = [t for t in available_teams if t != request.player_team]
        cpu_team = random.choice(cpu_teams) if cpu_teams else request.player_team
        player_is_home = request.play_as_home
        human_plays_offense = random.choice([True, False])
        if player_is_home:
            player_team_id = request.player_team
            cpu_team_id = cpu_team
            home_id = player_team_id
            away_id = cpu_team_id
        else:
            player_team_id = cpu_team
            cpu_team_id = request.player_team
            home_id = cpu_team_id
            away_id = player_team_id
    
    home_team = load_team_info(season_dir, home_id)
    away_team = load_team_info(season_dir, away_id)
    
    home_chart = load_team_chart(str(season_dir / home_team.id))
    away_chart = load_team_chart(str(season_dir / away_team.id))
    
    game_id = f"game_{uuid.uuid4().hex[:8]}"
    
    engine = PaydirtGameEngine(home_chart, away_chart)
    
    difficulty = request.difficulty.lower() if request.difficulty else "medium"
    difficulty_map = {'easy': 0.3, 'medium': 0.5, 'hard': 0.7}
    cpu_aggression = difficulty_map.get(difficulty, 0.5)
    
    game = {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "human_plays_offense": human_plays_offense,
        "player_team_id": player_team_id,
        "cpu_team_id": cpu_team_id,
        "engine": engine,
        "ai": ComputerAI(aggression=cpu_aggression),
        "created_at": datetime.now(),
        "season": request.season,
        "difficulty": difficulty,
    }
    
    game["ai"].set_team(home_chart if home_team.id == cpu_team_id else away_chart)
    
    games[game_id] = game
    
    return NewGameResponse(
        game_id=game_id,
        game_state=game_state_to_response(game),
        difficulty=difficulty,
    )


@router.get("/api/game/state/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return game_state_to_response(games[game_id])


class CoinTossRequest(BaseModel):
    game_id: str
    player_won: bool
    player_kicks: bool
    human_plays_offense: Optional[bool] = True


@router.post("/api/game/coin-toss")
async def process_coin_toss(request: CoinTossRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    # Update human's role based on coin toss choice
    if request.human_plays_offense is not None:
        game["human_plays_offense"] = request.human_plays_offense
    
    # Set possession based on coin toss result
    # player_kicks = True means player kicks (they have possession to kick)
    # player_kicks = False means player receives (opponent has possession to kick)
    # Extract team ID from home_chart.team_dir (e.g., "seasons/2026/TeamName" -> "TeamName")
    home_team_id = engine.state.home_chart.team_dir.split('/')[-1]
    human_is_home = home_team_id == game["player_team_id"]
    
    if request.player_kicks:
        # Player kicks - player has possession to kick
        engine.state.is_home_possession = human_is_home
    else:
        # Player receives - opponent has possession to kick
        engine.state.is_home_possession = not human_is_home
    
    # Calculate player_offense for frontend
    # If human is at home AND home has possession, OR human is away AND away has possession
    player_offense = human_is_home == engine.state.is_home_possession
    
    return {
        "status": "ok",
        "possession": "home" if engine.state.is_home_possession else "away",
        "player_offense": player_offense,
        "human_is_home": human_is_home,
        "human_team_id": game["player_team_id"],
        "cpu_team_id": game["cpu_team_id"],
    }


@router.post("/api/game/cpu-play", response_model=CPUPlayResponse)
async def get_cpu_play(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    
    if game["engine"].state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    cpu_is_offense = not game["human_plays_offense"]
    
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


class CPUFourthDownResponse(BaseModel):
    decision: str
    play: Optional[str] = None


@router.get("/api/game/cpu-4th-down-decision/{game_id}", response_model=CPUFourthDownResponse)
async def get_cpu_4th_down_decision(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    state = game["engine"].state
    
    # Determine CPU offense status based on current possession
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = state.is_home_possession
    player_is_on_offense = human_is_home == is_home_possession
    cpu_is_offense = not player_is_on_offense
    
    if not (cpu_is_offense and state.down == 4):
        return CPUFourthDownResponse(decision="none")
    
    play_map = {
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
    }
    
    play, _, _, _, _ = game["ai"].select_offense_with_clock_management(game["engine"])
    play_key = play_map.get(play, "1")
    
    if play == PlayType.PUNT:
        return CPUFourthDownResponse(decision="punt", play="P")
    elif play == PlayType.FIELD_GOAL:
        return CPUFourthDownResponse(decision="field_goal", play="F")
    else:
        return CPUFourthDownResponse(decision="go_for_it", play=play_key)


@router.post("/api/game/execute", response_model=ExecutePlayResponse)
async def execute_play(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    if engine.state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    player_play = request.player_play.upper()
    player_offense = game["human_plays_offense"]
    
    cpu_play = request.cpu_play.upper() if request.cpu_play else None
    
    if player_offense:
        offense_play = get_play_type_from_key(player_play)
        if cpu_play:
            defense_play = get_defense_type_from_key(cpu_play)
        else:
            defense_play = game["ai"].select_defense(engine)
    else:
        if cpu_play:
            offense_play = get_play_type_from_key(cpu_play)
        else:
            offense_play = game["ai"].select_offense(engine)
        defense_play = get_defense_type_from_key(player_play)
    
    quarter_before = engine.state.quarter
    home_score_before = engine.state.home_score
    away_score_before = engine.state.away_score
    
    result = engine.run_play_with_penalty_procedure(offense_play, defense_play)
    
    quarter_changed = engine.state.quarter != quarter_before
    half_changed = quarter_before in [2, 4] and engine.state.quarter != quarter_before
    
    scoring = result.touchdown or result.field_goal_made or result.safety
    
    # Determine if human needs to make penalty decision
    # OFFENSE committed penalty (OFF 5, OFF 15) → DEFENSE gets choice
    # DEFENSE committed penalty (DEF 5, DEF 15) → OFFENSE gets choice
    # Only prompt human if THEY are the non-offending team
    human_is_on_offense = game.get("human_plays_offense", True)
    
    should_prompt_human = False
    if result.penalty_choice and not result.penalty_choice.offsetting:
        offended_team = result.penalty_choice.offended_team  # "offense" or "defense"
        if offended_team == "offense":
            # Offense committed penalty → defense gets choice → prompt if human is on defense
            should_prompt_human = not human_is_on_offense
        else:  # defense committed penalty
            # Defense committed penalty → offense gets choice → prompt if human is on offense
            should_prompt_human = human_is_on_offense
    
    penalty_choice_model = None
    if should_prompt_human:
        penalty_options = []
        for opt in result.penalty_choice.penalty_options:
            penalty_options.append(PenaltyOptionModel(
                penalty_type=opt.penalty_type,
                raw_result=opt.raw_result,
                yards=opt.yards,
                description=opt.description,
                auto_first_down=opt.auto_first_down,
                is_pass_interference=getattr(opt, 'is_pass_interference', False),
            ))
        penalty_choice_model = PenaltyChoiceModel(
            penalty_options=penalty_options,
            offended_team=result.penalty_choice.offended_team,
            offsetting=result.penalty_choice.offsetting,
            is_pass_interference=result.penalty_choice.is_pass_interference,
            reroll_log=result.penalty_choice.reroll_log or [],
        )
    
    offense_team = engine.state.possession_team.peripheral.short_name if hasattr(engine.state, 'possession_team') and engine.state.possession_team else "OFF"
    defense_team = engine.state.defense_team.peripheral.short_name if hasattr(engine.state, 'defense_team') and engine.state.defense_team else "DEF"
    
    offense_roster = {}
    defense_roster = {}
    try:
        if engine.state.possession_team and hasattr(engine.state.possession_team, 'team_dir'):
            roster = load_roster_from_file(engine.state.possession_team.team_dir)
            if roster:
                offense_roster = {
                    'qb': roster.qb,
                    'rb': roster.rb,
                    'wr': roster.wr,
                    'te': roster.te,
                    'ol': roster.ol,
                    'dl': roster.dl,
                    'lb': roster.lb,
                    'db': roster.db,
                    'k': roster.k,
                    'p': roster.p,
                    'kr': roster.kr,
                }
    except Exception:
        pass
    try:
        if engine.state.defense_team and hasattr(engine.state.defense_team, 'team_dir'):
            roster = load_roster_from_file(engine.state.defense_team.team_dir)
            if roster:
                defense_roster = {
                    'qb': roster.qb,
                    'rb': roster.rb,
                    'wr': roster.wr,
                    'te': roster.te,
                    'ol': roster.ol,
                    'dl': roster.dl,
                    'lb': roster.lb,
                    'db': roster.db,
                    'k': roster.k,
                    'p': roster.p,
                    'kr': roster.kr,
                }
    except Exception:
        pass
    
    formatter = ResultFormatter(offense_team, defense_team, offense_roster, defense_roster)
    formatted = formatter.format(result)
    
    play_result = PlayResult(
        result=result.result.result_type.value,
        yards=result.yards_gained,
        description=result.description,
        turnover=result.turnover,
        scoring=scoring,
        touchdown=result.touchdown,
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
        pending_penalty_decision=result.pending_penalty_decision,
        penalty_choice=penalty_choice_model,
        play_type=result.play_type.value if hasattr(result.play_type, 'value') else str(result.play_type),
        headline=formatted.headline,
        commentary=formatted.commentary,
        big_play_factor=formatted.big_play_factor,
        big_play_type=formatted.big_play_type,
        is_gain=formatted.is_gain,
        is_stuffed=formatted.is_stuffed,
        is_big_play=formatted.is_big_play,
        is_explosive=formatted.is_explosive,
        is_interception=formatted.is_interception,
        is_fumble=formatted.is_fumble,
        is_first_down=formatted.is_first_down,
        is_safety=formatted.is_safety,
        is_sack=formatted.is_sack,
        is_breakaway=formatted.is_breakaway,
    )
    
    # Log the full response for debugging
    response_game_state = game_state_to_response(game)
    print(f"[EXECUTE PLAY] yards={play_result.yards}, new_down={response_game_state.down}, "
          f"new_pos={response_game_state.ball_position}, possession={response_game_state.possession}, "
          f"player_offense={response_game_state.player_offense}, "
          f"first_down={play_result.is_first_down}")
    
    # Parse dice from description for frontend display
    dice_details = parse_dice_from_description(play_result.description)
    
    return ExecutePlayResponse(
        player_play=player_play,
        cpu_play="CPU",
        dice_roll_offense=dice_details["offense"]["total"],
        dice_roll_defense=dice_details["defense"]["total"],
        dice_details=dice_details,
        result=play_result,
        game_state=response_game_state,
    )


@router.delete("/api/game/{game_id}")
async def delete_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    del games[game_id]
    return {"status": "deleted", "game_id": game_id}


@router.get("/api/game/pat-choice/{game_id}", response_model=PATChoiceResponse)
async def get_pat_choice(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    engine = game["engine"]
    
    pat_info = engine.get_touchdown_pat_info()
    
    human_is_home = game["home_team"].id == game["player_team_id"]
    is_home_possession = engine.state.is_home_possession
    scoring_team_is_player = (human_is_home and is_home_possession) or (not human_is_home and not is_home_possession)
    
    return PATChoiceResponse(
        can_go_for_two=pat_info['can_go_for_two'],
        cpu_should_go_for_two=pat_info['cpu_should_go_for_two'],
        scoring_team_is_player=scoring_team_is_player
    )


@router.post("/api/game/extra-point", response_model=ExtraPointResponse)
async def attempt_extra_point(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    success, description = engine.attempt_extra_point()
    
    return ExtraPointResponse(
        success=success,
        description=description,
        new_score_home=engine.state.home_score,
        new_score_away=engine.state.away_score,
    )


class KickoffRequest(BaseModel):
    game_id: str
    kickoff_spot: int = 35


@router.post("/api/game/kickoff")
async def perform_kickoff(request: KickoffRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    kicking_home = engine.state.is_home_possession
    print(f"[DEBUG] Kickoff: kicking_home={kicking_home}, is_home_possession before={engine.state.is_home_possession}")
    
    result = engine.kickoff(kicking_home=kicking_home, kickoff_spot=request.kickoff_spot)
    
    print(f"[DEBUG] Kickoff result: is_home_possession after={engine.state.is_home_possession}, ball_position={engine.state.ball_position}")
    
    # Debug: Check player_team_id
    print(f"[DEBUG] player_team_id: {game.get('player_team_id')}")
    print(f"[DEBUG] home_team.id: {game['home_team'].id}")
    print(f"[DEBUG] human_is_home = {game['home_team'].id == game.get('player_team_id')}")
    print(f"[DEBUG] player_offense = {game['home_team'].id == game.get('player_team_id') == engine.state.is_home_possession}")
    
    scoring = result.touchdown or result.safety
    possession_changed = True
    
    return ExecutePlayResponse(
        player_play="KICKOFF",
        cpu_play="KICKOFF",
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=PlayResult(
            result=result.result.result_type.value if hasattr(result.result, 'result_type') else str(result.result),
            yards=result.yards_gained,
            description=result.description,
            turnover=result.turnover,
            scoring=scoring,
            touchdown=result.touchdown,
            new_ball_position=engine.state.ball_position,
            new_down=engine.state.down,
            new_yards_to_go=engine.state.yards_to_go,
            new_score_home=engine.state.home_score,
            new_score_away=engine.state.away_score,
            possession_changed=possession_changed,
            game_over=engine.state.game_over,
            quarter_changed=False,
            half_changed=False,
            pending_penalty_decision=result.pending_penalty_decision,
            penalty_choice=None,
            play_type="kickoff",
        ),
        game_state=game_state_to_response(game),
    )


class TwoPointRequest(BaseModel):
    game_id: str
    offense_play: str
    defense_play: str = "A"


@router.post("/api/game/two-point", response_model=ExecutePlayResponse)
async def attempt_two_point(request: TwoPointRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    offense_play = get_play_type_from_key(request.offense_play)
    defense_play = get_defense_type_from_key(request.defense_play)
    
    success, defense_points, description = engine.attempt_two_point(offense_play, defense_play)
    
    return ExecutePlayResponse(
        player_play=request.offense_play,
        cpu_play="CPU",
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=PlayResult(
            result="two_point_conversion",
            yards=0,
            description=description,
            scoring=True,
            touchdown=False,
            new_ball_position=engine.state.ball_position,
            new_down=engine.state.down,
            new_yards_to_go=engine.state.yards_to_go,
            new_score_home=engine.state.home_score,
            new_score_away=engine.state.away_score,
            possession_changed=True,
            game_over=engine.state.game_over,
        ),
        game_state=game_state_to_response(game),
    )


class PenaltyDecisionRequest(BaseModel):
    game_id: str
    penalty_index: int
    accept_penalty: bool


@router.post("/api/game/penalty-decision", response_model=ExecutePlayResponse)
async def apply_penalty_decision(request: PenaltyDecisionRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[request.game_id]
    engine = game["engine"]
    
    outcome = getattr(engine, '_last_play_outcome', None)
    if not outcome or not outcome.pending_penalty_decision:
        raise HTTPException(status_code=400, detail="No pending penalty decision")
    
    player_offense = game["human_plays_offense"]
    penalty_choice = outcome.penalty_choice
    offended_is_offense = penalty_choice.offended_team == "offense"
    
    human_decides = (offended_is_offense and player_offense) or \
                   (not offended_is_offense and not player_offense)
    
    if not human_decides:
        accept_penalty = True
    else:
        accept_penalty = request.accept_penalty
    
    if outcome.play_type == PlayType.PUNT:
        new_outcome = engine.apply_punt_penalty_decision(outcome, accept_penalty)
    elif outcome.play_type == PlayType.FIELD_GOAL:
        new_outcome = engine.apply_fg_penalty_decision(outcome, accept_play=not request.accept_penalty, penalty_index=request.penalty_index)
    elif outcome.play_type == PlayType.KICKOFF:
        new_outcome = engine.apply_kickoff_penalty_decision(outcome, accept_penalty)
    else:
        new_outcome = engine.apply_penalty_decision(outcome, accept_play=not request.accept_penalty, penalty_index=request.penalty_index)
    
    scoring = new_outcome.touchdown or new_outcome.field_goal_made or new_outcome.safety
    
    penalty_choice_model = None
    if new_outcome.penalty_choice:
        penalty_options = []
        for opt in new_outcome.penalty_choice.penalty_options:
            penalty_options.append(PenaltyOptionModel(
                penalty_type=opt.penalty_type,
                raw_result=opt.raw_result,
                yards=opt.yards,
                description=opt.description,
                auto_first_down=opt.auto_first_down,
                is_pass_interference=getattr(opt, 'is_pass_interference', False),
            ))
        penalty_choice_model = PenaltyChoiceModel(
            penalty_options=penalty_options,
            offended_team=new_outcome.penalty_choice.offended_team,
            offsetting=new_outcome.penalty_choice.offsetting,
            is_pass_interference=new_outcome.penalty_choice.is_pass_interference,
            reroll_log=new_outcome.penalty_choice.reroll_log or [],
        )
    
    play_result = PlayResult(
        result=new_outcome.result.result_type.value if hasattr(new_outcome.result, 'result_type') else str(new_outcome.result),
        yards=new_outcome.yards_gained,
        description=new_outcome.description,
        turnover=new_outcome.turnover,
        scoring=scoring,
        touchdown=new_outcome.touchdown,
        new_ball_position=engine.state.ball_position,
        new_down=engine.state.down,
        new_yards_to_go=engine.state.yards_to_go,
        new_score_home=engine.state.home_score,
        new_score_away=engine.state.away_score,
        possession_changed=new_outcome.turnover or scoring,
        game_over=engine.state.game_over,
        quarter_changed=False,
        half_changed=False,
        pending_penalty_decision=False,
        penalty_choice=penalty_choice_model,
        play_type=new_outcome.play_type.value if hasattr(new_outcome.play_type, 'value') else str(new_outcome.play_type),
    )
    
    return ExecutePlayResponse(
        player_play="PENALTY",
        cpu_play="CPU",
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=play_result,
        game_state=game_state_to_response(game),
    )


class SaveReplayResponse(BaseModel):
    replay_id: str
    game_state: GameStateResponse
    play_history: List[Dict[str, Any]]
    created_at: str


class LoadReplayRequest(BaseModel):
    replay_data: Dict[str, Any]


@router.post("/api/game/save-replay/{game_id}", response_model=SaveReplayResponse)
async def save_replay(game_id: str):
    """Save current game state and play history for replay."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    replay_id = f"replay_{uuid.uuid4().hex[:8]}"
    
    return SaveReplayResponse(
        replay_id=replay_id,
        game_state=game_state_to_response(game),
        play_history=game.get("play_history", []),
        created_at=datetime.now().isoformat(),
    )


@router.post("/api/game/load-replay")
async def load_replay(request: LoadReplayRequest):
    """Load a saved replay and create a new game from it."""
    replay_data = request.replay_data
    
    if "game_state" not in replay_data:
        raise HTTPException(status_code=400, detail="Invalid replay data: missing game_state")
    
    game_state = replay_data["game_state"]
    
    season = replay_data.get("season", "2026")
    season_dir = SEASONS_DIR / season
    if not season_dir.exists():
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")
    
    home_team_id = game_state.get("home_team", {}).get("id")
    away_team_id = game_state.get("away_team", {}).get("id")
    
    if not home_team_id or not away_team_id:
        raise HTTPException(status_code=400, detail="Invalid replay data: missing team info")
    
    home_team = load_team_info(season_dir, home_team_id)
    away_team = load_team_info(season_dir, away_team_id)
    
    home_chart = load_team_chart(str(season_dir / home_team.id))
    away_chart = load_team_chart(str(season_dir / away_team.id))
    
    game_id = f"game_{uuid.uuid4().hex[:8]}"
    
    engine = PaydirtGameEngine(home_chart, away_chart)
    
    difficulty = replay_data.get("difficulty", "medium")
    difficulty_map = {'easy': 0.3, 'medium': 0.5, 'hard': 0.7}
    cpu_aggression = difficulty_map.get(difficulty, 0.5)
    
    new_game = {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "human_plays_offense": game_state.get("player_offense", True),
        "player_team_id": game_state.get("human_team_id", home_team_id),
        "cpu_team_id": game_state.get("cpu_team_id", away_team_id),
        "engine": engine,
        "ai": ComputerAI(aggression=cpu_aggression),
        "created_at": datetime.now(),
        "season": season,
        "difficulty": difficulty,
        "play_history": replay_data.get("play_history", []),
    }
    
    new_game["ai"].set_team(home_chart if home_team.id == new_game["cpu_team_id"] else away_chart)
    
    # Restore game state from replay
    state = engine.state
    state.home_score = game_state.get("home_score", 0)
    state.away_score = game_state.get("away_score", 0)
    state.quarter = game_state.get("quarter", 1)
    state.time_remaining = game_state.get("time_remaining", 900) / 60  # Convert seconds to minutes
    state.down = game_state.get("down", 1)
    state.yards_to_go = game_state.get("yards_to_go", 10)
    state.ball_position = game_state.get("ball_position", 20)
    state.home_timeouts = game_state.get("home_timeouts", 3)
    state.away_timeouts = game_state.get("away_timeouts", 3)
    
    # Set possession correctly
    possession = game_state.get("possession", "home")
    state.is_home_possession = (possession == "home")
    
    # Handle ball position swap if possession doesn't match expectations
    # The engine expects home_possession = ball at home yard line
    # If ball_position is > 50 and home has possession, that's correct
    # If ball_position is <= 50 and home has possession, that's correct
    
    games[game_id] = new_game
    
    print(f"[LOAD REPLAY] Restored game: {game_id}, Q{state.quarter}, {state.time_remaining*60}s, "
          f"possession={possession}, down={state.down}&{state.yards_to_go}, pos={state.ball_position}")
    
    return NewGameResponse(
        game_id=game_id,
        game_state=game_state_to_response(new_game),
        difficulty=difficulty,
    )


@router.get("/api/debug/settings")
async def get_debug_settings():
    """Get current debug settings."""
    return {
        "deterministic_mode": False,
        "seed": None,
    }


class SetDebugModeRequest(BaseModel):
    deterministic_mode: bool = False
    seed: Optional[int] = None


@router.post("/api/debug/settings")
async def set_debug_settings(request: SetDebugModeRequest):
    """Set debug mode for deterministic dice rolls."""
    return {
        "deterministic_mode": request.deterministic_mode,
        "seed": request.seed,
        "status": "ok",
    }
