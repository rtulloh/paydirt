"""
Packaging utilities for Paydirt standalone executables.
Provides path resolution for bundled data (PyInstaller) and development.
"""
import sys
from pathlib import Path


def is_bundled() -> bool:
    """Check if running as PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_seasons_path() -> Path:
    """
    Get the path to the seasons directory.
    
    Returns:
        Path to seasons directory (contains year subdirectories)
    """
    if is_bundled():
        # When bundled, seasons are in the temporary extraction directory
        return Path(sys._MEIPASS) / 'seasons'
    else:
        # Development: look relative to this file
        return Path(__file__).parent.parent / 'seasons'


def get_season_path(year: int) -> Path:
    """
    Get the path to a specific season directory.
    
    Args:
        year: Season year (e.g., 2026)
        
    Returns:
        Path to season directory (e.g., seasons/2026)
    """
    return get_seasons_path() / str(year)


def get_team_path(year: int, team_name: str) -> Path:
    """
    Get the path to a specific team's directory.
    
    Args:
        year: Season year
        team_name: Team name (e.g., 'Ironclads')
        
    Returns:
        Path to team directory (e.g., seasons/2026/Ironclads)
    """
    return get_season_path(year) / team_name