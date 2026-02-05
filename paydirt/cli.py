"""
Command-line interface for Paydirt football game.
"""
import sys
from typing import Optional

from .models import PlayType, DefenseType
from .teams import get_team, list_teams
from .game import PaydirtGame, simulate_drive
from .utils import ordinal


def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


def print_header():
    """Print the game header."""
    print("=" * 60)
    print("  PAYDIRT - Football Board Game Simulation")
    print("  Based on the classic Avalon Hill game")
    print("=" * 60)
    print()


def print_scoreboard(game: PaydirtGame):
    """Print the current scoreboard."""
    status = game.get_game_status()

    print("-" * 50)
    print(f"  Q{status['quarter']}  {status['time_remaining']}")
    print(f"  {status['score']['away']['team']}: {status['score']['away']['score']:2d}  |  "
          f"{status['score']['home']['team']}: {status['score']['home']['score']:2d}")
    print("-" * 50)
    print(f"  {status['possession']} ball at {status['ball_position']}")
    print(f"  {_ordinal(status['down'])} & {status['yards_to_go']}")
    print("-" * 50)


# _ordinal is now imported from utils as ordinal
_ordinal = ordinal


def print_play_menu():
    """Print the offensive play selection menu."""
    print("\nSelect your play:")
    print("  [1] Run Left       [5] Medium Pass")
    print("  [2] Run Middle     [6] Long Pass")
    print("  [3] Run Right      [7] Screen Pass")
    print("  [4] Short Pass     [8] Draw")
    print("  [9] Punt          [10] Field Goal")
    print("  [0] Quit game")


def print_defense_menu():
    """Print the defensive formation menu."""
    print("\nSelect defensive formation:")
    print("  [1] Normal    [2] Prevent")
    print("  [3] Blitz     [4] Goal Line")


def get_play_choice() -> Optional[PlayType]:
    """Get the user's play selection."""
    play_map = {
        "1": PlayType.RUN_LEFT,
        "2": PlayType.RUN_MIDDLE,
        "3": PlayType.RUN_RIGHT,
        "4": PlayType.SHORT_PASS,
        "5": PlayType.MEDIUM_PASS,
        "6": PlayType.LONG_PASS,
        "7": PlayType.SCREEN_PASS,
        "8": PlayType.DRAW,
        "9": PlayType.PUNT,
        "10": PlayType.FIELD_GOAL,
    }

    while True:
        choice = input("\nYour play (1-10, 0 to quit): ").strip()
        if choice == "0":
            return None
        if choice in play_map:
            return play_map[choice]
        print("Invalid choice. Please enter 1-10.")


def get_defense_choice() -> DefenseType:
    """Get the user's defensive formation selection."""
    defense_map = {
        "1": DefenseType.NORMAL,
        "2": DefenseType.PREVENT,
        "3": DefenseType.BLITZ,
        "4": DefenseType.GOAL_LINE,
    }

    while True:
        choice = input("\nDefense (1-4): ").strip()
        if choice in defense_map:
            return defense_map[choice]
        print("Invalid choice. Please enter 1-4.")


def print_play_result(result: dict):
    """Print the result of a play."""
    print()
    print("=" * 50)

    if result.get("type") == "kickoff":
        print(f"KICKOFF: {result['receiving_team']} returns it {result['return_yards']} yards")
        if result.get("touchdown"):
            print("TOUCHDOWN! Kickoff return for a score!")

    elif result.get("type") == "punt":
        print(f"PUNT: {result['punt_distance']} yards")
        if result.get("touchback"):
            print("Touchback!")
        print(f"Ball at {result['ball_position_after']}")

    elif result.get("type") == "field_goal":
        print(f"FIELD GOAL ATTEMPT: {result['distance']} yards")
        if result["success"]:
            print("IT'S GOOD!")
        else:
            print("NO GOOD! Wide!")

    elif result.get("type") == "extra_point":
        if result["success"]:
            print("Extra point is GOOD!")
        else:
            print("Extra point MISSED!")

    elif result.get("type") == "two_point_conversion":
        if result["success"]:
            print("Two-point conversion SUCCESSFUL!")
        else:
            print("Two-point conversion FAILED!")

    else:
        # Regular play
        play_name = result.get("play_type", "").replace("_", " ").title()
        print(f"PLAY: {play_name}")
        print(f"Dice Roll: {result['dice_roll']}")
        print(f"Result: {result['description']}")

        if result.get("yards", 0) > 0:
            print(f"GAIN of {result['yards']} yards!")
        elif result.get("yards", 0) < 0:
            print(f"LOSS of {abs(result['yards'])} yards!")
        else:
            print("No gain on the play.")

        if result.get("touchdown"):
            print("\n*** TOUCHDOWN! ***")
        elif result.get("turnover"):
            print(f"\n*** TURNOVER! {result['new_possession']} takes over! ***")
        elif result.get("safety"):
            print("\n*** SAFETY! ***")

    if "score" in result:
        print(f"\nScore: {result['score']}")

    print("=" * 50)


def select_team(prompt: str) -> str:
    """Let user select a team."""
    teams = list_teams()

    print(f"\n{prompt}")
    print("-" * 40)
    for i, (abbr, name, rating) in enumerate(teams, 1):
        print(f"  [{i:2d}] {abbr:4s} - {name} (PWR: {rating})")
    print("-" * 40)

    while True:
        choice = input("\nSelect team number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(teams):
                return teams[idx][0]
        except ValueError:
            pass
        print("Invalid choice. Please enter a valid team number.")


def play_interactive_game():
    """Run an interactive two-player game."""
    clear_screen()
    print_header()

    # Select teams
    print("\n--- TEAM SELECTION ---")
    away_abbr = select_team("Select AWAY team:")
    home_abbr = select_team("Select HOME team:")

    away_team = get_team(away_abbr)
    home_team = get_team(home_abbr)

    print(f"\n{away_team.name} @ {home_team.name}")
    input("\nPress Enter to start the game...")

    # Create game
    game = PaydirtGame(home_team, away_team)

    # Opening kickoff
    clear_screen()
    print_header()
    print("\n*** OPENING KICKOFF ***")
    result = game.kickoff(receiving_team_is_home=False)
    print_play_result(result)
    input("\nPress Enter to continue...")

    # Main game loop
    while not game.state.game_over:
        clear_screen()
        print_header()
        print_scoreboard(game)

        # Determine who is calling plays
        is_home_offense = game.state.is_home_possession
        offense_name = game.home_team.name if is_home_offense else game.away_team.name
        defense_name = game.away_team.name if is_home_offense else game.home_team.name

        print(f"\n{offense_name} on OFFENSE")
        print(f"{defense_name} on DEFENSE")

        # Get offensive play
        print_play_menu()
        play_type = get_play_choice()

        if play_type is None:
            print("\nGame ended by user.")
            break

        # Get defensive call
        print_defense_menu()
        defense_type = get_defense_choice()

        # Run the play
        result = game.run_play(play_type, defense_type)
        print_play_result(result)

        # Handle post-touchdown
        if result.get("touchdown"):
            print("\nChoose: [1] Extra Point  [2] Two-Point Conversion")
            pat_choice = input("Your choice: ").strip()

            if pat_choice == "2":
                print_play_menu()
                two_pt_play = get_play_choice()
                if two_pt_play and two_pt_play not in [PlayType.PUNT, PlayType.FIELD_GOAL]:
                    pat_result = game.attempt_two_point_conversion(two_pt_play)
                else:
                    pat_result = game.attempt_extra_point()
            else:
                pat_result = game.attempt_extra_point()

            print_play_result(pat_result)

            # Kickoff after score
            print("\n*** KICKOFF ***")
            ko_result = game.kickoff(receiving_team_is_home=not is_home_offense)
            print_play_result(ko_result)

        input("\nPress Enter to continue...")

    # Game over
    clear_screen()
    print_header()
    print("\n*** FINAL SCORE ***")
    print_scoreboard(game)

    print("\n--- GAME STATISTICS ---")
    stats = game.get_stats()
    for side in ["away", "home"]:
        s = stats[side]
        print(f"\n{s['team']}:")
        print(f"  Total Yards: {s['total_yards']}")
        print(f"  Rushing: {s['rushing_yards']} | Passing: {s['passing_yards']}")
        print(f"  Turnovers: {s['turnovers']}")


def play_simulated_game():
    """Run a fully simulated game between two teams."""
    clear_screen()
    print_header()

    # Select teams
    print("\n--- TEAM SELECTION ---")
    away_abbr = select_team("Select AWAY team:")
    home_abbr = select_team("Select HOME team:")

    away_team = get_team(away_abbr)
    home_team = get_team(home_abbr)

    print(f"\n{away_team.name} @ {home_team.name}")
    print("\nSimulating game...")

    # Create game
    game = PaydirtGame(home_team, away_team)

    # Opening kickoff
    game.kickoff(receiving_team_is_home=False)

    # Simulate until game over
    drive_count = 0
    max_drives = 30  # Safety limit

    while not game.state.game_over and drive_count < max_drives:
        drive_count += 1
        results = simulate_drive(game)

        # Handle scoring
        for result in results:
            if result.get("touchdown"):
                # Auto extra point
                game.attempt_extra_point()
                # Kickoff
                game.kickoff(receiving_team_is_home=not game.state.is_home_possession)
                break
            elif result.get("type") == "field_goal" and result.get("success"):
                game.kickoff(receiving_team_is_home=not game.state.is_home_possession)
                break

    # Print final results
    print("\n*** FINAL SCORE ***")
    print_scoreboard(game)

    print("\n--- GAME STATISTICS ---")
    stats = game.get_stats()
    for side in ["away", "home"]:
        s = stats[side]
        print(f"\n{s['team']}:")
        print(f"  Total Yards: {s['total_yards']}")
        print(f"  Rushing: {s['rushing_yards']} | Passing: {s['passing_yards']}")
        print(f"  Turnovers: {s['turnovers']}")


def main():
    """Main entry point for the CLI."""
    print_header()

    print("Select game mode:")
    print("  [1] Interactive (two players)")
    print("  [2] Simulated (watch AI play)")
    print("  [3] Quick simulation (just show final score)")
    print("  [0] Exit")

    choice = input("\nYour choice: ").strip()

    if choice == "1":
        play_interactive_game()
    elif choice == "2":
        play_simulated_game()
    elif choice == "3":
        play_simulated_game()
    elif choice == "0":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice.")
        sys.exit(1)


if __name__ == "__main__":
    main()
