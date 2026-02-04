"""
Interactive Paydirt game for human vs computer play.
Allows player to select team and make play calls on offense and defense.
"""
import os
import random
import re
from pathlib import Path
from typing import Optional

from .chart_loader import load_team_chart, TeamChart, OffenseChart
from .game_engine import PaydirtGameEngine
from .play_resolver import (
    PlayType, DefenseType, ResultType,
    is_passing_play
)
from .priority_chart import categorize_result, apply_priority_chart, ResultCategory
from .computer_ai import ComputerAI
from .penalty_handler import apply_half_distance_rule
from .commentary import Commentary, get_roster

# Global display mode flag (set by run_interactive_game)
COMPACT_MODE = False


def analyze_team_strength(offense: OffenseChart) -> str:
    """
    Analyze a team's offensive chart to determine if they favor running or passing.
    
    Returns:
        'run' if team is better at running
        'pass' if team is better at passing
        'balanced' if roughly equal
    """
    def count_positive_results(chart_column: dict) -> int:
        """Count results that are likely positive (yardage gains, breakaways)."""
        positive = 0
        for roll, result in chart_column.items():
            if not result:
                continue
            result_str = str(result).upper()
            # Skip penalties, fumbles, interceptions, sacks
            if any(x in result_str for x in ['OFF', 'DEF', 'F ', 'F+', 'F-', 'INT', 'SK', 'BK']):
                continue
            # Count breakaways as very positive
            if result_str.startswith('B'):
                positive += 2
                continue
            # Try to parse as yardage
            try:
                # Handle variable yardage like "DS", "T1", etc.
                if any(x in result_str for x in ['DS', 'T1', 'T2', 'T3', 'X']):
                    positive += 1  # Variable yardage is generally positive
                    continue
                # Parse numeric yardage
                yards = int(result_str.split()[0].replace('(', '').replace(')', ''))
                if yards > 0:
                    positive += 1
            except (ValueError, IndexError):
                pass
        return positive

    # Analyze running plays (Line Plunge, Off Tackle, End Run, Draw)
    run_positive = (
        count_positive_results(offense.line_plunge) +
        count_positive_results(offense.off_tackle) +
        count_positive_results(offense.end_run) +
        count_positive_results(offense.draw)
    )

    # Analyze passing plays (Screen, Short Pass, Medium Pass, Long Pass, TE)
    pass_positive = (
        count_positive_results(offense.screen) +
        count_positive_results(offense.short_pass) +
        count_positive_results(offense.medium_pass) +
        count_positive_results(offense.long_pass) +
        count_positive_results(offense.te_short_long)
    )

    # Normalize by number of play types (4 run, 5 pass)
    run_avg = run_positive / 4
    pass_avg = pass_positive / 5

    # Determine team tendency with a threshold
    if run_avg > pass_avg * 1.15:
        return 'run'
    elif pass_avg > run_avg * 1.15:
        return 'pass'
    else:
        return 'balanced'


# Play type display names and keys
OFFENSE_PLAYS = {
    '1': (PlayType.LINE_PLUNGE, 'Line Plunge', 'Short yardage power run up the middle'),
    '2': (PlayType.OFF_TACKLE, 'Off Tackle', 'Run between guard and tackle'),
    '3': (PlayType.END_RUN, 'End Run', 'Outside run around the end'),
    '4': (PlayType.DRAW, 'Draw', 'Delayed handoff, looks like pass'),
    '5': (PlayType.SCREEN, 'Screen', 'Short pass behind the line'),
    '6': (PlayType.SHORT_PASS, 'Short Pass', 'Quick pass, 5-10 yards'),
    '7': (PlayType.MEDIUM_PASS, 'Medium Pass', '10-20 yard pass'),
    '8': (PlayType.LONG_PASS, 'Long Pass', 'Deep pass, 20+ yards'),
    '9': (PlayType.TE_SHORT_LONG, 'TE Short/Long', 'Tight end route'),
    'Q': (PlayType.QB_SNEAK, 'QB Sneak', 'Sneak for 1 yard - defense cannot respond'),
    'H': (PlayType.HAIL_MARY, 'Hail Mary', 'Desperation pass (end of half only)'),
    'P': (PlayType.PUNT, 'Punt', 'Kick the ball away'),
    'F': (PlayType.FIELD_GOAL, 'Field Goal', 'Attempt a field goal'),
}

DEFENSE_PLAYS = {
    'A': (DefenseType.STANDARD, 'Standard (A)', 'Balanced defense'),
    'B': (DefenseType.SHORT_YARDAGE, 'Short Yardage (B)', 'Goal line / short yardage'),
    'C': (DefenseType.SPREAD, 'Spread (C)', 'Defend against spread offense'),
    'D': (DefenseType.SHORT_PASS, 'Short Pass (D)', 'Defend short passes'),
    'E': (DefenseType.LONG_PASS, 'Long Pass (E)', 'Defend deep passes'),
    'F': (DefenseType.BLITZ, 'Blitz (F)', 'All-out pass rush'),
}


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_time(minutes: float) -> str:
    """Format time as MM:SS."""
    mins = int(minutes)
    secs = int((minutes - mins) * 60)
    return f'{mins}:{secs:02d}'


def get_available_teams() -> list[tuple[str, str]]:
    """Find all available team chart directories."""
    teams = []
    seasons_path = Path('seasons')
    if seasons_path.exists():
        for season_dir in sorted(seasons_path.iterdir()):
            if season_dir.is_dir():
                for team_dir in sorted(season_dir.iterdir()):
                    if team_dir.is_dir():
                        # Check if it has the required CSV files
                        offense_file = team_dir / 'OFFENSE-Table 1.csv'
                        if offense_file.exists():
                            teams.append((str(team_dir), f"{season_dir.name} {team_dir.name}"))
    return teams


def select_team(prompt: str, exclude: Optional[str] = None) -> TeamChart:
    """Let user select a team from available teams."""
    teams = get_available_teams()

    if not teams:
        print("No team charts found in seasons/ directory!")
        raise SystemExit(1)

    print(f"\n{prompt}")
    print("-" * 50)

    available = [(path, name) for path, name in teams if path != exclude]
    for i, (path, name) in enumerate(available, 1):
        print(f"  {i}. {name}")

    while True:
        try:
            choice = input("\nEnter team number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                path, name = available[idx]
                print(f"Selected: {name}")
                return load_team_chart(path)
        except ValueError:
            pass
        print("Invalid choice. Please enter a number from the list.")


def display_game_status(game: PaydirtGameEngine, human_team: TeamChart, is_human_offense: bool):
    """Display current game status."""
    state = game.state

    # Determine team names
    if state.is_home_possession:
        off_team = state.home_chart.peripheral.short_name
        def_team = state.away_chart.peripheral.short_name
    else:
        off_team = state.away_chart.peripheral.short_name
        def_team = state.home_chart.peripheral.short_name


    # Field position
    if state.ball_position <= 50:
        field_pos = f"{off_team} {state.ball_position}"
    else:
        field_pos = f"{def_team} {100 - state.ball_position}"

    # Down and distance string
    yards_to_goal = 100 - state.ball_position
    if yards_to_goal <= 10 and state.yards_to_go >= yards_to_goal:
        down_str = f"{state.down}{_ordinal(state.down)} & Goal"
    else:
        down_str = f"{state.down}{_ordinal(state.down)} & {state.yards_to_go}"

    if COMPACT_MODE:
        # Compact single-line status with timeouts inline with score (Option 1)
        you_marker = "*" if is_human_offense else ""
        # Get individual team scores
        away_name = state.away_chart.peripheral.short_name
        home_name = state.home_chart.peripheral.short_name
        away_score = state.away_score
        home_score = state.home_score
        away_to = state.away_timeouts
        home_to = state.home_timeouts
        print(f"\nQ{state.quarter} {format_time(state.time_remaining)} | {away_name} {away_score} ({away_to}) - {home_name} {home_score} ({home_to}) | {down_str} {field_pos} | {off_team}{you_marker} ball")
    else:
        # Verbose multi-line status
        print("\n" + "=" * 70)
        print(f"  Q{state.quarter} | {format_time(state.time_remaining)} | {game.get_score_str()}")
        print("=" * 70)

        print(f"\n  Ball on: {field_pos}-yard line")
        if yards_to_goal <= 10 and state.yards_to_go >= yards_to_goal:
            print(f"  Down: {state.down}{_ordinal(state.down)} and Goal")
        else:
            print(f"  Down: {state.down}{_ordinal(state.down)} and {state.yards_to_go}")
        print(f"  Possession: {off_team}{' (YOU)' if is_human_offense else ''}")
        print(f"  Timeouts: {off_team} {state.offense_timeouts} | {def_team} {state.defense_timeouts}")
        print()


def _ordinal(n: int) -> str:
    """Return ordinal suffix for a number."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix


def display_box_score(game: PaydirtGameEngine, title: str = "BOX SCORE"):
    """Display a formatted box score with team statistics and scoring summary."""
    state = game.state
    away_name = state.away_chart.peripheral.short_name
    home_name = state.home_chart.peripheral.short_name
    away_stats = state.away_stats
    home_stats = state.home_stats

    # Calculate quarter scores from scoring plays
    away_q = {1: 0, 2: 0, 3: 0, 4: 0}
    home_q = {1: 0, 2: 0, 3: 0, 4: 0}
    for play in state.scoring_plays:
        q = min(play.quarter, 4)  # Cap at Q4 for OT
        if play.is_home_team:
            home_q[q] += play.points
        else:
            away_q[q] += play.points

    # Calculate width for formatting
    name_width = max(len(away_name), len(home_name), 10)

    print()
    print("+" + "-" * 58 + "+")
    print(f"|{title:^58}|")
    print("+" + "-" * 58 + "+")

    # Score line with quarter breakdown
    print(f"|  {'TEAM':<{name_width}}  |  {'1Q':>4}  {'2Q':>4}  {'3Q':>4}  {'4Q':>4}  |  {'TOTAL':>5}  |")
    print("|" + "-" * 58 + "|")
    print(f"|  {away_name:<{name_width}}  |  {away_q[1]:>4}  {away_q[2]:>4}  {away_q[3]:>4}  {away_q[4]:>4}  |  {state.away_score:>5}  |")
    print(f"|  {home_name:<{name_width}}  |  {home_q[1]:>4}  {home_q[2]:>4}  {home_q[3]:>4}  {home_q[4]:>4}  |  {state.home_score:>5}  |")
    print("+" + "-" * 58 + "+")

    # Scoring Summary - NFL style with running scores
    if state.scoring_plays:
        print()
        print("+" + "-" * 70 + "+")
        print(f"|{'SCORING SUMMARY':^70}|")
        print("+" + "-" * 70 + "+")

        # Build combined scoring entries (TD + PAT combined)
        combined_plays = []
        i = 0
        while i < len(state.scoring_plays):
            play = state.scoring_plays[i]

            # Check if next play is PAT/2PT for same team (combine them)
            if play.play_type == "TD" and i + 1 < len(state.scoring_plays):
                next_play = state.scoring_plays[i + 1]
                if next_play.play_type in ["PAT", "2PT"] and next_play.is_home_team == play.is_home_team:
                    # Combine TD + PAT
                    combined_plays.append({
                        'quarter': play.quarter,
                        'time': play.time_remaining,
                        'team': play.team,
                        'is_home': play.is_home_team,
                        'type': 'Touchdown',
                        'description': play.description,
                        'pat_desc': "Extra point is good." if next_play.play_type == "PAT" else "Two-point conversion good.",
                        'points': play.points + next_play.points
                    })
                    i += 2
                    continue

            # Single play (FG, Safety, missed PAT TD, etc.)
            play_type_display = {
                "TD": "Touchdown",
                "FG": "Field goal",
                "Safety": "Safety",
                "PAT": "Extra point",
                "2PT": "Two-point conversion",
                "Def 2PT": "Defensive 2-pt return"
            }.get(play.play_type, play.play_type)

            combined_plays.append({
                'quarter': play.quarter,
                'time': play.time_remaining,
                'team': play.team,
                'is_home': play.is_home_team,
                'type': play_type_display,
                'description': play.description,
                'pat_desc': None,
                'points': play.points
            })
            i += 1

        # Track running score
        away_running = 0
        home_running = 0
        current_quarter = 0

        # Fixed width = 70 chars between the | characters
        WIDTH = 70

        for entry in combined_plays:
            # Quarter header with team columns
            if entry['quarter'] != current_quarter:
                current_quarter = entry['quarter']
                q_names = {1: "1st Quarter", 2: "2nd Quarter", 3: "3rd Quarter", 4: "4th Quarter"}
                q_name = q_names.get(current_quarter, f"Q{current_quarter}")
                # Score header line
                score_header = f"{away_name:>8}  {home_name:>8}"
                print(f"|{score_header:>{WIDTH}}|")
                # Quarter name line
                print(f"|  {q_name:<{WIDTH-2}}|")
                print("|" + "-" * WIDTH + "|")

            # Update running score using is_home flag
            if entry['is_home']:
                home_running += entry['points']
            else:
                away_running += entry['points']

            # Format time as M:SS
            minutes = int(entry['time'])
            seconds = int((entry['time'] % 1) * 60)
            time_str = f"{minutes}:{seconds:02d}"

            # Format the scoring play header line
            play_info = f"  {entry['team']} - {entry['type']} · {time_str}"
            scores = f"{away_running:>5}  {home_running:>5}"
            gap = WIDTH - len(play_info) - len(scores)
            print(f"|{play_info}{' ' * gap}{scores}|")

            # Description line
            desc = entry['description']
            if entry['pat_desc']:
                desc = f"{desc}. {entry['pat_desc']}"

            # Wrap long descriptions to multiple lines
            max_desc = WIDTH - 4  # 4 chars for "    " indent
            if len(desc) <= max_desc:
                print(f"|    {desc:<{WIDTH-4}}|")
            else:
                # Word-wrap the description
                words = desc.split()
                lines = []
                current_line = ""
                for word in words:
                    if current_line and len(current_line) + 1 + len(word) > max_desc:
                        lines.append(current_line)
                        current_line = word
                    else:
                        current_line = f"{current_line} {word}" if current_line else word
                if current_line:
                    lines.append(current_line)

                for line in lines:
                    print(f"|    {line:<{WIDTH-4}}|")
            print(f"|{' ' * WIDTH}|")

        print("+" + "-" * WIDTH + "+")
    print()

    # Team Statistics
    print("+" + "-" * 58 + "+")
    print(f"|{'TEAM STATISTICS':^58}|")
    print("+" + "-" * 58 + "+")
    print(f"|  {'':20}  |  {away_name:^12}  |  {home_name:^12}  |")
    print("|" + "-" * 58 + "|")
    print(f"|  {'First Downs':20}  |  {away_stats.first_downs:^12}  |  {home_stats.first_downs:^12}  |")
    print(f"|  {'Total Yards':20}  |  {away_stats.total_yards:^12}  |  {home_stats.total_yards:^12}  |")
    print(f"|  {'  Rushing':20}  |  {away_stats.rushing_yards:^12}  |  {home_stats.rushing_yards:^12}  |")
    print(f"|  {'  Passing':20}  |  {away_stats.passing_yards:^12}  |  {home_stats.passing_yards:^12}  |")
    # Calculate turnovers as sum of interceptions thrown + fumbles lost
    away_turnovers = away_stats.interceptions_thrown + away_stats.fumbles_lost
    home_turnovers = home_stats.interceptions_thrown + home_stats.fumbles_lost
    print(f"|  {'Turnovers':20}  |  {away_turnovers:^12}  |  {home_turnovers:^12}  |")
    print(f"|  {'  Interceptions':20}  |  {away_stats.interceptions_thrown:^12}  |  {home_stats.interceptions_thrown:^12}  |")
    print(f"|  {'  Fumbles Lost':20}  |  {away_stats.fumbles_lost:^12}  |  {home_stats.fumbles_lost:^12}  |")
    print(f"|  {'Penalties':20}  |  {away_stats.penalties:^12}  |  {home_stats.penalties:^12}  |")
    print(f"|  {'Penalty Yards':20}  |  {away_stats.penalty_yards:^12}  |  {home_stats.penalty_yards:^12}  |")
    print(f"|  {'Sacks':20}  |  {away_stats.sacks:^12}  |  {home_stats.sacks:^12}  |")
    print(f"|  {'Sack Yards':20}  |  {away_stats.sack_yards:^12}  |  {home_stats.sack_yards:^12}  |")
    print("+" + "-" * 58 + "+")


def _get_human_offense_play_compact(game: PaydirtGameEngine, state, no_huddle: bool) -> tuple[PlayType, bool, bool, bool, bool]:
    """Compact offense menu - abbreviated display with '?' for full menu."""
    # Calculate default play
    team_strength = analyze_team_strength(state.possession_team.offense)
    if state.yards_to_go <= 2:
        default_play = '1'
        default_name = 'Plunge'
    elif state.yards_to_go >= 8:
        default_play = '7'
        default_name = 'Med Pass'
    elif state.down == 1:
        if team_strength == 'run':
            default_play = '3'
            default_name = 'End Run'
        elif team_strength == 'pass':
            default_play = '7'
            default_name = 'Med Pass'
        else:
            default_play = '3' if random.random() < 0.5 else '7'
            default_name = 'End Run' if default_play == '3' else 'Med Pass'
    else:
        default_play = '3'
        default_name = 'End Run'

    # Compact prompt
    if state.down == 4:
        fg_distance = 100 - state.ball_position + 17
        print(f"  *** 4TH DOWN *** P=Punt, F=FG({fg_distance}yd), or go for it (1-9)")
        print(f"  OFF: 1-9,Q,H,S,K,P,F | N,T,/ | ?=help (Default={default_play}/{default_name})")
    else:
        print(f"  OFF: 1-9,Q,H,S,K,P,F | N,T,/ | ?=help (Default={default_play}/{default_name})")

    while True:
        choice = input("  > ").strip().upper()

        # Show full menu on '?'
        if choice == '?':
            _show_full_offense_menu(state, no_huddle)
            continue

        # Handle Enter for default
        if choice == '':
            choice = default_play

        # Check for modifiers
        out_of_bounds = '+' in choice
        in_bounds = '-' in choice
        choice_clean = choice.replace('+', '').replace('-', '').strip()

        if out_of_bounds and in_bounds:
            print("  Cannot use both + and -!")
            continue

        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()

        if call_timeout:
            if state.offense_timeouts <= 0:
                print("  No timeouts!")
                continue

        # Handle choices
        if choice_clean in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            play_type, name, _ = OFFENSE_PLAYS[choice_clean]
            print(f"  You called: {name}")
            return play_type, no_huddle, out_of_bounds, in_bounds, call_timeout

        if choice_clean == 'Q':
            print("  You called: QB Sneak")
            return PlayType.QB_SNEAK, no_huddle, out_of_bounds, in_bounds, call_timeout
        elif choice_clean == 'H':
            print("  You called: Hail Mary")
            return PlayType.HAIL_MARY, no_huddle, out_of_bounds, in_bounds, call_timeout
        elif choice_clean == 'S':
            print("  You called: Spike Ball")
            return PlayType.SPIKE_BALL, no_huddle, False, False, call_timeout
        elif choice_clean == 'K':
            print("  You called: QB Kneel")
            return PlayType.QB_KNEEL, no_huddle, False, False, call_timeout
        elif choice_clean == 'P':
            print("  You called: Punt")
            return PlayType.PUNT, no_huddle, False, False, call_timeout
        elif choice_clean == 'F':
            print("  You called: Field Goal")
            return PlayType.FIELD_GOAL, no_huddle, out_of_bounds, in_bounds, call_timeout

        if choice == 'N':
            new_no_huddle = not no_huddle
            if new_no_huddle:
                print("  No Huddle ON")
            else:
                print("  No Huddle OFF")
            return _get_human_offense_play_compact(game, state, new_no_huddle)

        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return _get_human_offense_play_compact(game, state, no_huddle)

        print("  Invalid. 1-9,Q,H,S,K,P,F,N,T,/ or ? for help")


def _show_full_offense_menu(state, no_huddle: bool):
    """Display the full offense menu (called from compact mode with '?')."""
    print("\n  OFFENSIVE PLAY CALL")
    print("  " + "-" * 40)

    if state.down == 4:
        fg_distance = 100 - state.ball_position + 17
        print("\n  *** 4TH DOWN DECISION ***")
        print("    [P] PUNT              - Kick the ball away")
        if state.ball_position >= 55:
            print(f"    [F] FIELD GOAL        - {fg_distance}-yard attempt")
        else:
            print(f"    [F] Field Goal        - {fg_distance}-yard attempt (Out of range)")
        print(f"    [G] GO FOR IT         - Run a play (4th and {state.yards_to_go})")
        print()

    print("  RUNNING PLAYS:")
    for key in ['1', '2', '3', '4']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    print("\n  PASSING PLAYS:")
    for key in ['5', '6', '7', '8', '9']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    print("\n  SPECIAL PLAYS:")
    print(f"    [Q] {'QB Sneak':15} - Sneak for 1 yard (defense can't respond)")
    print(f"    [H] {'Hail Mary':15} - Desperation pass (end of half only)")
    print(f"    [S] {'Spike Ball':15} - Stop clock, waste down (saves 20 sec)")
    print(f"    [K] {'QB Kneel':15} - Run out clock (-2 yards, 40 sec)")

    if state.down < 4:
        fg_distance = 100 - state.ball_position + 17
        print("\n  SPECIAL TEAMS (early kick options):")
        print(f"    [F] {'Field Goal':15} - {fg_distance}-yard attempt")
        print(f"    [P] {'Punt':15} - Kick the ball away")

    print("\n  OPTIONS:")
    if no_huddle:
        print("    [N] EXIT No Huddle    - Return to normal offense")
    else:
        print("    [N] No Huddle         - Hurry-up offense (saves time, penalty risk)")
    print("    [T] Call Timeout      - Stop clock after this play")
    print("    [/] Stats             - View current game statistics")
    print("    Add '+' for Out of Bounds, '-' for In Bounds")
    print()


def get_human_offense_play(game: PaydirtGameEngine, no_huddle: bool = False) -> tuple[PlayType, bool, bool, bool, bool]:
    """
    Prompt human player to select an offensive play.
    
    Args:
        game: The game engine
        no_huddle: Whether No Huddle mode is currently active
    
    Returns:
        Tuple of (PlayType, no_huddle_for_next_play, out_of_bounds_designation, in_bounds_designation, call_timeout)
    """
    state = game.state

    # Show No Huddle status
    if no_huddle:
        print("\n  *** NO HUDDLE OFFENSE ACTIVE ***")
        print("  (Previous play time reduced, but penalty risks increased)")

    # In compact mode, show abbreviated menu
    if COMPACT_MODE:
        return _get_human_offense_play_compact(game, state, no_huddle)

    print("\n  OFFENSIVE PLAY CALL")
    print("  " + "-" * 40)

    # On 4th down, show special teams options FIRST and prominently
    if state.down == 4:
        print("\n  *** 4TH DOWN DECISION ***")
        print("  " + "-" * 40)

        # Calculate field goal distance
        fg_distance = 100 - state.ball_position + 17  # End zone + holder position

        # Punt option
        print("    [P] PUNT              - Kick the ball away")

        # Field goal option with distance and recommendation
        if state.ball_position >= 55:  # Roughly FG range (45 yards or less)
            if fg_distance <= 35:
                fg_note = "(Good range)"
            elif fg_distance <= 45:
                fg_note = "(Makeable)"
            elif fg_distance <= 55:
                fg_note = "(Long - risky)"
            else:
                fg_note = "(Very long - low %)"
            print(f"    [F] FIELD GOAL        - {fg_distance}-yard attempt {fg_note}")
        else:
            print(f"    [F] Field Goal        - {fg_distance}-yard attempt (Out of range)")

        # Go for it option
        print(f"    [G] GO FOR IT         - Run a play (4th and {state.yards_to_go})")

        # Determine default based on field position
        if state.ball_position <= 40:
            default_4th = 'P'
            default_4th_name = 'Punt'
        elif fg_distance <= 45:
            default_4th = 'F'
            default_4th_name = 'Field Goal'
        else:
            default_4th = 'P'
            default_4th_name = 'Punt'

        print("\n  " + "-" * 40)
        print(f"  [Enter] = {default_4th_name} (default)")

        while True:
            choice = input("\n  Your 4th down decision (P/F/G/T): ").strip().upper()

            # Handle Enter for default
            if choice == '':
                choice = default_4th

            if choice == 'P':
                return PlayType.PUNT, no_huddle, False, False, False
            elif choice == 'F':
                return PlayType.FIELD_GOAL, no_huddle, False, False, False
            elif choice == 'T':
                # Call timeout before the play
                if state.offense_timeouts > 0:
                    print("  *** TIMEOUT CALLED ***")
                    return PlayType.PUNT, no_huddle, False, False, True  # Will be handled specially
                else:
                    print("  No timeouts remaining!")
                    continue
            elif choice == 'G':
                # Fall through to regular play selection
                break
            else:
                print("  Enter P (Punt), F (Field Goal), G (Go for it), or T (Timeout)")

        print("\n  Select your play to go for it:")

    # Show running plays
    print("  RUNNING PLAYS:")
    for key in ['1', '2', '3', '4']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    # Show passing plays
    print("\n  PASSING PLAYS:")
    for key in ['5', '6', '7', '8', '9']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    # Show special plays
    print("\n  SPECIAL PLAYS:")
    print(f"    [Q] {'QB Sneak':15} - Sneak for 1 yard (defense can't respond)")
    print(f"    [H] {'Hail Mary':15} - Desperation pass (end of half only)")
    print(f"    [S] {'Spike Ball':15} - Stop clock, waste down (saves 20 sec)")
    print(f"    [K] {'QB Kneel':15} - Run out clock (-2 yards, 40 sec)")

    # Show FG/Punt options on non-4th down (for strategic kicks or time pressure)
    if state.down < 4:
        fg_distance = 100 - state.ball_position + 17
        print("\n  SPECIAL TEAMS (early kick options):")
        print(f"    [F] {'Field Goal':15} - {fg_distance}-yard attempt")
        print(f"    [P] {'Punt':15} - Kick the ball away")

    # Show No Huddle toggle option and timeout
    print("\n  OPTIONS:")
    if no_huddle:
        print("    [N] EXIT No Huddle    - Return to normal offense")
    else:
        print("    [N] No Huddle         - Hurry-up offense (saves time, penalty risk)")
    print(f"    [T] Call Timeout      - Stop clock after this play ({state.offense_timeouts} remaining)")
    print("    [/] Stats             - View current game statistics")
    print("    Add '+' for Out of Bounds (e.g., '5+' = stops clock, costs 5 yards)")
    print("    Add '-' for In Bounds (e.g., '5-' = keeps clock running, costs 5 yards)")

    # Suggest a default play based on situation and team strengths
    team_strength = analyze_team_strength(state.possession_team.offense)

    if state.yards_to_go <= 2:
        # Short yardage - always recommend run
        default_play = '1'  # Line Plunge for short yardage
        default_name = 'Line Plunge'
    elif state.yards_to_go >= 8:
        # Long yardage - pass is usually best, but consider team strength
        default_play = '7'  # Medium Pass for long yardage
        default_name = 'Medium Pass'
    elif state.down == 1:
        # First down with medium distance - recommend based on team strength
        if team_strength == 'run':
            default_play = '3'  # End Run for run-heavy teams
            default_name = 'End Run'
        elif team_strength == 'pass':
            default_play = '7'  # Medium Pass for pass-heavy teams
            default_name = 'Medium Pass'
        else:
            # Balanced team - mix it up randomly
            if random.random() < 0.5:
                default_play = '3'
                default_name = 'End Run'
            else:
                default_play = '7'
                default_name = 'Medium Pass'
    else:
        # 2nd/3rd down with medium distance
        default_play = '3'  # End Run for medium situations
        default_name = 'End Run'

    print(f"\n  [Enter] = {default_name} (default)")

    while True:
        choice = input("\n  Your play call: ").strip().upper()

        # Handle Enter for default
        if choice == '':
            choice = default_play

        # Check for Out of Bounds (+) or In Bounds (-) modifier
        out_of_bounds = '+' in choice
        in_bounds = '-' in choice
        choice_clean = choice.replace('+', '').replace('-', '').strip()

        # Can't have both modifiers
        if out_of_bounds and in_bounds:
            print("  Cannot use both + and - modifiers!")
            continue

        # Check for timeout
        call_timeout = 'T' in choice_clean
        choice_clean = choice_clean.replace('T', '').strip()

        if call_timeout:
            if state.offense_timeouts <= 0:
                print("  No timeouts remaining!")
                continue
            print("  *** TIMEOUT WILL BE CALLED AFTER THIS PLAY ***")

        if choice_clean in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            play_type, name, _ = OFFENSE_PLAYS[choice_clean]
            if out_of_bounds:
                print(f"  [OUT OF BOUNDS: {name} - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print(f"  [IN BOUNDS: {name} - keeps clock running, costs 5 yards]")
            return play_type, no_huddle, out_of_bounds, in_bounds, call_timeout

        # Special plays (with optional +/- modifier)
        if choice_clean == 'Q':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: QB Sneak - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: QB Sneak - keeps clock running, costs 5 yards]")
            return PlayType.QB_SNEAK, no_huddle, out_of_bounds, in_bounds, call_timeout
        elif choice_clean == 'H':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: Hail Mary - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: Hail Mary - keeps clock running, costs 5 yards]")
            return PlayType.HAIL_MARY, no_huddle, out_of_bounds, in_bounds, call_timeout
        elif choice_clean == 'S':
            # Spike ball doesn't need modifiers - it's already a clock-stopper
            return PlayType.SPIKE_BALL, no_huddle, False, False, call_timeout
        elif choice_clean == 'K':
            # QB Kneel doesn't need modifiers - it's already a clock-killer
            return PlayType.QB_KNEEL, no_huddle, False, False, call_timeout

        # No Huddle toggle
        if choice == 'N':
            new_no_huddle = not no_huddle
            if new_no_huddle:
                print("\n  *** NO HUDDLE OFFENSE ACTIVATED ***")
                print("  Benefits: Previous play counts as 20 sec instead of 40 sec")
                print("  Risks: Penalties may become bad snaps or false starts")
            else:
                print("\n  *** RETURNING TO NORMAL OFFENSE ***")
            return get_human_offense_play(game, new_no_huddle)

        # Stats request
        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return get_human_offense_play(game, no_huddle)

        # Allow P and F on any down (strategic kicks, time pressure, etc.)
        if choice_clean == 'P':
            # Punt cannot use modifiers
            return PlayType.PUNT, no_huddle, False, False, call_timeout
        elif choice_clean == 'F':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: Field Goal - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: Field Goal - keeps clock running, costs 5 yards]")
            return PlayType.FIELD_GOAL, no_huddle, out_of_bounds, in_bounds, call_timeout

        print("  Invalid choice. Enter 1-9, Q, H, S, K, N, T, P, F (add '+'/'-' for OOB/IB)")


def get_human_offense_play_for_conversion(game: PaydirtGameEngine) -> PlayType:
    """Prompt human player to select a play for 2-point conversion."""
    print("  " + "-" * 40)

    # Show running plays
    print("  RUNNING PLAYS:")
    for key in ['1', '2', '3', '4']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    # Show passing plays
    print("\n  PASSING PLAYS:")
    for key in ['5', '6', '7', '8', '9']:
        play_type, name, desc = OFFENSE_PLAYS[key]
        print(f"    [{key}] {name:15} - {desc}")

    while True:
        choice = input("\n  Your 2-point play: ").strip().upper()

        if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            play_type, name, _ = OFFENSE_PLAYS[choice]
            return play_type

        print("  Invalid choice. Enter a number 1-9.")


def cpu_should_go_for_two(game: PaydirtGameEngine, ai: ComputerAI = None) -> bool:
    """
    Determine if CPU should go for 2-point conversion.
    
    Generally kicks extra point (default), but goes for 2 when:
    - Late in game and need 2 points to tie/win
    - Down by 2 (2-point makes it a tie)
    - Down by 5 (TD + 2 = 8, makes it a 3-point game)
    - Down by 8 or 9 (need 2 to have chance to tie with another TD)
    - Up by 1 (2-point makes it a 3-point lead)
    """
    state = game.state

    # Calculate score differential (positive = CPU winning)
    if state.is_home_possession:
        # CPU just scored as home team (TD already added)
        score_diff = state.home_score - state.away_score
    else:
        # CPU just scored as away team
        score_diff = state.away_score - state.home_score

    # Note: TD (6 points) already added, so score_diff reflects post-TD score

    # Late game situations (4th quarter, under 5 minutes)
    late_game = state.quarter == 4 and state.time_remaining < 5.0

    # Very late game (under 2 minutes)
    very_late = state.quarter == 4 and state.time_remaining < 2.0

    # Specific score situations where going for 2 makes sense
    # After TD, if we're now:
    # - Tied (score_diff == 0): Go for 2 to take lead
    # - Down by 2: Go for 2 to tie
    # - Up by 6: Kick to go up 7 (default)
    # - Up by 1: Go for 2 to go up 3 (FG can't tie)
    # - Down by 8: Go for 2 (need 2 TDs, both need 2-pt to tie)

    if very_late:
        # Very late - be aggressive
        if score_diff == 0:
            return True  # Go for 2 to take lead
        if score_diff == -2:
            return True  # Go for 2 to tie
        if score_diff == 1:
            return True  # Go for 2 to go up 3

    if late_game:
        # Late game - consider going for 2 in specific situations
        if score_diff == -2:
            return True  # Down by 2, go for 2 to tie
        if score_diff == -8 or score_diff == -9:
            return True  # Down by 8-9, need 2 to have chance
        if score_diff == 1:
            return True  # Up by 1, go for 2 to go up 3

    # Default: kick the extra point
    return False


def get_kickoff_choice(game: PaydirtGameEngine, is_human_kicking: bool, ai: ComputerAI = None) -> bool:
    """
    Get kickoff choice - regular or onside.
    
    Args:
        game: The game engine
        is_human_kicking: True if human is the kicking team
        ai: Computer AI for CPU decisions
    
    Returns:
        True for onside kick, False for regular kickoff
    """
    if is_human_kicking:
        # Human chooses
        print("\n  *** KICKOFF ***")
        print("  " + "-" * 40)
        print("    [K] Regular kickoff - DEFAULT")
        print("    [O] Onside kick (risky - recover on roll 13-20)")

        choice = input("\n  Your choice (K or O, Enter for regular): ").strip().upper()
        return choice == 'O'
    else:
        # CPU decides - only attempt onside kick in desperation
        return cpu_should_onside_kick(game, ai)


def cpu_should_onside_kick(game: PaydirtGameEngine, ai: ComputerAI = None) -> bool:
    """
    Determine if CPU should attempt an onside kick.
    
    Only attempts onside kick in desperation situations:
    - 4th quarter, trailing, and running out of time
    - Need the ball back to have a chance to win
    """
    state = game.state

    # Calculate score differential (positive = CPU winning)
    # Note: CPU is the kicking team here
    if state.is_home_possession:
        # Home team just scored and will kick
        score_diff = state.home_score - state.away_score
    else:
        # Away team just scored and will kick
        score_diff = state.away_score - state.home_score

    # Only consider onside kick in 4th quarter when trailing
    if state.quarter != 4:
        return False

    if score_diff >= 0:
        return False  # Not trailing, no need for onside

    # Desperation situations
    time_left = state.time_remaining

    # Under 2 minutes and trailing - definitely try onside
    if time_left < 2.0 and score_diff < 0:
        return True

    # Under 5 minutes and trailing by more than one score
    if time_left < 5.0 and score_diff <= -9:
        return True

    return False


def _get_human_defense_play_compact(game: PaydirtGameEngine, state) -> tuple[DefenseType, bool]:
    """Compact defense menu - abbreviated display with '?' for full menu."""
    # Calculate default defense
    if state.yards_to_go <= 2:
        default_def = 'B'
        default_name = 'Short'
    elif state.down >= 3 and state.yards_to_go >= 8:
        default_def = 'E'
        default_name = 'Long Pass'
    elif state.down >= 2 and state.yards_to_go >= 6:
        default_def = 'D'
        default_name = 'Short Pass'
    else:
        default_def = 'A'
        default_name = 'Standard'

    print(f"  DEF: A-F | T,/ | ?=help (Default={default_def}/{default_name})")

    while True:
        choice = input("  > ").strip().upper()

        # Show full menu on '?'
        if choice == '?':
            _show_full_defense_menu(state)
            continue

        # Handle Enter for default
        if choice == '':
            choice = default_def

        call_timeout = 'T' in choice
        choice_clean = choice.replace('T', '').strip()

        if call_timeout and not choice_clean:
            if state.defense_timeouts <= 0:
                print("  No timeouts!")
                continue
            print("  Timeout - now pick defense (A-F):")
            continue

        if call_timeout:
            if state.defense_timeouts <= 0:
                print("  No timeouts!")
                continue

        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return _get_human_defense_play_compact(game, state)

        if choice_clean in DEFENSE_PLAYS:
            def_type, name, _ = DEFENSE_PLAYS[choice_clean]
            print(f"  You called: {name}")
            return def_type, call_timeout

        print("  Invalid. A-F, T, / or ? for help")


def _show_full_defense_menu(state):
    """Display the full defense menu (called from compact mode with '?')."""
    print("\n  DEFENSIVE FORMATION")
    print("  " + "-" * 40)

    if state.yards_to_go <= 2:
        print("  Situation: Short yardage - expect a run")
    elif state.down >= 2 and state.yards_to_go >= 8:
        print("  Situation: Long yardage - expect a pass")
    elif state.down == 4 and state.ball_position >= 55:
        print("  Situation: Field goal range - they may kick")
    elif state.down == 1:
        print("  Situation: First down - balanced attack likely")

    print()
    for key in ['A', 'B', 'C', 'D', 'E', 'F']:
        def_type, name, desc = DEFENSE_PLAYS[key]
        print(f"    [{key}] {name:20} - {desc}")

    print("\n    [T] Call Timeout      - Stop clock after this play")
    print("    [/] Stats             - View current game statistics")
    print()


def get_human_defense_play(game: PaydirtGameEngine) -> tuple[DefenseType, bool]:
    """
    Prompt human player to select a defensive formation.

    Returns:
        Tuple of (DefenseType, call_timeout)
    """
    state = game.state

    # In compact mode, show abbreviated menu
    if COMPACT_MODE:
        return _get_human_defense_play_compact(game, state)

    print("\n  DEFENSIVE FORMATION")
    print("  " + "-" * 40)

    # Provide situational advice
    if state.yards_to_go <= 2:
        print("  Situation: Short yardage - expect a run")
    elif state.down >= 2 and state.yards_to_go >= 8:
        # Long yardage only applies on 2nd down or later (1st and 10 is standard)
        print("  Situation: Long yardage - expect a pass")
    elif state.down == 4 and state.ball_position >= 55:
        print("  Situation: Field goal range - they may kick")
    elif state.down == 1:
        print("  Situation: First down - balanced attack likely")

    print()
    for key in ['A', 'B', 'C', 'D', 'E', 'F']:
        def_type, name, desc = DEFENSE_PLAYS[key]
        print(f"    [{key}] {name:20} - {desc}")

    print(f"\n    [T] Call Timeout      - Stop clock after this play ({state.defense_timeouts} remaining)")
    print("    [/] Stats             - View current game statistics")

    # Suggest a default defense based on situation
    # Consider both down and distance for realistic defaults
    if state.yards_to_go <= 2:
        default_def = 'B'  # Short Yardage
        default_name = 'Short Yardage (B)'
    elif state.down >= 3 and state.yards_to_go >= 8:
        # 3rd/4th and long - expect a pass
        default_def = 'E'  # Long Pass
        default_name = 'Long Pass (E)'
    elif state.down >= 2 and state.yards_to_go >= 6:
        # 2nd/3rd and medium-long - short pass defense
        default_def = 'D'  # Short Pass
        default_name = 'Short Pass (D)'
    else:
        # 1st down or short/medium yardage - balanced defense
        default_def = 'A'  # Standard
        default_name = 'Standard (A)'

    print(f"\n  [Enter] = {default_name} (default)")

    while True:
        choice = input("\n  Your defensive call: ").strip().upper()

        # Handle Enter for default
        if choice == '':
            choice = default_def

        # Check for timeout modifier
        call_timeout = 'T' in choice
        choice_clean = choice.replace('T', '').strip()

        if call_timeout and not choice_clean:
            # Just 'T' alone - need to also pick a defense
            if state.defense_timeouts <= 0:
                print("  No timeouts remaining!")
                continue
            print("  *** TIMEOUT WILL BE CALLED AFTER THIS PLAY ***")
            print("  Now select your defensive formation (A-F):")
            continue

        if call_timeout:
            if state.defense_timeouts <= 0:
                print("  No timeouts remaining!")
                continue
            print("  *** TIMEOUT WILL BE CALLED AFTER THIS PLAY ***")

        # Stats request
        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return get_human_defense_play(game)

        if choice_clean in DEFENSE_PLAYS:
            def_type, name, _ = DEFENSE_PLAYS[choice_clean]
            return def_type, call_timeout

        print("  Invalid choice. Enter A, B, C, D, E, F, T, or / for stats (add T for timeout, e.g., 'AT')")


def computer_select_offense(game: PaydirtGameEngine, ai: ComputerAI = None) -> PlayType:
    """Computer AI selects an offensive play using situational intelligence."""
    if ai is None:
        ai = ComputerAI(aggression=0.5)
    return ai.select_offense(game)


def computer_select_defense(game: PaydirtGameEngine, ai: ComputerAI = None) -> DefenseType:
    """Computer AI selects a defensive formation using situational intelligence."""
    if ai is None:
        ai = ComputerAI(aggression=0.5)
    return ai.select_defense(game)


def display_play_result(game: PaydirtGameEngine, outcome, play_type: PlayType,
                        def_type: DefenseType, human_team: TeamChart,
                        offense_was_home: bool = None):
    """Display the detailed play result with colorful commentary.
    
    Args:
        game: The game engine
        outcome: The play outcome
        play_type: The type of play called
        def_type: The defensive formation
        human_team: The human player's team chart
        offense_was_home: Whether home team was on offense BEFORE the play.
                         This is needed because possession may change during the play
                         (turnover, turnover on downs, punt, etc.)
    """
    state = game.state

    # If a penalty was applied, show simplified penalty result instead of play details
    if getattr(outcome, 'penalty_applied', False):
        if COMPACT_MODE:
            first_down_marker = " FIRST DOWN!" if outcome.first_down else ""
            print(f"► PENALTY: {outcome.description}{first_down_marker} → {outcome.field_position_after}")
        else:
            print("\n" + "=" * 70)
            print("  PENALTY ENFORCED")
            print("=" * 70)
            print(f"\n  {outcome.description}")
            if outcome.first_down:
                print("  >> FIRST DOWN!")
            print(f"\n  Ball spotted at {outcome.field_position_after}")
        return

    # Determine who was on offense during the play
    # Use the passed-in offense_was_home if available, otherwise try to infer from outcome
    if offense_was_home is not None:
        # Use the explicitly passed value (most reliable)
        if offense_was_home:
            off_team = state.home_chart.peripheral.short_name
            def_team = state.away_chart.peripheral.short_name
            off_chart = state.home_chart
            def_chart = state.away_chart
        else:
            off_team = state.away_chart.peripheral.short_name
            def_team = state.home_chart.peripheral.short_name
            off_chart = state.away_chart
            def_chart = state.home_chart
    elif outcome.turnover:
        # After turnover, current possession is the recovering team (original defense)
        # So original offense is the OPPOSITE of current possession
        if state.is_home_possession:
            # Home now has ball = home was defense, away was offense
            off_team = state.away_chart.peripheral.short_name
            def_team = state.home_chart.peripheral.short_name
            off_chart = state.away_chart
            def_chart = state.home_chart
        else:
            # Away now has ball = away was defense, home was offense
            off_team = state.home_chart.peripheral.short_name
            def_team = state.away_chart.peripheral.short_name
            off_chart = state.home_chart
            def_chart = state.away_chart
    else:
        # No turnover - current possession is still the offense
        if state.is_home_possession:
            off_team = state.home_chart.peripheral.short_name
            def_team = state.away_chart.peripheral.short_name
            off_chart = state.home_chart
            def_chart = state.away_chart
        else:
            off_team = state.away_chart.peripheral.short_name
            def_team = state.home_chart.peripheral.short_name
            off_chart = state.away_chart
            def_chart = state.home_chart

    # Handle special teams plays (punt, field goal, kickoff) differently
    if play_type == PlayType.PUNT:
        # Get punter name from roster
        punter = None
        try:
            roster = get_roster(off_chart.full_name, off_chart.team_dir)
            if roster and roster.p:
                punter = roster.p[0]
        except Exception:
            pass

        if COMPACT_MODE:
            # Compact punt display with dice details
            td_marker = " ★ TOUCHDOWN!" if outcome.touchdown else ""
            punter_str = f" ({punter})" if punter else ""
            print(f"► PUNT{punter_str}: {outcome.description}{td_marker}")
            # Show dice roll info if available
            dice_roll = outcome.result.dice_roll if outcome.result else "?"
            chart_result = outcome.result.raw_result if outcome.result else "?"
            print(f"  (Roll: {dice_roll} → \"{chart_result}\")")
            return

        print("\n" + "=" * 70)
        print("  PUNT")
        print("=" * 70)

        # Parse the description to provide better commentary
        desc = outcome.description
        if "Touchback" in desc:
            print(f"\n  {desc}")
            print("  >> Ball placed at the 20-yard line.")
        elif "fair catch" in desc.lower():
            print(f"\n  {desc}")
            print("  >> Fair catch signaled - no return.")
        elif "downed" in desc.lower():
            print(f"\n  {desc}")
            print("  >> Ball downed by the coverage team.")
        elif "out of bounds" in desc.lower():
            print(f"\n  {desc}")
            print("  >> Punt goes out of bounds.")
        elif "returned" in desc.lower():
            print(f"\n  {desc}")
            if outcome.touchdown:
                print("  >> PUNT RETURN TOUCHDOWN!")
        elif "BLOCKED" in desc.upper():
            print(f"\n  {desc}")
            print("  >> BLOCKED PUNT!")
        elif "FUMBLE" in desc.upper():
            print(f"\n  {desc}")
            print("  >> FUMBLE on the return! Kicking team recovers!")
        else:
            print(f"\n  {desc}")
        return

    if play_type == PlayType.FIELD_GOAL:
        # Get kicker name from roster
        kicker = "The kicker"
        try:
            roster = get_roster(off_chart.full_name, off_chart.team_dir)
            if roster and roster.k:
                kicker = roster.k[0]  # Use first kicker in list
        except Exception:
            pass

        # Parse the result to show details like other plays
        dice_roll = outcome.result.dice_roll if outcome.result else 0
        chart_result = outcome.result.raw_result if outcome.result else ""

        # Calculate distances for display
        fg_distance_match = re.search(r'(\d+) yards', outcome.description)
        statistical_distance = int(fg_distance_match.group(1)) if fg_distance_match else 0
        distance_to_goal = statistical_distance - 17 if statistical_distance > 17 else 0

        if COMPACT_MODE:
            # Compact field goal display
            if outcome.field_goal_made:
                print(f"► FG {statistical_distance} yards: GOOD! ({kicker})")
            elif "BLOCKED" in outcome.description.upper():
                print(f"► FG {statistical_distance} yards: BLOCKED!")
            else:
                print(f"► FG {statistical_distance} yards: NO GOOD")
            print(f"  (Roll: {dice_roll} → \"{chart_result}\" | Needed: {distance_to_goal} yds)")
            return

        print("\n" + "=" * 70)
        print("  FIELD GOAL ATTEMPT")
        print("=" * 70)

        print(f"\n  {kicker} lines up for the {statistical_distance}-yard attempt...")
        print(f"  Dice Roll: {dice_roll}")
        print(f"  Chart Result: {chart_result}")
        print(f"  Distance needed: {distance_to_goal} yards to goal line")

        if outcome.field_goal_made:
            print(f"\n  >> {kicker} kicks it... IT'S GOOD!")
            print("  >>> FIELD GOAL IS GOOD!")
        elif "BLOCKED" in outcome.description.upper():
            print(f"\n  >> BLOCKED! {outcome.description}")
        elif "FUMBLE" in outcome.description.upper():
            print(f"\n  >> {outcome.description}")
        else:
            # Miss - show what the kick achieved vs what was needed
            reached_match = re.search(r'reached (\d+)', outcome.description)
            if reached_match:
                reached = int(reached_match.group(1))
                print(f"\n  >> {kicker} kicks it... NO GOOD! Short!")
                print(f"  Kick reached {reached} yards, needed {distance_to_goal}")
            else:
                print(f"\n  >> {kicker} kicks it... NO GOOD!")
        return

    if play_type == PlayType.KICKOFF:
        if COMPACT_MODE:
            print(f"► KICKOFF: {outcome.description}")
            # Show dice roll info if available
            if outcome.result:
                print(f"  (Roll: {outcome.result.dice_roll} → \"{outcome.result.raw_result}\")")
            return
        print("\n" + "=" * 70)
        print("  KICKOFF")
        print("=" * 70)
        print(f"\n  {outcome.description}")
        return

    # Get rosters for commentary (try team directory first, fall back to hardcoded)
    off_roster = get_roster(off_chart.full_name, off_chart.team_dir)
    def_roster = get_roster(def_chart.full_name, def_chart.team_dir)
    commentary = Commentary(off_roster, def_roster, off_team, def_team)

    play_name = play_type.value.replace('_', ' ').title()
    def_name = def_type.value.replace('_', ' ').title()

    # Extract dice info from description (try both outcome.description and outcome.result.description)
    desc_to_search = outcome.description or outcome.result.description or ""
    off_match = re.search(r'Off: (B\d\+W\d\+W\d=\d+)', desc_to_search)
    def_match = re.search(r'Def: R(\d)\+G(\d)=(\d)', desc_to_search)

    # Priority resolution for display
    off_cat, _ = categorize_result(outcome.result.raw_result)
    def_cat, _ = categorize_result(outcome.result.defense_modifier)
    combined = apply_priority_chart(outcome.result.raw_result, outcome.result.defense_modifier,
                                    is_passing_play=is_passing_play(play_type))

    if COMPACT_MODE:
        # Build compact result string
        result_str = ""
        special_marker = ""

        if outcome.result.result_type == ResultType.INCOMPLETE:
            result_str = "Incomplete"
        elif outcome.result.result_type == ResultType.INTERCEPTION:
            result_str = "INTERCEPTED!"
            special_marker = " ★ TURNOVER!"
            if outcome.touchdown:
                special_marker = " ★ PICK SIX!"
        elif outcome.result.result_type == ResultType.FUMBLE:
            if outcome.turnover:
                result_str = "FUMBLE - Loss!"
                special_marker = " ★ TURNOVER!"
            else:
                result_str = "FUMBLE - Recovered"
        elif outcome.result.result_type == ResultType.BREAKAWAY:
            result_str = f"BREAKAWAY +{outcome.yards_gained}"
        elif outcome.result.result_type == ResultType.SACK:
            result_str = f"SACKED -{abs(outcome.yards_gained)}"
        elif outcome.yards_gained > 0:
            result_str = f"+{outcome.yards_gained}"
        elif outcome.yards_gained < 0:
            result_str = f"{outcome.yards_gained}"
        else:
            result_str = "No gain"

        if outcome.touchdown:
            special_marker = " ★ TOUCHDOWN!"
        elif outcome.first_down and not outcome.turnover:
            special_marker = " FIRST DOWN!"
        elif outcome.safety:
            special_marker = " ★ SAFETY!"

        # Generate commentary
        is_breakaway = outcome.result.result_type == ResultType.BREAKAWAY
        skip_commentary = (outcome.result.result_type == ResultType.FUMBLE and not outcome.turnover)
        is_check_down = False
        if outcome.result.defense_modifier:
            def_cat_check, _ = categorize_result(outcome.result.defense_modifier)
            is_check_down = (def_cat_check == ResultCategory.PARENS_NUMBER)

        comment = ""
        if not skip_commentary:
            comment = commentary.generate(
                play_type=play_type,
                result_type=outcome.result.result_type,
                yards=outcome.yards_gained,
                is_first_down=outcome.first_down,
                is_touchdown=outcome.touchdown,
                is_breakaway=is_breakaway,
                is_check_down=is_check_down
            )

        # Line 1: Result with play type and commentary
        if comment:
            print(f"► {play_name.upper()}: {result_str} - {comment}{special_marker}")
        else:
            print(f"► {play_name.upper()}: {result_str}{special_marker}")

        # Line 2: Dice details (condensed)
        def_row = def_match.group(3) if def_match else "?"
        print(f"  (O:{outcome.result.dice_roll}→\"{outcome.result.raw_result}\" | D:{def_row}→\"{outcome.result.defense_modifier}\" | {combined.priority.value})")
        return

    # Verbose mode display
    print("\n" + "=" * 70)
    print(f"  THE PLAY: {off_team} {play_name} vs {def_name}")
    print("=" * 70)

    # Offensive roll
    print(f"\n  Offensive Roll ({off_team}): {outcome.result.dice_roll}")
    if off_match:
        print(f"  Dice: {off_match.group(1)}")
    print(f"  Offense Chart Result: \"{outcome.result.raw_result}\"")

    # Defensive roll
    if def_match:
        r, g, row = def_match.groups()
        print(f"\n  Defensive Roll ({def_team}): R{r}+G{g} = Row {row}")
    print(f"  Defense Chart Result: \"{outcome.result.defense_modifier}\"")

    print(f"\n  Priority Chart: [{off_cat.value}] vs [{def_cat.value}]")
    print(f"  Resolution: {combined.priority.value} - {combined.description}")

    # Show offsetting penalties if they occurred (play is nullified)
    if outcome.penalty_choice and outcome.penalty_choice.offsetting:
        print("\n  *** OFFSETTING PENALTIES ***")
        for opt in outcome.penalty_choice.penalty_options:
            print(f"    - {opt.description}")
        print("  Play is nullified - down will be replayed")

    # Final result
    print("\n  " + "-" * 50)
    if outcome.result.result_type == ResultType.INCOMPLETE:
        print("  RESULT: Incomplete pass")
    elif outcome.result.result_type == ResultType.INTERCEPTION:
        # Show detailed interception info per official rules
        int_spot = outcome.result.int_spot if hasattr(outcome.result, 'int_spot') else 0
        int_return = outcome.result.int_return_yards if hasattr(outcome.result, 'int_return_yards') else 0
        int_dice = outcome.result.int_return_dice if hasattr(outcome.result, 'int_return_dice') else 0

        # Convert raw int_spot to proper field position string
        # int_spot is from offense's perspective (yards from their own goal)
        if int_spot <= 50:
            int_pos_str = f"{off_team} {int_spot}"
        else:
            int_pos_str = f"{def_team} {100 - int_spot}"

        print(f"  RESULT: INTERCEPTED at the {int_pos_str} yard line!")
        print(f"  Return roll: {int_dice} -> {int_return} yard return")
        if outcome.touchdown:
            print("  >>> PICK SIX! Returned for a TOUCHDOWN!")
    elif outcome.result.result_type == ResultType.FUMBLE:
        # Show detailed fumble info per official rules
        fumble_spot = outcome.result.fumble_spot if hasattr(outcome.result, 'fumble_spot') else 0
        recovery_roll = outcome.result.fumble_recovery_roll if hasattr(outcome.result, 'fumble_recovery_roll') else 0
        recovered = outcome.result.fumble_recovered if hasattr(outcome.result, 'fumble_recovered') else False
        return_yards = outcome.result.fumble_return_yards if hasattr(outcome.result, 'fumble_return_yards') else 0
        return_dice = outcome.result.fumble_return_dice if hasattr(outcome.result, 'fumble_return_dice') else 0

        # Convert raw fumble_spot to proper field position string
        # fumble_spot is from offense's perspective (yards from their own goal)
        if fumble_spot <= 50:
            fumble_pos_str = f"{off_team} {fumble_spot}"
        else:
            fumble_pos_str = f"{def_team} {100 - fumble_spot}"

        print(f"  RESULT: FUMBLE at the {fumble_pos_str} yard line!")
        print(f"  Recovery roll: {recovery_roll}")
        if recovered:
            print("  >>> OFFENSE RECOVERS!")
            if return_yards > 0:
                print(f"  Return: {return_yards} yards (roll: {return_dice})")
        else:
            print("  >>> DEFENSE RECOVERS - TURNOVER!")
            if return_yards > 0:
                print(f"  Return: {return_yards} yards (roll: {return_dice})")
        if outcome.touchdown:
            print("  >>> FUMBLE RETURN TOUCHDOWN!")
    elif outcome.result.result_type == ResultType.BREAKAWAY:
        print(f"  RESULT: BREAKAWAY! {outcome.yards_gained} yards!")
    elif outcome.result.result_type == ResultType.SACK:
        print(f"  RESULT: SACKED for {abs(outcome.yards_gained)} yard loss!")
    elif outcome.result.result_type == ResultType.QB_SCRAMBLE:
        if outcome.yards_gained >= 0:
            print(f"  RESULT: QB scrambles for {outcome.yards_gained} yards")
        else:
            print(f"  RESULT: SACKED for {abs(outcome.yards_gained)} yard loss!")
    elif outcome.result.result_type == ResultType.PENALTY_OFFENSE:
        print(f"  RESULT: OFFENSIVE PENALTY - {abs(outcome.yards_gained)} yards")
    elif outcome.result.result_type == ResultType.PENALTY_DEFENSE:
        # Show the full penalty description which includes the type (holding, personal foul, etc.)
        print(f"  RESULT: {outcome.description}")
    elif outcome.result.result_type == ResultType.PASS_INTERFERENCE:
        print(f"  RESULT: PASS INTERFERENCE - {outcome.yards_gained} yards")
    else:
        # Check for offsetting penalties (play nullified)
        if outcome.penalty_choice and outcome.penalty_choice.offsetting:
            print("  RESULT: OFFSETTING PENALTIES - Down replayed")
        elif outcome.yards_gained > 0:
            print(f"  RESULT: Gain of {outcome.yards_gained} yards")
        elif outcome.yards_gained < 0:
            print(f"  RESULT: Loss of {abs(outcome.yards_gained)} yards")
        else:
            print("  RESULT: No gain")

    # Generate and display colorful commentary
    # Skip fumble commentary if offense recovered (already shown in detailed display)
    is_breakaway = outcome.result.result_type == ResultType.BREAKAWAY
    skip_commentary = (outcome.result.result_type == ResultType.FUMBLE and not outcome.turnover)

    # Check if defense limited the gain with parentheses result
    is_check_down = False
    if outcome.result.defense_modifier:
        def_cat, _ = categorize_result(outcome.result.defense_modifier)
        is_check_down = (def_cat == ResultCategory.PARENS_NUMBER)

    if not skip_commentary:
        comment = commentary.generate(
            play_type=play_type,
            result_type=outcome.result.result_type,
            yards=outcome.yards_gained,
            is_first_down=outcome.first_down,
            is_touchdown=outcome.touchdown,
            is_breakaway=is_breakaway,
            is_check_down=is_check_down
        )
        if comment:
            print(f"\n  >> {comment}")

    # Special outcomes
    if outcome.first_down and not outcome.touchdown:
        print("  >>> FIRST DOWN!")
    if outcome.turnover:
        print(f"  >>> TURNOVER! {def_team} takes over!")
    if outcome.touchdown:
        print(f"  >>> TOUCHDOWN {off_team}!")
    if outcome.safety:
        print(f"  >>> SAFETY! {def_team} scores 2 points!")


def handle_penalty_decision(game: PaydirtGameEngine, outcome, is_human_offense: bool,
                            human_is_home: bool):
    """
    Handle the penalty decision when a penalty occurred.
    
    Per Paydirt rules, the offended team may accept either:
    - The result of the play (down counts)
    - The penalty yardage (down replayed)
    
    Args:
        game: The game engine
        outcome: PlayOutcome with pending_penalty_decision=True
        is_human_offense: Whether the human is on offense
        human_is_home: Whether the human is the home team
    
    Returns:
        Updated PlayOutcome after the decision is applied
    """
    penalty_choice = outcome.penalty_choice

    # Determine who is the offended team and if human decides
    offended_is_offense = penalty_choice.offended_team == "offense"
    human_decides = (offended_is_offense and is_human_offense) or \
                   (not offended_is_offense and not is_human_offense)

    # Display penalty information
    print("\n" + "=" * 70)
    print("  *** PENALTY ON THE PLAY ***")
    print("=" * 70)

    # Show reroll log if there were rerolls
    if penalty_choice.reroll_log:
        print("\n  Penalty Reroll Log:")
        for log_entry in penalty_choice.reroll_log:
            print(f"    {log_entry}")

    # Filter penalty options to only show those that benefit the offended team
    # This is used for both display and decision making
    if offended_is_offense:
        filtered_penalties = [opt for opt in penalty_choice.penalty_options
                              if opt.penalty_type in ["DEF", "PI"]]
    else:
        filtered_penalties = [opt for opt in penalty_choice.penalty_options
                              if opt.penalty_type == "OFF"]

    # Show penalty options
    print(f"\n  Penalty Options ({penalty_choice.offended_team.upper()} is offended):")
    for i, opt in enumerate(filtered_penalties):
        auto_first = " + automatic first down" if opt.auto_first_down else ""
        print(f"    [{i+1}] {opt.description}{auto_first}")

    # Show play result with projected down/distance
    play_result = penalty_choice.play_result
    print("\n  Play Result (if accepted, down counts):")
    print(f"    {play_result.description}")
    if play_result.turnover:
        print("    ** TURNOVER **")
    elif play_result.touchdown:
        print("    ** TOUCHDOWN **")
    else:
        # Calculate what the next down/distance would be
        yards_gained = play_result.yards
        current_down = game.state.down
        yards_to_go = game.state.yards_to_go

        # Check if play would result in touchdown (ball crosses goal line at 100)
        new_position = game.state.ball_position + yards_gained
        if new_position >= 100:
            print("    -> TOUCHDOWN!")
        elif yards_gained >= yards_to_go:
            print("    -> FIRST DOWN")
        elif current_down < 4:
            next_down = current_down + 1
            next_ytg = yards_to_go - yards_gained
            down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
            print(f"    -> {next_down}{down_suffix[next_down]} and {next_ytg}")

    if human_decides:
        # Human makes the decision
        print(f"\n  You ({penalty_choice.offended_team.upper()}) may choose:")

        # Show play result option with outcome details
        yards_gained = play_result.yards
        play_new_pos = game.state.ball_position + yards_gained

        # Check for touchdown first (ball crosses goal line at 100)
        if play_result.touchdown or play_new_pos >= 100:
            play_outcome_str = "TOUCHDOWN!"
            play_field_str = "end zone"
        elif play_result.turnover:
            play_outcome_str = "TURNOVER"
            play_new_pos = max(1, min(99, play_new_pos))
            if play_new_pos <= 50:
                play_field_str = f"own {play_new_pos}"
            else:
                play_field_str = f"opp {100 - play_new_pos}"
        else:
            play_new_pos = max(1, min(99, play_new_pos))
            if play_new_pos <= 50:
                play_field_str = f"own {play_new_pos}"
            else:
                play_field_str = f"opp {100 - play_new_pos}"

            if yards_gained >= game.state.yards_to_go:
                play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
            elif yards_gained > 0:
                next_down = game.state.down + 1
                next_ytg = game.state.yards_to_go - yards_gained
                down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
                play_outcome_str = f"{yards_gained} yards -> {next_down}{down_suffix[next_down]} and {next_ytg}"
            elif yards_gained == 0:
                next_down = game.state.down + 1
                down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
                play_outcome_str = f"No gain -> {next_down}{down_suffix[next_down]} and {game.state.yards_to_go}"
            else:
                next_down = game.state.down + 1
                next_ytg = game.state.yards_to_go - yards_gained  # yards_gained is negative
                down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
                play_outcome_str = f"Loss of {abs(yards_gained)} -> {next_down}{down_suffix[next_down]} and {next_ytg}"

        # Option 0 is always the play result
        print(f"    [0] Accept PLAY result: {play_outcome_str} at {play_field_str}")

        # Show penalty options with projected field position (use filtered_penalties from above)
        for i, opt in enumerate(filtered_penalties):
            # Calculate where ball would be after penalty
            # Apply half-distance rule (except for PI)
            if opt.penalty_type == "PI":
                # PI is exempt from half-distance rule
                adjusted_yards = opt.yards
            else:
                is_offensive_penalty = opt.penalty_type == "OFF"
                adjusted_yards = apply_half_distance_rule(
                    opt.yards, game.state.ball_position, is_offensive_penalty
                )

            if opt.penalty_type in ["DEF", "PI"]:
                # Defensive penalty - offense gains yards
                pen_new_pos = game.state.ball_position + adjusted_yards
            else:
                # Offensive penalty - offense loses yards
                pen_new_pos = game.state.ball_position - adjusted_yards
            pen_new_pos = max(1, min(99, pen_new_pos))

            if pen_new_pos <= 50:
                pen_field_str = f"own {pen_new_pos}"
            else:
                pen_field_str = f"opp {100 - pen_new_pos}"

            # Determine down/distance after penalty (use adjusted_yards for half-distance)
            if opt.auto_first_down:
                pen_down_str = "1st and 10"
            elif opt.penalty_type in ["DEF", "PI"]:
                # Defensive penalty - offense gains yards, reduces yards to go
                if adjusted_yards >= game.state.yards_to_go:
                    pen_down_str = "1st and 10"
                else:
                    pen_down_str = f"{game.state.down}{['st','nd','rd','th'][min(game.state.down-1,3)]} and {max(1, game.state.yards_to_go - adjusted_yards)}"
            else:
                # Offensive penalty - offense loses yards, increases yards to go
                pen_down_str = f"{game.state.down}{['st','nd','rd','th'][min(game.state.down-1,3)]} and {game.state.yards_to_go + adjusted_yards}"

            # Show half-distance note if penalty was reduced
            half_dist_note = ""
            if adjusted_yards != opt.yards:
                half_dist_note = f" (half-distance: {adjusted_yards} yds)"
            print(f"    [{i+1}] Accept PENALTY: {opt.description}{half_dist_note} -> {pen_down_str} at {pen_field_str}")

        while True:
            choice = input("\n  Your choice (0 for play, or penalty number): ").strip()

            if choice == '0' or choice == '':
                # Accept play result - announce like NFL refs
                penalty_desc = filtered_penalties[0].description if filtered_penalties else "penalty"
                print(f"\n  >> {penalty_desc.upper()} - DECLINED. Result of the play stands.")
                return game.apply_penalty_decision(outcome, accept_play=True)
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(filtered_penalties):
                    opt = filtered_penalties[idx]
                    # Find the original index in penalty_options for apply_penalty_decision
                    original_idx = penalty_choice.penalty_options.index(opt)
                    print(f"\n  >> Accepting penalty: {opt.description}")
                    return game.apply_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)
                else:
                    print("  Invalid choice. Try again.")
            else:
                print("  Invalid choice. Enter P for play or a penalty number.")
    else:
        # CPU makes the decision - use simple logic
        # Accept penalty if it's better for the offended team
        play_yards = play_result.yards
        play_turnover = play_result.turnover
        play_td = play_result.touchdown

        # If play resulted in turnover or negative yards, likely accept penalty
        # If play resulted in TD, likely accept play
        accept_play = True
        best_penalty_idx = 0

        if play_td:
            # Always accept TD
            accept_play = True
        elif play_turnover:
            # Always decline turnover, take penalty
            accept_play = False
        elif offended_is_offense:
            # Offense is offended (defensive penalty)
            # Accept penalty if it gives more yards or first down
            best_penalty = filtered_penalties[0] if filtered_penalties else None
            if best_penalty:
                if best_penalty.auto_first_down:
                    accept_play = False  # Take the first down
                elif best_penalty.yards > play_yards:
                    accept_play = False  # Penalty gives more yards
        else:
            # Defense is offended (offensive penalty)
            # Accept penalty if play gained yards
            if play_yards > 0:
                accept_play = False  # Take back the yards

        # Get CPU team name for display
        # If human is offense, CPU is defense; if human is defense, CPU is offense
        cpu_team = game.state.defense_team.peripheral.short_name if is_human_offense else game.state.possession_team.peripheral.short_name

        if accept_play:
            print(f"\n  >> {cpu_team} accepts play result")
            return game.apply_penalty_decision(outcome, accept_play=True)
        else:
            opt = filtered_penalties[best_penalty_idx]
            # Find the original index in penalty_options for apply_penalty_decision
            original_idx = penalty_choice.penalty_options.index(opt)
            print(f"\n  >> {cpu_team} accepts penalty: {opt.description}")
            return game.apply_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)


def run_interactive_game(difficulty: str = 'medium', compact: bool = False):
    """
    Main interactive game loop.
    
    Args:
        difficulty: CPU difficulty level ('easy', 'medium', 'hard')
                   - easy: CPU aggression 0.3 (conservative)
                   - medium: CPU aggression 0.5 (balanced, default)
                   - hard: CPU aggression 0.7 (aggressive, optimal)
        compact: If True, use compact display mode with less verbose output
    """
    # Set global display mode
    global COMPACT_MODE
    COMPACT_MODE = compact

    # Map difficulty to aggression value
    difficulty_map = {
        'easy': 0.3,
        'medium': 0.5,
        'hard': 0.7
    }
    cpu_aggression = difficulty_map.get(difficulty, 0.5)

    clear_screen()

    print("=" * 70)
    print("  PAYDIRT - Interactive Football Simulation")
    print("=" * 70)
    print()

    # Select teams
    print("Select your team:")
    human_chart = select_team("Available Teams:")
    human_name = human_chart.peripheral.short_name

    print("\nSelect your opponent:")
    cpu_chart = select_team("Available Teams:", exclude=None)
    cpu_name = cpu_chart.peripheral.short_name

    # Home/Away selection
    print("\nDo you want to be Home or Away?")
    print("  [H] Home (kick off first)")
    print("  [A] Away (receive first)")
    print("  [Enter] = Home (default)")

    while True:
        choice = input("\nYour choice: ").strip().upper()
        if choice == '':
            choice = 'H'
        if choice in ['H', 'A']:
            break
        print("Enter H or A")

    if choice == 'H':
        away_chart, home_chart = cpu_chart, human_chart
        human_is_home = True
    else:
        away_chart, home_chart = human_chart, cpu_chart
        human_is_home = False

    # Create game
    game = PaydirtGameEngine(home_chart, away_chart)

    clear_screen()
    print("=" * 70)
    print(f"  {away_chart.full_name}")
    print("  vs")
    print(f"  {home_chart.full_name}")
    print("=" * 70)
    print(f"\n  You are: {human_name} ({'Home' if human_is_home else 'Away'})")
    print(f"  Power Rating: {human_chart.peripheral.power_rating}")
    print(f"\n  Opponent: {cpu_name}")
    print(f"  Power Rating: {cpu_chart.peripheral.power_rating}")

    # Coin flip
    print("\n  " + "-" * 40)
    print("  COIN FLIP")
    print("  " + "-" * 40)

    coin_result = random.choice(['HEADS', 'TAILS'])
    print(f"  The coin lands... {coin_result}!")

    # Human calls the toss
    print("\n  You call the toss:")
    print("    [H] Heads")
    print("    [T] Tails")
    print("  [Enter] = Heads (default)")

    while True:
        call = input("  Your call: ").strip().upper()
        if call == '':
            call = 'H'
        if call in ['H', 'T']:
            break
        print("  Enter H or T")

    human_call = 'HEADS' if call == 'H' else 'TAILS'
    human_won_toss = (human_call == coin_result)

    if human_won_toss:
        print(f"\n  You called {human_call} - YOU WIN THE TOSS!")
        print("\n  What do you want to do?")
        print("    [R] Receive the ball")
        print("    [K] Kick off")
        print("  [Enter] = Receive (default)")

        while True:
            choice = input("  Your choice: ").strip().upper()
            if choice == '':
                choice = 'R'
            if choice in ['R', 'K']:
                break
            print("  Enter R or K")

        human_receives_first = (choice == 'R')
        if human_receives_first:
            print(f"  You elect to RECEIVE. {cpu_name} will kick off.")
        else:
            print(f"  You elect to KICK. {cpu_name} will receive.")
    else:
        print(f"\n  You called {human_call} - {cpu_name} wins the toss!")
        # CPU always elects to receive (simple AI)
        human_receives_first = False
        print(f"  {cpu_name} elects to RECEIVE.")

    # Track who receives at start of 2nd half (opposite of 1st half)

    # Determine who kicks first based on coin flip result
    if human_is_home:
        # Human is home team
        if human_receives_first:
            first_half_kicking_home = False  # Away (CPU) kicks
        else:
            first_half_kicking_home = True   # Home (human) kicks
    else:
        # Human is away team
        if human_receives_first:
            first_half_kicking_home = True   # Home (CPU) kicks
        else:
            first_half_kicking_home = False  # Away (human) kicks

    # Create CPU AI for computer opponent decisions
    cpu_ai = ComputerAI(aggression=cpu_aggression)

    # Display difficulty setting
    difficulty_names = {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'}
    print(f"\n  CPU Difficulty: {difficulty_names.get(difficulty, 'Medium')}")

    input("\n  Press Enter to start the game...")

    # Opening kickoff
    clear_screen()
    print("\n  OPENING KICKOFF")
    print("  " + "-" * 40)

    kicking_team = home_chart.peripheral.short_name if first_half_kicking_home else away_chart.peripheral.short_name
    receiving_team = away_chart.peripheral.short_name if first_half_kicking_home else home_chart.peripheral.short_name

    # Allow kickoff choice (regular or onside) - even on opening kickoff!
    is_human_kicking = (first_half_kicking_home == human_is_home)
    onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

    if onside:
        print(f"\n  {kicking_team} attempts an ONSIDE KICK!")
        outcome = game.onside_kick(kicking_home=first_half_kicking_home)
    else:
        print(f"\n  {kicking_team} kicks off...")
        outcome = game.kickoff(kicking_home=first_half_kicking_home)
    print(f"  {outcome.description}")
    print(f"  {receiving_team} will start at {game.state.field_position_str()}")

    # Main game loop
    play_num = 0
    no_huddle_mode = False  # Track No Huddle offense state
    last_quarter = game.state.quarter  # Track quarter for detecting transitions
    while not game.state.game_over:
        play_num += 1

        # Check if quarter changed (game engine advances quarter automatically in _use_time)
        if game.state.quarter != last_quarter:
            # Quarter changed - handle transitions
            if last_quarter == 2 and game.state.quarter == 3:
                # Halftime - show stats and kickoff to start 3rd quarter
                print("\n  END OF QUARTER 2")
                print("\n" + "=" * 70)
                print("  HALFTIME")
                print("=" * 70)
                display_box_score(game, "HALFTIME STATS")
                input("\n  Press Enter for 2nd half kickoff...")

                # Team that kicked to start the game now receives
                second_half_kicking_home = not first_half_kicking_home
                kicking_team = home_chart.peripheral.short_name if second_half_kicking_home else away_chart.peripheral.short_name
                receiving_team = away_chart.peripheral.short_name if second_half_kicking_home else home_chart.peripheral.short_name

                # Allow kickoff choice at halftime too
                is_human_kicking = (second_half_kicking_home == human_is_home)
                onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

                if onside:
                    print(f"\n  {kicking_team} attempts an ONSIDE KICK to start the 2nd half!")
                    outcome = game.onside_kick(kicking_home=second_half_kicking_home)
                else:
                    print(f"\n  {kicking_team} kicks off to start the 2nd half...")
                    outcome = game.kickoff(kicking_home=second_half_kicking_home)
                print(f"  {outcome.description}")
                print(f"  {receiving_team} will start at {game.state.field_position_str()}")
            elif last_quarter < 4:
                # End of Q1 or Q3 - just announce
                print(f"\n  END OF QUARTER {last_quarter}")

            last_quarter = game.state.quarter

        # Check if quarter ended or overtime needed
        # But first check for untimed down (defensive penalty at 0:00)
        if game.state.time_remaining <= 0 and game.has_untimed_down():
            print("\n  *** UNTIMED DOWN - Defensive penalty at 0:00 ***")
            print("  The quarter cannot end on an accepted defensive penalty.")
            game.clear_untimed_down()
            # Continue to run the untimed play - don't process quarter end yet
            # The play will be run in the normal flow below
        elif game.state.time_remaining <= 0:
            if game.state.is_overtime:
                # End of OT period - game engine handles this
                if game.state.game_over:
                    break
                # If not game over, continue OT
                continue
            elif game.state.quarter == 4:
                # End of Q4 - check for overtime
                if game.needs_overtime():
                    print("\n" + "=" * 70)
                    print("  END OF REGULATION - GAME TIED!")
                    print("=" * 70)
                    display_box_score(game, "END OF REGULATION")

                    # Start overtime
                    ot_msg = game.start_overtime()
                    print(f"\n  {ot_msg}")

                    rules = game.get_overtime_rules()
                    print(f"  Overtime period: {rules.period_length_minutes:.0f} minutes")
                    print(f"  Format: {'Sudden Death' if rules.format.value == 'sudden_death' else 'Modified Sudden Death'}")

                    # OT kickoff
                    kicking_home = not game.state.ot_coin_toss_winner_is_home
                    kicking_team = home_chart.peripheral.short_name if kicking_home else away_chart.peripheral.short_name
                    receiving_team = away_chart.peripheral.short_name if kicking_home else home_chart.peripheral.short_name

                    print(f"\n  {kicking_team} kicks off to start overtime...")
                    outcome = game.kickoff(kicking_home=kicking_home)
                    print(f"  {outcome.description}")
                    print(f"  {receiving_team} will start at {game.state.field_position_str()}")
                    continue
                else:
                    # Game over (not tied)
                    break
            else:
                # Normal quarter change - this path is for Q4 end only now
                # (Q1-Q3 transitions are handled by the quarter change detection above)
                pass

        # Determine if human is on offense or defense
        is_human_offense = (game.state.is_home_possession == human_is_home)

        display_game_status(game, human_chart, is_human_offense)

        # Get play calls
        if is_human_offense:
            # Human on offense
            play_type, no_huddle_mode, out_of_bounds, in_bounds, call_timeout = get_human_offense_play(game, no_huddle_mode)

            # Computer selects defense (hidden)
            def_type = computer_select_defense(game)

            print(f"\n  You called: {play_type.value.replace('_', ' ').title()}")
            print(f"  Defense shows: {def_type.value.replace('_', ' ').title()}")
        else:
            # Human on defense
            # On 4th down, CPU decides FIRST so we know if they're punting/kicking
            # This avoids asking for defensive call when CPU is just going to punt
            call_timeout = False
            out_of_bounds = False
            in_bounds = False

            if game.state.down == 4:
                # CPU makes 4th down decision first
                play_type = computer_select_offense(game, cpu_ai)

                if play_type == PlayType.PUNT:
                    # CPU punts - no defensive call needed
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} punts on 4th and {game.state.yards_to_go}")
                    def_type = DefenseType.STANDARD  # Default, doesn't matter for punt
                elif play_type == PlayType.FIELD_GOAL:
                    # CPU kicks FG - no defensive call needed
                    cpu_team = game.state.possession_team.peripheral.short_name
                    fg_dist = 100 - game.state.ball_position + 17
                    print(f"\n  {cpu_team} attempts a {fg_dist}-yard field goal")
                    def_type = DefenseType.STANDARD  # Default, doesn't matter for FG
                else:
                    # CPU is going for it! Now ask for defensive call
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  *** {cpu_team} is going for it on 4th and {game.state.yards_to_go}! ***")
                    def_type, call_timeout = get_human_defense_play(game)
                    print(f"\n  You called: {def_type.value.replace('_', ' ').title()}")
                    print(f"  Offense runs: {play_type.value.replace('_', ' ').title()}")
            else:
                # Normal down - get defensive call first, then CPU selects offense
                def_type, call_timeout = get_human_defense_play(game)
                play_type = computer_select_offense(game, cpu_ai)

                print(f"\n  You called: {def_type.value.replace('_', ' ').title()}")
                print(f"  Offense runs: {play_type.value.replace('_', ' ').title()}")

        # If timeout is called, save time before play to ensure we can refund properly
        time_before_play = game.state.time_remaining

        # Track who was on offense BEFORE the play (possession may change during play)
        offense_was_home = game.state.is_home_possession

        # Track 2-minute warning state before play
        two_min_warning_before = game.state.two_minute_warning_called

        # Run the play with penalty procedure
        if out_of_bounds:
            print("  [OUT OF BOUNDS DESIGNATION - guarantees 10-sec play, costs 5 yards]")
        elif in_bounds:
            print("  [IN BOUNDS DESIGNATION - keeps clock running, costs 5 yards]")
        outcome = game.run_play_with_penalty_procedure(play_type, def_type,
                                                        out_of_bounds_designation=out_of_bounds,
                                                        in_bounds_designation=in_bounds)

        # Handle pending penalty decision if applicable
        if outcome.pending_penalty_decision and outcome.penalty_choice:
            outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)

        # Display result - pass offense_was_home so we show the correct team even after turnover on downs
        display_play_result(game, outcome, play_type, def_type, human_chart, offense_was_home)

        # Check for 2-minute warning (official timeout, not charged to either team)
        if not two_min_warning_before and game.state.two_minute_warning_called:
            quarter_name = "first half" if game.state.quarter == 2 else "second half"
            print("\n" + "=" * 70)
            print("  *** TWO-MINUTE WARNING ***")
            print(f"  Official timeout - 2:00 remaining in the {quarter_name}")
            print("=" * 70)

        # Process timeout if called (reduces play time to 10 seconds)
        if call_timeout:
            if game.state.use_timeout(human_is_home):
                # With timeout, play only uses 10 seconds (0.167 minutes)
                # Calculate what time should be after a 10-second play
                time_after_timeout = time_before_play - 0.167
                if time_after_timeout < 0:
                    time_after_timeout = 0
                game.state.time_remaining = time_after_timeout
                # Ensure quarter doesn't end prematurely if there was time for the play
                if time_before_play > 0 and game.state.quarter <= 4:
                    game.state.game_over = False
                print(f"\n  *** TIMEOUT - Clock stops at {int(game.state.time_remaining)}:{int((game.state.time_remaining % 1) * 60):02d} ***")

        # Handle field goal made - kickoff after score
        if outcome.field_goal_made:
            print(f"  Score: {game.get_score_str()}")

            input("\n  Press Enter for kickoff...")

            # Kickoff after field goal - offer onside kick option
            kicking_home = game.state.is_home_possession
            is_human_kicking = (kicking_home == human_is_home)

            onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

            if onside:
                print("\n  ONSIDE KICK ATTEMPT!")
                print("  " + "-" * 40)
                outcome = game.onside_kick(kicking_home=kicking_home)
            else:
                print("\n  KICKOFF")
                print("  " + "-" * 40)
                outcome = game.kickoff(kicking_home=kicking_home)
            print(f"  {outcome.description}")
            continue  # Skip to next iteration after kickoff

        # Handle touchdown - offer PAT or 2-point conversion choice
        if outcome.touchdown:
            # Determine if human scored
            human_scored = (is_human_offense)

            # Check if 2-point conversion is allowed (introduced in 1994)
            # Use home team's year to determine era
            team_year = game.state.home_chart.peripheral.year
            two_point_allowed = team_year >= 1994

            if human_scored:
                if two_point_allowed:
                    # Human chooses: kick (default) or go for 2
                    print("\n  *** POINT AFTER TOUCHDOWN ***")
                    print("  " + "-" * 40)
                    print("    [K] Kick extra point (1 point) - DEFAULT")
                    print("    [2] Go for 2-point conversion")

                    choice = input("\n  Your choice (K or 2, Enter for kick): ").strip().upper()

                    if choice == '2':
                        # Human goes for 2 - select a play
                        print("\n  Select play for 2-point conversion:")
                        play_type = get_human_offense_play_for_conversion(game)
                        success, def_points, description = game.attempt_two_point(play_type)
                        print(f"\n  {description}")
                        if def_points > 0:
                            print(f"  Defense scores {def_points} points on the return!")
                    else:
                        # Kick extra point (default)
                        success, description = game.attempt_extra_point()
                        print(f"\n  {description}")
                else:
                    # Pre-1994: only kick option, no prompt needed
                    success, description = game.attempt_extra_point()
                    print(f"\n  {description}")
            else:
                # CPU decides whether to kick or go for 2
                go_for_two = two_point_allowed and cpu_should_go_for_two(game, cpu_ai)

                if go_for_two:
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} elects to go for 2-point conversion!")
                    play_type = cpu_ai.select_offense(game) if cpu_ai else PlayType.LINE_PLUNGE
                    # Use short yardage play for 2-point conversion
                    if play_type in [PlayType.PUNT, PlayType.FIELD_GOAL]:
                        play_type = PlayType.LINE_PLUNGE
                    success, def_points, description = game.attempt_two_point(play_type)
                    print(f"  {description}")
                    if def_points > 0:
                        print(f"  Defense scores {def_points} points on the return!")
                else:
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} kicks the extra point...")
                    success, description = game.attempt_extra_point()
                    print(f"  {description}")

            print(f"  Score: {game.get_score_str()}")

            input("\n  Press Enter for kickoff...")

            # Kickoff after score - offer onside kick option
            kicking_home = game.state.is_home_possession
            is_human_kicking = (kicking_home == human_is_home)

            onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

            if onside:
                print("\n  ONSIDE KICK ATTEMPT!")
                print("  " + "-" * 40)
                outcome = game.onside_kick(kicking_home=kicking_home)
            else:
                print("\n  KICKOFF")
                print("  " + "-" * 40)
                outcome = game.kickoff(kicking_home=kicking_home)
            print(f"  {outcome.description}")
            continue  # Skip to next iteration after kickoff

        # Handle safety - team that gave up safety kicks from their 20
        if outcome.safety:
            print(f"\n  Score: {game.get_score_str()}")

            input("\n  Press Enter for free kick...")

            # The team that gave up the safety kicks from their 20
            # They currently have possession (set up for free kick)
            kicking_home = game.state.is_home_possession
            is_human_kicking = (kicking_home == human_is_home)

            # Offer punt option for free kick (rare but allowed)
            if is_human_kicking:
                print("\n  *** FREE KICK AFTER SAFETY ***")
                print("  " + "-" * 40)
                print("    [K] Kickoff from own 20 - DEFAULT")
                print("    [P] Punt from own 20")
                choice = input("\n  Your choice (K or P, Enter for kickoff): ").strip().upper()
                use_punt = (choice == 'P')
            else:
                # CPU always kicks
                use_punt = False

            print("\n  FREE KICK")
            print("  " + "-" * 40)
            outcome = game.safety_free_kick(use_punt=use_punt)
            print(f"  {outcome.description}")

    # Game over
    print("\n" + "=" * 70)
    print("  GAME OVER")
    print("=" * 70)

    # Determine winner
    if game.state.away_score > game.state.home_score:
        winner = away_chart.peripheral.short_name
    elif game.state.home_score > game.state.away_score:
        winner = home_chart.peripheral.short_name
    else:
        winner = None

    if winner:
        if winner == human_name:
            print("\n  CONGRATULATIONS! YOU WIN!")
        else:
            print(f"\n  {winner} wins!")
    else:
        print("\n  TIE GAME!")

    display_box_score(game, "FINAL STATISTICS")


if __name__ == "__main__":
    run_interactive_game()
