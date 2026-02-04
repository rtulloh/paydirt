#!/usr/bin/env python3
"""
Season and standings tracking for Paydirt football simulation.

This script allows tracking of game results and displaying standings
by division and conference in the typical NFL format.

Usage:
    python -m paydirt.standings --help
    python -m paydirt.standings add 1983 "Redskins" 31 "Cowboys" 17
    python -m paydirt.standings show 1983
    python -m paydirt.standings games 1983
"""

import argparse
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


# 1983 NFL Division structure
# AFC and NFC each had 3 divisions: East, Central, West
NFL_DIVISIONS_1983 = {
    "AFC": {
        "East": ["Bills", "Colts", "Dolphins", "Jets", "Patriots"],
        "Central": ["Bengals", "Browns", "Oilers", "Steelers"],
        "West": ["Broncos", "Chiefs", "Raiders", "Chargers", "Seahawks"],
    },
    "NFC": {
        "East": ["Cardinals", "Cowboys", "Eagles", "Giants", "Redskins"],
        "Central": ["Bears", "Buccaneers", "Lions", "Packers", "Vikings"],
        "West": ["49ers", "Falcons", "Rams", "Saints"],
    },
}


@dataclass
class GameResult:
    """A single game result."""
    week: int
    home_team: str
    home_score: int
    away_team: str
    away_score: int
    
    @property
    def winner(self) -> Optional[str]:
        """Return the winning team, or None if tie."""
        if self.home_score > self.away_score:
            return self.home_team
        elif self.away_score > self.home_score:
            return self.away_team
        return None
    
    @property
    def loser(self) -> Optional[str]:
        """Return the losing team, or None if tie."""
        if self.home_score > self.away_score:
            return self.away_team
        elif self.away_score > self.home_score:
            return self.home_team
        return None
    
    @property
    def is_tie(self) -> bool:
        """Return True if game was a tie."""
        return self.home_score == self.away_score


@dataclass
class TeamRecord:
    """A team's season record."""
    team: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0
    division_wins: int = 0
    division_losses: int = 0
    division_ties: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    conference_ties: int = 0
    
    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties
    
    @property
    def win_pct(self) -> float:
        """Calculate winning percentage (ties count as half win)."""
        games = self.games_played
        if games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / games
    
    @property
    def point_diff(self) -> int:
        return self.points_for - self.points_against
    
    @property
    def record_str(self) -> str:
        """Format record as W-L or W-L-T."""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"
    
    @property
    def div_record_str(self) -> str:
        """Format division record."""
        if self.division_ties > 0:
            return f"{self.division_wins}-{self.division_losses}-{self.division_ties}"
        return f"{self.division_wins}-{self.division_losses}"


@dataclass
class Season:
    """A complete season with games and standings."""
    year: int
    divisions: dict = field(default_factory=dict)
    games: list = field(default_factory=list)
    
    def __post_init__(self):
        # Load division structure for the year
        if self.year == 1983:
            self.divisions = NFL_DIVISIONS_1983
        else:
            # Default to 1983 structure for now
            self.divisions = NFL_DIVISIONS_1983
    
    def get_team_conference(self, team: str) -> Optional[str]:
        """Get the conference for a team."""
        for conf, divs in self.divisions.items():
            for div, teams in divs.items():
                if team in teams:
                    return conf
        return None
    
    def get_team_division(self, team: str) -> Optional[tuple]:
        """Get the (conference, division) for a team."""
        for conf, divs in self.divisions.items():
            for div, teams in divs.items():
                if team in teams:
                    return (conf, div)
        return None
    
    def add_game(self, home_team: str, home_score: int, 
                 away_team: str, away_score: int, week: int = 0) -> GameResult:
        """Add a game result."""
        if week == 0:
            week = len(self.games) + 1
        
        game = GameResult(
            week=week,
            home_team=home_team,
            home_score=home_score,
            away_team=away_team,
            away_score=away_score
        )
        self.games.append(game)
        return game
    
    def get_standings(self) -> dict:
        """Calculate standings for all teams."""
        # Initialize records for all teams
        records = {}
        for conf, divs in self.divisions.items():
            for div, teams in divs.items():
                for team in teams:
                    records[team] = TeamRecord(team=team)
        
        # Process all games
        for game in self.games:
            home = game.home_team
            away = game.away_team
            
            if home not in records or away not in records:
                continue
            
            home_rec = records[home]
            away_rec = records[away]
            
            # Update points
            home_rec.points_for += game.home_score
            home_rec.points_against += game.away_score
            away_rec.points_for += game.away_score
            away_rec.points_against += game.home_score
            
            # Check if division/conference game
            home_div = self.get_team_division(home)
            away_div = self.get_team_division(away)
            is_division_game = home_div == away_div
            is_conference_game = home_div and away_div and home_div[0] == away_div[0]
            
            # Update win/loss/tie
            if game.is_tie:
                home_rec.ties += 1
                away_rec.ties += 1
                if is_division_game:
                    home_rec.division_ties += 1
                    away_rec.division_ties += 1
                if is_conference_game:
                    home_rec.conference_ties += 1
                    away_rec.conference_ties += 1
            elif game.winner == home:
                home_rec.wins += 1
                away_rec.losses += 1
                if is_division_game:
                    home_rec.division_wins += 1
                    away_rec.division_losses += 1
                if is_conference_game:
                    home_rec.conference_wins += 1
                    away_rec.conference_losses += 1
            else:
                away_rec.wins += 1
                home_rec.losses += 1
                if is_division_game:
                    away_rec.division_wins += 1
                    home_rec.division_losses += 1
                if is_conference_game:
                    away_rec.conference_wins += 1
                    home_rec.conference_losses += 1
        
        return records
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "year": self.year,
            "games": [asdict(g) for g in self.games]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Season":
        """Create from dictionary."""
        season = cls(year=data["year"])
        for g in data.get("games", []):
            season.games.append(GameResult(**g))
        return season


class StandingsManager:
    """Manages season data persistence."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to seasons directory in project
            data_dir = Path(__file__).parent.parent / "standings_data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_season_file(self, year: int) -> Path:
        return self.data_dir / f"season_{year}.json"
    
    def load_season(self, year: int) -> Season:
        """Load a season from disk, or create new if not exists."""
        filepath = self._get_season_file(year)
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
            return Season.from_dict(data)
        return Season(year=year)
    
    def save_season(self, season: Season):
        """Save a season to disk."""
        filepath = self._get_season_file(season.year)
        with open(filepath, 'w') as f:
            json.dump(season.to_dict(), f, indent=2)
    
    def list_seasons(self) -> list:
        """List all available seasons."""
        seasons = []
        for f in self.data_dir.glob("season_*.json"):
            try:
                year = int(f.stem.split("_")[1])
                seasons.append(year)
            except (ValueError, IndexError):
                pass
        return sorted(seasons)


def display_standings(season: Season):
    """Display standings in NFL format."""
    records = season.get_standings()
    
    print(f"\n{'=' * 70}")
    print(f"  {season.year} NFL STANDINGS")
    print(f"{'=' * 70}")
    
    for conf in ["AFC", "NFC"]:
        print(f"\n  {conf}")
        print(f"  {'-' * 66}")
        
        for div in ["East", "Central", "West"]:
            if div not in season.divisions.get(conf, {}):
                continue
            
            teams = season.divisions[conf][div]
            div_records = [records[t] for t in teams if t in records]
            
            # Sort by: win%, then point diff
            div_records.sort(key=lambda r: (-r.win_pct, -r.point_diff))
            
            print(f"\n  {conf} {div}")
            print(f"  {'Team':<15} {'W':>3} {'L':>3} {'T':>3} {'Pct':>6} {'PF':>5} {'PA':>5} {'Diff':>5} {'Div':>7}")
            print(f"  {'-' * 64}")
            
            for rec in div_records:
                pct_str = f"{rec.win_pct:.3f}"
                diff_str = f"+{rec.point_diff}" if rec.point_diff > 0 else str(rec.point_diff)
                print(f"  {rec.team:<15} {rec.wins:>3} {rec.losses:>3} {rec.ties:>3} {pct_str:>6} "
                      f"{rec.points_for:>5} {rec.points_against:>5} {diff_str:>5} {rec.div_record_str:>7}")
    
    print()


def display_games(season: Season):
    """Display all games for a season."""
    print(f"\n{'=' * 70}")
    print(f"  {season.year} GAME RESULTS")
    print(f"{'=' * 70}")
    
    if not season.games:
        print("\n  No games recorded yet.")
        print()
        return
    
    # Group by week
    games_by_week = {}
    for game in season.games:
        if game.week not in games_by_week:
            games_by_week[game.week] = []
        games_by_week[game.week].append(game)
    
    for week in sorted(games_by_week.keys()):
        print(f"\n  Week {week}")
        print(f"  {'-' * 50}")
        for game in games_by_week[week]:
            # Show winner in bold-ish format
            if game.home_score > game.away_score:
                print(f"  {game.away_team:<15} {game.away_score:>3}  @  {game.home_team:<15} {game.home_score:>3} *")
            elif game.away_score > game.home_score:
                print(f"  {game.away_team:<15} {game.away_score:>3} *@  {game.home_team:<15} {game.home_score:>3}")
            else:
                print(f"  {game.away_team:<15} {game.away_score:>3}  @  {game.home_team:<15} {game.home_score:>3}  (TIE)")
    
    print()


def normalize_team_name(name: str, season: Season) -> Optional[str]:
    """Try to match a team name to the official name."""
    name_lower = name.lower()
    
    for conf, divs in season.divisions.items():
        for div, teams in divs.items():
            for team in teams:
                if team.lower() == name_lower:
                    return team
                # Partial match
                if name_lower in team.lower() or team.lower() in name_lower:
                    return team
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Track NFL season standings for Paydirt football simulation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add game command
    add_parser = subparsers.add_parser("add", help="Add a game result")
    add_parser.add_argument("year", type=int, help="Season year (e.g., 1983)")
    add_parser.add_argument("home_team", help="Home team name")
    add_parser.add_argument("home_score", type=int, help="Home team score")
    add_parser.add_argument("away_team", help="Away team name")
    add_parser.add_argument("away_score", type=int, help="Away team score")
    add_parser.add_argument("--week", type=int, default=0, help="Week number (auto-assigned if not specified)")
    
    # Show standings command
    show_parser = subparsers.add_parser("show", help="Show standings")
    show_parser.add_argument("year", type=int, help="Season year (e.g., 1983)")
    
    # Show games command
    games_parser = subparsers.add_parser("games", help="Show all games")
    games_parser.add_argument("year", type=int, help="Season year (e.g., 1983)")
    
    # List seasons command
    subparsers.add_parser("list", help="List all seasons with data")
    
    # Teams command - show teams for a year
    teams_parser = subparsers.add_parser("teams", help="Show teams and divisions for a year")
    teams_parser.add_argument("year", type=int, help="Season year (e.g., 1983)")
    
    args = parser.parse_args()
    
    manager = StandingsManager()
    
    if args.command == "add":
        season = manager.load_season(args.year)
        
        # Normalize team names
        home = normalize_team_name(args.home_team, season)
        away = normalize_team_name(args.away_team, season)
        
        if not home:
            print(f"Error: Unknown team '{args.home_team}'")
            print("Use 'standings teams <year>' to see valid team names.")
            return 1
        if not away:
            print(f"Error: Unknown team '{args.away_team}'")
            print("Use 'standings teams <year>' to see valid team names.")
            return 1
        
        game = season.add_game(
            home_team=home,
            home_score=args.home_score,
            away_team=away,
            away_score=args.away_score,
            week=args.week
        )
        manager.save_season(season)
        
        winner = game.winner or "TIE"
        print(f"Added: Week {game.week} - {away} {args.away_score} @ {home} {args.home_score}")
        if game.is_tie:
            print(f"Result: TIE")
        else:
            print(f"Winner: {winner}")
    
    elif args.command == "show":
        season = manager.load_season(args.year)
        display_standings(season)
    
    elif args.command == "games":
        season = manager.load_season(args.year)
        display_games(season)
    
    elif args.command == "list":
        seasons = manager.list_seasons()
        if seasons:
            print("\nSeasons with recorded games:")
            for year in seasons:
                season = manager.load_season(year)
                print(f"  {year}: {len(season.games)} games")
        else:
            print("\nNo seasons recorded yet.")
            print("Use 'standings add <year> <home> <home_score> <away> <away_score>' to add a game.")
    
    elif args.command == "teams":
        season = Season(year=args.year)
        print(f"\n{args.year} NFL Teams by Division")
        print("=" * 50)
        for conf in ["AFC", "NFC"]:
            print(f"\n{conf}")
            for div in ["East", "Central", "West"]:
                if div in season.divisions.get(conf, {}):
                    teams = season.divisions[conf][div]
                    print(f"  {div}: {', '.join(teams)}")
    
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    exit(main())
