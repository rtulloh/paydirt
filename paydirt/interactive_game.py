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
from .computer_ai import (
    ComputerAI, cpu_should_go_for_two, cpu_should_onside_kick, cpu_should_accept_penalty
)
from .penalty_handler import apply_half_distance_rule
from .commentary import Commentary, get_roster
from .utils import (
    ordinal_suffix, ordinal, format_field_position, format_field_position_with_team,
    format_dice_roll, format_time,
    clamp_ball_position, yards_to_goal, fg_distance
)
from .play_events import EventType
from .save_game import save_game
from .ai_analysis import create_easy_mode_helper

# Global display mode flag (set by run_interactive_game)
COMPACT_MODE = False

# Global AI helper toggle (set by run_interactive_game)
AI_HELPER_ENABLED = False


def analyze_team_strength(offense: OffenseChart) -> str:
    """
    Analyze a team's offensive chart to determine if they favor running or passing.
    
    This is a wrapper function that delegates to ComputerAI.analyze_team_strength().
    
    Returns:
        'run' if team is better at running
        'pass' if team is better at passing
        'balanced' if roughly equal
    """
    return ComputerAI.analyze_team_strength(offense)


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


# format_time is now imported from utils


def get_available_seasons() -> list[str]:
    """Find all available season directories."""
    seasons = []
    seasons_path = Path('seasons')
    if seasons_path.exists():
        for season_dir in sorted(seasons_path.iterdir()):
            if season_dir.is_dir() and season_dir.name.isdigit():
                seasons.append(season_dir.name)
    return seasons


def select_season(prompt: str = "Select Season:") -> str:
    """Let user select a season."""
    seasons = get_available_seasons()
    if not seasons:
        print("No seasons found!")
        raise SystemExit(1)

    print(f"\n{prompt}")
    print("-" * 50)
    for i, season in enumerate(seasons, 1):
        print(f"  {i}. {season}")

    while True:
        try:
            choice = input("\nEnter season number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(seasons):
                selected = seasons[idx]
                print(f"Selected: {selected}")
                return selected
        except ValueError:
            pass
        print("Invalid choice. Please enter a number from the list.")


def get_available_teams(season: Optional[str] = None) -> list[tuple[str, str]]:
    """Find all available team chart directories."""
    teams = []
    seasons_path = Path('seasons')
    if seasons_path.exists():
        season_dirs = [seasons_path / season] if season else sorted(seasons_path.iterdir())
        for season_dir in season_dirs:
            if season_dir.is_dir() and season_dir.name.isdigit():
                for team_dir in sorted(season_dir.iterdir()):
                    if team_dir.is_dir():
                        offense_file_new = team_dir / 'offense.csv'
                        offense_file_old = team_dir / 'OFFENSE-Table 1.csv'
                        if offense_file_new.exists() or offense_file_old.exists():
                            teams.append((str(team_dir), team_dir.name))
    return teams


def select_team(prompt: str, exclude: Optional[str] = None) -> TeamChart:
    """Let user select a team from available teams."""
    selected_season = select_season("Select Season:")
    teams = get_available_teams(selected_season)

    if not teams:
        print(f"No team charts found in {selected_season} season!")
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


    # Field position - use abbreviated team name (e.g., "SF" instead of "SF '83")
    field_pos = format_field_position_with_team(state.ball_position, off_team, def_team)

    # Down and distance string
    ytg = yards_to_goal(state.ball_position)
    # Show "& Goal @ X" when you need a touchdown to convert (yards_to_go >= yards to goal)
    # But don't show "Goal @ 0" - that indicates the ball is already at/past the goal line
    if state.yards_to_go >= ytg and ytg > 0:
        down_str = f"{state.down}{_ordinal(state.down)} & Goal @ {ytg}"
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
        print(f"\nQ{state.quarter} {format_time(state.time_remaining)} | {away_name} {away_score} ({away_to}) - {home_name} {home_score} ({home_to}) | {down_str} @ {field_pos} | {off_team}{you_marker} ball")
    else:
        # Verbose multi-line status
        print("\n" + "=" * 70)
        print(f"  Q{state.quarter} | {format_time(state.time_remaining)} | {game.get_score_str()}")
        print("=" * 70)

        print(f"\n  Ball on: {field_pos}-yard line")
        if ytg <= 10 and state.yards_to_go >= ytg:
            print(f"  Down: {state.down}{_ordinal(state.down)} and Goal")
        else:
            print(f"  Down: {state.down}{_ordinal(state.down)} and {state.yards_to_go}")
        print(f"  Possession: {off_team}{' (YOU)' if is_human_offense else ''}")
        print(f"  Timeouts: {off_team} {state.offense_timeouts} | {def_team} {state.defense_timeouts}")
        print()


# _ordinal is now imported from utils as ordinal_suffix
_ordinal = ordinal_suffix


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


def _get_human_offense_play_compact(game: PaydirtGameEngine, state, no_huddle: bool, easy_helper=None) -> tuple[PlayType, bool, bool, bool, bool, bool]:
    """Compact offense menu - abbreviated display with '?' for full menu."""
    global AI_HELPER_ENABLED
    # Auto-show AI helper if enabled
    if AI_HELPER_ENABLED and easy_helper:
        _show_easy_mode_helper(easy_helper, game, is_offense=True)
    
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

    # Compact prompt - show Z only in easy mode (when easy_helper is available)
    z_option = ",Z" if easy_helper else ""
    if state.down == 4:
        fg_dist = fg_distance(state.ball_position)
        print(f"  *** 4TH DOWN *** P=Punt, F=FG({fg_dist}yd), or go for it (1-9)")
        print(f"  OFF: 1-9,Q,H,S,K,P,F | N,T,/{z_option} | ?=help (Default={default_play}/{default_name})")
    else:
        print(f"  OFF: 1-9,Q,H,S,K,P,F | N,T,/{z_option} | ?=help (Default={default_play}/{default_name})")

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
                print("  No timeouts remaining!")
                continue
            # If user entered just 'T' without a play, prompt for play
            if not choice_clean:
                print("  *** TIMEOUT - Now select your play (e.g., 7T for Med Pass + Timeout) ***")
                continue

        # Check for spike modifier (must be with a play, not standalone)
        call_spike = 'S' in choice_clean
        choice_clean = choice_clean.replace('S', '').strip()

        if call_spike:
            # If user entered just 'S' without a play, they want standalone spike ball
            if not choice_clean:
                call_spike = False  # Reset - this is standalone spike, not modifier
                # Will be handled below by the standalone 'S' check

        # Handle choices
        if choice_clean in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            play_type, name, _ = OFFENSE_PLAYS[choice_clean]
            print(f"  You called: {name}")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return play_type, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike

        if choice_clean == 'Q':
            print("  You called: QB Sneak")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return PlayType.QB_SNEAK, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike
        elif choice_clean == 'H':
            print("  You called: Hail Mary")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return PlayType.HAIL_MARY, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike
        elif choice_clean == 'S':
            print("  You called: Spike Ball")
            return PlayType.SPIKE_BALL, no_huddle, False, False, call_timeout, False
        elif choice_clean == 'K':
            print("  You called: QB Kneel")
            return PlayType.QB_KNEEL, no_huddle, False, False, call_timeout, False
        elif choice_clean == 'P':
            print("  You called: Punt")
            return PlayType.PUNT, no_huddle, False, False, call_timeout, False
        elif choice_clean == 'F':
            print("  You called: Field Goal")
            return PlayType.FIELD_GOAL, no_huddle, out_of_bounds, in_bounds, call_timeout, False

        if choice == 'N':
            new_no_huddle = not no_huddle
            if new_no_huddle:
                print("  No Huddle ON")
            else:
                print("  No Huddle OFF")
            return _get_human_offense_play_compact(game, state, new_no_huddle)

        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return _get_human_offense_play_compact(game, state, no_huddle, easy_helper)

        if choice_clean == 'Z':
            if easy_helper:
                AI_HELPER_ENABLED = not AI_HELPER_ENABLED
                if AI_HELPER_ENABLED:
                    print("\n  *** AI HELPER ENABLED ***")
                    _show_easy_mode_helper(easy_helper, game, is_offense=True)
                else:
                    print("\n  *** AI HELPER DISABLED ***")
                return _get_human_offense_play_compact(game, state, no_huddle, easy_helper)
            else:
                print("  Invalid. 1-9,Q,H,S,K,P,F,N,T,W,/ or ? for help")
                return _get_human_offense_play_compact(game, state, no_huddle, easy_helper)

        if choice_clean == 'W':
            # Save game - return special marker to trigger save in main loop
            return None, no_huddle, False, False, False, False

        print("  Invalid. 1-9,Q,H,S,K,P,F,N,T,W,/ or ? for help")


def _show_full_offense_menu(state, no_huddle: bool):
    """Display the full offense menu (called from compact mode with '?')."""
    print("\n  OFFENSIVE PLAY CALL")
    print("  " + "-" * 40)

    if state.down == 4:
        fg_dist = fg_distance(state.ball_position)
        print("\n  *** 4TH DOWN DECISION ***")
        print("    [P] PUNT              - Kick the ball away")
        if state.ball_position >= 55:
            print(f"    [F] FIELD GOAL        - {fg_dist}-yard attempt")
        else:
            print(f"    [F] Field Goal        - {fg_dist}-yard attempt (Out of range)")
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
        fg_dist = fg_distance(state.ball_position)
        print("\n  SPECIAL TEAMS (early kick options):")
        print(f"    [F] {'Field Goal':15} - {fg_dist}-yard attempt")
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


def get_human_offense_play(game: PaydirtGameEngine, no_huddle: bool = False, easy_helper=None) -> tuple[PlayType, bool, bool, bool, bool, bool]:
    """
    Prompt human player to select an offensive play.
    
    Args:
        game: The game engine
        no_huddle: Whether No Huddle mode is currently active
        easy_helper: Optional EasyModeHelper for suggestions
    
    Returns:
        Tuple of (PlayType, no_huddle_for_next_play, out_of_bounds_designation, in_bounds_designation, call_timeout, call_spike)
    """
    state = game.state

    # Show No Huddle status
    if no_huddle:
        print("\n  *** NO HUDDLE OFFENSE ACTIVE ***")
        print("  (Previous play time reduced, but penalty risks increased)")

    # In compact mode, show abbreviated menu
    if COMPACT_MODE:
        return _get_human_offense_play_compact(game, state, no_huddle, easy_helper)

    print("\n  OFFENSIVE PLAY CALL")
    print("  " + "-" * 40)

    # On 4th down, show special teams options FIRST and prominently
    if state.down == 4:
        print("\n  *** 4TH DOWN DECISION ***")
        print("  " + "-" * 40)

        # Calculate field goal distance
        fg_dist = fg_distance(state.ball_position)

        # Punt option
        print("    [P] PUNT              - Kick the ball away")

        # Field goal option with distance and recommendation
        if state.ball_position >= 55:  # Roughly FG range (45 yards or less)
            if fg_dist <= 35:
                fg_note = "(Good range)"
            elif fg_dist <= 45:
                fg_note = "(Makeable)"
            elif fg_dist <= 55:
                fg_note = "(Long - risky)"
            else:
                fg_note = "(Very long - low %)"
            print(f"    [F] FIELD GOAL        - {fg_dist}-yard attempt {fg_note}")
        else:
            print(f"    [F] Field Goal        - {fg_dist}-yard attempt (Out of range)")

        # Go for it option
        print(f"    [G] GO FOR IT         - Run a play (4th and {state.yards_to_go})")

        # Determine default based on field position
        if state.ball_position <= 40:
            default_4th = 'P'
            default_4th_name = 'Punt'
        elif fg_dist <= 45:
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
                return PlayType.PUNT, no_huddle, False, False, False, False
            elif choice == 'F':
                return PlayType.FIELD_GOAL, no_huddle, False, False, False, False
            elif choice == 'T':
                # Call timeout before the play
                if state.offense_timeouts > 0:
                    print("  *** TIMEOUT CALLED ***")
                    return PlayType.PUNT, no_huddle, False, False, True, False  # Will be handled specially
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
        fg_dist = fg_distance(state.ball_position)
        print("\n  SPECIAL TEAMS (early kick options):")
        print(f"    [F] {'Field Goal':15} - {fg_dist}-yard attempt")
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
    print("    Add 'S' for Spike (e.g., '7S' = pass + spike to stop clock)")

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
            # If user entered just 'T' without a play, prompt for play
            if not choice_clean:
                print("  *** TIMEOUT - Now select your play (e.g., 7T for Med Pass + Timeout) ***")
                continue
            print("  *** TIMEOUT WILL BE CALLED AFTER THIS PLAY ***")

        # Check for spike modifier (must be with a play, not standalone)
        call_spike = 'S' in choice_clean
        choice_clean = choice_clean.replace('S', '').strip()

        if call_spike:
            # If user entered just 'S' without a play, they want standalone spike ball
            if not choice_clean:
                call_spike = False  # Reset - this is standalone spike, not modifier
                # Will be handled below by the standalone 'S' check

        if choice_clean in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            play_type, name, _ = OFFENSE_PLAYS[choice_clean]
            if out_of_bounds:
                print(f"  [OUT OF BOUNDS: {name} - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print(f"  [IN BOUNDS: {name} - keeps clock running, costs 5 yards]")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return play_type, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike

        # Special plays (with optional +/- modifier)
        if choice_clean == 'Q':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: QB Sneak - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: QB Sneak - keeps clock running, costs 5 yards]")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return PlayType.QB_SNEAK, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike
        elif choice_clean == 'H':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: Hail Mary - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: Hail Mary - keeps clock running, costs 5 yards]")
            if call_spike:
                print("  [SPIKE: Stop clock after play, costs a down]")
            return PlayType.HAIL_MARY, no_huddle, out_of_bounds, in_bounds, call_timeout, call_spike
        elif choice_clean == 'S':
            # Spike ball doesn't need modifiers - it's already a clock-stopper
            return PlayType.SPIKE_BALL, no_huddle, False, False, call_timeout, False
        elif choice_clean == 'K':
            # QB Kneel doesn't need modifiers - it's already a clock-killer
            return PlayType.QB_KNEEL, no_huddle, False, False, call_timeout, False

        # No Huddle toggle
        if choice == 'N':
            new_no_huddle = not no_huddle
            if new_no_huddle:
                print("\n  *** NO HUDDLE OFFENSE ACTIVATED ***")
                print("  Benefits: Previous play counts as 20 sec instead of 40 sec")
                print("  Risks: Penalties may become bad snaps or false starts")
            else:
                print("\n  *** RETURNING TO NORMAL OFFENSE ***")
            return get_human_offense_play(game, new_no_huddle, easy_helper)

        # Stats request
        if choice_clean == '/':
            display_box_score(game, "CURRENT STATS")
            return get_human_offense_play(game, no_huddle, easy_helper)

        # Allow P and F on any down (strategic kicks, time pressure, etc.)
        if choice_clean == 'P':
            # Punt cannot use modifiers
            return PlayType.PUNT, no_huddle, False, False, call_timeout, False
        elif choice_clean == 'F':
            if out_of_bounds:
                print("  [OUT OF BOUNDS: Field Goal - guarantees 10-sec, costs 5 yards]")
            elif in_bounds:
                print("  [IN BOUNDS: Field Goal - keeps clock running, costs 5 yards]")
            return PlayType.FIELD_GOAL, no_huddle, out_of_bounds, in_bounds, call_timeout, False

        print("  Invalid choice. Enter 1-9, Q, H, S, K, N, T, P, F (add '+'/'-' for OOB/IB)")


def get_punt_options(game: PaydirtGameEngine) -> tuple[bool, int]:
    """
    Prompt human player for advanced punt options.
    
    Per advanced rules:
    - Short-Drop: If LOS is inside 5-yard line, defenders get Free All-Out Kick Rush,
      all * and † are deleted, minus yardage returns become 0
    - Coffin-Corner: Can subtract yardage from punt before dice roll.
      If 15+ yards subtracted, punt is automatic out of bounds (no return)
    
    Returns:
        Tuple of (short_drop: bool, coffin_corner_yards: int)
    """
    state = game.state
    field_pos = state.ball_position  # 0=own goal, 100=opponent goal
    
    # Short-drop punt is mandatory inside opponent's 5-yard line (position >= 95)
    is_short_drop_mandatory = field_pos >= 95
    is_short_drop_available = field_pos >= 95
    
    # If short-drop is mandatory, return it directly without prompting
    if is_short_drop_mandatory:
        print("\n  >> Short-Drop Punt (mandatory inside 5)")
        print("     Defenders will get Free All-Out Kick Rush")
        return (True, 0)
    
    print("\n  PUNT OPTIONS:")
    print("  " + "-" * 40)
    print("    [1] Normal Punt (default)")
    
    options = ["1", ""]  # Empty string for default
    
    if is_short_drop_available:
        print("    [2] Short-Drop Punt (from inside 5-yard line)")
        print("        - Defenders get Free All-Out Kick Rush")
        print("        - All * and † markers deleted")
        print("        - Minus returns become 0 yards")
        options.append("2")
    else:
        print("    [2] Coffin-Corner Punt (specify yards to subtract)")
        options.append("2")
    
    print(f"\n  Current: Ball at {state.field_position_str()}")
    
    while True:
        choice = input("\n  Select punt option (Enter for 1): ").strip().upper()
        
        # Handle default (just Enter)
        if choice == "":
            choice = "1"
        
        if choice not in options:
            print("  Invalid choice.")
            continue
        
        if choice == "1":
            # Normal punt
            return (False, 0)
        
        if choice == "2":
            if is_short_drop_available:
                # Short-drop punt
                print("\n  >> Short-Drop Punt selected")
                print("     Defenders will get Free All-Out Kick Rush")
                return (True, 0)
            else:
                # Coffin corner - ask how many yards to subtract
                while True:
                    try:
                        yards_str = input("  Yards to subtract (0-25): ").strip()
                        yards = int(yards_str)
                        if 0 <= yards <= 25:
                            break
                        print("  Enter a number between 0 and 25")
                    except ValueError:
                        print("  Enter a valid number")
                
                if yards >= 15:
                    print(f"\n  >> Coffin-Corner Punt: {yards} yards subtracted")
                    print("     Punt will be automatic out of bounds (no return)")
                elif yards > 0:
                    print(f"\n  >> Coffin-Corner Punt: {yards} yards subtracted")
                else:
                    print("\n  >> Normal Punt (0 yards subtracted)")
                
                return (False, yards)
            
            return (False, yards)


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


def _show_easy_mode_helper(helper, game: PaydirtGameEngine, is_offense: bool):
    """Show easy mode AI helper suggestions."""
    state = game.state
    
    if is_offense:
        suggestions = helper.suggest_offense_plays(state.down, state.yards_to_go, 3)
        print("\n  === AI HELPER (Your Best Plays) ===")
        print("  " + "-" * 40)
        for i, s in enumerate(suggestions, 1):
            print(f"    {i}. {s['play']} - {s['success_rate']:.0f}% success, {s['avg_yards']:.1f} avg yards")
        
        # Show tip
        if state.is_home_possession:
            score_diff = state.home_score - state.away_score
        else:
            score_diff = state.away_score - state.home_score
        
        tip = helper.get_situation_tip(state.down, state.yards_to_go, state.quarter, 
                                       state.time_remaining, score_diff)
        if tip:
            print(f"\n  Tip: {tip}")
    else:
        defense = helper.suggest_defense(state.down, state.yards_to_go)
        print("\n  === AI HELPER (Suggested Defense) ===")
        print("  " + "-" * 40)
        defense_names = {
            'A': 'Standard (balanced)',
            'B': 'Short Yardage',
            'C': 'Spread',
            'D': 'Short Pass',
            'E': 'Long Pass',
            'F': 'Blitz',
        }
        print(f"    Recommended: {defense} - {defense_names.get(defense, 'Unknown')}")
        
        # Show warning if any
        warning = helper.warn_danger(state.down, state.yards_to_go)
        if warning:
            print(f"\n  {warning}")


def _get_human_defense_play_compact(game: PaydirtGameEngine, state, easy_helper=None) -> tuple[DefenseType, bool]:
    """Compact defense menu - abbreviated display with '?' for full menu."""
    global AI_HELPER_ENABLED
    # Auto-show AI helper if enabled
    if AI_HELPER_ENABLED and easy_helper:
        _show_easy_mode_helper(easy_helper, game, is_offense=False)
    
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

    # Show Z only in easy mode (when easy_helper is available)
    z_option = ",Z" if easy_helper else ""
    print(f"  DEF: A-F | T,W{z_option},/ | ?=help (Default={default_def}/{default_name})")

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
            return _get_human_defense_play_compact(game, state, easy_helper)

        if choice_clean == 'Z':
            if easy_helper:
                AI_HELPER_ENABLED = not AI_HELPER_ENABLED
                if AI_HELPER_ENABLED:
                    print("\n  *** AI HELPER ENABLED ***")
                    _show_easy_mode_helper(easy_helper, game, is_offense=False)
                else:
                    print("\n  *** AI HELPER DISABLED ***")
                return _get_human_defense_play_compact(game, state, easy_helper)
            else:
                print("  Invalid. A-F, T, / or ? for help")
                return _get_human_defense_play_compact(game, state, easy_helper)

        if choice_clean == 'W':
            # Save game - return special marker to trigger save in main loop
            return None, False

        if choice_clean in DEFENSE_PLAYS:
            def_type, name, _ = DEFENSE_PLAYS[choice_clean]
            print(f"  You called: {name}")
            return def_type, call_timeout

        print("  Invalid. A-F, T, W, / or ? for help")


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


def get_human_defense_play(game: PaydirtGameEngine, easy_helper=None) -> tuple[DefenseType, bool]:
    """
    Prompt human player to select a defensive formation.

    Returns:
        Tuple of (DefenseType, call_timeout)
    """
    global AI_HELPER_ENABLED
    state = game.state

    # In compact mode, show abbreviated menu
    if COMPACT_MODE:
        return _get_human_defense_play_compact(game, state, easy_helper)

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
            return get_human_defense_play(game, easy_helper)
        
        # AI Helper toggle (only in easy mode)
        if choice_clean == 'Z':
            if easy_helper:
                AI_HELPER_ENABLED = not AI_HELPER_ENABLED
                if AI_HELPER_ENABLED:
                    print("\n  *** AI HELPER ENABLED ***")
                    _show_easy_mode_helper(easy_helper, game, is_offense=False)
                else:
                    print("\n  *** AI HELPER DISABLED ***")
            return get_human_defense_play(game, easy_helper)

        if choice_clean == 'W':
            # Save game - return special marker to trigger save in main loop
            return None, False

        if choice_clean in DEFENSE_PLAYS:
            def_type, name, _ = DEFENSE_PLAYS[choice_clean]
            return def_type, call_timeout

        print("  Invalid choice. Enter A, B, C, D, E, F, T, or / for stats (add T for timeout, e.g., 'AT')")


def computer_select_offense(game: PaydirtGameEngine, ai: ComputerAI = None) -> PlayType:
    """Computer AI selects an offensive play using situational intelligence."""
    if ai is None:
        ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)
    return ai.select_offense(game)


def computer_select_defense(game: PaydirtGameEngine, ai: ComputerAI = None) -> DefenseType:
    """Computer AI selects a defensive formation using situational intelligence."""
    if ai is None:
        ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)
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
            # Show dice roll info if available (both punt and return)
            if outcome.result:
                # Format: (O:10→"4" | D:2→"" | offense) style
                punt_dice = outcome.result.dice_roll
                punt_result_str = outcome.result.raw_result or ""
                return_dice = getattr(outcome.result, 'punt_return_dice', 0) or 0
                # Get return result from description
                return_match = re.search(r'returned (\d+) yards', outcome.description)
                return_yards_str = return_match.group(1) if return_match else ""
                
                if return_dice > 0:
                    print(f"  (P:{punt_dice}→\"{punt_result_str}\" | R:{return_dice}→\"{return_yards_str}\" | return)")
                else:
                    print(f"  ({format_dice_roll(punt_dice, result=punt_result_str, style='verbose')})")
            # Clarify fumble recovery possession
            if "FUMBLE" in outcome.description.upper():
                print(f"  >> {off_team} recovers and keeps possession!")
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
            # Show return dice if available
            return_dice = getattr(outcome.result, 'punt_return_dice', 0) or 0
            if return_dice > 0:
                punt_dice = outcome.result.dice_roll if outcome.result else 0
                print(f"  (P:{punt_dice}→\"{outcome.result.raw_result}\" | R:{return_dice}→\"F\" | return)")
            print(f"  >> FUMBLE on the return! {off_team} recovers and keeps possession!")
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

        # Check if FG was nullified by penalty with untimed down (half extended)
        fg_nullified = "UNTIMED DOWN" in outcome.description.upper() or "HALF EXTENDED" in outcome.description.upper()

        if COMPACT_MODE:
            # Compact field goal display
            if outcome.field_goal_made and not fg_nullified:
                print(f"► FG {statistical_distance} yards: GOOD! ({kicker})")
            elif "BLOCKED" in outcome.description.upper():
                # Show full description for blocked kicks (includes recovery/return info)
                print(f"► FG {statistical_distance} yards: {outcome.description}")
            elif fg_nullified:
                # Penalty accepted, half extended - show the penalty description instead
                print(f"  {outcome.description}")
                return
            else:
                print(f"► FG {statistical_distance} yards: NO GOOD")
            print(f"  ({format_dice_roll(dice_roll, result=chart_result, style='verbose')} | Needed: {distance_to_goal} yds)")
            return

        print("\n" + "=" * 70)
        print("  FIELD GOAL ATTEMPT")
        print("=" * 70)

        print(f"\n  {kicker} lines up for the {statistical_distance}-yard attempt...")
        print(f"  {format_dice_roll(dice_roll, result=chart_result, style='verbose')}")
        print(f"  Distance needed: {distance_to_goal} yards to goal line")

        if outcome.field_goal_made and not fg_nullified:
            print(f"\n  >> {kicker} kicks it... IT'S GOOD!")
            print("  >>> FIELD GOAL IS GOOD!")
        elif "BLOCKED" in outcome.description.upper():
            print(f"\n  >> BLOCKED! {outcome.description}")
        elif "FUMBLE" in outcome.description.upper():
            print(f"\n  >> {outcome.description}")
        elif fg_nullified:
            # Penalty accepted, half extended - show the penalty description
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

        # Check for offsetting penalties first (special case)
        if outcome.penalty_choice and outcome.penalty_choice.offsetting:
            print(f"► {play_name.upper()}: OFFSETTING PENALTIES - Down replayed")
            print("  (Penalties offset, no change in field position)")
            return

        # Use transaction-based display if available
        txn = outcome.transaction
        if txn and txn.is_complete:
            # Build result string from transaction
            if txn.has_event_type(EventType.INTERCEPTION):
                int_events = txn.get_events_by_type(EventType.INT_RETURN)
                if int_events and int_events[0].yards != 0:
                    result_str = f"INTERCEPTED! Returned {int_events[0].yards} yds"
                else:
                    result_str = "INTERCEPTED!"
                if txn.touchdown:
                    special_marker = " ★ PICK SIX!"
                elif game.state.ball_position >= 95:
                    special_marker = " ★ TURNOVER! GOAL LINE!"
                elif game.state.ball_position >= 80:
                    special_marker = " ★ TURNOVER! IN THE RED ZONE!"
                else:
                    special_marker = " ★ TURNOVER!"
            elif txn.has_event_type(EventType.FUMBLE):
                recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
                if txn.turnover:
                    if txn.touchdown:
                        result_str = "FUMBLE - Loss! RETURNED FOR TD!"
                        special_marker = " ★ SCOOP AND SCORE!"
                    else:
                        return_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
                        if return_events and return_events[0].yards > 0:
                            result_str = f"FUMBLE - Loss! Returned {return_events[0].yards} yds"
                        else:
                            result_str = "FUMBLE - Loss!"
                        if game.state.ball_position >= 95:
                            special_marker = " ★ TURNOVER! GOAL LINE!"
                        elif game.state.ball_position >= 80:
                            special_marker = " ★ TURNOVER! IN THE RED ZONE!"
                        else:
                            special_marker = " ★ TURNOVER!"
                else:
                    # Offense recovered - show yardage gained/lost
                    if txn.yards_gained > 0:
                        result_str = f"FUMBLE - Recovered! +{txn.yards_gained} yds"
                    elif txn.yards_gained < 0:
                        result_str = f"FUMBLE - Recovered! {txn.yards_gained} yds"
                    else:
                        result_str = "FUMBLE - Recovered!"
            elif txn.touchdown:
                result_str = "TOUCHDOWN!"
                special_marker = " ★ TOUCHDOWN!"
            elif txn.safety:
                result_str = "SAFETY!"
                special_marker = " ★ SAFETY!"
            elif txn.first_down:
                result_str = f"+{txn.yards_gained}"
                special_marker = " FIRST DOWN!"
            elif txn.yards_gained > 0:
                result_str = f"+{txn.yards_gained}"
            elif txn.yards_gained < 0:
                result_str = f"{txn.yards_gained}"
            else:
                result_str = "No gain"

            # Detect turnover on downs (4th down failure)
            is_turnover_on_downs = (
                outcome.down_before == 4 and
                not txn.first_down and
                not txn.turnover and
                not txn.touchdown and
                not txn.safety
            )
            if is_turnover_on_downs:
                special_marker = " ★ TURNOVER ON DOWNS!"

            # Generate commentary
            is_breakaway = outcome.result.result_type == ResultType.BREAKAWAY
            skip_commentary = (txn.has_event_type(EventType.FUMBLE) and not txn.turnover)
            is_check_down = False
            if outcome.result.defense_modifier:
                def_cat_check, _ = categorize_result(outcome.result.defense_modifier)
                is_check_down = (def_cat_check == ResultCategory.PARENS_NUMBER)

            comment = ""
            if not skip_commentary:
                comment = commentary.generate(
                    play_type=play_type,
                    result_type=outcome.result.result_type,
                    yards=txn.yards_gained,
                    is_first_down=txn.first_down,
                    is_touchdown=txn.touchdown,
                    is_breakaway=is_breakaway,
                    is_check_down=is_check_down
                )

            # Line 1: Result with play type and commentary
            if comment:
                print(f"► {play_name.upper()}: {result_str} - {comment}{special_marker}")
            else:
                print(f"► {play_name.upper()}: {result_str}{special_marker}")

            # Line 2: Action line for turnovers (interception/fumble returns)
            if txn.has_event_type(EventType.INTERCEPTION):
                int_event = txn.get_events_by_type(EventType.INTERCEPTION)[0]
                ret_events = txn.get_events_by_type(EventType.INT_RETURN)
                if ret_events:
                    ret_event = ret_events[0]
                    int_spot = int_event.spot
                    ret_yards = ret_event.yards
                    int_pos_str = format_field_position(int_spot)
                    # Describe the return action
                    if txn.touchdown:
                        print(f"  → Intercepted at the {int_pos_str}, returned {ret_yards} yards for a TOUCHDOWN!")
                    elif ret_yards > 0:
                        final_spot = int_spot + ret_yards
                        final_pos_str = format_field_position(final_spot)
                        print(f"  → Intercepted at the {int_pos_str}, returned {ret_yards} yards to the {final_pos_str}")
                    elif ret_yards < 0:
                        print(f"  → Intercepted at the {int_pos_str}, tackled {-ret_yards} yards behind the catch")
                    else:
                        print(f"  → Intercepted at the {int_pos_str}, tackled immediately")
            elif txn.has_event_type(EventType.FUMBLE):
                fumble_event = txn.get_events_by_type(EventType.FUMBLE)[0]
                fumble_spot = fumble_event.spot
                fumble_pos_str = format_field_position(fumble_spot)
                if txn.turnover:
                    ret_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
                    if ret_events:
                        ret_event = ret_events[0]
                        ret_yards = ret_event.yards
                        if txn.touchdown:
                            print(f"  → Fumble at the {fumble_pos_str}, recovered and returned {ret_yards} yards for a TOUCHDOWN!")
                        elif ret_yards > 0:
                            print(f"  → Fumble at the {fumble_pos_str}, recovered and returned {ret_yards} yards")
                        else:
                            # Defense recovered at the fumble spot (0 return yards)
                            print(f"  → Fumble at the {fumble_pos_str}, recovered by the defense at the spot")
                    else:
                        # No return event but still a turnover
                        print(f"  → Fumble at the {fumble_pos_str}, recovered by the defense")
                else:
                    # Offense recovered
                    if txn.yards_gained > 0:
                        print(f"  → Fumble at the {fumble_pos_str}, recovered by offense, advanced {txn.yards_gained} yards")
                    elif txn.yards_gained < 0:
                        print(f"  → Fumble at the {fumble_pos_str}, recovered by offense, lost {-txn.yards_gained} yards")
                    else:
                        print(f"  → Fumble at the {fumble_pos_str}, recovered by offense at the spot")

            # Line 3: Show transaction events as technical details
            # Build extra info from transaction events using consistent O:/D:/R: syntax
            extra_info = ""
            if txn.has_event_type(EventType.INTERCEPTION):
                int_event = txn.get_events_by_type(EventType.INTERCEPTION)[0]
                ret_events = txn.get_events_by_type(EventType.INT_RETURN)
                if ret_events:
                    ret_event = ret_events[0]
                    extra_info = f" | INT@{int_event.spot} | R:{ret_event.dice_roll}→\"{ret_event.yards}\""
            elif txn.has_event_type(EventType.FUMBLE):
                fumble_event = txn.get_events_by_type(EventType.FUMBLE)[0]
                recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
                if recovery_events:
                    rec_event = recovery_events[0]
                    rec_result = "kept" if not txn.turnover else "lost"
                    if txn.turnover:
                        ret_events = txn.get_events_by_type(EventType.FUMBLE_RETURN)
                        ret_yards = ret_events[0].yards if ret_events else 0
                        ret_dice = ret_events[0].dice_roll if ret_events else 0
                        extra_info = f" | F@{fumble_event.spot} | R:{rec_event.dice_roll}→\"{rec_result}\" | Ret:{ret_dice}→{ret_yards}"
                    else:
                        extra_info = f" | F@{fumble_event.spot} | R:{rec_event.dice_roll}→\"{rec_result}\""

            def_row = def_match.group(3) if def_match else "?"
            
            # Add breakaway dice if this is a breakaway play
            breakaway_extra = ""
            if outcome.result.result_type == ResultType.BREAKAWAY:
                b_dice = getattr(outcome.result, 'breakaway_dice', 0)
                b_yards = getattr(outcome.result, 'breakaway_yards', 0)
                if b_dice:
                    breakaway_extra = f" | B:{b_dice}→{b_yards}"
            
            print(f"  (O:{outcome.result.dice_roll}→\"{outcome.result.raw_result}\" | D:{def_row}→\"{outcome.result.defense_modifier}\" | {combined.priority.value}{extra_info}{breakaway_extra})")

            # Announce turnover on downs with expressive commentary and possession change
            if is_turnover_on_downs:
                print()
                print("  " + "=" * 50)
                print("  *** TURNOVER ON DOWNS! ***")
                print(f"  The defense holds! {def_team} takes over!")
                print("  " + "=" * 50)
            return

        # Fallback to legacy display if no transaction
        if outcome.result.result_type == ResultType.INCOMPLETE:
            result_str = "Incomplete"
        elif outcome.result.result_type == ResultType.INTERCEPTION:
            # Check for return yardage on interception
            int_return = getattr(outcome.result, 'int_return_yards', None)
            int_dice = getattr(outcome.result, 'int_return_dice', None)
            int_spot = getattr(outcome.result, 'int_spot', None)
            if int_dice is not None:
                # We have return info - show clean game action, details go on technical line
                if int_return and int_return != 0:
                    result_str = f"INTERCEPTED! Returned {int_return} yds"
                else:
                    result_str = "INTERCEPTED!"
                # Check if return ended in red zone
                if game.state.ball_position >= 95:
                    special_marker = " ★ TURNOVER! GOAL LINE!"
                elif game.state.ball_position >= 80:
                    special_marker = " ★ TURNOVER! IN THE RED ZONE!"
                else:
                    special_marker = " ★ TURNOVER!"
            else:
                result_str = "INTERCEPTED!"
                special_marker = " ★ TURNOVER!"
            if outcome.touchdown:
                special_marker = " ★ PICK SIX!"
        elif outcome.result.result_type == ResultType.FUMBLE:
            if outcome.turnover:
                # Check for touchback (fumble in end zone recovered by defense)
                if "TOUCHBACK" in outcome.result.description.upper():
                    result_str = "FUMBLE in end zone - TOUCHBACK!"
                    special_marker = " ★ TURNOVER!"
                # Check for fumble return TD
                elif outcome.touchdown:
                    result_str = "FUMBLE - Loss! RETURNED FOR TD!"
                    special_marker = " ★ SCOOP AND SCORE!"
                # Check for return yardage on fumble recovery
                else:
                    return_yards = getattr(outcome.result, 'fumble_return_yards', 0)
                    if return_yards and return_yards > 0:
                        result_str = f"FUMBLE - Loss! Returned {return_yards} yds"
                        # Check if return ended in red zone (ball_position >= 80 from new offense perspective)
                        if game.state.ball_position >= 95:
                            special_marker = " ★ TURNOVER! GOAL LINE!"
                        elif game.state.ball_position >= 80:
                            special_marker = " ★ TURNOVER! IN THE RED ZONE!"
                        else:
                            special_marker = " ★ TURNOVER!"
                    else:
                        result_str = "FUMBLE - Loss!"
                        special_marker = " ★ TURNOVER!"
            else:
                # Offense recovered their own fumble - clean game action
                result_str = "FUMBLE - Recovered!"
        elif outcome.result.result_type == ResultType.TOUCHDOWN or outcome.touchdown:
            # Check for TD before checking yards_gained (TD may have yards_gained=0)
            result_str = "TOUCHDOWN!"
            special_marker = " ★ TOUCHDOWN!"
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

        # Detect turnover on downs (4th down failure) - for legacy path
        is_turnover_on_downs = (
            outcome.down_before == 4 and
            not outcome.first_down and
            not outcome.turnover and
            not outcome.touchdown and
            not outcome.safety
        )

        # Don't overwrite special turnover TD markers (PICK SIX, SCOOP AND SCORE)
        turnover_td_markers = [" ★ PICK SIX!", " ★ SCOOP AND SCORE!"]
        if outcome.touchdown and special_marker not in turnover_td_markers and special_marker != " ★ TOUCHDOWN!":
            special_marker = " ★ TOUCHDOWN!"
        elif outcome.first_down and not outcome.turnover and not outcome.touchdown:
            special_marker = " FIRST DOWN!"
        elif outcome.safety:
            special_marker = " ★ SAFETY!"
        elif is_turnover_on_downs:
            special_marker = " ★ TURNOVER ON DOWNS!"

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

        # Line 2: Dice details (condensed) - include turnover return info here
        def_row = def_match.group(3) if def_match else "?"
        extra_info = ""
        breakaway_extra = ""
        qt_extra = ""
        
        if outcome.result.result_type == ResultType.INTERCEPTION:
            int_dice = getattr(outcome.result, 'int_return_dice', None)
            int_spot = getattr(outcome.result, 'int_spot', None)
            int_return = getattr(outcome.result, 'int_return_yards', 0)
            if int_dice is not None:
                extra_info = f" | INT@{int_spot} | R:{int_dice}→\"{int_return}\""
        elif outcome.result.result_type == ResultType.FUMBLE:
            recovery_roll = getattr(outcome.result, 'fumble_recovery_roll', None)
            fumble_spot = getattr(outcome.result, 'fumble_spot', None)
            fumble_return = getattr(outcome.result, 'fumble_return_yards', 0)
            if recovery_roll is not None:
                rec_result = "kept" if not outcome.turnover else "lost"
                if outcome.turnover:
                    extra_info = f" | F@{fumble_spot} | R:{recovery_roll}→\"{rec_result}\" | Ret:{fumble_return}"
                elif fumble_return > 0:
                    extra_info = f" | F@{fumble_spot} | R:{recovery_roll}→\"{rec_result}\" | Ret:{fumble_return}"
                else:
                    extra_info = f" | F@{fumble_spot} | R:{recovery_roll}→\"{rec_result}\""
        
        # Add breakaway dice if this is a breakaway play
        if outcome.result.result_type == ResultType.BREAKAWAY:
            b_dice = getattr(outcome.result, 'breakaway_dice', 0)
            b_yards = getattr(outcome.result, 'breakaway_yards', 0)
            if b_dice:
                breakaway_extra = f" | B:{b_dice}→{b_yards}"
        
        # Add QB scramble (QT) dice if this is a QT result
        if outcome.result.result_type in (ResultType.QB_SCRAMBLE, ResultType.SACK):
            qt_dice = getattr(outcome.result, 'qb_scramble_dice', 0)
            qt_yards = getattr(outcome.result, 'qb_scramble_yards', 0)
            if qt_dice:
                qt_extra = f" | QT:{qt_dice}→{qt_yards}"
        
        # Handle Hail Mary specially - only offense dice, no defense or priority chart
        if play_type == PlayType.HAIL_MARY:
            print(f"  (O:{outcome.result.dice_roll}→\"{outcome.result.raw_result}\")")
        else:
            print(f"  (O:{outcome.result.dice_roll}→\"{outcome.result.raw_result}\" | D:{def_row}→\"{outcome.result.defense_modifier}\" | {combined.priority.value}{extra_info}{breakaway_extra}{qt_extra})")

        # Announce turnover on downs with expressive commentary and possession change
        if is_turnover_on_downs:
            print()
            print("  " + "=" * 50)
            print("  *** TURNOVER ON DOWNS! ***")
            print(f"  The defense holds! {def_team} takes over!")
            print("  " + "=" * 50)
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

        int_pos_str = format_field_position_with_team(int_spot, off_team, def_team)

        print(f"  RESULT: INTERCEPTED at the {int_pos_str} yard line!")
        print(f"  {format_dice_roll(int_dice, result=str(int_return), prefix='R')} yard return")
        if outcome.touchdown:
            print("  >>> PICK SIX! Returned for a TOUCHDOWN!")
    elif outcome.result.result_type == ResultType.FUMBLE:
        # Show detailed fumble info per official rules
        fumble_spot = outcome.result.fumble_spot if hasattr(outcome.result, 'fumble_spot') else 0
        recovery_roll = outcome.result.fumble_recovery_roll if hasattr(outcome.result, 'fumble_recovery_roll') else 0
        recovered = outcome.result.fumble_recovered if hasattr(outcome.result, 'fumble_recovered') else False
        return_yards = outcome.result.fumble_return_yards if hasattr(outcome.result, 'fumble_return_yards') else 0
        return_dice = outcome.result.fumble_return_dice if hasattr(outcome.result, 'fumble_return_dice') else 0

        fumble_pos_str = format_field_position_with_team(fumble_spot, off_team, def_team)

        print(f"  RESULT: FUMBLE at the {fumble_pos_str} yard line!")
        print(f"  {format_dice_roll(recovery_roll, prefix='R')}")
        if recovered:
            print("  >>> OFFENSE RECOVERS!")
            if return_yards > 0:
                print(f"  Return: {format_dice_roll(return_dice, result=str(return_yards), prefix='Ret')}")
        else:
            print("  >>> DEFENSE RECOVERS - TURNOVER!")
            if return_yards > 0:
                print(f"  Return: {format_dice_roll(return_dice, result=str(return_yards), prefix='Ret')}")
        if outcome.touchdown:
            print("  >>> FUMBLE RETURN TOUCHDOWN!")
    elif outcome.result.result_type == ResultType.BREAKAWAY:
        print(f"  RESULT: BREAKAWAY! {outcome.yards_gained} yards!")
    elif outcome.result.result_type == ResultType.SACK:
        print(f"  RESULT: SACKED for {abs(outcome.yards_gained)} yard loss!")
    elif outcome.result.result_type == ResultType.QB_SCRAMBLE:
        if outcome.touchdown:
            print(f"  RESULT: QB scrambles for {outcome.yards_gained} yards - TOUCHDOWN!")
        elif outcome.yards_gained >= 0:
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

    # Detect and announce turnover on downs (4th down failure)
    is_turnover_on_downs = (
        outcome.down_before == 4 and
        not outcome.first_down and
        not outcome.turnover and
        not outcome.touchdown and
        not outcome.safety
    )
    if is_turnover_on_downs:
        print()
        print("  " + "=" * 50)
        print("  *** TURNOVER ON DOWNS! ***")
        print(f"  The defense holds! {def_team} takes over!")
        print("  " + "=" * 50)


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
    
    # Check play type to use correct apply method
    is_fg_penalty = outcome.play_type == PlayType.FIELD_GOAL
    is_punt_penalty = outcome.play_type == PlayType.PUNT
    is_kickoff_penalty = outcome.play_type == PlayType.KICKOFF

    # Determine who is the offended team and if human decides
    offended_is_offense = penalty_choice.offended_team == "offense"
    human_decides = (offended_is_offense and is_human_offense) or \
                   (not offended_is_offense and not is_human_offense)

    # Display penalty information
    print("\n" + "=" * 70)
    print("  *** PENALTY ON THE PLAY ***")
    print("=" * 70)

    # Show dice rolls in standard format
    play_result = penalty_choice.play_result
    
    # For punt/kickoff penalties, get dice info from pending state
    if is_punt_penalty and hasattr(game, '_pending_punt_state'):
        state = game._pending_punt_state
        punt_roll = state.get('punt_roll', 0)
        punt_result = state.get('punt_result', '')
        punt_yards = state.get('punt_yards', 0)
        return_yards = state.get('return_yards', 0)
        
        # Format: (Punt: 35 yards | P:14→"OFF 15" | R:10→"10")
        roll_parts = []
        if punt_yards > 0:
            roll_parts.append(f"Punt: {punt_yards} yards")
        roll_parts.append(f"P:{punt_roll}→\"{punt_result}\"")
        
        # If there was a reroll for actual yardage, show it
        if penalty_choice.reroll_log:
            for log_entry in penalty_choice.reroll_log:
                roll_parts.append(f"reroll: {log_entry}")
        
        # Show return roll if there was a return
        return_roll = state.get('return_roll', 0)
        if return_roll > 0:
            roll_parts.append(f"R:{return_roll}→\"{return_yards}\"")
        
        print(f"\n  ({' | '.join(roll_parts)})")
    elif is_kickoff_penalty and hasattr(game, '_pending_kickoff_penalty_state'):
        state = game._pending_kickoff_penalty_state
        kick_roll = state.get('kick_roll', 0)
        kick_result = state.get('kick_result', '')
        return_yards = state.get('return_yards', 0)
        
        roll_parts = []
        roll_parts.append(f"K:{kick_roll}→\"{kick_result}\"")
        
        if return_yards > 0:
            roll_parts.append(f"R:→\"{return_yards}\"")
        
        print(f"\n  ({' | '.join(roll_parts)})")
    else:
        # Standard scrimmage play - show O:/D: format
        off_roll_str = ""
        def_roll_str = ""
        
        # Try to extract dice descriptions from play_result.description
        # Format is: "... [Off: B2+W5+W3=28, Def: R1+G2=12]"
        desc = play_result.description if play_result else ""
        off_dice_match = re.search(r'\[Off: (B\d\+W\d\+W\d=\d+)', desc)
        def_dice_match = re.search(r'Def: (R\d\+G\d=\d+)\]', desc)
        
        # Build offense roll string
        if off_dice_match and play_result:
            off_roll_str = f"O:{off_dice_match.group(1)}→\"{play_result.raw_result}\""
        elif play_result and play_result.dice_roll:
            off_roll_str = f"O:{play_result.dice_roll}→\"{play_result.raw_result}\""
        
        # Build defense roll string
        def_result = penalty_choice.original_defense_result or (play_result.defense_modifier if play_result else "")
        if def_dice_match and def_result:
            def_roll_str = f"D:{def_dice_match.group(1)}→\"{def_result}\""
        elif def_result:
            def_roll_str = f"D:\"{def_result}\""
        
        if off_roll_str or def_roll_str:
            roll_parts = [p for p in [off_roll_str, def_roll_str] if p]
            print(f"\n  ({' | '.join(roll_parts)})")

    # Show reroll log if there were rerolls (for detailed penalty tracking)
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
    txn = penalty_choice.transaction
    print("\n  Play Result (if accepted, down counts):")
    
    # Handle FG plays specially - the chart yardage is kick distance, not yards gained
    if is_fg_penalty:
        # For FG, show whether the kick was good or not
        print(f"    {play_result.description}")
        if outcome.field_goal_made:
            print("    -> FIELD GOAL GOOD!")
        else:
            print("    -> FIELD GOAL NO GOOD (turnover on downs)")
    elif play_result.result_type == ResultType.FUMBLE:
        # Fumble - show the play result and recovery from transaction
        print(f"    {play_result.description}")
        # Get recovery info from transaction
        if txn and txn.has_event_type(EventType.FUMBLE_RECOVERY):
            recovery_events = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)
            if recovery_events:
                rec_event = recovery_events[0]
                print(f"    Recovery roll {rec_event.dice_roll}: {rec_event.description}")
                if rec_event.possession_change:
                    print("    ** TURNOVER **")
                else:
                    print("    (Offense keeps possession)")
        elif play_result.turnover:
            print("    ** TURNOVER **")
    elif play_result.turnover:
        print(f"    {play_result.description}")
        print("    ** TURNOVER **")
    elif play_result.touchdown:
        print(f"    {play_result.description}")
        print("    ** TOUCHDOWN **")
    else:
        print(f"    {play_result.description}")
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
            print(f"    -> {ordinal(next_down)} and {next_ytg}")

    if human_decides:
        # Human makes the decision
        print(f"\n  You ({penalty_choice.offended_team.upper()}) may choose:")

        # Show play result option with outcome details
        # Handle FG plays specially - the chart yardage is kick distance, not yards gained
        if is_fg_penalty:
            if outcome.field_goal_made:
                play_outcome_str = "FIELD GOAL GOOD!"
                play_field_str = "kickoff"
            else:
                play_outcome_str = "FIELD GOAL NO GOOD (turnover)"
                play_field_str = "defense ball"
        elif is_punt_penalty:
            # For punt penalties, show the punt result (not turnover on downs)
            play_outcome_str = "Punt stands as called"
            # Get the final position from the pending state if available
            if hasattr(game, '_pending_punt_state'):
                final_pos = game._pending_punt_state.get('final_position', game.state.ball_position)
                # Check for touchdown - ball past goal line (position >= 100)
                if final_pos >= 100:
                    play_field_str = "TOUCHDOWN"
                else:
                    play_field_str = format_field_position(final_pos, style="short")
            else:
                play_field_str = "opponent's ball"
        elif is_kickoff_penalty:
            # For kickoff penalties, show the kickoff result
            play_outcome_str = "Kickoff stands as called"
            play_field_str = format_field_position(game.state.ball_position, style="short")
        else:
            yards_gained = play_result.yards
            play_new_pos = game.state.ball_position + yards_gained

            # Check for touchdown first (ball crosses goal line at 100)
            if play_result.touchdown or play_new_pos >= 100:
                play_outcome_str = "TOUCHDOWN!"
                play_field_str = "end zone"
            elif play_result.result_type == ResultType.FUMBLE:
                # Fumble - recovery is now pre-determined, show actual result
                fumble_recovered = getattr(play_result, 'fumble_recovered', False)
                recovery_roll = getattr(play_result, 'fumble_recovery_roll', 0)
                if fumble_recovered:
                    play_outcome_str = f"FUMBLE - Offense recovers (roll {recovery_roll})"
                else:
                    play_outcome_str = f"FUMBLE - TURNOVER (roll {recovery_roll})"
                play_new_pos = clamp_ball_position(play_new_pos)
                play_field_str = format_field_position(play_new_pos, style="short")
            elif play_result.turnover:
                # Non-fumble turnover (interception)
                play_outcome_str = "TURNOVER"
                play_new_pos = clamp_ball_position(play_new_pos)
                play_field_str = format_field_position(play_new_pos, style="short")
            else:
                play_new_pos = clamp_ball_position(play_new_pos)
                play_field_str = format_field_position(play_new_pos, style="short")

                if yards_gained >= game.state.yards_to_go:
                    play_outcome_str = f"{yards_gained} yards, FIRST DOWN"
                elif game.state.down >= 4:
                    # 4th down failure = turnover on downs
                    if yards_gained > 0:
                        play_outcome_str = f"{yards_gained} yards -> TURNOVER ON DOWNS"
                    elif yards_gained == 0:
                        play_outcome_str = "No gain -> TURNOVER ON DOWNS"
                    else:
                        play_outcome_str = f"Loss of {abs(yards_gained)} -> TURNOVER ON DOWNS"
                elif yards_gained > 0:
                    next_down = game.state.down + 1
                    next_ytg = game.state.yards_to_go - yards_gained
                    play_outcome_str = f"{yards_gained} yards -> {ordinal(next_down)} and {next_ytg}"
                elif yards_gained == 0:
                    next_down = game.state.down + 1
                    play_outcome_str = f"No gain -> {ordinal(next_down)} and {game.state.yards_to_go}"
                else:
                    next_down = game.state.down + 1
                    next_ytg = game.state.yards_to_go - yards_gained  # yards_gained is negative
                    play_outcome_str = f"Loss of {abs(yards_gained)} -> {ordinal(next_down)} and {next_ytg}"

        # Option 1 is always the play result
        print(f"    [1] Accept PLAY result: {play_outcome_str} at {play_field_str}")

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
            pen_new_pos = clamp_ball_position(pen_new_pos)

            pen_field_str = format_field_position(pen_new_pos, style="short")

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

            # Build description - use adjusted position if half-distance was applied
            if adjusted_yards != opt.yards:
                # Half-distance was applied - rebuild description with correct position
                if is_punt_penalty and "Replay punt" in opt.description:
                    display_desc = f"Replay punt from {pen_field_str} (half-distance: {adjusted_yards} yds)"
                elif is_kickoff_penalty and "Re-kick" in opt.description:
                    display_desc = f"Re-kick from {pen_field_str} (half-distance: {adjusted_yards} yds)"
                else:
                    display_desc = f"{opt.description} (half-distance: {adjusted_yards} yds)"
            else:
                display_desc = opt.description
            print(f"    [{i+2}] Accept PENALTY: {display_desc} -> {pen_down_str} at {pen_field_str}")

        while True:
            choice = input("\n  Your choice (1 for play, or penalty number): ").strip()

            if choice == '1' or choice == '':
                # Accept play result - announce like NFL refs
                penalty_desc = filtered_penalties[0].description if filtered_penalties else "penalty"
                print(f"\n  >> {penalty_desc.upper()} - DECLINED. Result of the play stands.")
                if is_fg_penalty:
                    return game.apply_fg_penalty_decision(outcome, accept_play=True)
                elif is_punt_penalty:
                    return game.apply_punt_penalty_decision(outcome, accept_penalty=False)
                elif is_kickoff_penalty:
                    return game.apply_kickoff_penalty_decision(outcome, accept_penalty=False)
                else:
                    return game.apply_penalty_decision(outcome, accept_play=True)
            elif choice.isdigit():
                idx = int(choice) - 2  # Subtract 2 since penalties start at [2]
                if 0 <= idx < len(filtered_penalties):
                    opt = filtered_penalties[idx]
                    # Find the original index in penalty_options for apply_penalty_decision
                    original_idx = penalty_choice.penalty_options.index(opt)
                    print(f"\n  >> Accepting penalty: {opt.description}")
                    if is_fg_penalty:
                        return game.apply_fg_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)
                    elif is_punt_penalty:
                        return game.apply_punt_penalty_decision(outcome, accept_penalty=True, penalty_index=original_idx)
                    elif is_kickoff_penalty:
                        return game.apply_kickoff_penalty_decision(outcome, accept_penalty=True)
                    else:
                        return game.apply_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)
                else:
                    print("  Invalid choice. Try again.")
            else:
                print("  Invalid choice. Enter P for play or a penalty number.")
    else:
        # CPU makes the decision - use centralized AI logic
        accept_play, best_penalty_idx = cpu_should_accept_penalty(
            outcome, is_human_offense, human_is_home
        )

        # Get CPU team name for display
        cpu_team = game.state.defense_team.peripheral.short_name if is_human_offense else game.state.possession_team.peripheral.short_name

        if accept_play:
            print(f"\n  >> {cpu_team} accepts play result")
            if is_fg_penalty:
                return game.apply_fg_penalty_decision(outcome, accept_play=True)
            elif is_punt_penalty:
                return game.apply_punt_penalty_decision(outcome, accept_penalty=False)
            elif is_kickoff_penalty:
                return game.apply_kickoff_penalty_decision(outcome, accept_penalty=False)
            else:
                return game.apply_penalty_decision(outcome, accept_play=True)
        else:
            opt = filtered_penalties[best_penalty_idx]
            # Find the original index in penalty_options for apply_penalty_decision
            original_idx = penalty_choice.penalty_options.index(opt)
            print(f"\n  >> {cpu_team} accepts penalty: {opt.description}")
            if is_fg_penalty:
                return game.apply_fg_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)
            elif is_punt_penalty:
                return game.apply_punt_penalty_decision(outcome, accept_penalty=True)
            elif is_kickoff_penalty:
                return game.apply_kickoff_penalty_decision(outcome, accept_penalty=True)
            else:
                return game.apply_penalty_decision(outcome, accept_play=False, penalty_index=original_idx)


def _offer_record_to_standings(year: int, home_team: str, home_score: int,
                                away_team: str, away_score: int, week: int = 0):
    """Offer to record the game result to season standings.
    
    Args:
        year: Season year
        home_team: Home team nickname
        home_score: Home team final score
        away_team: Away team nickname
        away_score: Away team final score
        week: Week number (0 = auto-assign based on game count)
    """
    from .standings import add_game_result
    
    print("\n" + "-" * 50)
    record = input("  Record this game to season standings? (y/n): ").strip().lower()
    
    if record == 'y':
        success = add_game_result(
            year=year,
            home_team=home_team,
            home_score=home_score,
            away_team=away_team,
            away_score=away_score,
            week=week
        )
        if success:
            week_str = f"Week {week} - " if week > 0 else ""
            print(f"  Game recorded: {week_str}{away_team} {away_score} @ {home_team} {home_score}")
        else:
            print("  Error: Could not record game (unknown team name?)")
            week_arg = f" --week {week}" if week > 0 else ""
            print(f"  You can manually add with: python -m paydirt.standings add {year} \"{home_team}\" {home_score} \"{away_team}\" {away_score}{week_arg}")
    else:
        print("  Game not recorded.")
        week_arg = f" --week {week}" if week > 0 else ""
        print(f"  To record later: python -m paydirt.standings add {year} \"{home_team}\" {home_score} \"{away_team}\" {away_score}{week_arg}")


def run_interactive_game(difficulty: str = 'medium', compact: bool = False, week: int = 0,
                         home_team: Optional[str] = None, away_team: Optional[str] = None,
                         human_is_home: bool = True, is_playoff: bool = False):
    """
    Main interactive game loop.
    
    Args:
        difficulty: CPU difficulty level ('easy', 'medium', 'hard')
                   - easy: CPU aggression 0.3 (conservative)
                   - medium: CPU aggression 0.5 (balanced, default)
                   - hard: CPU aggression 0.7 (aggressive, optimal)
        compact: If True, use compact display mode with less verbose output
        week: Week number for recording to standings (0 = auto-assign)
        home_team: Home team name/path (optional)
        away_team: Away team name/path (optional)
        human_is_home: If True, human plays at home
        is_playoff: If True, this is a playoff game
    """
    # Set global display mode
    global COMPACT_MODE, AI_HELPER_ENABLED
    COMPACT_MODE = compact
    AI_HELPER_ENABLED = (difficulty == 'easy')

    # Map difficulty to aggression value
    difficulty_map = {
        'easy': 0.3,
        'medium': 0.5,
        'hard': 0.7
    }
    cpu_aggression = difficulty_map.get(difficulty, 0.5)

    # Easy mode helper - available in easy mode
    easy_mode_helper = None
    if difficulty == 'easy':
        # Will be set after team selection (need human_chart first)
        pass

    clear_screen()

    print("=" * 70)
    print("  PAYDIRT - Interactive Football Simulation")
    print("=" * 70)
    print()

    # Select teams - either from command line or interactive prompt
    if home_team or away_team:
        # Load teams from command line arguments
        from .chart_loader import find_team_charts, load_team_chart
        from .packaging import get_seasons_path
        from pathlib import Path
        
        # Find available teams
        seasons_dir = str(get_seasons_path())
        
        available_charts = find_team_charts(seasons_dir)
        
        # Create a lookup for team names
        team_lookup = {}
        for year, name, path in available_charts:
            # Normalize name for matching
            normalized = name.lower().replace(' ', '').replace("'", '')
            team_lookup[normalized] = path
            team_lookup[name.lower()] = path
            # Also add just the city or nickname
            parts = name.lower().split()
            if len(parts) >= 2:
                team_lookup[parts[-1]] = path  # last word (e.g., "cowboys")
        
        # Helper to find team path
        def find_team_path(team_name: str) -> Optional[str]:
            if not team_name:
                return None
            # Try exact path first
            if Path(f"seasons/{team_name}").exists():
                return f"seasons/{team_name}"
            if Path(team_name).exists():
                return team_name
            # Try lookup
            normalized = team_name.lower().replace(' ', '').replace("'", '')
            if normalized in team_lookup:
                return team_lookup[normalized]
            if team_name.lower() in team_lookup:
                return team_lookup[team_name.lower()]
            # Fall back to searching
            for year, name, path in available_charts:
                if team_name.lower() in name.lower():
                    return path
            raise ValueError(f"Team not found: {team_name}")
        
        # Parse team positions from command line
        # --away X means YOU play as X (away position)
        # --home X means YOU play as X (home position)
        # If both are specified, the FIRST one determines your team/position
        human_team_path = None
        cpu_team_path = None
        
        if away_team and not home_team:
            # Only --away specified - you play that team (away)
            human_team_path = find_team_path(away_team)
            human_is_home = False  # Human is away
            # Need to prompt for opponent
            cpu_team_path = None
        elif home_team and not away_team:
            # Only --home specified - you play that team (home)
            human_team_path = find_team_path(home_team)
            human_is_home = True  # Human is home
            # Need to prompt for opponent
            cpu_team_path = None
        elif home_team and away_team:
            # Both specified - use human_is_home to determine which is your team
            if human_is_home:
                # You play at home - your team is the --home flag
                human_team_path = find_team_path(home_team)
                cpu_team_path = find_team_path(away_team)
            else:
                # You play away - your team is the --away flag
                human_team_path = find_team_path(away_team)
                cpu_team_path = find_team_path(home_team)
        else:
            # No teams specified - will prompt
            pass  # human_is_home keeps its default value
        
        # Load the teams
        human_chart = load_team_chart(human_team_path) if human_team_path else None
        cpu_chart = load_team_chart(cpu_team_path) if cpu_team_path else None
        
        # If either team wasn't specified, prompt interactively
        if not human_chart:
            print("Select your team:")
            human_chart = select_team("Select YOUR team:")
        if not cpu_chart:
            print("\nSelect your opponent:")
            cpu_chart = select_team("Select OPPONENT team:", exclude=None)
        
        human_name = human_chart.peripheral.short_name
        cpu_name = cpu_chart.peripheral.short_name
    else:
        # Original interactive team selection
        print("Select your team:")
        human_chart = select_team("Select YOUR team:")
        human_name = human_chart.peripheral.short_name

        print("\nSelect your opponent:")
        cpu_chart = select_team("Select OPPONENT team:", exclude=None)
        cpu_name = cpu_chart.peripheral.short_name

    # Home/Away selection - skip if specified via parameters
    if home_team or away_team:
        # Teams specified on command line - use human_is_home parameter (default True)
        if human_is_home:
            away_chart, home_chart = cpu_chart, human_chart
        else:
            away_chart, home_chart = human_chart, cpu_chart
    else:
        # Interactive team selection
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
    game.state.is_playoff = is_playoff

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
    # Enable analysis/opponent modeling in hard mode
    use_analysis = (difficulty == 'hard')
    cpu_ai = ComputerAI(
        aggression=cpu_aggression,
        use_analysis=use_analysis,
        ai_behavior=game.season_rules.ai_behavior,
    )
    
    # Set the AI's team for analysis
    if use_analysis:
        # CPU AI needs to know its own team (the team it's controlling)
        cpu_team_chart = home_chart if not human_is_home else away_chart
        cpu_ai.set_team(cpu_team_chart)
    
    # Create easy mode helper if in easy mode
    if difficulty == 'easy':
        easy_mode_helper = create_easy_mode_helper(human_chart)
    else:
        easy_mode_helper = None
    
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
    
    # Handle kickoff penalty decision if applicable
    if outcome.pending_penalty_decision and outcome.penalty_choice:
        is_human_offense = (first_half_kicking_home != human_is_home)  # Receiving team is offense
        outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)
    
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
                
                # Handle kickoff penalty decision if applicable
                if outcome.pending_penalty_decision and outcome.penalty_choice:
                    is_human_offense = (second_half_kicking_home != human_is_home)
                    outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)
                
                print(f"  {outcome.description}")
                print(f"  {receiving_team} will start at {game.state.field_position_str()}")
            elif last_quarter < 4:
                # End of Q1 or Q3 - just announce
                print(f"\n  END OF QUARTER {last_quarter}")

            last_quarter = game.state.quarter

        # Check if quarter ended or overtime needed
        # Use < 0.0167 (1 second) threshold to catch tiny positive residuals
        # from floating-point arithmetic in timeout calculations that display as 0:00
        time_effectively_zero = game.state.time_remaining < 0.0167
        # But first check for untimed down (defensive penalty at 0:00)
        is_untimed_down = False
        if time_effectively_zero and game.has_untimed_down():
            print("\n  *** UNTIMED DOWN - Defensive penalty at 0:00 ***")
            print("  The quarter cannot end on an accepted defensive penalty.")
            is_untimed_down = True
            # Don't clear the flag yet - it prevents quarter from advancing during _use_time
            # We'll clear it after the untimed play completes
        elif time_effectively_zero:
            # Clamp any tiny residual to exactly 0
            game.state.time_remaining = 0
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
                    
                    # Handle kickoff penalty decision if applicable
                    if outcome.pending_penalty_decision and outcome.penalty_choice:
                        is_human_offense = (kicking_home != human_is_home)
                        outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)
                    
                    print(f"  {outcome.description}")
                    print(f"  {receiving_team} will start at {game.state.field_position_str()}")
                    continue
                else:
                    # Game over (not tied)
                    break
            elif game.state.quarter < 4:
                # Safety net: time expired in Q1-Q3 but quarter wasn't advanced
                # (can happen if timeout reverted the quarter with tiny residual time)
                # Force the quarter transition that _use_time() would normally handle
                game.state.quarter += 1
                game.state.time_remaining = 15.0
                if game.state.quarter == 3:
                    game.state.reset_timeouts_for_half()
                continue  # Re-enter loop to handle quarter change detection

        # Determine if human is on offense or defense
        is_human_offense = (game.state.is_home_possession == human_is_home)

        display_game_status(game, human_chart, is_human_offense)

        # Get play calls
        if is_human_offense:
            # Human on offense
            play_type, no_huddle_mode, out_of_bounds, in_bounds, call_timeout, call_spike = get_human_offense_play(game, no_huddle_mode, easy_mode_helper)

            # Check for save command (play_type is None)
            if play_type is None:
                filepath = save_game(game, human_is_away=not human_is_home, human_is_home=human_is_home, cpu_ai=cpu_ai)
                print(f"\n  *** GAME SAVED to {filepath} ***")
                print("  Use 'python -m paydirt --load' to resume")
                continue

            # Computer selects defense (hidden)
            def_type = computer_select_defense(game)

            print(f"  Defense shows: {def_type.value.replace('_', ' ').title()}")
        else:
            # Human on defense
            # On 4th down, CPU decides FIRST so we know if they're punting/kicking
            # This avoids asking for defensive call when CPU is just going to punt
            call_timeout = False
            call_spike = False
            out_of_bounds = False
            in_bounds = False
            cpu_punt_short_drop = False
            cpu_punt_coffin_yards = 0
            cpu_call_spike = False

            if game.state.down == 4:
                # CPU makes 4th down decision first (with clock management)
                play_type, cpu_oob, cpu_no_huddle, cpu_punt_short_drop, cpu_punt_coffin_yards, cpu_call_spike = cpu_ai.select_offense_with_clock_management(game)
                call_spike = cpu_call_spike
                if cpu_oob:
                    out_of_bounds = True
                if cpu_no_huddle:
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} in NO-HUDDLE offense!")

                if play_type == PlayType.PUNT:
                    # CPU punts - no defensive call needed
                    cpu_team = game.state.possession_team.peripheral.short_name
                    if cpu_punt_short_drop:
                        print(f"\n  {cpu_team} uses SHORT-DROP PUNT on 4th and {game.state.yards_to_go}")
                    elif cpu_punt_coffin_yards > 0:
                        print(f"\n  {cpu_team} uses COFFIN-CORNER PUNT ({cpu_punt_coffin_yards} yards subtracted) on 4th and {game.state.yards_to_go}")
                    else:
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
                    def_type, call_timeout = get_human_defense_play(game, easy_mode_helper)
                    # Check for save command (def_type is None)
                    if def_type is None:
                        filepath = save_game(game, human_is_away=not human_is_home, human_is_home=human_is_home, cpu_ai=cpu_ai)
                        print(f"\n  *** GAME SAVED to {filepath} ***")
                        print("  Use 'python -m paydirt --load' to resume")
                        continue
                    print(f"\n  You called: {def_type.value.replace('_', ' ').title()}")
                    print(f"  Offense runs: {play_type.value.replace('_', ' ').title()}")
            else:
                # Normal down - get defensive call first, then CPU selects offense
                def_type, call_timeout = get_human_defense_play(game, easy_mode_helper)
                # Initialize CPU punt options for non-4th-down case
                cpu_punt_short_drop = False
                cpu_punt_coffin_yards = 0
                # Check for save command (def_type is None)
                if def_type is None:
                    filepath = save_game(game, human_is_away=not human_is_home, human_is_home=human_is_home, cpu_ai=cpu_ai)
                    print(f"\n  *** GAME SAVED to {filepath} ***")
                    print("  Use 'python -m paydirt --load' to resume")
                    continue
                # Get play with clock management flags
                play_type, cpu_oob, cpu_no_huddle, cpu_punt_short_drop, cpu_punt_coffin_yards, cpu_call_spike = cpu_ai.select_offense_with_clock_management(game)
                call_spike = cpu_call_spike
                if cpu_oob:
                    out_of_bounds = True
                if cpu_no_huddle:
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} in NO-HUDDLE offense!")

                print(f"\n  You called: {def_type.value.replace('_', ' ').title()}")
                print(f"  Offense runs: {play_type.value.replace('_', ' ').title()}")

        time_before_play = game.state.time_remaining
        offense_was_home = game.state.is_home_possession
        two_min_warning_before = game.state.two_minute_warning_called

        # Initialize punt options
        punt_short_drop = False
        punt_coffin_corner_yards = 0
        if is_human_offense and play_type == PlayType.PUNT:
            punt_short_drop, punt_coffin_corner_yards = get_punt_options(game)
        elif not is_human_offense and play_type == PlayType.PUNT:
            # CPU is punting - use CPU's punt options
            punt_short_drop = cpu_punt_short_drop
            punt_coffin_corner_yards = cpu_punt_coffin_yards

        # Determine if CPU should call timeout (when CPU is on offense)
        cpu_call_timeout = False
        if not is_human_offense and cpu_ai:
            from .computer_ai import computer_should_call_timeout_on_offense
            cpu_call_timeout = computer_should_call_timeout_on_offense(game)

        outcome = game.run_play_with_penalty_procedure(play_type, def_type,
                                                        out_of_bounds_designation=out_of_bounds,
                                                        in_bounds_designation=in_bounds,
                                                        punt_short_drop=punt_short_drop,
                                                        punt_coffin_corner_yards=punt_coffin_corner_yards,
                                                        no_huddle=no_huddle_mode,
                                                        call_spike=call_spike,
                                                        call_timeout=call_timeout or cpu_call_timeout)

        if outcome.pending_penalty_decision and outcome.penalty_choice:
            outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)

        display_play_result(game, outcome, play_type, def_type, human_chart, offense_was_home)

        # Display modifier results
        if outcome.timeout_used:
            mins = int(game.state.time_remaining)
            secs = int((game.state.time_remaining % 1) * 60)
            team_name = "CPU" if cpu_call_timeout else None
            if team_name:
                print(f"\n  *** {team_name} TIMEOUT - Clock stops at {mins}:{secs:02d} ***")
            else:
                print(f"\n  *** TIMEOUT - Clock stops at {mins}:{secs:02d} ***")
        elif (call_timeout or cpu_call_timeout) and not outcome.touchdown:
            # Timeout was called but skipped (incomplete, OOB, or short play)
            play_seconds = (time_before_play - game.state.time_remaining) * 60
            _, skip_msg = game._should_apply_timeout_after_play(outcome, play_seconds)
            if skip_msg:
                print(f"  {skip_msg}")

        if outcome.spike_used:
            mins = int(game.state.time_remaining)
            secs = int((game.state.time_remaining % 1) * 60)
            print(f"\n  *** SPIKE - Clock stops at {mins}:{secs:02d} ***")
        elif call_spike and not outcome.touchdown:
            # Spike was called but skipped (incomplete or short play)
            play_seconds = (time_before_play - game.state.time_remaining) * 60
            _, skip_msg = game._should_apply_spike_after_play(outcome, play_seconds)
            if skip_msg:
                print(f"  {skip_msg}")

        # Record opponent play for tendency tracking (if AI is using analysis)
        if cpu_ai and cpu_ai.use_analysis and cpu_ai.opponent_model:
            if is_human_offense:
                from paydirt.play_resolver import is_passing_play
                game_state = game.state
                cpu_ai.opponent_model.record_opponent_play(
                    down=game_state.down,
                    distance=game_state.yards_to_go,
                    play_type=play_type.value if hasattr(play_type, 'value') else str(play_type),
                    yards_gained=outcome.yards_gained,
                    is_pass=is_passing_play(play_type)
                )

        if is_untimed_down:
            game.clear_untimed_down()

        if not two_min_warning_before and game.state.two_minute_warning_called:
            quarter_name = "first half" if game.state.quarter == 2 else "second half"
            print("\n" + "=" * 70)
            print("  *** TWO-MINUTE WARNING ***")
            print(f"  Official timeout - 2:00 remaining in the {quarter_name}")
            print("=" * 70)

        # Handle field goal made - kickoff after score
        if outcome.field_goal_made:
            print(f"  Score: {game.get_score_str()}")

            # Kickoff after field goal
            kicking_home = game.state.is_home_possession
            kicking_team = home_chart.peripheral.short_name if kicking_home else away_chart.peripheral.short_name

            is_human_kicking = (kicking_home == human_is_home)
            onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

            if onside:
                print(f"\n  {kicking_team} attempts an ONSIDE KICK!")
                outcome = game.onside_kick(kicking_home=kicking_home)
            else:
                print(f"\n  {kicking_team} kicks off...")
                outcome = game.kickoff(kicking_home=kicking_home)
            
            # Handle kickoff penalty decision if applicable
            if outcome.pending_penalty_decision and outcome.penalty_choice:
                is_human_offense = (kicking_home != human_is_home)
                outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)
            
            print(f"  {outcome.description}")
            continue

        # Handle safety - free kick after score
        if outcome.safety:
            print(f"  Score: {game.get_score_str()}")

            # Free kick after safety
            kicking_home = game.state.is_home_possession
            kicking_team = home_chart.peripheral.short_name if kicking_home else away_chart.peripheral.short_name

            print(f"\n  {kicking_team} free kick after safety...")
            outcome = game.safety_free_kick(use_punt=False)
            print(f"  {outcome.description}")
            continue

        # Handle scoring plays (TD, FG, safety) - simplified for resume
        if outcome.touchdown:
            human_scored = is_human_offense
            two_point_allowed = game.season_rules.two_point_conversion

            if human_scored:
                if two_point_allowed:
                    print("\n  *** POINT AFTER TOUCHDOWN ***")
                    print("    [K] Kick extra point (1 point) - DEFAULT")
                    print("    [2] Go for 2-point conversion")
                    choice = input("\n  Your choice (K or 2, Enter for kick): ").strip().upper()
                    if choice == '2':
                        play_type = get_human_offense_play_for_conversion(game)
                        success, def_points, description = game.attempt_two_point(play_type)
                        print(f"\n  {description}")
                    else:
                        success, description = game.attempt_extra_point()
                        print(f"\n  {description}")
                else:
                    success, description = game.attempt_extra_point()
                    print(f"\n  {description}")
            else:
                go_for_two = two_point_allowed and cpu_should_go_for_two(game, cpu_ai)
                if go_for_two:
                    cpu_team = game.state.possession_team.peripheral.short_name
                    print(f"\n  {cpu_team} elects to go for 2-point conversion!")
                    play_type = cpu_ai.select_offense(game) if cpu_ai else PlayType.LINE_PLUNGE
                    if play_type in [PlayType.PUNT, PlayType.FIELD_GOAL]:
                        play_type = PlayType.LINE_PLUNGE
                    success, def_points, description = game.attempt_two_point(play_type)
                    print(f"\n  {description}")
                else:
                    success, description = game.attempt_extra_point()
                    print(f"\n  {description}")

            # Kickoff after score
            print(f"  Score: {game.get_score_str()}")
            
            kicking_home = game.state.is_home_possession
            kicking_team = home_chart.peripheral.short_name if kicking_home else away_chart.peripheral.short_name
            receiving_team = away_chart.peripheral.short_name if kicking_home else home_chart.peripheral.short_name

            is_human_kicking = (kicking_home == human_is_home)
            onside = get_kickoff_choice(game, is_human_kicking, cpu_ai)

            if onside:
                print(f"\n  {kicking_team} attempts an ONSIDE KICK!")
                outcome = game.onside_kick(kicking_home=kicking_home)
            else:
                print(f"\n  {kicking_team} kicks off...")
                outcome = game.kickoff(kicking_home=kicking_home)
            
            # Handle kickoff penalty decision if applicable
            if outcome.pending_penalty_decision and outcome.penalty_choice:
                is_human_offense = (kicking_home != human_is_home)
                outcome = handle_penalty_decision(game, outcome, is_human_offense, human_is_home)
            
            print(f"  {outcome.description}")
            continue

        # Handle turnover on downs (only for regular plays, not punts/kicks)
        # Turnover on downs is when offense fails to convert on 4th down
        is_turnover_on_downs = (
            outcome.down_before == 4 and
            not outcome.first_down and
            not outcome.turnover and  # Not INT/fumble
            not outcome.touchdown and
            not outcome.safety and
            outcome.play_type not in [PlayType.PUNT, PlayType.FIELD_GOAL]
        )
        if is_turnover_on_downs:
            print("\n  *** TURNOVER ON DOWNS ***")

    # Game over
    print("\n" + "=" * 70)
    print("  FINAL")
    print("=" * 70)
    display_box_score(game, "FINAL STATS")

    # Determine winner
    if game.state.home_score > game.state.away_score:
        winner = home_chart.peripheral.short_name
    elif game.state.away_score > game.state.home_score:
        winner = away_chart.peripheral.short_name
    else:
        winner = "TIE"

    if winner != "TIE":
        print(f"\n  {winner} WINS!")
    else:
        print("\n  GAME ENDS IN A TIE!")

    # Print AI opponent analysis summary (hard mode only)
    if cpu_ai and cpu_ai.use_analysis and cpu_ai.opponent_model:
        tracker = cpu_ai.opponent_model.tracker
        total_plays = sum(len(plays) for plays in tracker.situation_plays.values())
        if total_plays > 0:
            total_runs = 0
            total_passes = 0
            for situation, plays in tracker.situation_plays.items():
                for play in plays:
                    if play.value == 'run':
                        total_runs += 1
                    elif play.value == 'pass':
                        total_passes += 1
            
            run_pct = (total_runs / total_plays * 100) if total_plays > 0 else 0
            pass_pct = (total_passes / total_plays * 100) if total_plays > 0 else 0
            
            print("\n" + "=" * 70)
            print("  AI OPPONENT ANALYSIS SUMMARY")
            print("=" * 70)
            print("\n  Opponent (human) play tendencies:")
            print(f"    Total plays tracked: {total_plays}")
            print(f"    Run: {total_runs} ({run_pct:.0f}%)")
            print(f"    Pass: {total_passes} ({pass_pct:.0f}%)")
            
            streak = tracker.get_streak()
            if streak:
                print(f"\n  Current streak detected: {streak.value.upper()} ({streak.value} plays in a row)")
            
            if total_plays >= 5:
                common_situations = [
                    (1, 10, "1st & 10"),
                    (2, 7, "2nd & 7"), 
                    (3, 5, "3rd & 5"),
                    (4, 3, "4th & 3")
                ]
                print("\n  Tendencies by situation:")
                for down, dist, name in common_situations:
                    tendency = tracker.get_tendency(down, dist)
                    if tendency.total_plays > 0:
                        rec = tracker.get_defense_recommendation(down, dist)
                        print(f"    {name}: {tendency.run_plays}R/{tendency.pass_plays}P -> recommend {rec}")
            else:
                print(f"\n  Need more plays to analyze specific situations (have {total_plays}, need 5)")
            
            print("\n  AI used this analysis to help defend against you!")
            
            human_won = (human_is_home and game.state.home_score > game.state.away_score) or \
                        (not human_is_home and game.state.away_score > game.state.home_score)
            if human_won:
                print("\n  Result: You won! The AI learned from its mistakes.")
            else:
                print("\n  Result: AI won! Its analysis helped predict your plays.")

    # Offer to record game to standings
    _offer_record_to_standings(
        year=home_chart.peripheral.year,
        home_team=home_chart.peripheral.team_nickname,
        home_score=game.state.home_score,
        away_team=away_chart.peripheral.team_nickname,
        away_score=game.state.away_score,
        week=week
    )


if __name__ == "__main__":
    run_interactive_game()
