# Paydirt Release Notes

## Recent Changes (February 2026)

### Standings Management
- **Post-game standings prompt**: After each game, you're asked if you want to record the result to season standings
- **Edit game results**: `python -m paydirt.standings edit <year> <game#>` with options for `--home-team`, `--home-score`, `--away-team`, `--away-score`, `--week`
- **Delete game results**: `python -m paydirt.standings delete <year> <game#>` with confirmation prompt

### CPU AI Improvements
- **End-of-half offense**: CPU now uses hurry-up offense and calls timeouts at end of Q2 even when leading (unless up by 14+)
- **Defensive timeouts**: CPU calls timeouts when trailing late in Q4 to preserve clock
- **Offensive timeouts**: CPU calls timeouts on offense to preserve clock for scoring drives

### Compact Display Mode (`--compact`)
- **Streamlined menus**: Offense/defense menus show abbreviated options on one line; press `?` for full menu
- **Inline timeouts**: Timeouts shown with each team's score (e.g., `ATL '83 14 (3)`)
- **Dice roll details**: Shows dice rolls for punts, kickoffs, and field goals
- **Default prompts**: Shows `Default=X/Name` format for quick selection
- **Play confirmation**: Shows "You called: X" after selection
- **4th down alert**: Reminds you of kicking options on 4th down

### Turnover Display Enhancements
- **Return yardage**: Shows return distance on fumbles and interceptions (e.g., "Returned 29 yds")
- **Red zone alerts**: Dramatic markers when turnovers put team in red zone or at goal line
- **Touchback indicator**: Shows "FUMBLE in end zone - TOUCHBACK!" for end zone fumble recoveries
- **Special markers**: Preserves "★ PICK SIX!" and "★ SCOOP AND SCORE!" for turnover TDs

### Bug Fixes
- **Touchdown display**: Fixed compact mode showing "No gain" instead of "TOUCHDOWN!"
- **Blocked kicks**: Fixed handling - defense recovery in end zone is touchback, kicking team recovery is safety
- **Field goals on any down**: Can now attempt FG or punt on any down, not just 4th
- **Kicker/punter names**: Fixed name lookup in compact display
- **Priority chart**: Fixed (TD) categorization as PARENS_TD
- **Penalty options**: Only show penalties that benefit the offended team
- **Half-distance rule**: Penalty advice now correctly applies near goal line

### Commentary Enhancements
- **Punt commentary**: Special messages for pinning inside 20 and extra-long kicks
- **Kickoff/punt returns**: Commentary for exceptional returns and great coverage

---

## Initial Release (January 2026)

### Core Features
- Full implementation of Paydirt football board game mechanics
- Interactive CLI game mode (Human vs CPU)
- Auto game mode (CPU vs CPU) for testing and simulation
- 1983 NFL season with all 28 teams

### Game Mechanics
- Priority Chart for combining offensive and defensive results
- Full Feature Method penalty handling
- Official dice system (Black + 2 White for offense, Red + Green for defense)
- Special teams charts for punts, kickoffs, field goals, and returns
- Variable yardage entries (DS, X, T1, T2, T3)
- Clock management rules (2-minute warning, out-of-bounds timing)

### Season Tracking
- `python -m paydirt.standings add` - Record game results
- `python -m paydirt.standings show` - Display standings by division
- `python -m paydirt.standings games` - List all recorded games
- Week simulation script for automated season play
