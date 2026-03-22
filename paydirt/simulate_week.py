#!/usr/bin/env python3
"""
Simulate a week of NFL games and record results to standings.

Usage:
    python -m paydirt.simulate_week 1983 1    # Simulate Week 1 of 1983
"""

import argparse
from pathlib import Path

from .chart_loader import find_team_charts, load_team_chart
from .game_engine import PaydirtGameEngine
from .computer_ai import ComputerAI
from .standings import StandingsManager, display_standings


# 1983 NFL Week 1 Schedule (actual historical matchups)
# Format: (away_team, home_team)
NFL_1983_WEEK_1 = [
    # Sunday games
    ("49ers", "Eagles"),
    ("Bears", "Falcons"),
    ("Bills", "Dolphins"),
    ("Broncos", "Steelers"),
    ("Browns", "Lions"),
    ("Buccaneers", "Saints"),
    ("Chargers", "Chiefs"),
    ("Colts", "Patriots"),
    ("Giants", "Rams"),
    ("Jets", "Chargers"),  # Note: This was actually Chargers at home
    ("Oilers", "Packers"),
    ("Raiders", "Bengals"),
    ("Seahawks", "Chiefs"),  # Adjusted - Chiefs had 2 home games week 1 historically
    ("Vikings", "Browns"),  # Adjusted
    # Monday Night
    ("Cowboys", "Redskins"),
]

# Simplified Week 1 schedule ensuring each team plays once
NFL_1983_WEEK_1_BALANCED = [
    # AFC East
    ("Jets", "Patriots"),
    ("Colts", "Bills"),
    ("Dolphins", "Oilers"),  # vs AFC Central
    # AFC Central
    ("Bengals", "Browns"),
    ("Steelers", "Broncos"),  # vs AFC West
    # AFC West
    ("Chiefs", "Chargers"),
    ("Raiders", "Seahawks"),
    # NFC East
    ("Cowboys", "Redskins"),
    ("Giants", "Eagles"),
    ("Cardinals", "Falcons"),  # vs NFC West/Central
    # NFC Central
    ("Bears", "Packers"),
    ("Vikings", "Lions"),
    ("Buccaneers", "Saints"),  # vs NFC West
    # NFC West
    ("49ers", "Rams"),
]


# 1972 NFL Week 1 - Balanced schedule for 26 teams (13 games)
# AFC has 13 teams (East: Dolphins, Jets, Patriots, Colts | Central: Steelers, Bengals, Browns, Oilers | West: Raiders, Chiefs, Chargers, Broncos)
# NFC has 13 teams (East: Cowboys, Giants, Redskins, Eagles | Central, Packers, Bears, Lions | West: Vikings: 49ers, Rams, Cardinals, Falcons, Saints)
NFL_1972_WEEK_1 = [
    # AFC Games
    ("Dolphins", "Patriots"),  # AFC East
    ("Jets", "Colts"),  # AFC East
    ("Steelers", "Browns"),  # AFC Central
    ("Bengals", "Oilers"),  # AFC Central
    ("Raiders", "Chiefs"),  # AFC West
    ("Chargers", "Broncos"),  # AFC West
    # NFC Games
    ("Cowboys", "Giants"),  # NFC East
    ("Redskins", "Eagles"),  # NFC East
    ("Vikings", "Packers"),  # NFC Central
    ("Bears", "Lions"),  # NFC Central
    ("49ers", "Rams"),  # NFC West
    ("Cardinals", "Falcons"),  # NFC West
    ("Saints", "Bills"),  # Interconference (AFL East vs NFC)
]


def find_team_chart_path(team_name: str, charts: list) -> str:
    """Find the chart path for a team name."""
    team_lower = team_name.lower()
    for season, chart_team, path in charts:
        if chart_team.lower() == team_lower:
            return path
    return None


def simulate_game(home_chart, away_chart, verbose: bool = False) -> tuple:
    """
    Simulate a complete game between two teams.
    
    Returns:
        (home_score, away_score)
    """
    game = PaydirtGameEngine(home_chart, away_chart)

    home_ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)
    away_ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)

    home_name = home_chart.peripheral.short_name
    away_name = away_chart.peripheral.short_name

    if verbose:
        print(f"  Simulating: {away_name} @ {home_name}...", end=" ", flush=True)

    # Opening kickoff - home team kicks to start
    opening_kicking_home = True
    game.kickoff(kicking_home=opening_kicking_home)

    play_count = 0
    last_quarter = 1

    while not game.state.game_over:
        state = game.state

        # Handle quarter changes
        if state.quarter != last_quarter:
            # Halftime kickoff
            if state.quarter == 3 and last_quarter == 2:
                game.kickoff(kicking_home=not opening_kicking_home)
            last_quarter = state.quarter

        # Select plays
        if state.is_home_possession:
            play_type = home_ai.select_offense(game)
            def_type = away_ai.select_defense(game)
        else:
            play_type = away_ai.select_offense(game)
            def_type = home_ai.select_defense(game)

        # Run the play
        outcome = game.run_play(play_type, def_type)

        # Handle scoring
        if outcome.touchdown:
            game.attempt_extra_point()
            game.kickoff(kicking_home=game.state.is_home_possession)
        elif outcome.field_goal_made:
            game.kickoff(kicking_home=game.state.is_home_possession)
        elif outcome.safety:
            game.safety_free_kick()

        play_count += 1

        # Safety limit
        if play_count > 500:
            break

    if verbose:
        print(f"{away_name} {game.state.away_score} - {home_name} {game.state.home_score}")

    return (game.state.home_score, game.state.away_score)


def simulate_week(year: int, week: int, verbose: bool = True):
    """Simulate a full week of NFL games."""

    # Find team charts
    seasons_dir = Path(__file__).parent.parent / "seasons"
    if not seasons_dir.exists():
        seasons_dir = Path("seasons")

    charts = find_team_charts(str(seasons_dir))

    # Filter to the requested year
    year_charts = [(s, t, p) for s, t, p in charts if s == str(year)]

    if not year_charts:
        print(f"Error: No team charts found for {year}")
        return

    # Get schedule for the week
    if year == 1983 and week == 1:
        schedule = NFL_1983_WEEK_1_BALANCED
    elif year == 1972 and week == 1:
        schedule = NFL_1972_WEEK_1
    else:
        print(f"Error: No schedule defined for {year} Week {week}")
        return

    # Load standings
    manager = StandingsManager()
    season = manager.load_season(year)

    print("=" * 70)
    print(f"  {year} NFL WEEK {week} SIMULATION")
    print("=" * 70)
    print()

    results = []

    for away_team, home_team in schedule:
        # Find chart paths
        away_path = find_team_chart_path(away_team, year_charts)
        home_path = find_team_chart_path(home_team, year_charts)

        if not away_path:
            print(f"  Warning: Team '{away_team}' not found, skipping game")
            continue
        if not home_path:
            print(f"  Warning: Team '{home_team}' not found, skipping game")
            continue

        # Load charts
        away_chart = load_team_chart(away_path)
        home_chart = load_team_chart(home_path)

        # Simulate the game
        home_score, away_score = simulate_game(home_chart, away_chart, verbose=verbose)

        # Record result
        season.add_game(home_team, home_score, away_team, away_score, week=week)
        results.append((away_team, away_score, home_team, home_score))

    # Save standings
    manager.save_season(season)

    # Display results
    print()
    print("=" * 70)
    print(f"  WEEK {week} RESULTS")
    print("=" * 70)
    print()
    print(f"  {'Away':<15} {'':>3}  @  {'Home':<15} {'':>3}")
    print(f"  {'-' * 45}")

    for away, away_score, home, home_score in results:
        if away_score > home_score:
            print(f"  {away:<15} {away_score:>3} *@  {home:<15} {home_score:>3}")
        elif home_score > away_score:
            print(f"  {away:<15} {away_score:>3}  @  {home:<15} {home_score:>3} *")
        else:
            print(f"  {away:<15} {away_score:>3}  @  {home:<15} {home_score:>3}  TIE")

    print()

    # Display standings
    display_standings(season)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate a week of NFL games"
    )
    parser.add_argument("year", type=int, help="Season year (e.g., 1983)")
    parser.add_argument("week", type=int, help="Week number")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="Suppress play-by-play output")

    args = parser.parse_args()

    simulate_week(args.year, args.week, verbose=not args.quiet)


if __name__ == "__main__":
    main()
