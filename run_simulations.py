#!/usr/bin/env python3
"""
CPU vs CPU Simulation Runner
"""
import json
import random
from collections import defaultdict

from paydirt.game_engine import PaydirtGameEngine, simulate_drive
from paydirt.models import Team
from paydirt.play_resolver import PlayType, DefenseType

class TestTeam(Team):
    def __init__(self, name, abbr):
        super().__init__(
            name=name,
            abbreviation=abbr,
            rushing_offense=6,
            passing_offense=6,
            rushing_defense=6,
            passing_defense=6,
            special_teams=6,
        )

def _ai_select_play(state):
    """Simple AI to select an offensive play based on game situation."""
    ball_pos = state.ball_position
    down = state.down
    yards_to_go = state.yards_to_go

    # 4th down decisions
    if down == 4:
        # In field goal range (inside opponent's 35)
        if ball_pos >= 65:
            return PlayType.FIELD_GOAL
        # Deep in own territory - punt
        elif ball_pos < 50:
            return PlayType.PUNT
        # Go for it in no-man's land or short yardage
        elif yards_to_go <= 2:
            return random.choice([PlayType.LINE_PLUNGE, PlayType.SHORT_PASS])
        else:
            return PlayType.PUNT

    # Goal line (inside 5)
    if ball_pos >= 95:
        return random.choice([PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS])

    # Red zone (inside 20)
    if ball_pos >= 80:
        return random.choice([
            PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS
        ])

    # Long yardage (need 7+)
    if yards_to_go >= 7:
        return random.choice([
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN
        ])

    # Short yardage (need 3 or less)
    if yards_to_go <= 3:
        return random.choice([
            PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
            PlayType.END_RUN, PlayType.SHORT_PASS
        ])

    # Normal situation - mix it up
    return random.choice([
        PlayType.END_RUN, PlayType.OFF_TACKLE, PlayType.LINE_PLUNGE,
        PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.DRAW,
        PlayType.SCREEN
    ])

def _ai_select_defense(state):
    """Simple AI to select a defensive formation based on game situation."""
    ball_pos = state.ball_position
    down = state.down
    yards_to_go = state.yards_to_go

    # Goal line defense
    if ball_pos >= 95:
        return DefenseType.STANDARD

    # Prevent defense in obvious passing situations
    if yards_to_go >= 15:
        return DefenseType.STANDARD

    # Blitz on 3rd and medium
    if down == 3 and 4 <= yards_to_go <= 8:
        return random.choice([DefenseType.STANDARD, DefenseType.STANDARD])

    # Normal defense most of the time
    return DefenseType.STANDARD

def run_simulation(num_games=10):
    """Run multiple CPU vs CPU simulations and collect stats."""
    results = []
    
    for game_num in range(num_games):
        home_team = TestTeam("Home", "HOM")
        away_team = TestTeam("Away", "AWY")
        
        game = PaydirtGame(home_team, away_team)
        
        # Run the game
        while not game.state.game_over:
            simulate_drive(game)
        
# Collect stats
        result = {
            'game_num': game_num + 1,
            'home_score': game.state.home_score,
            'away_score': game.state.away_score,
            'winner': 'home' if game.state.home_score > game.state.away_score else 'away',
            'total_yards': game.home_team.stats.total_yards + game.away_team.stats.total_yards,
            'rushing_yards': game.home_team.stats.rushing_yards + game.away_team.stats.rushing_yards,
            'passing_yards': game.home_team.stats.passing_yards + game.away_team.stats.passing_yards,
            'first_downs': game.home_team.stats.first_downs + game.away_team.stats.first_downs,
            'turnovers': game.home_team.stats.turnovers + game.away_team.stats.turnovers,
            'interceptions': 0,  # Need to parse from play history
            'fumbles_lost': 0,  # Need to parse from play history
            'penalties': game.home_team.stats.penalties + game.away_team.stats.penalties,
            'penalty_yards': game.home_team.stats.penalty_yards + game.away_team.stats.penalty_yards,
            'sacks': 0,  # Need to parse from play history
            'sack_yards': 0,  # Need to parse from play history
            'plays': len(game.play_history),
        }
        
        # Parse play history to extract detailed stats
        for play in game.play_history:
            # Count touchdowns for scoring
            if play.get('result') == 'touchdown':
                result['total_yards'] += 80  # Estimate
            elif play.get('yards') is not None:
                result['total_yards'] += play['yards']
            
            # Count play types
            if play.get('type') == 'play':
                play_type = play.get('play_type', '')
                yards = play.get('yards', 0)
                
                # Check for interceptions
                if 'INTERCEPTED' in play.get('description', '').upper():
                    result['interceptions'] += 1
                
                # Check for fumbles
                if 'FUMBLE' in play.get('description', '').upper():
                    result['fumbles_lost'] += 1
                
                # Count rushing plays
                if play_type in ['run_left', 'run_right', 'run_middle', 'draw']:
                    result['rushing_yards'] += yards
                
                # Count passing plays
                elif play_type in ['short_pass', 'medium_pass', 'long_pass', 'screen_pass']:
                    result['passing_yards'] += yards
            
            # Count turnovers (from play history turnover flag)
            if play.get('turnover'):
                result['turnovers'] += 1
            
            # Count penalties
            if play.get('penalty_applied'):
                result['penalties'] += 1
                result['penalty_yards'] += play.get('penalty_yards', 0)
            
            # Count sacks
            if play.get('sack'):
                result['sacks'] += 1
                result['sack_yards'] += play.get('yards', 0)
        
        results.append(result)
    
    return results

def analyze_results(results):
    """Analyze simulation results."""
    summary = {
        'games_played': len(results),
        'avg_home_score': 0,
        'avg_away_score': 0,
        'avg_total_score': 0,
        'avg_total_yards': 0,
        'avg_rushing_yards': 0,
        'avg_passing_yards': 0,
        'avg_first_downs': 0,
        'avg_turnovers': 0,
        'avg_interceptions': 0,
        'avg_fumbles_lost': 0,
        'avg_penalties': 0,
        'avg_penalty_yards': 0,
        'avg_sacks': 0,
        'avg_sack_yards': 0,
        'avg_plays': 0,
        'close_games': 0,  # Games decided by 8 points or less
        'blowouts': 0,     # Games decided by 20+ points
        'highest_scoring_game': 0,
        'lowest_scoring_game': float('inf'),
    }
    
    for result in results:
        summary['avg_home_score'] += result['home_score']
        summary['avg_away_score'] += result['away_score']
        summary['avg_total_yards'] += result['total_yards']
        summary['avg_rushing_yards'] += result['rushing_yards']
        summary['avg_passing_yards'] += result['passing_yards']
        summary['avg_first_downs'] += result['first_downs']
        summary['avg_turnovers'] += result['turnovers']
        summary['avg_interceptions'] += result['interceptions']
        summary['avg_fumbles_lost'] += result['fumbles_lost']
        summary['avg_penalties'] += result['penalties']
        summary['avg_penalty_yards'] += result['penalty_yards']
        summary['avg_sacks'] += result['sacks']
        summary['avg_sack_yards'] += result['sack_yards']
        summary['avg_plays'] += result['plays']
        
        total_score = result['home_score'] + result['away_score']
        if total_score > summary['highest_scoring_game']:
            summary['highest_scoring_game'] = total_score
        if total_score < summary['lowest_scoring_game']:
            summary['lowest_scoring_game'] = total_score
        
        # Close games (within 8 points)
        if abs(result['home_score'] - result['away_score']) <= 8:
            summary['close_games'] += 1
        
        # Blowouts (20+ point difference)
        if abs(result['home_score'] - result['away_score']) >= 20:
            summary['blowouts'] += 1
    
    # Calculate averages
    for key in summary:
        if key.startswith('avg_') and key != 'avg_plays':
            summary[key] /= len(results)
    
    summary['avg_plays'] /= len(results)
    
    return summary, results

def print_summary(summary):
    """Print the summary in a readable format."""
    print("=" * 70)
    print("SIMULATION SUMMARY - CPU vs CPU BALANCE TEST")
    print("=" * 70)
    print()
    
    print(f"Games Played: {summary['games_played']}")
    print()
    
    print("SCORING:")
    print(f"  Home Team Avg: {summary['avg_home_score']:.1f}")
    print(f"  Away Team Avg: {summary['avg_away_score']:.1f}")
    print(f"  Total Avg: {summary['avg_total_score']:.1f}")
    print(f"  Avg Margin: {abs(summary['avg_home_score'] - summary['avg_away_score']):.1f}")
    print()
    
    print("GAME COMPETITIVENESS:")
    print(f"  Close Games (8 pts or less): {summary['close_games']} ({summary['close_games']/summary['games_played']*100:.1f}%)")
    print(f"  Blowouts (20+ pts): {summary['blowouts']} ({summary['blowouts']/summary['games_played']*100:.1f}%)")
    print()
    
    print("OFFENSIVE PRODUCTION:")
    print(f"  Total Yards per Game: {summary['avg_total_yards']:.1f}")
    print(f"  Rushing Yards per Game: {summary['avg_rushing_yards']:.1f}")
    print(f"  Passing Yards per Game: {summary['avg_passing_yards']:.1f}")
    print(f"  Plays per Game: {summary['avg_plays']:.1f}")
    print()
    
    print("TURNOVERS:")
    print(f"  Total Turnovers per Game: {summary['avg_turnovers']:.1f}")
    print(f"  Interceptions per Game: {summary['avg_interceptions']:.1f}")
    print(f"  Fumbles Lost per Game: {summary['avg_fumbles_lost']:.1f}")
    print()
    
    print("PENALTIES:")
    print(f"  Penalties per Game: {summary['avg_penalties']:.1f}")
    print(f"  Penalty Yards per Game: {summary['avg_penalty_yards']:.1f}")
    print()
    
    print("DEFENSIVE PRODUCTION:")
    print(f"  Sacks per Game: {summary['avg_sacks']:.1f}")
    print(f"  Sack Yards per Game: {summary['avg_sack_yards']:.1f}")
    print()
    
    print("GAME PACE:")
    print(f"  Highest Scoring Game: {summary['highest_scoring_game']}")
    print(f"  Lowest Scoring Game: {summary['lowest_scoring_game']}")
    print()
    print("=" * 70)

if __name__ == "__main__":
    # Run 20 simulations for better statistical significance
    results = run_simulation(num_games=20)
    summary, all_results = analyze_results(results)
    
    # Print summary
    print_summary(summary)
    
    # Save detailed results to file
    with open('simulation_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print("\nDetailed results saved to simulation_results.json")