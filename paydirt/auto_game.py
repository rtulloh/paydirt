"""
Auto game mode - CPU vs CPU simulation.

Usage: 
    python -m paydirt -auto Bears Cowboys           # Simple team names (uses default season)
    python -m paydirt -auto seasons/1983/Bears seasons/1985/Cowboys  # Full paths for cross-season
"""
import time
from pathlib import Path

from .chart_loader import find_team_charts, load_team_chart
from .game_engine import PaydirtGameEngine
from .computer_ai import ComputerAI
from .interactive_game import display_box_score
from .play_resolver import PlayType


def resolve_team_path(team_spec: str, charts: list, seasons_dir: str) -> str:
    """
    Resolve a team specification to a chart path.
    
    Accepts either:
    - Full path: "seasons/1983/Bears" or "1983/Bears"
    - Simple name: "Bears" (searches all seasons)
    
    Args:
        team_spec: Team specification (path or name)
        charts: List of (season, team_name, path) tuples from find_team_charts()
        seasons_dir: Base seasons directory
    
    Returns:
        Path to the team's chart directory, or None if not found
    """
    # Check if it looks like a path (contains / or \)
    if '/' in team_spec or '\\' in team_spec:
        # Normalize path
        team_spec = team_spec.replace('\\', '/')

        # Handle various path formats
        # "seasons/1983/Bears" -> "seasons/1983/Bears"
        # "1983/Bears" -> "seasons/1983/Bears"
        if not team_spec.startswith('seasons/'):
            team_spec = f"seasons/{team_spec}"

        # Check if path exists
        path = Path(team_spec)
        if path.exists():
            return str(path)

        # Try relative to script directory
        script_dir = Path(__file__).parent.parent
        path = script_dir / team_spec
        if path.exists():
            return str(path)

        return None

    # Simple team name - search all seasons
    team_name_lower = team_spec.lower()

    for season, chart_team_name, chart_path in charts:
        # Check for exact match or partial match
        if chart_team_name.lower() == team_name_lower or team_name_lower in chart_team_name.lower():
            return chart_path

    return None


def list_available_teams(charts: list) -> list:
    """Get list of available teams with season info."""
    teams = []
    for season, team_name, chart_path in charts:
        teams.append(f"{season}/{team_name}")
    return sorted(teams)


def run_auto_game(team1_spec: str, team2_spec: str, delay: float = 0.0):
    """
    Run a CPU vs CPU game between two teams.
    
    Args:
        team1_spec: Away team - name (e.g., "Bears") or path (e.g., "seasons/1983/Bears")
        team2_spec: Home team - name (e.g., "Cowboys") or path (e.g., "seasons/1985/Cowboys")
        delay: Seconds to pause between plays (default 0.0)
    """
    # Find team charts
    seasons_dir = "seasons"
    if not Path(seasons_dir).exists():
        script_dir = Path(__file__).parent.parent
        seasons_dir = str(script_dir / "seasons")

    charts = find_team_charts(seasons_dir)

    if not charts:
        print("Error: No team charts found in seasons/ directory")
        return

    # Resolve team paths (accepts both simple names and full paths)
    team1_path = resolve_team_path(team1_spec, charts, seasons_dir)
    team2_path = resolve_team_path(team2_spec, charts, seasons_dir)

    if not team1_path:
        print(f"Error: Team '{team1_spec}' not found")
        print("\nAvailable teams:")
        for team in list_available_teams(charts):
            print(f"  {team}")
        print("\nUsage: python -m paydirt -auto <team1> <team2>")
        print("  Examples:")
        print("    python -m paydirt -auto Bears Cowboys")
        print("    python -m paydirt -auto 1983/Bears 1983/Cowboys")
        print("    python -m paydirt -auto seasons/1983/Bears seasons/1983/Cowboys")
        return

    if not team2_path:
        print(f"Error: Team '{team2_spec}' not found")
        print("\nAvailable teams:")
        for team in list_available_teams(charts):
            print(f"  {team}")
        return

    # Load team charts
    away_chart = load_team_chart(team1_path)
    home_chart = load_team_chart(team2_path)

    away_name = away_chart.peripheral.short_name
    home_name = home_chart.peripheral.short_name

    print("=" * 70)
    print("  PAYDIRT - CPU vs CPU SIMULATION")
    print("=" * 70)
    print(f"\n  {away_chart.peripheral.team_name} @ {home_chart.peripheral.team_name}")
    print(f"  ({away_name} vs {home_name})")
    print()

    # Create game engine
    game = PaydirtGameEngine(home_chart, away_chart)

    # Create AI for both teams
    away_ai = ComputerAI(aggression=0.5)
    home_ai = ComputerAI(aggression=0.5)

    # Opening kickoff - home team kicks to start
    opening_kicking_home = True
    print("=" * 70)
    print("  OPENING KICKOFF")
    print("=" * 70)

    game.kickoff(kicking_home=opening_kicking_home)
    receiving_team = home_name if game.state.is_home_possession else away_name
    print(f"  {receiving_team} receives the kickoff")
    print(f"  Ball spotted at {game.state.field_position_str()}")
    time.sleep(delay)

    play_count = 0
    last_quarter = 1

    # Main game loop
    while not game.state.game_over:
        state = game.state

        # Check for quarter change
        if state.quarter != last_quarter:
            print("\n" + "=" * 70)
            print(f"  END OF QUARTER {last_quarter}")
            display_box_score(game, f"QUARTER {last_quarter} STATS")
            print("=" * 70)

            # Halftime
            if state.quarter == 3 and last_quarter == 2:
                print("\n  *** HALFTIME ***")
                print(f"  Score: {away_name} {state.away_score} - {home_name} {state.home_score}")
                print()

                # Second half kickoff
                game.kickoff(kicking_home=not opening_kicking_home)
                receiving_team = home_name if state.is_home_possession else away_name
                print(f"  {receiving_team} receives the second half kickoff")
                print(f"  Ball spotted at {state.field_position_str()}")

            last_quarter = state.quarter
            time.sleep(delay)

        # Determine which team is on offense
        if state.is_home_possession:
            off_team = home_name
            def_team = away_name
            off_ai = home_ai
            def_ai = away_ai
        else:
            off_team = away_name
            def_team = home_name
            off_ai = away_ai
            def_ai = home_ai

        # Display game status
        minutes = int(state.time_remaining)
        seconds = int((state.time_remaining % 1) * 60)

        print(f"\n  Q{state.quarter} {minutes}:{seconds:02d} | {away_name} {state.away_score} - {home_name} {state.home_score}")
        print(f"  {off_team} ball at {state.field_position_str()} | {state.down}&{state.yards_to_go}")

        # CPU selects plays with clock management
        play_type, use_oob, use_no_huddle, punt_short_drop, punt_coffin_yards = off_ai.select_offense_with_clock_management(game)
        def_type = def_ai.select_defense(game)

        play_name = play_type.value.replace('_', ' ').title()
        def_name = def_type.value.replace('_', ' ').title()

        # Show special mode if active
        if off_ai.last_mode:
            print(f"  [{off_ai.last_mode}]")

        # Show clock management
        if use_no_huddle:
            print(f"  {off_team} in NO-HUDDLE offense!")
        if use_oob:
            print("  [OUT OF BOUNDS DESIGNATION]")
        
        # Show punt options
        if play_type == PlayType.PUNT:
            if punt_short_drop:
                print("  [SHORT-DROP PUNT]")
            elif punt_coffin_yards > 0:
                print(f"  [COFFIN-CORNER PUNT: {punt_coffin_yards} yards subtracted]")

        print(f"  {off_team}: {play_name} vs {def_name}")

        # Run the play with OOB designation and punt options if applicable
        outcome = game.run_play(play_type, def_type, 
                                out_of_bounds_designation=use_oob,
                                punt_short_drop=punt_short_drop,
                                punt_coffin_corner_yards=punt_coffin_yards,
                                no_huddle=use_no_huddle)

        # Display result
        if outcome.touchdown:
            # Use current possession to determine who scored (handles defensive TDs)
            scoring_team = home_name if state.is_home_possession else away_name
            print(f"  >>> TOUCHDOWN {scoring_team}! <<<")
            # CPU kicks extra point (or goes for 2 in certain situations)
            success, description = game.attempt_extra_point()
            print(f"  {description}")

            # Kickoff after score - scoring team kicks
            kicking_home = game.state.is_home_possession
            game.kickoff(kicking_home=kicking_home)
            receiving_team = home_name if state.is_home_possession else away_name
            print(f"  {receiving_team} receives kickoff at {state.field_position_str()}")

        elif outcome.field_goal_made:
            print(f"  >>> FIELD GOAL {off_team}! <<<")
            # Kickoff after field goal - scoring team kicks
            kicking_home = game.state.is_home_possession
            game.kickoff(kicking_home=kicking_home)
            receiving_team = home_name if state.is_home_possession else away_name
            print(f"  {receiving_team} receives kickoff at {state.field_position_str()}")

        elif outcome.safety:
            print(f"  >>> SAFETY! {def_team} scores 2 points <<<")
            # Safety free kick from the 20
            game.safety_free_kick()
            receiving_team = home_name if state.is_home_possession else away_name
            print(f"  {receiving_team} receives safety kick at {state.field_position_str()}")

        elif outcome.turnover:
            if "INTERCEPTION" in outcome.description.upper():
                print(f"  INTERCEPTED by {def_team}!")
            elif "FUMBLE" in outcome.description.upper():
                print(f"  FUMBLE recovered by {def_team}!")
            elif "DOWNS" in outcome.description.upper():
                print("  Turnover on downs!")
            else:
                print(f"  Turnover! {def_team} takes over")
        else:
            # Normal play result
            yards = outcome.yards_gained
            if yards > 0:
                result_str = f"Gain of {yards}"
            elif yards < 0:
                result_str = f"Loss of {abs(yards)}"
            else:
                result_str = "No gain"

            if outcome.first_down:
                result_str += " - FIRST DOWN"

            # Show penalty details if the play was a penalty
            desc = outcome.description or ""
            if "penalty" in desc.lower() or "BAD SNAP" in desc or "FALSE START" in desc:
                result_str += f" [{desc}]"

            print(f"  {result_str}")

        # Handle penalty decisions for special teams (punt, field goal, kickoff)
        if outcome.pending_penalty_decision and outcome.penalty_choice:
            penalty_choice = outcome.penalty_choice
            
            # CPU makes a decision based on what's beneficial
            # For punt: OFF penalty = accept (replay from worse spot), DEF penalty = accept (usually first down)
            # For FG: usually accept the penalty
            # For kickoff: usually accept the penalty
            
            if penalty_choice.offended_team == "defense":
                # Defense was offended - accept penalty is usually better
                accept_penalty = True
            else:
                # Offense was offended - usually accept penalty
                accept_penalty = True
            
            # Apply the decision
            if play_type == PlayType.PUNT:
                outcome = game.apply_punt_penalty_decision(outcome, accept_penalty)
                print(f"  [PENALTY: {'Accepted' if accept_penalty else 'Declined'}]")
            elif play_type == PlayType.FIELD_GOAL:
                outcome = game.apply_fg_penalty_decision(outcome, accept_play=True, penalty_index=0)
                print("  [PENALTY: Accepted]")
            elif play_type == PlayType.KICKOFF:
                outcome = game.apply_kickoff_penalty_decision(outcome, accept_penalty=True)
                print("  [PENALTY: Accepted]")

        play_count += 1
        time.sleep(delay)

        # Safety check - prevent infinite loops
        if play_count > 500:
            print("\n  [Game ended - play limit reached]")
            break

    # Game over
    print("\n" + "=" * 70)
    print("  FINAL")
    print("=" * 70)
    print(f"\n  {away_name} {game.state.away_score} - {home_name} {game.state.home_score}")

    if game.state.away_score > game.state.home_score:
        print(f"\n  {away_chart.peripheral.team_name} WIN!")
    elif game.state.home_score > game.state.away_score:
        print(f"\n  {home_chart.peripheral.team_name} WIN!")
    else:
        print("\n  TIE GAME!")

    display_box_score(game, "FINAL STATISTICS")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        run_auto_game(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python -m paydirt.auto_game <team1> <team2>")
        print("Example: python -m paydirt.auto_game Bears Cowboys")
