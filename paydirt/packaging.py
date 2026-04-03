"""
Packaging utilities for Paydirt standalone executables.
Provides path resolution for bundled data (PyInstaller) and development.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def is_bundled() -> bool:
    """Check if running as PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_user_data_path() -> Optional[Path]:
    """
    Get the platform-specific user data directory for Paydirt.
    
    This is where user-added content (seasons, save files, etc.) can be stored.
    The directory is created if it doesn't exist.
    
    Platform locations:
        - macOS: ~/Library/Application Support/Paydirt/
        - Windows: %LOCALAPPDATA%\\Paydirt\\
        - Linux: ~/.local/share/Paydirt/
    
    Returns:
        Path to user data directory, or None if not running as bundled app
    """
    if not is_bundled():
        # In development, we don't use a separate user data directory
        return None

    if sys.platform == "darwin":
        # macOS
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        # Windows - use LOCALAPPDATA
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = Path.home() / "AppData" / "Local"
    else:
        # Linux and others - use XDG_DATA_HOME or ~/.local/share
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base = Path(xdg_data_home)
        else:
            base = Path.home() / ".local" / "share"

    user_data_path = base / "Paydirt"

    # Create the directory if it doesn't exist
    user_data_path.mkdir(parents=True, exist_ok=True)

    return user_data_path


def get_user_seasons_path() -> Optional[Path]:
    """
    Get the path to the user's custom seasons directory.
    
    This is where users can add their own season data (e.g., 1983/, 1972/).
    The directory is NOT created automatically - users must create it and
    add season folders following the required structure.
    
    Platform locations:
        - macOS: ~/Library/Application Support/Paydirt/seasons/
        - Windows: %LOCALAPPDATA%\\Paydirt\\seasons\\
        - Linux: ~/.local/share/Paydirt/seasons/
    
    Returns:
        Path to user seasons directory, or None if not running as bundled app
    """
    user_data = get_user_data_path()
    if user_data is None:
        return None
    return user_data / "seasons"


def get_builtin_seasons_path() -> Path:
    """
    Get the path to the built-in seasons directory (bundled with the app).

    This contains the default seasons shipped with the application (e.g., 2026).
    In development mode, this is the repo's seasons/ directory.
    In bundled mode, this is inside the PyInstaller temp directory.

    Returns:
        Path to built-in seasons directory
    """
    if is_bundled():
        # When bundled, seasons are in the temporary extraction directory
        return Path(sys._MEIPASS) / "seasons"
    else:
        # Development: look relative to this file
        return Path(__file__).parent.parent / "seasons"


def get_seasons_path() -> Path:
    """
    Get the path to the seasons directory (for backwards compatibility).

    Returns the built-in seasons path. For user seasons, use get_user_seasons_path().
    For listing all available seasons, use get_all_season_paths().

    Returns:
        Path to seasons directory (contains year subdirectories)
    """
    return get_builtin_seasons_path()


def get_all_season_paths() -> list[Path]:
    """
    Get all paths that should be scanned for season data.

    Returns a list of paths to scan, with user seasons path first (if it exists)
    so that user data takes precedence over built-in data for duplicate years.

    Returns:
        List of Path objects to scan for seasons (user path first, then built-in)
    """
    paths = []

    # User seasons path first (takes precedence)
    user_path = get_user_seasons_path()
    if user_path is not None and user_path.exists():
        paths.append(user_path)

    # Built-in seasons path
    paths.append(get_builtin_seasons_path())

    return paths


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
