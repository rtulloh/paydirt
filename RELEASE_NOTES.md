# Paydirt Release Notes

## Recent Changes (February 2026)

### Code Quality Improvements
- **pytest-cov integration**: Added test coverage analysis tooling
- **Ruff linting**: All code passes static analysis checks
- **Test coverage improvements**:
  - `computer_ai.py`: 41% → 69% (+28%)
  - `play_resolver.py`: 59% → 67% (+8%)
  - `interactive_game.py`: 13% → 14% (testable functions covered)
  - Overall: 46% → 49%, 846 tests total

### Shared Utilities Refactoring
- **`paydirt/utils.py`**: Consolidated duplicate code into shared utilities
  - `ordinal_suffix()` and `ordinal()` for "1st", "2nd", etc.
  - `format_time()` for clock display
  - `format_down_and_distance()` for game state display
- Removed duplicate implementations from `cli.py`, `cli_charts.py`, `interactive_game.py`

### Bug Fixes
- **Timeout at end of half**: Fixed bug where calling timeout near end of half still triggered halftime/end of game. Timeout now correctly reverts quarter advancement when time is preserved.
- **Offsetting penalties display**: Fixed misleading display where offsetting penalties showed play result (e.g., "No gain" with "O:24→4") instead of clearly indicating "OFFSETTING PENALTIES - Down replayed"
- **Blocked kick touchdown flag**: Fixed bug where blocked FG returned for TD scored 6 points but skipped PAT/kickoff flow (touchdown flag was hardcoded to False)
- **Blocked kick display**: Blocked FG now shows full description with recovery roll and return info instead of just "BLOCKED!"
- **Blocked kick return rolls**: Added return dice roll to descriptions for blocked FG and punt returns
- **Penalty yardage ignored**: Fixed bug where chart penalties (e.g., "DEF 15") were re-rolled instead of using the explicit yardage. Now uses chart yardage when specified.
- **Punt return penalties**: Fixed "DEF 15" triggering false fumble detection (DEF contains "F")
- **Punt/kickoff return penalty yardage**: Now correctly parses and applies penalty yards
  - OFF penalty: Ball moves back (receiving team penalized)
  - DEF penalty: Ball moves forward (kicking team penalized)
- **Kickoff dice roll**: Fixed tuple unpacking bug where `roll_chart_dice()` return value was used directly as dict key
- **Kickoff return position clamping**: Added minimum position (1) to prevent invalid ball placement

### Field Goal Penalty Handling
- **Full penalty procedure**: FG attempts now follow the same penalty rules as normal plays
- **Roll until outcome**: If a penalty occurs, dice are re-rolled until a non-penalty result
- **Penalty choice**: Offended team can choose between the play result or the penalty
- **Offsetting penalties**: Result in a rekick (replay the down)
- **Bug fix**: Fixed infinite re-kick bug where offensive penalties allowed repeated FG attempts

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
- **Untimed down rule**: Quarter/half cannot end on accepted defensive penalty - offense gets one more play at 0:00
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
