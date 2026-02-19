# Paydirt Release Notes

## Version 1.4 (February 2026)

### Bug Fixes
- **Nested tuple AttributeError**: Fixed crash in CPU AI when selecting certain plays. A nested tuple was being created when going for it on 4th down in opponent territory, causing `AttributeError: 'tuple' object has no attribute 'value'`
- **Blocked punt dice roll**: Fixed blocked punts showing "Roll: 0" instead of actual dice roll in game output
- **Punt penalty yardage**: Fixed penalties on punts not being applied to field position. DEF penalties now add yardage to the receiving team, OFF penalties subtract yardage. Description now shows applied penalty

### Sample Teams
- **Expanded roster data**: Added complete rosters to sample teams (Ironclads, Thunderhawks) for commentary - now includes full depth charts with player names for all positions (QB, RB, WR, TE, OL, DL, LB, DB, K, P)
- **Team discovery fix**: Fixed interactive mode not discovering teams with new CSV format (offense.csv). Now detects both old (OFFENSE-Table 1.csv) and new (offense.csv) formats

### Test Coverage
- **1044 unit tests** passing
- Added 3 tests for punt penalty handling

---

## Version 1.3 (February 2026)

### Data Improvements
- **Consistent offense.csv format**: All 28 teams now use the same 13-column format
  - Added missing Breakaway (B) and QB Time (QT) columns to 16 teams
  - Format: `#,Line Plunge,Off Tackle,End Run,Draw,Screen,Short,Med,Long,T/E S/L,B,QT,Fumble`
- **extra data file no longer required**: All team data is now extracted from the OFFENSE chart
  - Team name and year parsed from header row
  - Fumble recovery ranges parsed from the FUMBLE line (varies by team: 10-23 to 10-33)
  - Short names generated programmatically with proper disambiguation (NYG/NYA, LAR/LAN)

### Bug Fixes
- **Punt return fumble turnover flag**: Fixed incorrect `turnover=True` when punting team recovered their own fumble on a muffed punt return. Now correctly sets `turnover=False` since possession doesn't change
- **Interception return into own end zone**: Fixed per NFL momentum rule. When a defender intercepts and their return momentum carries them into their own end zone, it's now correctly ruled a touchback at the 20-yard line (not clamped to the 1-yard line). Commentary explains the momentum rule
- **TD yardage in scoring summary**: Fixed direct TD results showing "0 yards" instead of actual distance to end zone. A TD pass from the 25-yard line now correctly shows "25 yards" in the scoring summary
- **PI penalty transaction**: Fixed missing transaction in pass interference penalty choice, ensuring all play events are properly tracked
- **Hail Mary PI untimed down**: Fixed Hail Mary pass interference at 0:00 not setting `untimed_down_pending`, which caused the quarter to end instead of granting an extra play
- **CPU timeout after penalty**: Fixed CPU wasting timeout after penalty when clock is already stopped
- **CPU clock management at end of half**: Fixed CPU entering red zone/goal line offense instead of two-minute drill when time is low at end of half. Time-based decisions now take priority over field-position decisions, ensuring proper OOB designation and hurry-up mode
- **Long pass from goal line**: Fixed CPU calling long pass from red zone/goal line during two-minute drill. Now avoids long passes when in the red zone (inside 20) since there's no room to throw deep

### New Features
- **Advanced Punt Rules**: Added support for Short-Drop and Coffin-Corner punts per advanced rules
  - Short-Drop Punts: When punting from inside own 5-yard line, defenders get Free All-Out Kick Rush, all * and † markers are deleted, minus yardage returns become 0 yards
  - Coffin-Corner Punts: Can specify yards to subtract from punt before dice roll. If 15+ yards subtracted, punt is automatic out of bounds (no return possible)

### Analysis
- **Power ratings investigation**: Analyzed power ratings vs actual 1983 NFL records. Found that power ratings are a handicapping mechanism for human vs human play (point spreads, yardage factors), not a simulation of team strength. The chart data itself determines team performance

### Test Coverage
- **1041 unit tests** passing
- Added 7 tests for chart loader data extraction
- Added 2 tests for TD yardage fix
- Added 3 tests for Hail Mary PI untimed down
- Added 1 test for CPU timeout after penalty
- Added 7 tests for CPU clock management at end of half (including red zone long pass fix)
- Added 7 tests for advanced punt rules (Short-Drop and Coffin-Corner punts)
- Added tests for CPU AI punt options
- Added tests for punt and kickoff dice display
- Full 28-team simulation verified with consistent offense.csv format

---

## Version 1.2 (February 2026)

### New Features
- **Week number support**: Added `--week N` flag to specify week number when recording games to standings
  - Usage: `python -m paydirt --play --week 1 --compact`
  - Multiple games can be recorded for the same week
  - Week number persists correctly through save/load

### Bug Fixes
- **End zone coordinate system**: Fixed incorrect end zone handling throughout the game engine. Goal lines are now correctly treated as part of the end zone (position <= 0 for offense's end zone, position >= 100 for defense's end zone). Field of play is positions 1-99
- **Interception in defense's end zone**: Defense intercepting in their own end zone (where offense was trying to score) now correctly results in a touchback
- **Interception in offense's end zone**: Defense intercepting in opponent's end zone (behind offense's goal line) now correctly results in a TD for defense
- **Fumble in offense's end zone**: Defense recovering a fumble in opponent's end zone now correctly results in a TD for defense (was incorrectly always a safety)
- **Kickoff/punt end zone returns**: Fixed per official rules VI-12-F. Returns from end zone now correctly count end zone yardage; ball must cross goal line or it's a touchback. Returns cannot be attempted from on/behind the end line
- **Fumble penalty decision flow**: Fixed fumble recovery to be rolled BEFORE presenting penalty choice, matching NFL rules where the play is fully completed before the penalty decision. Uses the transaction system to capture all play events (chart lookup, fumble, recovery) before displaying the choice. UI now shows actual recovery result from the transaction
- **Week auto-increment bug**: Fixed bug where `--week` flag was ignored and games were recorded with auto-incrementing week numbers based on total game count
- **Raiders abbreviation**: Fixed team abbreviation from "LAA" to "LAR" for the Los Angeles Raiders
- **Fumble recovery roll 19**: Fixed incorrect auto-TD on recovery roll 19. Per official rules, auto-TD on roll 19 only applies to blocked kicks, not regular fumbles. Fumble recovery rolls 17, 18, 19 now correctly use the INT return chart
- **Penalty turnover acceptance**: Fixed bug where accepting a turnover play result after a penalty would re-roll for fumble recovery instead of using the already-determined result
- **Turnover on downs after punt**: Fixed incorrect "TURNOVER ON DOWNS" message displaying after punts. Punts are normal possession changes, not turnover on downs
- **Punt fumble recovery clarity**: Added team name to fumble recovery message (e.g., "NYG '83 recovers and keeps possession!")
- **Midfield display**: Changed 50-yard line display from team-specific (e.g., "CIN 50") to "midfield" for clarity
- **Resume game standings**: Added prompt to record game to standings when a resumed game ends
- **Missing import**: Fixed `NameError: format_time not defined` in resume_game function

### Test Coverage
- **985 unit tests** passing
- Added tests for week parameter in standings (explicit week, auto-assign, persistence)
- Added tests for interception in end zone touchback scenarios

---

## Version 1.1 (February 2026)

### Transaction-Based Play Tracking
- **Play events system**: New `PlayTransaction` and `PlayEvent` classes track every aspect of a play
- **Event types**: Primary play, fumble, fumble return, interception, interception return, penalty, touchdown, safety
- **Improved action lines**: Commentary now uses transaction events for accurate play-by-play descriptions
- **Fumble/INT returns**: Action lines now show return yardage and spot correctly

### AI Clock Management
- **No-huddle offense**: AI uses no-huddle when trailing late in Q4 (announced in output)
- **Out-of-bounds designation**: AI automatically uses OOB on passing plays to stop clock when trailing
- **Earlier hurry-up**: Down by 9+ points triggers hurry-up with 8+ minutes left; down by 4+ with 5+ minutes
- **Pass-only under 2 minutes**: AI avoids running plays (Draw, Line Plunge) when under 2 minutes and trailing
- **Smarter play selection**: Two-minute offense prioritizes clock-stopping plays

### Game Save/Load
- **Save mid-game**: Type `save` during play selection to save current game state
- **Resume games**: `python -m paydirt --load` to resume saved game
- **Full state preservation**: Saves score, field position, down/distance, time, timeouts, scoring plays

### Bug Fixes
- **Fumble return events**: Fixed missing FUMBLE_RETURN events in transactions for defense recoveries
- **Fumble action line**: Shows fumble spot when defense recovers with 0 return yards
- **Blocked punt on 4th down**: Now correctly results in turnover if recovery is short of first down marker
- **Sack ignores OOB designation**: QB sacks no longer incorrectly stop the clock with OOB designation
- **KeyError on 4th down penalties**: Fixed crash when penalty decision occurred on 4th down
- **Interception return TD**: Fixed yardage calculation for pick-six plays
- **ScoringPlay serialization**: Fixed `time_remaining` and `is_home_team` fields for save/load

### Test Coverage
- **917 unit tests** passing
- **14 integration games** (28 teams) verified
- New test files: `test_play_events.py`, `test_save_game.py`
- Added tests for clock management, fumble handling, punt blocking, sack OOB

---

## Version 1.0 (February 2026)

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
- **Cleaner turnover display**: Moved dice roll details from game action line to technical details line. Game action now shows clean commentary (e.g., "INTERCEPTED! Returned 15 yds") while technical line shows full details (e.g., "INT@47, Ret:15(roll 34)").
- **Fumble recovery display**: Shows fumble recovery info on technical line with spot and recovery roll.
- **Interception return display**: Shows INT return info on technical line with spot, return yards, and roll.
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
