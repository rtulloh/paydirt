"""
Pytest configuration and shared fixtures for paydirt-web backend tests.
"""
import os
from pathlib import Path

import pytest


def season_data_exists(year: int, team: str = None) -> bool:
    """
    Check if season data exists for testing.
    
    Args:
        year: Season year (e.g., 1983, 2026)
        team: Optional team name within the season
        
    Returns:
        True if the season (and optionally team) data exists
    """
    # Try multiple possible locations for season data
    possible_base_paths = [
        Path(__file__).parent.parent.parent.parent / 'seasons',
        Path(os.environ.get('SEASONS_DIR', 'seasons')),
    ]
    
    for base_path in possible_base_paths:
        season_path = base_path / str(year)
        if team:
            team_path = season_path / team
            if team_path.exists() and team_path.is_dir():
                return True
        else:
            if season_path.exists() and season_path.is_dir():
                return True
    return False


# Pre-computed flags for common season checks (evaluated once at import time)
HAS_1983_SEASON = season_data_exists(1983)
HAS_1983_49ERS = season_data_exists(1983, '49ers')
HAS_1983_BEARS = season_data_exists(1983, 'Bears')
HAS_2026_SEASON = season_data_exists(2026)


# Skip markers for tests requiring specific season data
requires_1983_season = pytest.mark.skipif(
    not HAS_1983_SEASON,
    reason="1983 season data not available"
)

requires_1983_49ers = pytest.mark.skipif(
    not HAS_1983_49ERS,
    reason="1983/49ers season data not available"
)

requires_1983_bears = pytest.mark.skipif(
    not HAS_1983_BEARS,
    reason="1983/Bears season data not available"
)
