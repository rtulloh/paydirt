#!/usr/bin/env python3
"""Run all 28 teams in 14 matchups and verify results."""
import subprocess
import re

matchups = [
    ('Packers', '49ers'),
    ('Bills', 'Vikings'),
    ('Bears', 'Browns'),
    ('Rams', 'Saints'),
    ('Colts', 'Broncos'),
    ('Raiders', 'Chiefs'),
    ('Steelers', 'Falcons'),
    ('Bengals', 'Jets'),
    ('Buccaneers', 'Patriots'),
    ('Seahawks', 'Dolphins'),
    ('Eagles', 'Chargers'),
    ('Cowboys', 'Giants'),
    ('Lions', 'Oilers'),
    ('Cardinals', 'Redskins'),
]

# Regex pattern for team names - handles both "Team '83" and "Team 83" formats
TEAM_PATTERN = r"(\w+ '?\d+)"

errors = []
games_summary = []
all_stats = []  # Store stats for each game
clock_management_stats = []  # Track clock management usage

def parse_team_stats(output, team_name):
    """Parse team statistics from output."""
    stats = {
        'team': team_name,
        'first_downs': 0,
        'total_yards': 0,
        'rushing_yards': 0,
        'passing_yards': 0,
        'turnovers': 0,
        'interceptions': 0,
        'fumbles_lost': 0,
        'penalties': 0,
        'penalty_yards': 0,
        'sacks': 0,
        'sack_yards': 0,
    }
    
    lines = output.split('\n')
    in_stats_section = False
    team_col = None  # Which column (0 or 1) is this team
    
    for i, line in enumerate(lines):
        if 'TEAM STATISTICS' in line:
            in_stats_section = True
            continue
        
        if in_stats_section:
            # Find which column the team is in
            if team_col is None and team_name in line:
                # Check if team is in first or second data column
                parts = line.split('|')
                for j, part in enumerate(parts):
                    if team_name in part:
                        team_col = j - 2  # Adjust for header columns
                        break
            
            # Parse stat lines
            if 'First Downs' in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['first_downs'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Total Yards' in line and 'Rushing' not in line and 'Passing' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['total_yards'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Rushing' in line and 'Total' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['rushing_yards'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Passing' in line and 'Total' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['passing_yards'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Turnovers' in line and 'Interceptions' not in line and 'Fumbles' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['turnovers'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Interceptions' in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['interceptions'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Fumbles Lost' in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['fumbles_lost'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Penalties' in line and 'Penalty Yards' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['penalties'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Penalty Yards' in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['penalty_yards'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Sacks' in line and 'Sack Yards' not in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['sacks'] = int(m.group(1 if team_col == 0 else 2))
            elif 'Sack Yards' in line:
                m = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+\|', line)
                if m:
                    stats['sack_yards'] = int(m.group(1 if team_col == 0 else 2))
            
            # End of stats section
            if line.startswith('+--') and in_stats_section and 'First Downs' in output[:output.find(line)]:
                break
    
    return stats

for away, home in matchups:
    print(f"\n{'='*70}")
    print(f"  GAME: {away} @ {home}")
    print(f"{'='*70}")
    
    result = subprocess.run(
        ['python3', '-m', 'paydirt', '-auto', f'1983/{away}', f'1983/{home}'],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    output = result.stdout + result.stderr
    
    # Check for any Python errors first
    if 'Traceback' in output:
        errors.append(f"{away}@{home}: Python traceback in output")
        print(f"  ERROR: Python exception!")
        # Print the traceback for debugging
        print("  Traceback output:")
        for line in output.split('\n'):
            if 'Traceback' in line or 'Error' in line or 'Exception' in line or '  File' in line:
                print(f"    {line}")
        continue
    
    # Extract final score - handles both apostrophe and non-apostrophe team names
    final_match = re.search(
        rf"FINAL.*?\n.*?\n.*?{TEAM_PATTERN}\s+(\d+)\s+-\s+{TEAM_PATTERN}\s+(\d+)", 
        output, re.DOTALL
    )
    away_team = away_score = home_team = home_score = None
    if final_match:
        away_team, away_score, home_team, home_score = final_match.groups()
        print(f"  Final: {away_team} {away_score} - {home_team} {home_score}")
        games_summary.append((away_team, int(away_score), home_team, int(home_score)))
    else:
        # Try alternate pattern from box score
        box_match = re.search(
            rf"\|\s+{TEAM_PATTERN}\s+\|\s+\d+\s+\d+\s+\d+\s+\d+\s+\|\s+(\d+)\s+\|.*?"
            rf"\|\s+{TEAM_PATTERN}\s+\|\s+\d+\s+\d+\s+\d+\s+\d+\s+\|\s+(\d+)\s+\|",
            output, re.DOTALL
        )
        if box_match:
            away_team, away_score, home_team, home_score = box_match.groups()
            print(f"  Final: {away_team} {away_score} - {home_team} {home_score}")
            games_summary.append((away_team, int(away_score), home_team, int(home_score)))
        else:
            errors.append(f"{away}@{home}: Could not parse final score")
            print(f"  ERROR: Could not parse final score")
    
    # Extract quarter scores from box score
    lines = output.split('\n')
    teams_found = []
    for i, line in enumerate(lines):
        if 'TEAM' in line and '1Q' in line:
            # Next lines contain the teams
            for team_line in lines[i+1:i+5]:
                m = re.search(
                    rf"\|\s+{TEAM_PATTERN}\s+\|\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\|\s+(\d+)\s+\|", 
                    team_line
                )
                if m:
                    team, q1, q2, q3, q4, total = m.groups()
                    calc_total = int(q1) + int(q2) + int(q3) + int(q4)
                    if calc_total != int(total):
                        errors.append(f"{away}@{home}: {team} quarters {q1}+{q2}+{q3}+{q4}={calc_total} != {total}")
                        print(f"  ERROR: {team} quarter math wrong!")
                    else:
                        print(f"  {team}: {q1}+{q2}+{q3}+{q4}={total} ✓")
                    teams_found.append(team)
            break
    
    if len(teams_found) < 2:
        errors.append(f"{away}@{home}: Only found {len(teams_found)} team(s) in box score")
        print(f"  WARNING: Only found {len(teams_found)} team(s) in box score")
    
    # Parse team stats
    if away_team and home_team:
        away_stats = parse_team_stats(output, away_team)
        home_stats = parse_team_stats(output, home_team)
        all_stats.append({
            'away': away_stats,
            'home': home_stats,
            'away_score': int(away_score) if away_score else 0,
            'home_score': int(home_score) if home_score else 0,
        })
        
        # Print per-game stats
        print(f"  Stats: {away_team}: {away_stats['total_yards']} yds, {away_stats['turnovers']} TO, {away_stats['penalties']} pen")
        print(f"         {home_team}: {home_stats['total_yards']} yds, {home_stats['turnovers']} TO, {home_stats['penalties']} pen")
    
    # Parse clock management stats
    no_huddle_count = output.count("NO-HUDDLE offense!")
    oob_count = output.count("OUT OF BOUNDS DESIGNATION")
    two_min_drill_count = output.count("[Two-Minute Drill]")
    clock_management_stats.append({
        'game': f"{away}@{home}",
        'no_huddle': no_huddle_count,
        'oob': oob_count,
        'two_min_drill': two_min_drill_count,
    })
    if no_huddle_count > 0 or oob_count > 0:
        print(f"  Clock Mgmt: {no_huddle_count} no-huddle, {oob_count} OOB designations, {two_min_drill_count} 2-min drill plays")

print(f"\n{'='*70}")
print(f"  SUMMARY: {len(matchups)} games played")
print(f"{'='*70}")

# Print all game results
if games_summary:
    print("\n  RESULTS:")
    print("  " + "-"*50)
    total_away_wins = 0
    total_home_wins = 0
    total_ties = 0
    for away_team, away_score, home_team, home_score in games_summary:
        winner = ""
        if away_score > home_score:
            winner = f"({away_team} wins)"
            total_away_wins += 1
        elif home_score > away_score:
            winner = f"({home_team} wins)"
            total_home_wins += 1
        else:
            winner = "(TIE)"
            total_ties += 1
        print(f"    {away_team:12} {away_score:3} - {home_team:12} {home_score:3}  {winner}")
    print("  " + "-"*50)
    print(f"    Away wins: {total_away_wins}  |  Home wins: {total_home_wins}  |  Ties: {total_ties}")

# Print aggregate statistics
if all_stats:
    print("\n  AGGREGATE STATISTICS:")
    print("  " + "-"*50)
    
    total_points = sum(g['away_score'] + g['home_score'] for g in all_stats)
    total_yards = sum(g['away']['total_yards'] + g['home']['total_yards'] for g in all_stats)
    total_rushing = sum(g['away']['rushing_yards'] + g['home']['rushing_yards'] for g in all_stats)
    total_passing = sum(g['away']['passing_yards'] + g['home']['passing_yards'] for g in all_stats)
    total_turnovers = sum(g['away']['turnovers'] + g['home']['turnovers'] for g in all_stats)
    total_interceptions = sum(g['away']['interceptions'] + g['home']['interceptions'] for g in all_stats)
    total_fumbles = sum(g['away']['fumbles_lost'] + g['home']['fumbles_lost'] for g in all_stats)
    total_penalties = sum(g['away']['penalties'] + g['home']['penalties'] for g in all_stats)
    total_penalty_yards = sum(g['away']['penalty_yards'] + g['home']['penalty_yards'] for g in all_stats)
    total_sacks = sum(g['away']['sacks'] + g['home']['sacks'] for g in all_stats)
    total_first_downs = sum(g['away']['first_downs'] + g['home']['first_downs'] for g in all_stats)
    
    num_games = len(all_stats)
    
    print(f"    Total Points:        {total_points:5}  (avg {total_points/num_games:.1f}/game, {total_points/(num_games*2):.1f}/team)")
    print(f"    Total Yards:         {total_yards:5}  (avg {total_yards/num_games:.1f}/game, {total_yards/(num_games*2):.1f}/team)")
    print(f"      Rushing:           {total_rushing:5}  (avg {total_rushing/(num_games*2):.1f}/team)")
    print(f"      Passing:           {total_passing:5}  (avg {total_passing/(num_games*2):.1f}/team)")
    print(f"    First Downs:         {total_first_downs:5}  (avg {total_first_downs/(num_games*2):.1f}/team)")
    print(f"    Turnovers:           {total_turnovers:5}  (avg {total_turnovers/(num_games*2):.1f}/team)")
    print(f"      Interceptions:     {total_interceptions:5}")
    print(f"      Fumbles Lost:      {total_fumbles:5}")
    print(f"    Penalties:           {total_penalties:5}  (avg {total_penalties/(num_games*2):.1f}/team)")
    print(f"    Penalty Yards:       {total_penalty_yards:5}  (avg {total_penalty_yards/(num_games*2):.1f}/team)")
    print(f"    Sacks:               {total_sacks:5}  (avg {total_sacks/(num_games*2):.1f}/team)")

if errors:
    print(f"\n  ERRORS FOUND ({len(errors)}):")
    for e in errors:
        print(f"    - {e}")
else:
    print("\n  ALL GAMES PASSED! ✓")

# Print clock management summary
if clock_management_stats:
    print("\n  CLOCK MANAGEMENT SUMMARY:")
    print("  " + "-"*50)
    total_no_huddle = sum(g['no_huddle'] for g in clock_management_stats)
    total_oob = sum(g['oob'] for g in clock_management_stats)
    total_two_min = sum(g['two_min_drill'] for g in clock_management_stats)
    games_with_clock_mgmt = sum(1 for g in clock_management_stats if g['no_huddle'] > 0 or g['oob'] > 0)
    
    print(f"    Games with clock management: {games_with_clock_mgmt}/{len(clock_management_stats)}")
    print(f"    Total no-huddle plays:       {total_no_huddle}")
    print(f"    Total OOB designations:      {total_oob}")
    print(f"    Total two-minute drill plays: {total_two_min}")
    
    # Show games with most clock management
    if games_with_clock_mgmt > 0:
        print("\n    Games with clock management activity:")
        for g in sorted(clock_management_stats, key=lambda x: x['no_huddle'] + x['oob'], reverse=True)[:5]:
            if g['no_huddle'] > 0 or g['oob'] > 0:
                print(f"      {g['game']}: {g['no_huddle']} no-huddle, {g['oob']} OOB")
