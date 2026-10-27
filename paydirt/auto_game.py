"""
Auto game mode - CPU vs CPU simulation.

Usage: 
    python -m paydirt -auto Bears Cowboys           # Simple team names (uses default season)
    python -m paydirt -auto seasons/1983/Bears seasons/1985/Cowboys  # Full paths for cross-season
"""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from .chart_loader import find_team_charts, load_team_chart
from .computer_ai import ComputerAI
from .game_engine import PaydirtGameEngine, PlayOutcome
from .interactive_game import display_box_score
from .packaging import get_seasons_path
from .play_resolver import DefenseType, PlayType


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


def _resolve_auto_penalties(
    game: PaydirtGameEngine, outcome: PlayOutcome, offense_home: bool,
    home_ai: ComputerAI, away_ai: ComputerAI,
) -> PlayOutcome:
    """Collect AI choices and apply them before using a provisional outcome."""
    for _ in range(100):
        if not outcome.pending_penalty_decision:
            return outcome
        choice = outcome.penalty_choice
        if choice is None:
            raise RuntimeError("Pending penalty decision has no choices")
        offended_home = offense_home if choice.offended_team == "offense" else not offense_home
        ai = home_ai if offended_home else away_ai
        accept_play, penalty_index = ai.should_accept_penalty(
            outcome, is_human_offense=offense_home != offended_home,
            human_is_home=not offended_home,
        )
        penalty_index = 0 if penalty_index is None else penalty_index
        if outcome.play_type == PlayType.FIELD_GOAL:
            outcome = game.apply_fg_penalty_decision(outcome, accept_play, penalty_index)
        elif outcome.play_type == PlayType.PUNT:
            outcome = game.apply_punt_penalty_decision(outcome, not accept_play, penalty_index)
        elif outcome.play_type == PlayType.KICKOFF:
            outcome = game.apply_kickoff_penalty_decision(outcome, not accept_play)
        else:
            outcome = game.apply_penalty_decision(outcome, accept_play, penalty_index)
        print(f"  [Penalty: {'play stands' if accept_play else 'penalty accepted'}]")
    raise RuntimeError("Auto-game penalty decision limit reached")


def _complete_auto_outcome(
    game: PaydirtGameEngine, outcome: PlayOutcome, offense_home: bool,
    quarter_before: int, home_ai: ComputerAI, away_ai: ComputerAI,
    on_result: Callable[[PaydirtGameEngine, PlayOutcome], None] | None = None,
) -> None:
    """Display finalized engine results and complete any scoring/kickoff chain."""
    for _ in range(500):
        outcome = _resolve_auto_penalties(game, outcome, offense_home, home_ai, away_ai)
        if on_result is not None:
            on_result(game, outcome)
            on_result = None  # Observe this finalized call, not subsequent kickoff chains.
        print(f"  {outcome.description}")
        result = outcome.result
        dice_info = (f'O:{result.dice_roll}→"{result.raw_result}"'
                     f' | Def:→"{result.defense_modifier or ""}"')
        if result.breakaway_dice:
            dice_info += f" | B:{result.breakaway_dice}→{result.breakaway_yards}"
        if result.qb_scramble_dice:
            dice_info += f" | QT:{result.qb_scramble_dice}→{result.qb_scramble_yards}"
        if result.int_return_dice:
            dice_info += f" | INT@{result.int_spot} | R:{result.int_return_dice}→{result.int_return_yards}"
        print(f"  ({dice_info})")

        if outcome.touchdown:
            if not game.can_attempt_conversion_after_touchdown():
                return
            _, description = game.attempt_extra_point()
            print(f"  {description}")
        elif not outcome.field_goal_made and not outcome.safety:
            return

        if not game.can_kickoff_after_play(quarter_before):
            return
        kicking_home = game.state.is_home_possession
        quarter_before = game.state.quarter
        if outcome.safety:
            outcome = game.safety_free_kick()
        else:
            outcome = game.kickoff(kicking_home=kicking_home)
        # Kickoff decisions use the receiving team's offense perspective, as in CLI.
        offense_home = not kicking_home
    raise RuntimeError("Auto-game scoring/kickoff sequence limit reached")


def run_auto_game(
    team1_spec: str, team2_spec: str, delay: float = 0.0, is_playoff: bool = False, *,
    ai_factory: Callable[[PaydirtGameEngine, bool], ComputerAI] | None = None,
    on_decision: Callable[[PaydirtGameEngine, ComputerAI, PlayType, DefenseType], None] | None = None,
    on_result: Callable[[PaydirtGameEngine, PlayOutcome], None] | None = None,
    play_limit: int = 500,
) -> PaydirtGameEngine | None:
    """
    Run a CPU vs CPU game between two teams.
    
    Args:
        team1_spec: Away team - name (e.g., "Bears") or path (e.g., "seasons/1983/Bears")
        team2_spec: Home team - name (e.g., "Cowboys") or path (e.g., "seasons/1985/Cowboys")
        delay: Seconds to pause between plays (default 0.0)
        is_playoff: If True, this is a playoff game
        ai_factory: Optional caller-owned AI configuration; default remains balanced.
        on_decision: Read-only observer after selection, before execution.
        on_result: Read-only observer after penalty resolution, before scoring chains.
        play_limit: Maximum selected calls; incomplete runs raise RuntimeError.

    Returns:
        Completed engine, or None if team lookup fails. Observers must not mutate it.
    """
    if play_limit < 1:
        raise ValueError("Auto-game play limit must be positive")
    # Find team charts
    seasons_dir = str(get_seasons_path())

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
    game.state.is_playoff = is_playoff

    # Create AI for both teams (home team's season rules govern AI behavior)
    if ai_factory is None:
        away_ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)
        home_ai = ComputerAI(aggression=0.5, ai_behavior=game.season_rules.ai_behavior)
    else:
        away_ai = ai_factory(game, False)
        home_ai = ai_factory(game, True)

    # Opening kickoff - home team kicks to start
    opening_kicking_home = True
    print("=" * 70)
    print("  OPENING KICKOFF")
    print("=" * 70)

    quarter_before = game.state.quarter
    outcome = game.kickoff(kicking_home=opening_kicking_home)
    _complete_auto_outcome(game, outcome, not opening_kicking_home, quarter_before, home_ai, away_ai)
    print(f"  Ball spotted at {game.state.field_position_str()}")
    time.sleep(delay)

    play_count = 0
    last_quarter = 1

    # Main game loop
    while not game.state.game_over:
        state = game.state

        # The engine consumes untimed downs when the play starts, and may award
        # a replacement down after another accepted defensive penalty.
        if state.time_remaining <= 0 and game.has_untimed_down():
            print("  UNTIMED DOWN - period extended by the engine")
        elif game.needs_overtime():
            display_box_score(game, "END OF REGULATION")
            print(f"\n  {game.start_overtime()}")
            last_quarter = state.quarter
            quarter_before = state.quarter
            kicking_home = not state.ot_coin_toss_winner_is_home
            outcome = game.kickoff(kicking_home=kicking_home)
            _complete_auto_outcome(game, outcome, not kicking_home, quarter_before, home_ai, away_ai)
            continue

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
                quarter_before = state.quarter
                kicking_home = not opening_kicking_home
                outcome = game.kickoff(kicking_home=kicking_home)
                _complete_auto_outcome(game, outcome, not kicking_home, quarter_before, home_ai, away_ai)
                if state.game_over:
                    break

            last_quarter = state.quarter
            time.sleep(delay)

        # Determine which team is on offense
        if state.is_home_possession:
            off_team = home_name
            off_ai = home_ai
            def_ai = away_ai
        else:
            off_team = away_name
            off_ai = away_ai
            def_ai = home_ai

        if state.game_over:
            break

        # Display game status
        minutes = int(state.time_remaining)
        seconds = int((state.time_remaining % 1) * 60)

        period = f"OT{state.ot_period}" if state.is_overtime else f"Q{state.quarter}"
        print(f"\n  {period} {minutes}:{seconds:02d} | {away_name} {state.away_score} - {home_name} {state.home_score}")
        print(f"  {off_team} ball at {state.field_position_str()} | {state.down}&{state.yards_to_go}")

        # CPU selects plays with clock management
        play_type, use_oob, use_no_huddle, punt_short_drop, punt_coffin_yards, use_spike = off_ai.select_offense_with_clock_management(game)
        def_type = def_ai.select_defense(game)
        if on_decision is not None:
            on_decision(game, off_ai, play_type, def_type)
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
        if use_spike:
            print("  [SPIKE: Will stop clock after play]")

        # Show punt options
        if play_type == PlayType.PUNT:
            if punt_short_drop:
                print("  [SHORT-DROP PUNT]")
            elif punt_coffin_yards > 0:
                print(f"  [COFFIN-CORNER PUNT: {punt_coffin_yards} yards subtracted]")

        print(f"  {off_team}: {play_name} vs {def_name}")

        # Run the play with OOB designation, punt options, and spike modifier
        offense_home = state.is_home_possession
        quarter_before = state.quarter
        outcome = game.run_play_with_penalty_procedure(play_type, def_type,
                                                        out_of_bounds_designation=use_oob,
                                                        punt_short_drop=punt_short_drop,
                                                        punt_coffin_corner_yards=punt_coffin_yards,
                                                        no_huddle=use_no_huddle,
                                                        call_spike=use_spike)

        _complete_auto_outcome(
            game, outcome, offense_home, quarter_before, home_ai, away_ai, on_result)

        play_count += 1
        time.sleep(delay)

        # Safety check - prevent infinite loops
        if play_count >= play_limit and not game.state.game_over:
            raise RuntimeError("Auto-game play limit reached before game completion")

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
    return game


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        run_auto_game(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python -m paydirt.auto_game <team1> <team2>")
        print("Example: python -m paydirt.auto_game Bears Cowboys")
