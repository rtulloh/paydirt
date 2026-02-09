#!/usr/bin/env python3
"""
Simulation script to find edge case bugs in special plays.

Runs many simulated games and logs all:
- Interceptions and INT returns
- Fumbles and fumble recoveries
- Safeties
- Blocked kicks (punts and FGs)
- Blocked kick returns

This helps find bugs that are hard to hit during manual playtesting.
"""

import sys
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from paydirt.chart_loader import load_team_chart, find_team_charts
from paydirt.game_engine import PaydirtGameEngine, PlayType, DefenseType


@dataclass
class SpecialPlayEvent:
    """Record of a special play event for analysis."""
    game_num: int
    play_num: int
    event_type: str  # INT, FUMBLE, SAFETY, BLOCKED_PUNT, BLOCKED_FG, etc.
    description: str
    ball_pos_before: int
    ball_pos_after: int
    possession_before: str
    possession_after: str
    score_before: str
    score_after: str
    down_before: int
    down_after: int
    outcome_flags: str  # turnover, touchdown, safety, first_down


@dataclass
class SimulationStats:
    """Aggregate statistics from simulation."""
    games_played: int = 0
    total_plays: int = 0
    interceptions: int = 0
    int_returns: int = 0
    int_touchdowns: int = 0
    fumbles: int = 0
    fumble_recoveries_offense: int = 0
    fumble_recoveries_defense: int = 0
    fumble_return_tds: int = 0
    safeties: int = 0
    blocked_punts: int = 0
    blocked_fgs: int = 0
    blocked_kick_returns: int = 0
    blocked_kick_tds: int = 0
    touchbacks: int = 0
    errors: List[str] = field(default_factory=list)
    events: List[SpecialPlayEvent] = field(default_factory=list)


def run_simulated_game(home_chart, away_chart, game_num: int, stats: SimulationStats, verbose: bool = False):
    """Run a single simulated game and collect special play events."""
    game = PaydirtGameEngine(home_chart, away_chart)
    
    # Kickoff
    game.kickoff(kicking_home=True)
    
    play_types = [
        PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN,
        PlayType.DRAW, PlayType.SCREEN, PlayType.SHORT_PASS,
        PlayType.MEDIUM_PASS, PlayType.LONG_PASS
    ]
    def_types = [
        DefenseType.STANDARD, DefenseType.SHORT_YARDAGE, 
        DefenseType.SPREAD, DefenseType.BLITZ
    ]
    
    play_num = 0
    max_plays = 200
    
    while not game.state.game_over and play_num < max_plays:
        play_num += 1
        stats.total_plays += 1
        
        # Record state before play
        ball_pos_before = game.state.ball_position
        possession_before = game.state.possession_team.peripheral.short_name
        score_before = f"{game.state.home_score}-{game.state.away_score}"
        down_before = game.state.down
        
        try:
            # Decide play type based on situation
            if game.state.down == 4:
                if game.state.ball_position < 35:
                    # Punt
                    outcome = game._handle_punt()
                elif game.state.ball_position > 60 and game.state.yards_to_go > 5:
                    # Field goal attempt
                    outcome = game._handle_field_goal()
                else:
                    # Go for it
                    play = random.choice(play_types)
                    defense = random.choice(def_types)
                    outcome = game.run_play(play, defense)
            else:
                play = random.choice(play_types)
                defense = random.choice(def_types)
                outcome = game.run_play(play, defense)
            
            # Handle pending penalty decisions automatically (accept play result)
            if outcome.pending_penalty_decision:
                outcome = game.apply_penalty_decision(outcome, accept_play=True)
            
            # Record state after play
            ball_pos_after = game.state.ball_position
            possession_after = game.state.possession_team.peripheral.short_name
            score_after = f"{game.state.home_score}-{game.state.away_score}"
            down_after = game.state.down
            
            # Build outcome flags string
            flags = []
            if outcome.turnover:
                flags.append("TURNOVER")
            if outcome.touchdown:
                flags.append("TD")
            if outcome.safety:
                flags.append("SAFETY")
            if outcome.first_down:
                flags.append("1ST")
            outcome_flags = ",".join(flags) if flags else "-"
            
            desc_lower = outcome.description.lower()
            
            # Check for special plays
            event_type = None
            
            # Interceptions
            if "intercept" in desc_lower or "int" in desc_lower:
                stats.interceptions += 1
                event_type = "INTERCEPTION"
                if "return" in desc_lower:
                    stats.int_returns += 1
                if outcome.touchdown and outcome.turnover:
                    stats.int_touchdowns += 1
                    event_type = "INT_TD"
            
            # Fumbles
            elif "fumble" in desc_lower:
                stats.fumbles += 1
                if "recover" in desc_lower:
                    if "defense" in desc_lower or "lost" in desc_lower:
                        stats.fumble_recoveries_defense += 1
                        event_type = "FUMBLE_LOST"
                    else:
                        stats.fumble_recoveries_offense += 1
                        event_type = "FUMBLE_REC"
                else:
                    event_type = "FUMBLE"
                if outcome.touchdown and outcome.turnover:
                    stats.fumble_return_tds += 1
                    event_type = "FUMBLE_TD"
            
            # Safeties
            if outcome.safety:
                stats.safeties += 1
                event_type = "SAFETY"
                
                # Handle safety free kick
                kick_outcome = game.safety_free_kick(use_punt=False)
                if verbose:
                    print(f"  Safety free kick: {kick_outcome.description}")
            
            # Blocked kicks
            if "blocked" in desc_lower or "block" in desc_lower:
                if outcome.play_type == PlayType.PUNT:
                    stats.blocked_punts += 1
                    event_type = "BLOCKED_PUNT"
                elif outcome.play_type == PlayType.FIELD_GOAL:
                    stats.blocked_fgs += 1
                    event_type = "BLOCKED_FG"
                
                if "return" in desc_lower:
                    stats.blocked_kick_returns += 1
                if outcome.touchdown:
                    stats.blocked_kick_tds += 1
                    event_type = f"{event_type}_TD" if event_type else "BLOCKED_TD"
            
            # Touchbacks
            if "touchback" in desc_lower:
                stats.touchbacks += 1
                if event_type is None:
                    event_type = "TOUCHBACK"
            
            # Log special events
            if event_type:
                event = SpecialPlayEvent(
                    game_num=game_num,
                    play_num=play_num,
                    event_type=event_type,
                    description=outcome.description,
                    ball_pos_before=ball_pos_before,
                    ball_pos_after=ball_pos_after,
                    possession_before=possession_before,
                    possession_after=possession_after,
                    score_before=score_before,
                    score_after=score_after,
                    down_before=down_before,
                    down_after=down_after,
                    outcome_flags=outcome_flags
                )
                stats.events.append(event)
                
                if verbose:
                    print(f"  [{event_type}] {outcome.description[:80]}")
            
            # Check for INT return into own end zone (negative final position)
            if "intercept" in desc_lower and ball_pos_after <= 1:
                # This could indicate an INT return that went into the end zone
                # Currently clamped to 1, but should potentially be touchback at 20
                stats.errors.append(
                    f"Game {game_num} Play {play_num}: INT return ended at position {ball_pos_after} "
                    f"(possible end zone issue) - {outcome.description[:60]}"
                )
            
            # Sanity checks for potential bugs
            # 1. Ball position should be valid (1-99 for field, 0/100 for end zones during scoring)
            if ball_pos_after < 0 or ball_pos_after > 100:
                stats.errors.append(f"Game {game_num} Play {play_num}: Invalid ball position {ball_pos_after}")
            
            # 2. After turnover, possession should change (unless TD scored)
            if outcome.turnover and not outcome.touchdown and possession_before == possession_after:
                stats.errors.append(f"Game {game_num} Play {play_num}: Turnover but possession didn't change - {outcome.description[:60]}")
            
            # 3. After safety, score should increase by 2
            if outcome.safety:
                home_before, away_before = map(int, score_before.split("-"))
                home_after, away_after = map(int, score_after.split("-"))
                score_diff = (home_after + away_after) - (home_before + away_before)
                if score_diff != 2:
                    stats.errors.append(f"Game {game_num} Play {play_num}: Safety but score didn't increase by 2 - {score_before} -> {score_after}")
            
            # 4. After TD, score should increase by 6 (before PAT)
            if outcome.touchdown:
                home_before, away_before = map(int, score_before.split("-"))
                home_after, away_after = map(int, score_after.split("-"))
                score_diff = (home_after + away_after) - (home_before + away_before)
                # TD scores 6, but PAT might have been attempted already
                if score_diff < 6:
                    stats.errors.append(f"Game {game_num} Play {play_num}: TD but score increased by {score_diff} - {score_before} -> {score_after}")
            
        except Exception as e:
            stats.errors.append(f"Game {game_num} Play {play_num}: Exception - {str(e)}")
            if verbose:
                print(f"  ERROR: {e}")
            break
    
    stats.games_played += 1
    return game.state.home_score, game.state.away_score


def main():
    print("=" * 70)
    print("  SPECIAL PLAYS SIMULATION - Finding Edge Case Bugs")
    print("=" * 70)
    
    # Load team charts
    seasons_dir = Path(__file__).parent.parent / "seasons"
    
    # Try 1983 teams first, fall back to samples
    teams_1983 = seasons_dir / "1983"
    samples = seasons_dir / "samples"
    
    if (teams_1983 / "49ers").exists():
        home_chart = load_team_chart(teams_1983 / "49ers")
        away_chart = load_team_chart(teams_1983 / "Cowboys")
    elif samples.exists():
        home_chart = load_team_chart(samples / "Thunderhawks")
        away_chart = load_team_chart(samples / "Ironclads")
    else:
        print("ERROR: No team charts found!")
        return
    
    print(f"\n  Teams: {home_chart.peripheral.short_name} vs {away_chart.peripheral.short_name}")
    
    # Run simulations
    num_games = 50
    stats = SimulationStats()
    
    print(f"\n  Running {num_games} simulated games...")
    print()
    
    for game_num in range(1, num_games + 1):
        home_score, away_score = run_simulated_game(
            home_chart, away_chart, game_num, stats, verbose=False
        )
        
        # Progress indicator
        if game_num % 10 == 0:
            print(f"  Completed {game_num}/{num_games} games...")
    
    # Print results
    print()
    print("=" * 70)
    print("  SIMULATION RESULTS")
    print("=" * 70)
    
    print(f"\n  Games played: {stats.games_played}")
    print(f"  Total plays: {stats.total_plays}")
    
    print(f"\n  INTERCEPTIONS:")
    print(f"    Total: {stats.interceptions}")
    print(f"    With returns: {stats.int_returns}")
    print(f"    Pick-sixes: {stats.int_touchdowns}")
    
    print(f"\n  FUMBLES:")
    print(f"    Total: {stats.fumbles}")
    print(f"    Offense recovers: {stats.fumble_recoveries_offense}")
    print(f"    Defense recovers: {stats.fumble_recoveries_defense}")
    print(f"    Scoop-and-scores: {stats.fumble_return_tds}")
    
    print(f"\n  SAFETIES: {stats.safeties}")
    
    print(f"\n  BLOCKED KICKS:")
    print(f"    Blocked punts: {stats.blocked_punts}")
    print(f"    Blocked FGs: {stats.blocked_fgs}")
    print(f"    With returns: {stats.blocked_kick_returns}")
    print(f"    Return TDs: {stats.blocked_kick_tds}")
    
    print(f"\n  TOUCHBACKS: {stats.touchbacks}")
    
    # Print errors
    if stats.errors:
        print()
        print("=" * 70)
        print("  ERRORS FOUND!")
        print("=" * 70)
        for error in stats.errors:
            print(f"  ❌ {error}")
    else:
        print()
        print("  ✓ No errors detected!")
    
    # Print sample events for review
    print()
    print("=" * 70)
    print("  SAMPLE SPECIAL PLAY EVENTS (for manual review)")
    print("=" * 70)
    
    # Group events by type
    event_types = {}
    for event in stats.events:
        if event.event_type not in event_types:
            event_types[event.event_type] = []
        event_types[event.event_type].append(event)
    
    for event_type, events in sorted(event_types.items()):
        print(f"\n  {event_type} ({len(events)} total):")
        # Show up to 3 examples of each type
        for event in events[:3]:
            print(f"    Game {event.game_num} Play {event.play_num}:")
            print(f"      {event.description[:70]}...")
            print(f"      Pos: {event.ball_pos_before} -> {event.ball_pos_after}")
            print(f"      Poss: {event.possession_before} -> {event.possession_after}")
            print(f"      Score: {event.score_before} -> {event.score_after}")
            print(f"      Flags: {event.outcome_flags}")
    
    print()
    print("=" * 70)
    print("  SIMULATION COMPLETE")
    print("=" * 70)
    
    return len(stats.errors)


if __name__ == "__main__":
    sys.exit(main())
