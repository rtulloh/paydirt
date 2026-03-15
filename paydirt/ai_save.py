"""
AI data persistence for opponent model learning.

This module handles saving and loading AI opponent model data to separate files,
allowing the AI to maintain learned tendencies across multiple games between the same teams.
"""
import json
import os
from datetime import datetime
from typing import Optional

from paydirt.ai_analysis import OpponentModel


AI_DATA_VERSION = 1


def get_ai_filepath(away_team_path: str, home_team_path: str, save_dir: str = ".") -> str:
    """
    Generate the AI data file path for a team pair.
    
    Args:
        away_team_path: Path to away team (e.g., "seasons/1983/Bills")
        home_team_path: Path to home team (e.g., "seasons/1983/Dolphins")
        save_dir: Directory to store the AI data file
        
    Returns:
        Path to the AI data file
    """
    # Create abbreviated names from team paths
    away_abbrev = away_team_path.split("/")[-1][:3].upper()
    home_abbrev = home_team_path.split("/")[-1][:3].upper()
    
    # Create filename: AWAY_HOME_ai.json
    filename = f"{away_abbrev}_{home_abbrev}_ai.json"
    
    return os.path.join(save_dir, filename)


def save_ai_data(engine, away_team_path: str, home_team_path: str, 
                 save_dir: str = ".") -> Optional[str]:
    """
    Save AI opponent model data to a team-pair specific file.
    
    Args:
        engine: The game engine with cpu_ai
        away_team_path: Path to away team
        home_team_path: Path to home team  
        save_dir: Directory to store the AI data file
        
    Returns:
        The filepath where data was saved, or None if nothing to save
    """
    # Check if AI has opponent model
    cpu_ai = getattr(engine, 'cpu_ai', None)
    if not cpu_ai or not cpu_ai.use_analysis or not cpu_ai.opponent_model:
        return None
    
    opponent_model = cpu_ai.opponent_model
    
    # Generate filepath
    filepath = get_ai_filepath(away_team_path, home_team_path, save_dir)
    
    # Check if file exists to get creation date
    created_at = datetime.now().isoformat()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                existing_data = json.load(f)
                created_at = existing_data.get("metadata", {}).get("created_at", created_at)
        except (json.JSONDecodeError, IOError):
            pass  # Use current time if can't read existing
    
    # Build save data
    save_data = {
        "version": AI_DATA_VERSION,
        "metadata": {
            "away_team_path": away_team_path,
            "home_team_path": home_team_path,
            "created_at": created_at,
            "last_updated": datetime.now().isoformat(),
        },
        "opponent_model": opponent_model.to_dict(),
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
            f.flush()
        return filepath
    except IOError as e:
        print(f"  [WARNING] Failed to save AI data: {e}")
        return None


def load_ai_data(away_team_path: str, home_team_path: str, 
                 save_dir: str = ".") -> Optional[OpponentModel]:
    """
    Load AI opponent model data if metadata matches current game.
    
    Args:
        away_team_path: Path to away team
        home_team_path: Path to home team
        save_dir: Directory to search for AI data file
        
    Returns:
        Restored OpponentModel if metadata matches, None otherwise
    """
    filepath = get_ai_filepath(away_team_path, home_team_path, save_dir)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            save_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [WARNING] Failed to load AI data from {filepath}: {e}")
        return None
    
    # Check version
    version = save_data.get("version", 0)
    if version != AI_DATA_VERSION:
        print(f"  [WARNING] AI data version mismatch ({version} vs {AI_DATA_VERSION}), creating fresh model")
        return None
    
    # Check metadata
    metadata = save_data.get("metadata", {})
    saved_away = metadata.get("away_team_path", "")
    saved_home = metadata.get("home_team_path", "")
    
    if saved_away != away_team_path or saved_home != home_team_path:
        # Metadata mismatch - teams have changed, don't load
        print(f"  [INFO] AI data teams don't match (saved: {saved_away} vs {saved_home}, "
              f"current: {away_team_path} vs {home_team_path}), creating fresh model")
        return None
    
    # Restore opponent model
    opponent_model_data = save_data.get("opponent_model")
    if not opponent_model_data:
        print("  [WARNING] No opponent model data found in AI file, creating fresh model")
        return None
    
    try:
        opponent_model = OpponentModel.from_dict(opponent_model_data)
        print(f"  [INFO] Loaded AI opponent model from {filepath}")
        return opponent_model
    except Exception as e:
        print(f"  [WARNING] Failed to restore opponent model: {e}, creating fresh model")
        return None
