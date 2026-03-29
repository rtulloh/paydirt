"""
Command-line interface for Paydirt using actual team charts.
"""
import sys
from typing import Optional
from .packaging import get_seasons_path

from .chart_loader import load_team_chart, find_team_charts
from .game_engine import PaydirtGameEngine, PlayOutcome
from .play_resolver import PlayType, DefenseType
from .utils import ordinal


def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


def print_header():
    """Print the game header."""
    print("=" * 60)
    print("  PAYDIRT - Football Board Game Simulation")
    print("  Using Actual Team Charts")
    print("=" * 60)
    print()


def print_scoreboard(game: PaydirtGameEngine):
    """Print the current scoreboard."""
    status = game.get_status()

    print("-" * 50)
    print(f"  Q{status['quarter']}  {status['time']}")
    print(f"  {status['score']}")
    print("-" * 50)
    print(f"  {status['possession']} ball at {status['field_position']}")
    print(f"  {_ordinal(status['down'])} & {status['yards_to_go']}")
    print("-" * 50)


# _ordinal is now imported from utils as ordinal
_ordinal = ordinal


def print_play_menu():
    """Print the offensive play selection menu."""
    print("\nSelect your play:")
    print("  [1] Line Plunge     [6] Short Pass")
    print("  [2] Off Tackle      [7] Medium Pass")
    print("  [3] End Run         [8] Long Pass")
    print("  [4] Draw            [9] TE Short/Long")
    print("  [5] Screen")
    print("  [P] Punt           [F] Field Goal")
    print("  [Q] Quit game")


def print_defense_menu():
    """Print the defensive formation menu."""
    print("\nSelect defensive formation:")
    print("  [A] Standard       [D] Short Pass Defense")
    print("  [B] Short Yardage  [E] Long Pass Defense")
    print("  [C] Spread         [F] Blitz")


def get_play_choice() -> Optional[PlayType]:
    """Get the user's play selection."""
    play_map = {
        "1": PlayType.LINE_PLUNGE,
        "2": PlayType.OFF_TACKLE,
        "3": PlayType.END_RUN,
        "4": PlayType.DRAW,
        "5": PlayType.SCREEN,
        "6": PlayType.SHORT_PASS,
        "7": PlayType.MEDIUM_PASS,
        "8": PlayType.LONG_PASS,
        "9": PlayType.TE_SHORT_LONG,
        "P": PlayType.PUNT,
        "F": PlayType.FIELD_GOAL,
    }

    while True:
        choice = input("\nYour play: ").strip().upper()
        if choice == "Q":
            return None
        if choice in play_map:
            return play_map[choice]
        print("Invalid choice. Please enter 1-9, P, F, or Q.")


def get_defense_choice() -> DefenseType:
    """Get the user's defensive formation selection."""
    defense_map = {
        "A": DefenseType.STANDARD,
        "B": DefenseType.SHORT_YARDAGE,
        "C": DefenseType.SPREAD,
        "D": DefenseType.SHORT_PASS,
        "E": DefenseType.LONG_PASS,
        "F": DefenseType.BLITZ,
        "1": DefenseType.STANDARD,
        "2": DefenseType.SHORT_YARDAGE,
        "3": DefenseType.SPREAD,
        "4": DefenseType.SHORT_PASS,
        "5": DefenseType.LONG_PASS,
        "6": DefenseType.BLITZ,
    }

    while True:
        choice = input("\nDefense (A-F): ").strip().upper()
        if choice in defense_map:
            return defense_map[choice]
        print("Invalid choice. Please enter A-F.")


def print_play_result(outcome: PlayOutcome):
    """Print the result of a play."""
    print()
    print("=" * 50)

    play_name = outcome.play_type.value.replace("_", " ").title()
    print(f"PLAY: {play_name}")

    if outcome.result.dice_roll:
        print(f"Dice Roll: {outcome.result.dice_roll}")

    print(f"Result: {outcome.description}")

    if outcome.yards_gained > 0:
        print(f"GAIN of {outcome.yards_gained} yards!")
    elif outcome.yards_gained < 0:
        print(f"LOSS of {abs(outcome.yards_gained)} yards!")

    if outcome.first_down:
        print("FIRST DOWN!")

    if outcome.touchdown:
        print("\n*** TOUCHDOWN! ***")
    elif outcome.turnover:
        print("\n*** TURNOVER! ***")
    elif outcome.safety:
        print("\n*** SAFETY! ***")

    print(f"Ball at: {outcome.field_position_after}")
    print("=" * 50)


def select_team(seasons_dir: str, prompt: str) -> str:
    """Let user select a team from available charts."""
    charts = find_team_charts(seasons_dir)

    if not charts:
        print(f"No team charts found in {seasons_dir}")
        print("Please add team chart CSV files to seasons/<year>/<team>/ directories")
        sys.exit(1)

    print(f"\n{prompt}")
    print("-" * 50)
    for i, (year, team, path) in enumerate(charts, 1):
        print(f"  [{i:2d}] {year} {team}")
    print("-" * 50)

    while True:
        choice = input("\nSelect team number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(charts):
                return charts[idx][2]  # Return the path
        except ValueError:
            pass
        print("Invalid choice. Please enter a valid team number.")


def play_interactive_game(seasons_dir: Optional[str] = None):
    """Run an interactive game using team charts."""
    if seasons_dir is None:
        seasons_dir = str(get_seasons_path())
    clear_screen()
    print_header()

    # Select teams
    print("\n--- TEAM SELECTION ---")
    away_path = select_team(seasons_dir, "Select AWAY team:")
    home_path = select_team(seasons_dir, "Select HOME team:")

    # Load team charts
    print("\nLoading team charts...")
    away_chart = load_team_chart(away_path)
    home_chart = load_team_chart(home_path)

    print(f"\n{away_chart.full_name} @ {home_chart.full_name}")
    print(f"Power Ratings: {away_chart.peripheral.power_rating} vs {home_chart.peripheral.power_rating}")
    input("\nPress Enter to start the game...")

    # Create game
    game = PaydirtGameEngine(home_chart, away_chart)

    # Opening kickoff (home team kicks to away team)
    clear_screen()
    print_header()
    print("\n*** OPENING KICKOFF ***")
    print(f"{home_chart.short_name} kicks off to {away_chart.short_name}")
    outcome = game.kickoff(kicking_home=True)
    print_play_result(outcome)
    input("\nPress Enter to continue...")

    # Main game loop
    while not game.state.game_over:
        clear_screen()
        print_header()
        print_scoreboard(game)

        offense_name = game.state.possession_team.full_name
        defense_name = game.state.defense_team.full_name

        print(f"\n{offense_name} on OFFENSE")
        print(f"{defense_name} on DEFENSE")

        # Get offensive play
        print_play_menu()
        play_type = get_play_choice()

        if play_type is None:
            print("\nGame ended by user.")
            break

        # Get defensive call (in a real 2-player game, this would be hidden)
        print_defense_menu()
        defense_type = get_defense_choice()

        # Run the play
        outcome = game.run_play(play_type, defense_type)
        print_play_result(outcome)

        # Handle post-touchdown
        if outcome.touchdown:
            print("\nChoose: [1] Extra Point  [2] Two-Point Conversion")
            pat_choice = input("Your choice: ").strip()

            if pat_choice == "2":
                print_play_menu()
                two_pt_play = get_play_choice()
                if two_pt_play and two_pt_play not in [PlayType.PUNT, PlayType.FIELD_GOAL]:
                    success, _def_pts, _desc = game.attempt_two_point(two_pt_play)
                    print("Two-point conversion GOOD!" if success else "Two-point conversion FAILED!")
                else:
                    success, _ = game.attempt_extra_point()
                    print("Extra point GOOD!" if success else "Extra point NO GOOD!")
            else:
                success, _ = game.attempt_extra_point()
                print("Extra point GOOD!" if success else "Extra point NO GOOD!")

            print(f"\nScore: {game.get_score_str()}")

            # Kickoff after score
            print("\n*** KICKOFF ***")
            # Scoring team kicks off
            outcome = game.kickoff(kicking_home=game.state.is_home_possession)
            print_play_result(outcome)

        input("\nPress Enter to continue...")

    # Game over
    clear_screen()
    print_header()
    print("\n*** FINAL SCORE ***")
    print_scoreboard(game)

    print("\n--- GAME STATISTICS ---")
    print(f"\n{game.state.away_chart.full_name}:")
    print(f"  Total Yards: {game.state.away_stats.total_yards}")
    print(f"  Rushing: {game.state.away_stats.rushing_yards}")
    print(f"  Passing: {game.state.away_stats.passing_yards}")
    print(f"  Turnovers: {game.state.away_stats.turnovers}")
    print(f"  First Downs: {game.state.away_stats.first_downs}")

    print(f"\n{game.state.home_chart.full_name}:")
    print(f"  Total Yards: {game.state.home_stats.total_yards}")
    print(f"  Rushing: {game.state.home_stats.rushing_yards}")
    print(f"  Passing: {game.state.home_stats.passing_yards}")
    print(f"  Turnovers: {game.state.home_stats.turnovers}")
    print(f"  First Downs: {game.state.home_stats.first_downs}")


def quick_demo(seasons_dir: Optional[str] = None):
    """Run a quick demo showing the chart system."""
    if seasons_dir is None:
        seasons_dir = str(get_seasons_path())
    print_header()

    charts = find_team_charts(seasons_dir)
    if not charts:
        print(f"No team charts found in {seasons_dir}")
        return

    # Load first available chart
    year, team, path = charts[0]
    print(f"Loading {year} {team}...")
    chart = load_team_chart(path)

    print(f"\nTeam: {chart.full_name}")
    print(f"Power Rating: {chart.peripheral.power_rating}")
    print(f"Yardage Factors: {chart.peripheral.base_yardage_factor}/{chart.peripheral.reduced_yardage_factor}")

    print("\n--- Sample Offense Chart Data ---")
    print("Dice Roll | Line Plunge | Off Tackle | Short Pass | Long Pass")
    print("-" * 65)
    for roll in range(10, 20):
        lp = chart.offense.line_plunge.get(roll, "")
        ot = chart.offense.off_tackle.get(roll, "")
        sp = chart.offense.short_pass.get(roll, "")
        lg = chart.offense.long_pass.get(roll, "")
        print(f"    {roll:2d}    | {lp:^11s} | {ot:^10s} | {sp:^10s} | {lg:^9s}")

    print("\n--- Running Sample Plays ---")
    game = PaydirtGameEngine(chart, chart)
    game.kickoff(kicking_home=True)

    plays = [
        (PlayType.LINE_PLUNGE, DefenseType.STANDARD),
        (PlayType.SHORT_PASS, DefenseType.SHORT_PASS),
        (PlayType.LONG_PASS, DefenseType.LONG_PASS),
        (PlayType.END_RUN, DefenseType.BLITZ),
    ]

    for play_type, def_type in plays:
        outcome = game.run_play(play_type, def_type)
        print(f"\n{play_type.value} vs {def_type.value}:")
        print(f"  Roll: {outcome.result.dice_roll}, Result: {outcome.description}")
        print(f"  Yards: {outcome.yards_gained}, Position: {outcome.field_position_after}")


def main():
    """Main entry point."""
    # Determine seasons directory
    seasons_dir = str(get_seasons_path())

    print_header()

    charts = find_team_charts(seasons_dir)
    if not charts:
        print(f"No team charts found in '{seasons_dir}'")
        print("\nTo use this game, you need team chart CSV files.")
        print("Place them in: seasons/<year>/<team>/")
        print("Required files:")
        print("  - OFFENSE-Table 1.csv")
        print("  - DEFENSE-Table 1.csv")
        print("  - PERIPHERAL DATA-Table 1.csv")
        sys.exit(1)

    print(f"Found {len(charts)} team chart(s)")
    print("\nSelect mode:")
    print("  [1] Interactive game")
    print("  [2] Quick demo")
    print("  [0] Exit")

    choice = input("\nYour choice: ").strip()

    if choice == "1":
        play_interactive_game(seasons_dir)
    elif choice == "2":
        quick_demo(seasons_dir)
    elif choice == "0":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice.")
        sys.exit(1)


if __name__ == "__main__":
    main()
