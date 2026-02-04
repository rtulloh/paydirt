"""
Pre-defined NFL teams with their ratings.
These are sample teams inspired by various NFL seasons.
"""
from .models import Team


def get_sample_teams() -> dict[str, Team]:
    """
    Get a dictionary of sample NFL teams with their ratings.
    Ratings are on a 1-10 scale where 5 is average.
    """
    return {
        "KC": Team(
            name="Kansas City Chiefs",
            abbreviation="KC",
            rushing_offense=6,
            passing_offense=9,
            rushing_defense=5,
            passing_defense=6,
            special_teams=7,
            power_rating=85,
        ),
        "SF": Team(
            name="San Francisco 49ers",
            abbreviation="SF",
            rushing_offense=8,
            passing_offense=7,
            rushing_defense=7,
            passing_defense=7,
            special_teams=6,
            power_rating=82,
        ),
        "BUF": Team(
            name="Buffalo Bills",
            abbreviation="BUF",
            rushing_offense=6,
            passing_offense=8,
            rushing_defense=7,
            passing_defense=8,
            special_teams=6,
            power_rating=80,
        ),
        "DAL": Team(
            name="Dallas Cowboys",
            abbreviation="DAL",
            rushing_offense=7,
            passing_offense=7,
            rushing_defense=6,
            passing_defense=6,
            special_teams=5,
            power_rating=75,
        ),
        "PHI": Team(
            name="Philadelphia Eagles",
            abbreviation="PHI",
            rushing_offense=8,
            passing_offense=7,
            rushing_defense=6,
            passing_defense=5,
            special_teams=6,
            power_rating=78,
        ),
        "MIA": Team(
            name="Miami Dolphins",
            abbreviation="MIA",
            rushing_offense=6,
            passing_offense=8,
            rushing_defense=5,
            passing_defense=5,
            special_teams=5,
            power_rating=72,
        ),
        "BAL": Team(
            name="Baltimore Ravens",
            abbreviation="BAL",
            rushing_offense=9,
            passing_offense=6,
            rushing_defense=7,
            passing_defense=6,
            special_teams=8,
            power_rating=80,
        ),
        "DET": Team(
            name="Detroit Lions",
            abbreviation="DET",
            rushing_offense=7,
            passing_offense=7,
            rushing_defense=5,
            passing_defense=5,
            special_teams=5,
            power_rating=74,
        ),
        "CLE": Team(
            name="Cleveland Browns",
            abbreviation="CLE",
            rushing_offense=7,
            passing_offense=5,
            rushing_defense=8,
            passing_defense=7,
            special_teams=5,
            power_rating=70,
        ),
        "GB": Team(
            name="Green Bay Packers",
            abbreviation="GB",
            rushing_offense=6,
            passing_offense=7,
            rushing_defense=5,
            passing_defense=6,
            special_teams=5,
            power_rating=72,
        ),
        "NE": Team(
            name="New England Patriots",
            abbreviation="NE",
            rushing_offense=5,
            passing_offense=4,
            rushing_defense=5,
            passing_defense=5,
            special_teams=6,
            power_rating=55,
        ),
        "NYG": Team(
            name="New York Giants",
            abbreviation="NYG",
            rushing_offense=5,
            passing_offense=5,
            rushing_defense=5,
            passing_defense=5,
            special_teams=5,
            power_rating=58,
        ),
        "PIT": Team(
            name="Pittsburgh Steelers",
            abbreviation="PIT",
            rushing_offense=6,
            passing_offense=5,
            rushing_defense=7,
            passing_defense=7,
            special_teams=6,
            power_rating=68,
        ),
        "SEA": Team(
            name="Seattle Seahawks",
            abbreviation="SEA",
            rushing_offense=6,
            passing_offense=6,
            rushing_defense=5,
            passing_defense=6,
            special_teams=5,
            power_rating=65,
        ),
        "LAR": Team(
            name="Los Angeles Rams",
            abbreviation="LAR",
            rushing_offense=5,
            passing_offense=6,
            rushing_defense=6,
            passing_defense=5,
            special_teams=5,
            power_rating=62,
        ),
        "DEN": Team(
            name="Denver Broncos",
            abbreviation="DEN",
            rushing_offense=6,
            passing_offense=5,
            rushing_defense=6,
            passing_defense=6,
            special_teams=5,
            power_rating=60,
        ),
    }


def get_team(abbreviation: str) -> Team:
    """Get a team by its abbreviation."""
    teams = get_sample_teams()
    if abbreviation.upper() not in teams:
        raise ValueError(f"Unknown team: {abbreviation}. Available teams: {list(teams.keys())}")
    return teams[abbreviation.upper()]


def list_teams() -> list[tuple[str, str, int]]:
    """
    List all available teams.
    Returns list of (abbreviation, name, power_rating) tuples.
    """
    teams = get_sample_teams()
    return [(abbr, team.name, team.power_rating) for abbr, team in sorted(teams.items(), key=lambda x: -x[1].power_rating)]
