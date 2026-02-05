"""
Entry point for running the paydirt package as a module.
Usage: python -m paydirt [--play [-d easy|medium|hard] [--compact] | --load [file] | -auto team1 team2]
"""
import sys

def main():
    """Main entry point - choose between interactive, chart-based, or simple mode."""
    # Check for --load flag to resume a saved game
    if len(sys.argv) > 1 and sys.argv[1] in ['--load', '-l', 'load']:
        # Get optional save file path
        save_file = None
        if len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
            save_file = sys.argv[2]
        
        from .interactive_game import resume_game
        resume_game(save_file)
        return

    # Check for --play flag for interactive mode
    if len(sys.argv) > 1 and sys.argv[1] in ['--play', '-p', 'play']:
        # Parse optional flags
        difficulty = 'medium'  # default
        compact = False

        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] in ['-d', '--difficulty']:
                if i + 1 < len(args) and args[i + 1] in ['easy', 'medium', 'hard']:
                    difficulty = args[i + 1]
                    i += 2
                else:
                    print("Usage: python -m paydirt --play [-d easy|medium|hard] [--compact]")
                    print("  Difficulty levels:")
                    print("    easy   - CPU makes conservative decisions")
                    print("    medium - Balanced CPU play calling (default)")
                    print("    hard   - CPU makes aggressive, optimal decisions")
                    print("  Display modes:")
                    print("    --compact - Use compact display (less verbose)")
                    return
            elif args[i] in ['--compact', '-c']:
                compact = True
                i += 1
            else:
                i += 1

        from .interactive_game import run_interactive_game
        run_interactive_game(difficulty=difficulty, compact=compact)
        return

    # Check for -auto flag for CPU vs CPU mode
    if len(sys.argv) >= 4 and sys.argv[1] in ['--auto', '-auto', '-a', 'auto']:
        team1_name = sys.argv[2]
        team2_name = sys.argv[3]
        from .auto_game import run_auto_game
        run_auto_game(team1_name, team2_name)
        return

    # Show help if -auto with wrong args
    if len(sys.argv) > 1 and sys.argv[1] in ['--auto', '-auto', '-a', 'auto']:
        print("Usage: python -m paydirt -auto <team1> <team2>")
        print("\nExamples:")
        print("  python -m paydirt -auto Bears Cowboys              # Simple team names")
        print("  python -m paydirt -auto 1983/Bears 1983/Cowboys    # With season")
        print("  python -m paydirt -auto seasons/1983/Bears seasons/1985/Cowboys  # Full paths")
        print("\nAvailable teams can be found in the seasons/ directory")
        return

    # Try chart-based mode first if team charts are available
    try:
        from .chart_loader import find_team_charts
        from pathlib import Path

        # Check for team charts
        seasons_dir = "seasons"
        if not Path(seasons_dir).exists():
            script_dir = Path(__file__).parent.parent
            seasons_dir = str(script_dir / "seasons")

        charts = find_team_charts(seasons_dir)

        if charts:
            # Show menu
            print("PAYDIRT - Football Simulation")
            print("-" * 40)
            print("  1. Play Interactive Game (Human vs CPU)")
            print("  2. Watch Simulation")
            print("  3. Exit")
            print()

            choice = input("Select option: ").strip()

            if choice == '1':
                # Ask for difficulty
                print("\nSelect CPU difficulty:")
                print("  [1] Easy   - CPU makes conservative decisions")
                print("  [2] Medium - Balanced CPU play calling (default)")
                print("  [3] Hard   - CPU makes aggressive, optimal decisions")
                print("  [Enter] = Medium")
                diff_choice = input("\nDifficulty: ").strip()
                difficulty = {'1': 'easy', '2': 'medium', '3': 'hard'}.get(diff_choice, 'medium')
                from .interactive_game import run_interactive_game
                run_interactive_game(difficulty=difficulty)
            elif choice == '2':
                from .cli_charts import main as charts_main
                charts_main()
            else:
                print("Goodbye!")
        else:
            # Fall back to simple CLI
            from .cli import main as simple_main
            simple_main()
    except ImportError as e:
        print(f"Import error: {e}")
        # Fall back to simple CLI
        from .cli import main as simple_main
        simple_main()


if __name__ == "__main__":
    main()
