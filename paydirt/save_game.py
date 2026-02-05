"""
Save and load game state for resuming games.
"""
import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from .game_engine import TeamStats, ScoringPlay, PaydirtGameEngine
from .chart_loader import load_team_chart


DEFAULT_SAVE_FILE = "paydirt_save.json"


def save_game(engine: PaydirtGameEngine, filepath: str = DEFAULT_SAVE_FILE,
              human_is_away: bool = True, human_is_home: bool = False) -> str:
    """
    Save the current game state to a JSON file.
    
    Args:
        engine: The game engine with current state
        filepath: Path to save file (default: paydirt_save.json)
        human_is_away: Whether human controls away team
        human_is_home: Whether human controls home team
    
    Returns:
        The filepath where the game was saved
    """
    state = engine.state
    
    # Build save data
    save_data = {
        "version": 1,
        "saved_at": datetime.now().isoformat(),
        # Team paths for reloading charts
        "away_team_path": state.away_chart.team_dir,
        "home_team_path": state.home_chart.team_dir,
        # Human control settings
        "human_is_away": human_is_away,
        "human_is_home": human_is_home,
        # Core game state
        "home_score": state.home_score,
        "away_score": state.away_score,
        "quarter": state.quarter,
        "time_remaining": state.time_remaining,
        "is_home_possession": state.is_home_possession,
        "ball_position": state.ball_position,
        "down": state.down,
        "yards_to_go": state.yards_to_go,
        "game_over": state.game_over,
        # Timeouts
        "home_timeouts": state.home_timeouts,
        "away_timeouts": state.away_timeouts,
        # 2-minute warning
        "two_minute_warning_called": state.two_minute_warning_called,
        # Overtime
        "is_overtime": state.is_overtime,
        "ot_period": state.ot_period,
        "ot_first_possession_complete": state.ot_first_possession_complete,
        "ot_first_possession_scored": state.ot_first_possession_scored,
        "ot_first_possession_was_td": state.ot_first_possession_was_td,
        "ot_coin_toss_winner_is_home": state.ot_coin_toss_winner_is_home,
        "is_playoff": state.is_playoff,
        "untimed_down_pending": state.untimed_down_pending,
        # Team stats
        "home_stats": asdict(state.home_stats),
        "away_stats": asdict(state.away_stats),
        # Scoring plays
        "scoring_plays": [
            {
                "quarter": sp.quarter,
                "time": sp.time_remaining,
                "team": sp.team,
                "play_type": sp.play_type,
                "description": sp.description,
                "points": sp.points,
            }
            for sp in state.scoring_plays
        ],
    }
    
    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    return filepath


def load_game(filepath: str = DEFAULT_SAVE_FILE) -> Optional[tuple]:
    """
    Load a saved game state from a JSON file.
    
    Args:
        filepath: Path to save file
    
    Returns:
        Tuple of (engine, human_is_away, human_is_home) or None if file not found
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        save_data = json.load(f)
    
    # Check version
    version = save_data.get("version", 1)
    if version != 1:
        raise ValueError(f"Unsupported save file version: {version}")
    
    # Load team charts
    away_chart = load_team_chart(save_data["away_team_path"])
    home_chart = load_team_chart(save_data["home_team_path"])
    
    # Create engine with loaded charts (constructor takes home_chart, away_chart)
    engine = PaydirtGameEngine(home_chart, away_chart)
    state = engine.state
    
    # Restore core game state
    state.home_score = save_data["home_score"]
    state.away_score = save_data["away_score"]
    state.quarter = save_data["quarter"]
    state.time_remaining = save_data["time_remaining"]
    state.is_home_possession = save_data["is_home_possession"]
    state.ball_position = save_data["ball_position"]
    state.down = save_data["down"]
    state.yards_to_go = save_data["yards_to_go"]
    state.game_over = save_data["game_over"]
    
    # Restore timeouts
    state.home_timeouts = save_data["home_timeouts"]
    state.away_timeouts = save_data["away_timeouts"]
    
    # Restore 2-minute warning
    state.two_minute_warning_called = save_data["two_minute_warning_called"]
    
    # Restore overtime state
    state.is_overtime = save_data.get("is_overtime", False)
    state.ot_period = save_data.get("ot_period", 0)
    state.ot_first_possession_complete = save_data.get("ot_first_possession_complete", False)
    state.ot_first_possession_scored = save_data.get("ot_first_possession_scored", False)
    state.ot_first_possession_was_td = save_data.get("ot_first_possession_was_td", False)
    state.ot_coin_toss_winner_is_home = save_data.get("ot_coin_toss_winner_is_home", False)
    state.is_playoff = save_data.get("is_playoff", False)
    state.untimed_down_pending = save_data.get("untimed_down_pending", False)
    
    # Restore team stats
    home_stats_data = save_data.get("home_stats", {})
    away_stats_data = save_data.get("away_stats", {})
    state.home_stats = TeamStats(**home_stats_data)
    state.away_stats = TeamStats(**away_stats_data)
    
    # Restore scoring plays
    state.scoring_plays = [
        ScoringPlay(
            quarter=sp["quarter"],
            time_remaining=sp["time"],
            team=sp["team"],
            play_type=sp["play_type"],
            description=sp["description"],
            points=sp["points"],
        )
        for sp in save_data.get("scoring_plays", [])
    ]
    
    # Return engine and human control settings
    human_is_away = save_data.get("human_is_away", True)
    human_is_home = save_data.get("human_is_home", False)
    
    return engine, human_is_away, human_is_home


def get_save_info(filepath: str = DEFAULT_SAVE_FILE) -> Optional[dict]:
    """
    Get summary info about a save file without fully loading it.
    
    Returns:
        Dict with save info or None if file not found
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        save_data = json.load(f)
    
    return {
        "saved_at": save_data.get("saved_at", "Unknown"),
        "away_team": os.path.basename(save_data.get("away_team_path", "Unknown")),
        "home_team": os.path.basename(save_data.get("home_team_path", "Unknown")),
        "quarter": save_data.get("quarter", 0),
        "time_remaining": save_data.get("time_remaining", 0),
        "away_score": save_data.get("away_score", 0),
        "home_score": save_data.get("home_score", 0),
    }
