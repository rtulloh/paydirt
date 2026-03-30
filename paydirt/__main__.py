"""
Entry point for running the paydirt package as a module.
Usage: python -m paydirt [--play [-d easy|medium|hard] [--compact] | --load [file] | --auto away home | --web [--port PORT]]
"""
import sys
import os
import webbrowser
import threading
import time
from .packaging import get_seasons_path

# Pre-import uvicorn for PyInstaller bundling
try:
    import uvicorn
except ImportError as e:
    print(f"Warning: uvicorn not available: {e}")


def get_web_static_path():
    """Get the path to web static files (works both in development and bundled)."""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller
            return os.path.join(sys._MEIPASS, 'web_static')
        else:
            # cx_Freeze or similar
            return os.path.join(os.path.dirname(sys.executable), 'web_static')
    else:
        # Running in development
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'paydirt-web', 'backend', 'web_static')


def start_web_server(port=8000, open_browser=True):
    """Start the web server in a separate thread."""
    def run_server():
        global uvicorn
        try:
            import uvicorn
        except ImportError as e:
            print(f"Error: uvicorn not installed. Install with: pip install uvicorn")
            print(f"Details: {e}")
            return
        
        # Find the backend path - either in development or bundled
        if getattr(sys, 'frozen', False):
            # Running as bundled executable
            if hasattr(sys, '_MEIPASS'):
                backend_path = os.path.join(sys._MEIPASS, 'paydirt-web', 'backend')
            else:
                backend_path = os.path.join(os.path.dirname(sys.executable), 'paydirt-web', 'backend')
        else:
            # Running in development
            backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'paydirt-web', 'backend')
        
        print(f"Backend path: {backend_path}")
        sys.path.insert(0, backend_path)
        
        # Import and configure the app to serve static files
        from fastapi.responses import FileResponse
        from fastapi import Request
        
        # Import the existing app using importlib
        import importlib.util
        main_file = os.path.join(backend_path, 'main.py')
        print(f"Loading main.py from: {main_file}")
        print(f"main.py exists: {os.path.exists(main_file)}")
        print(f"Is file: {os.path.isfile(main_file)}")
        print(f"List backend dir: {os.listdir(backend_path)}")
        
        spec = importlib.util.spec_from_file_location("main", main_file)
        web_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(web_main)
        
        app = web_main.app
        
        # Add static file serving
        web_static_path = get_web_static_path()
        print(f"Web static path: {web_static_path}")
        print(f"Web static exists: {os.path.exists(web_static_path)}")
        
        # Create a catch-all route to serve index.html for SPA
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str, request: Request):
            # Check if the file exists in web_static
            file_path = os.path.join(web_static_path, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # Otherwise serve index.html for SPA routing
            index_path = os.path.join(web_static_path, 'index.html')
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            print(f"Not found: {full_path}, looking in {web_static_path}")
            return {"detail": "Not found"}
        
        # Also serve root
        @app.get("/")
        async def serve_root():
            index_path = os.path.join(web_static_path, 'index.html')
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            return {"detail": "Web interface not found. Please run 'python -m paydirt' to use CLI mode."}
        
        # Start uvicorn
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    
    # Start server in a thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    url = f"http://127.0.0.1:{port}"
    print("\n🎮 Starting Paydirt Web Interface...")
    print(f"   Open {url} in your browser\n")
    
    if open_browser:
        webbrowser.open(url)
    
    return server_thread


def main():
    """Main entry point - choose between interactive, chart-based, web, or simple mode."""
    # If no arguments (e.g., double-clicked app), default to web mode
    if len(sys.argv) == 1:
        print("Starting Paydirt Web Interface...")
        start_web_server(port=8000, open_browser=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        return
    
    # Check for --web flag first
    if '--web' in sys.argv or '-w' in sys.argv:
        port = 8000
        open_browser = True
        
        # Parse --web options
        web_args = [a for a in sys.argv[1:] if a not in ['--web', '-w']]
        for i, arg in enumerate(web_args):
            if arg == '--port' and i + 1 < len(web_args):
                try:
                    port = int(web_args[i + 1])
                except ValueError:
                    print(f"Error: --port requires a number, got '{web_args[i + 1]}'")
                    return
            elif arg == '--no-browser':
                open_browser = False
        
        start_web_server(port=port, open_browser=open_browser)
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down web server...")
        return
    
    # Check for --help or -h first
    if '--help' in sys.argv or '-h' in sys.argv:
        print("PAYDIRT - Football Board Game Simulation")
        print("=" * 50)
        print("\nUsage:")
        print("  python -m paydirt -p [options]               # Interactive game")
        print("  python -m paydirt -a <away> <home> [opts]  # CPU vs CPU simulation")
        print("  python -m paydirt --web [--port PORT]       # Web interface (browser)")
        print("  python -m paydirt --teams                   # List available teams")
        print("  python -m paydirt --simulate                # Run season simulation")
        print("  python -m paydirt --scaffold-season <year>  # Create season rules YAML")
        print("  python -m paydirt -l [file]                 # Resume saved game")
        print("\nPositional Arguments:")
        print("  away-team          Away team (e.g., 2026/Ironclads)")
        print("  home-team         Home team (e.g., 2026/Thunderhawks)")
        print("\nCommands:")
        print("  -p, --play        Interactive game")
        print("  -a, --auto        CPU vs CPU simulation")
        print("  --web             Web interface (browser)")
        print("  -l, --load        Resume saved game")
        print("  --teams           List available teams")
        print("  --simulate        Run season simulation")
        print("\nOptions:")
        print("  -d, --difficulty  CPU difficulty (easy|medium|hard)")
        print("  -c, --compact     Compact display")
        print("  -h, --help        Show this help message")
        print("  -H, --home <team>   Home team")
        print("  -A, --away <team>   Away team")
        print("  --playoff-game    Playoff game (no ties in OT)")
        print("  --web             Launch web interface")
        print("  --port <port>     Port for web server (default: 8000)")
        print("  --no-browser      Don't open browser automatically")
        print("  -w, --week        Week number for standings")
        print("  -r, --record      Record result to standings")
        print("  -y, --year        Season year for simulation (e.g., 2026)")
        print("\nNote: In interactive mode, the human player commands the first team listed.")
        print("\nExamples:")
        print("  python -m paydirt -p                   # menus to select teams")
        print("  python -m paydirt -p -H 2026/Ironclads -A 2026/Thunderhawks  # you are Ironclads")
        print("  python -m paydirt -p -H 2026/Thunderhawks -A 2026/Ironclads  # you are Thunderhawks")
        print("  python -m paydirt -a 2026/Ironclads 2026/Thunderhawks  # away @ home")
        print("  python -m paydirt -a 2026/Ironclads 2026/Thunderhawks --playoff-game")
        print("  python -m paydirt --scaffold-season 1995")
        return

    # Check for --scaffold-season
    if '--scaffold-season' in sys.argv:
        idx = sys.argv.index('--scaffold-season')
        force = '--force' in sys.argv
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('-'):
            year_str = sys.argv[idx + 1]
            try:
                year = int(year_str)
            except ValueError:
                print(f"Error: --scaffold-season requires a year (integer), got '{year_str}'")
                return
            from .season_rules import scaffold_season_rules
            seasons_dir = get_seasons_path()
            season_dir = seasons_dir / str(year)
            yaml_path = season_dir / f"{year}.yaml"
            if yaml_path.exists() and not force:
                print(f"Error: {yaml_path} already exists. Use --force to overwrite.")
                return
            season_dir.mkdir(parents=True, exist_ok=True)
            yaml_content = scaffold_season_rules(year)
            yaml_path.write_text(yaml_content, encoding="utf-8")
            print(f"Created {yaml_path}")
            return
        else:
            print("Error: --scaffold-season requires a year argument")
            print("Usage: python -m paydirt --scaffold-season <year> [--force]")
            return

    if len(sys.argv) > 1 and sys.argv[1] in ['--load', 'load']:
        # Get optional save file path
        save_file = None
        if len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
            save_file = sys.argv[2]
        
        from .interactive_game import resume_game
        resume_game(save_file)
        return

    # Check for --auto/-a flag for CPU vs CPU mode
    if len(sys.argv) >= 2 and sys.argv[1] in ['--auto', '-a', 'auto']:
        # Check for --playoff-game flag
        is_playoff = '--playoff-game' in sys.argv or '--playoff' in sys.argv
        
        # Extract team specs (filter out flags)
        team_args = [arg for arg in sys.argv[2:] if not arg.startswith('-')]
        if len(team_args) >= 2:
            team1_name = team_args[0]
            team2_name = team_args[1]
            from .auto_game import run_auto_game
            run_auto_game(team1_name, team2_name, is_playoff=is_playoff)
            return
        else:
            print("Usage: python -m paydirt --auto <away> <home> [--playoff-game]")
            print("  or:   python -m paydirt -a <away> <home> [--playoff-game]")
            print("\nExamples:")
            print("  python -m paydirt --auto 2026/Ironclads 2026/Thunderhawks")
            print("  python -m paydirt --auto 2026/Ironclads 2026/Thunderhawks --playoff-game")
            return

    # Check for --play/-p flag for interactive mode
    if len(sys.argv) > 1 and sys.argv[1] in ['--play', '-p', 'play']:
        # Parse optional flags
        difficulty = 'medium'  # default
        compact = False
        load_save = False
        save_file = None
        week = 0  # 0 means auto-assign
        home_team = None
        away_team = None
        human_is_home = True  # default to human at home
        is_playoff = False  # Track if this is a playoff game

        args = sys.argv[2:]
        i = 0
        # Check for --help first
        if '--help' in args:
            print("Usage: python -m paydirt --play [-d easy|medium|hard] [--compact] [--load [file]] [--week N] [--record] [--home team] [--away team] [--playoff-game]")
            print("  Difficulty levels:")
            print("    easy   - CPU makes conservative decisions")
            print("    medium - Balanced CPU play calling (default)")
            print("    hard   - CPU makes aggressive, optimal decisions")
            print("  Display modes:")
            print("    --compact - Use compact display (less verbose)")
            print("  Save/Load:")
            print("    --load [file] - Resume a saved game (default: paydirt_save.json)")
            print("  Standings:")
            print("    --week N   - Week number for recording to standings")
            print("    --record   - Prompt to record game to standings at end")
            print("  Teams:")
            print("    --home team - Your team (e.g., --home Chargers)")
            print("    --away team - Opponent team (e.g., --away Seahawks)")
            print("    Use team name or season/team (e.g., --home 1983/Chargers)")
            print("    Note: The human player commands --home team")
            print("  Playoff:")
            print("    --playoff-game - This is a playoff game (affects overtime rules)")
            return

        while i < len(args):
            if args[i] in ['-d', '--difficulty']:
                if i + 1 < len(args):
                    difficulty = args[i + 1]
                    if difficulty not in ['easy', 'medium', 'hard']:
                        print(f"Error: -d/--difficulty must be easy, medium, or hard, got '{difficulty}'")
                        return
                    i += 2
                else:
                    print("Error: -d/--difficulty requires a value (easy, medium, or hard)")
                    return
            elif args[i] in ['--compact', '-c']:
                compact = True
                i += 1
            elif args[i] in ['--load', '-l']:
                load_save = True
                # Check if next arg is a filename (not another flag)
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    save_file = args[i + 1]
                    i += 2
                else:
                    i += 1
            elif args[i] in ['--week', '-w']:
                if i + 1 < len(args):
                    try:
                        week = int(args[i + 1])
                        i += 2
                    except ValueError:
                        print(f"Error: --week requires a number, got '{args[i + 1]}'")
                        return
                else:
                    print("Error: --week requires a number")
                    return
            elif args[i] in ['--record', '-r']:
                i += 1
            elif args[i] in ['--home', '-H']:
                if i + 1 < len(args):
                    home_team = args[i + 1]
                    i += 2
                else:
                    print("Error: --home requires a team name")
                    return
            elif args[i] in ['--away', '-A']:
                if i + 1 < len(args):
                    away_team = args[i + 1]
                    i += 2
                else:
                    print("Error: --away requires a team name")
                    return
            elif args[i] in ['--playoff-game', '--playoff']:
                # This is a playoff game
                is_playoff = True
                i += 1
            else:
                i += 1
        
        # If user specified both --home and --away, determine position from order
        if home_team and away_team:
            # Find which flag came first in the original args
            away_idx = next ((j for j, a in enumerate(args) if a == '--away'), 999)
            home_idx = next ((j for j, a in enumerate(args) if a == '--home'), 999)
            if away_idx < home_idx:
                # --away came first: user plays that team (away), other is opponent (home)
                human_is_home = False
            else:
                # --home came first: user plays that team (home), other is opponent (away)
                human_is_home = True

        if load_save:
            from .interactive_game import resume_game
            save_file_arg = save_file if save_file else "paydirt_save.json"
            resume_game(save_file_arg, difficulty=difficulty, compact=compact, week=week)
        else:
            from .interactive_game import run_interactive_game
            run_interactive_game(difficulty=difficulty, compact=compact, week=week, 
                                home_team=home_team, away_team=away_team,
                                human_is_home=human_is_home, is_playoff=is_playoff)
        return

    # Try chart-based mode first if team charts are available
    try:
        from .chart_loader import find_team_charts

        # Determine seasons directory using packaging helper
        seasons_dir = str(get_seasons_path())

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
