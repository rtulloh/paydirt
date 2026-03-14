# Paydirt Release Notes

## Unreleased

### Touchdown Scoring Audit
Comprehensive audit of all touchdown scoring paths in `run_play` and `_apply_play_result` to prevent missed touchdowns:
- **QB_SCRAMBLE touchdown detection**: Fixed `_apply_play_result` (penalty procedure path) missing touchdown check when a QB scramble reached the end zone. The `run_play` path already had this check, but the penalty procedure path did not.
- **OOB 5-yard deduction in penalty path**: Fixed `_apply_play_result` missing the out-of-bounds designation 5-yard deduction that `run_play` already applied. Plays going through the penalty procedure path now correctly deduct 5 yards for OOB designation.

### Out-of-Bounds (*) Chart Marker Fixes
Fixed the `*` out-of-bounds marker being silently dropped at multiple levels of the play resolution pipeline:
- **Priority chart OOB propagation**: The `*` marker on offense chart results (e.g., `"3*"`, `"9*"`) was stripped by `categorize_result()` and never propagated to `PlayResult`. Added `out_of_bounds` field to `CombinedResult` and detection logic in `apply_priority_chart()`. **~568 chart entries** across all 28 teams were affected.
- **Breakaway (B) column OOB**: `resolve_breakaway()` silently dropped `*` markers (e.g., `"11*"`, `"32*"`) by falling through `int()` parse to random defaults. Now returns a `ColumnResult` with correct yardage and `out_of_bounds=True`. **~20+ entries** affected.
- **QB Time (QT) column OOB**: `resolve_qb_scramble()` silently dropped `*` markers (e.g., `"3*"`, `"-6*"`) the same way. Now returns `ColumnResult` with correct yardage and `out_of_bounds=True`.

### QB Time (QT) Column Fumble Handling
- **QT fumble results ignored**: `resolve_qb_scramble()` silently dropped fumble results like `"F - 8"`, `"F - 23"`, and `"F"` from the QT column by falling through `int()` parse to random yardage. Now correctly returns `ColumnResult` with `is_fumble=True` and proper yardage. Callers set `ResultType.FUMBLE` accordingly. **~50+ entries** affected across all teams.

### Clock Management Fixes
- **OOB designation (+) broken outside final minutes**: The `+` modifier (costs 5 yards, guarantees 10-sec play) was gated by `in_final_minutes` in `_use_time`, meaning it only worked in Q2 ≤2:00 and Q4 ≤5:00. In Q1/Q3, players paid 5 yards for zero clock benefit. Now forces exactly 10 seconds in all quarters. Natural `*` chart markers still respect the final-minutes gate per rules.
- **No-huddle was purely cosmetic**: The no-huddle flag was toggled in the UI and printed but never passed to the game engine. Play timing always used `random.uniform(5, 40)` regardless. Added `no_huddle` parameter to `run_play`, `run_play_with_penalty_procedure`, and `_apply_play_result`. When active, uses `random.uniform(5, 20)`. Updated callers in `interactive_game.py` and `auto_game.py`.

### Code Improvements
- **`ColumnResult` dataclass**: New dataclass in `play_resolver.py` for structured results from B and QT column resolution (yards, out_of_bounds, is_fumble).
- **`_parse_column_value()` helper**: Shared parser for B/QT column entries handling plain integers, `*` OOB markers, and `F - X` fumble results.
- **Priority chart duplicate key**: Removed stale duplicate `(BREAKAWAY, BLACK)` entry in priority chart lookup table.

### Bug Fixes (Prior)
- **Punt penalty decision**: Fixed bug where selecting "Keep return + yards" option on offensive punt penalties incorrectly applied the replay logic instead of keeping the return result. Added `penalty_index` parameter to distinguish between penalty options.
- **Priority chart Oyl + Oyg**: Fixed priority chart to correctly ADD negative offense result (Oyl) with positive defense result (Oyg) per official rules. Example: -1 + 1 = 0 net yards (was incorrectly using -1).
- **Priority chart Breakaway (B) + defense**: Fixed breakaway vs positive/negative results to ADD per official chart. Also fixed breakaway vs BLACK to be incomplete on passing plays.
- **Priority chart FUMBLE**: Fixed fumble/BK to take priority over all but penalty per official chart - includes fixes for FUMBLE vs QT, INT, (TD), and RED_NUMBER.
- **Priority chart GREEN/WHITE/RED vs BLACK**: Fixed all cases where offense has yardage vs defense BLACK to be BLACK (incomplete/no gain) per priority chart.
- **Priority chart WHITE vs GREEN/RED**: Fixed WHITE vs GREEN and WHITE vs RED to ADD per priority chart (no notion of GREEN in CSV files).
- **Priority chart RED vs WHITE**: Fixed to ADD per priority chart (negative + zero = negative).
- **Priority chart TD vs QT/BLACK**: Fixed to use QT and BLACK respectively per priority chart.
- **Priority chart INT vs INT**: Fixed to use shortest yards when both have INT.
- **Priority chart penalties always win**: Added tests confirming PI, OFF, and DEF penalties take priority over all but penalty.

### Test Coverage
- **1342 unit tests** passing
- Added 18 tests for OOB designation and no-huddle clock management (`test_clock_management_fixes.py`)
- Added 15 tests for all touchdown scoring paths via penalty procedure (`test_touchdown_all_paths.py`)
- Added 11 tests for OOB deduction and QB_SCRAMBLE fixes in penalty path (`test_oob_penalty_procedure_path.py`)
- Added 32 tests for `_parse_column_value`, `resolve_breakaway`, `resolve_qb_scramble` (`test_column_resolvers.py`)
- Added 18 tests for OOB marker propagation through priority chart (`test_oob_priority_chart.py`)
- Added tests for penalty_index parameter in punt penalty handling
- Added tests for RED_NUMBER + GREEN_NUMBER priority resolution
- Added comprehensive tests for (TD) defense overriding all offense result types
- Added tests for penalties vs fumble and (TD)

---

## Version 1.6 (February 2026)

### AI Helper System
Added an AI-powered helper system to assist players in Easy mode:
- **AI Helper toggle**: Press `Z` to toggle the AI helper on/off (Easy mode only)
- **Play suggestions**: Shows top 3 plays ranked by success rate and average yards
- **Situational tips**: Provides context-aware advice for clock management, red zone, two-minute drill, etc.
- **Team chart analysis**: Analyzes your team's offensive charts to find optimal plays based on historical dice roll results
- **Defense suggestions**: Recommends defensive formations based on opponent tendencies

### Bug Fixes
- **Breakaway (B) in play suggestions**: Fixed the AI helper from incorrectly suggesting the "B" play type. "B" is not a callable play - it's a random result that occurs during play resolution when a big gain is possible. The breakaway column now correctly shows 0 valid plays in suggestions.
- **Z key in Medium/Hard modes**: The Z key no longer appears in the play menu or responds to input in Medium/Hard difficulty modes. It now only works in Easy mode where the AI helper is available.

### Test Coverage
- **1165 unit tests** passing (up from 1154)
- Added tests for breakaway exclusion from play suggestions
- Added tests for PlayOutcome is_breakaway field
- Added tests for AI Helper Z key behavior in different difficulty modes

---

## Version 1.5.2 (February 2026)

### Critical Bug Fixes - Priority Chart
Fixed 5 bugs in priority chart resolution that would have caused incorrect yardage calculations during gameplay:
- **(PARENS, WHITE_NUMBER)**: Was incorrectly ADDING, should use OFFENSE (parentheses take precedence)
- **(PARENS, RED_NUMBER)**: Was incorrectly ADDING, should use PARENS (parentheses overrule negative)
- **(WHITE_NUMBER, RED_NUMBER)**: Was incorrectly ADDING, should use DEFENSE (defense wins over no gain)
- **(RED_NUMBER, WHITE_NUMBER)**: Was incorrectly ADDING, should use DEFENSE (defense wins)
- **PARENS result handling**: Was using defense's value in both cases, now correctly uses offense's value when offense has parentheses

### Bug Fixes
- **Defense chart CSV parsing**: Fixed wrong column indices in parse_defense_csv that prevented defense modifiers from loading
- **1983 Bears defense chart**: All 30 formation/sub-row combinations now load correctly
- **Auto game penalty handling**: Fixed bug where CPU vs CPU games didn't handle penalty decisions for punts (including coffin corner), field goals, and kickoffs
- **Timeout after two-minute warning**: Fixed bug where timeout used pre-play time instead of current time after two-minute warning triggered. Now correctly uses current time (2:00) when subtracting 10 seconds

### Test Coverage
- **1118 unit tests** passing (up from 1107)
- Added 1983 Bears defense chart tests (B-3, D-5, all 30 rows, all formations)
- Added 1983 Bears offense chart test (die roll 24 with empty cell and BLACK cells)
- Added priority chart edge case tests for the 5 bugs fixed

## Version 1.5.1 (February 2026)

### AI Improvements
- **End-of-half field goal awareness**: CPU now kicks a field goal on any down (not just 4th) when ~10 seconds or less remain in Q2 or Q4 and the ball is in makeable FG range (inside opponent's 30, <=47 yard attempt). In Q4, the CPU only kicks if trailing by 3 or fewer (where a FG ties or wins); otherwise it goes for the TD. Previously the CPU would run a normal play and waste the last seconds of the half.

### Bug Fixes
- **Punt penalty ignored on touchback**: Fixed a bug where a punt that went into the end zone for a touchback with a penalty (e.g., OFF 5) would skip the penalty decision entirely. The receiving team now correctly gets the choice to either replay the punt from the LOS minus penalty yards, or keep the touchback plus the penalty yards (e.g., 20 + 5 = 25). Previously the ball would just be placed at the 20 with no penalty applied.
- **Punt penalty ignored on coffin corner**: Fixed a similar bug where a punt that went out of bounds due to coffin corner rules (15+ yards subtracted) with a penalty would skip the penalty decision. The receiving team now correctly gets the choice.
- **Half not ending at 0:00**: Fixed a bug where a play could randomly use just enough clock time to leave a sub-second residual (e.g., 0.003 minutes) that displayed as "0:00" but was technically positive, preventing the quarter from advancing. The game would prompt for another play at "Q2 0:00" instead of going to halftime. The `_use_time()` method now clamps any residual under 1 second to exactly 0 so the quarter-end logic triggers correctly.
- **Game loop safety net for quarter end**: Added a safety net in both the `run_interactive_game` and `resume_game` loops to force quarter advancement when time is effectively zero at Q1-Q3, preventing any edge case from allowing play to continue past the end of a half.
- **Timeout clock residual**: Fixed `_apply_timeout()` to clamp residuals under 1 second to 0, preventing timeouts from leaving the game in an inconsistent state.
- **Breakaway commentary on negative yardage**: Fixed commentary incorrectly using exciting breakaway language (e.g., "LOOK OUT! Wilbert Montgomery has daylight!") when the B column roll produced negative yardage (e.g., -10 yards). Breakaway commentary now correctly uses loss language for negative yards and no-gain language for zero yards.
- **1983 Redskins & Eagles charts**: Fixed defense and offense charts to correctly parse parentheses from Excel cell format and detect BLACK cells (incomplete passes) from background color.
- **Interception return after penalty decision**: Fixed a bug where accepting a play result after a penalty would re-roll the interception return dice instead of using the original return. This was causing 5-yard interceptions to become 70-yard returns after penalty choices.
- **BLACK categorized as BREAKAWAY**: Fixed a bug where "BLACK" in offense charts was being miscategorized as BREAKAWAY (since it starts with "B"), causing incomplete passes to trigger breakaway resolution instead of being treated as incomplete. Now checks for "BLACK" before "B" in the categorization logic.
- **FG penalty result showing "Gain of X yards"**: Fixed a bug where field goal attempts with penalties would incorrectly display "Gain of X yards" in the penalty choice. The FG chart result (e.g., "12" for a 12-yard kick) was being parsed as 12 yards gained on a normal play. Now uses yards=0 for FG penalty results to avoid incorrect display.
- **Punt penalty options showing wrong down/distance**: Fixed a bug where punt penalty options ("Keep touchback + X yards" and "Keep result + X yards") were showing "4th and X" instead of "1st and 10". When the offense accepts a defensive penalty on a punt, they should get an automatic first down. Now sets auto_first_down=True for keep options.
- **Breakaway dice not shown in diagnostic display**: Fixed a bug where breakaway plays didn't show the breakaway dice roll in the diagnostic output (e.g., `(O:34→"B" | D:3→"-2" | #B)`). Now also shows `| B:22` for the breakaway roll. Added `breakaway_dice` field to PlayResult and updated display logic.
- **FG penalty auto first down shows wrong distance**: Fixed a bug where accepting a defensive penalty on a field goal attempt showed "1st & Goal @ X" instead of "1st and 10 at opp X". After a defensive penalty with automatic first down, the offense gets a fresh set of downs (10 yards to go), not the distance to the goal line. Previously the code used `100 - ball_position` which resulted in showing "& Goal" when inside the 20.
- **D1 Black should mean incomplete**: Fixed a bug where defense rolling BLACK (incomplete) was being treated the same as an empty/no result. For passing plays with positive offense yards and BLACK defense, the pass is now correctly ruled incomplete. Empty cells now return GREEN_NUMBER with value 0 so they ADD with defense results (e.g., empty + 3 = 3 yards).

### Test Coverage
- **1107 unit tests** passing
- Added tests for interception return reuse after penalty decision
- Added tests for BLACK result categorization
- Added tests for punt penalty keep options auto_first_down
- Added tests for breakaway_dice field in PlayResult

## Version 1.5 (February 2026)

### Kickoff & Punt Penalty Handling Overhaul
- **Kickoff chart penalties**: Added support for penalties on the kickoff chart itself (pre-return)
  - DEF penalty (receiving team foul): Kicking team gets choice - accept (re-kick from adjusted spot) or decline
  - OFF penalty (kicking team foul): Receiving team gets choice - accept (re-kick from adjusted spot) or decline
  - Offsetting penalties on re-roll: Automatic re-kick from original spot
- **Punt chart penalties with choice**: Penalties on punt chart now offer the offended team a choice
  - OFF penalty (punting team foul): Receiving team chooses - replay punt from LOS minus penalty yards, or keep result plus penalty yards
  - DEF penalty (receiving team foul): Punting team chooses - accept penalty (ball moves forward, potential first down), or decline and take punt result
  - X modifier support (e.g., DEF 5X): Automatic first down for punting team when accepting penalty
- **Removed default yardage bug**: No more 35-yard default punt or 20-yard default return - game re-rolls until actual yardage is obtained from chart
- **Chart penalty perspective clarified**: Penalties use scrimmage play perspective (punting/kicking team = offense, receiving team = defense)

### Kickoff & Punt Return Penalty Consistency
- **Re-roll for return yardage**: When a penalty occurs on a kickoff or punt return, the game now re-rolls for actual return yardage instead of using a default value
- **Offsetting penalties**: If the re-roll results in an offsetting penalty (OFF + DEF), the play is reset and the kick is replayed
- **Larger penalty selection**: If the re-roll results in the same type of penalty (OFF + OFF or DEF + DEF), the larger penalty is automatically chosen
- **OFF penalty on TD return**: Negates the touchdown; penalty applied from catch point with half-the-distance rule
- **DEF penalty on TD return**: Touchdown stands; penalty applied to ensuing kickoff spot
- **Safety kicks now use shared logic**: Safety free kicks (kickoff and punt) now use the same penalty handling as regular kicks

### Code Quality & Refactoring
- **Extracted `game_state.py`**: Moved `ScoringPlay`, `TeamStats`, `GameState`, and `PlayOutcome` dataclasses to a new module for better organization
- **Shared `_handle_return_penalty()` helper**: Both kickoff and punt returns use the same function for penalty handling (re-roll, offsetting, larger penalty selection)
- **Shared `_apply_half_the_distance()` helper**: Centralized half-the-distance rule calculation
- **Parameterized kickoff/punt**: Added `kickoff_spot` and `punt_from` parameters to eliminate duplicated safety kick code
- **New `apply_kickoff_penalty_decision()` method**: Handles kickoff chart penalty choices
- **New `apply_punt_penalty_decision()` method**: Handles punt chart penalty choices

### Test Coverage
- **1065 unit tests** passing
- Added tests for kickoff chart penalty handling (DEF/OFF penalties, offsetting, choice mechanism)
- Added tests for punt chart penalty handling (DEF/OFF penalties, X modifier, first down logic)
- Added tests for kickoff/punt return penalty re-rolls
- Added tests for offsetting penalties causing rekick/repunt
- Added tests for larger penalty selection on same-type penalties

### Bug Fixes
- **QB kneel commentary**: Fixed commentary incorrectly referencing the running back instead of the quarterback when a QB takes a knee. Now shows "Phil Simms is hit in the backfield!" instead of "Gerald Riggs is hit in the backfield!"
- **Punt return dice display**: Added return dice roll to display in format `(P:17→"32" | R:10→"13" | return)` showing both punt and return dice rolls

### AI Penalty Decision Handling
- **Correct apply methods for punt/kickoff**: `handle_penalty_decision` now routes to `apply_punt_penalty_decision` and `apply_kickoff_penalty_decision` instead of the generic `apply_penalty_decision`
- **CPU decision logic**: Added intelligent CPU decision-making for punt/kickoff penalties (generally accepts penalties, takes first downs)
- **Kickoff penalty handling**: All kickoff locations (opening, halftime, overtime, post-score) now properly handle penalty decisions

### Penalty Display Improvements
- **Fixed punt penalty option 1**: Now shows "Punt stands as called" instead of incorrectly showing "TURNOVER ON DOWNS"
- **Half-distance position fix**: Penalty descriptions now show the adjusted position after half-distance rule (e.g., "Replay punt from own 9" not "from own 2")
- **Dice roll display for punt/kickoff penalties**: Shows rolls in format `(P:14→"OFF 15" | reroll: 15→40 | R:→"10")` for easier diagnosis

### Documentation
- **Prerequisites section**: Added Python installation instructions for macOS, Linux, and Windows to README

### Test Coverage Additions
- **1074 unit tests** passing
- Added test for punt return dice roll tracking
- Added tests for punt penalty display logic (play_type, final_position, half-distance)
- Added test for dice roll storage in _pending_punt_state

---

## Version 1.4 (February 2026)

### Bug Fixes
- **Nested tuple AttributeError**: Fixed crash in CPU AI when selecting certain plays. A nested tuple was being created when going for it on 4th down in opponent territory, causing `AttributeError: 'tuple' object has no attribute 'value'`
- **Blocked punt dice roll**: Fixed blocked punts showing "Roll: 0" instead of actual dice roll in game output
- **Punt penalty yardage**: Fixed penalties on punts not being applied to field position. DEF penalties now add yardage to the receiving team, OFF penalties subtract yardage. Description now shows applied penalty
- **TD with penalty on return**: When a touchdown is scored AND the kicking team commits a penalty during the return, the penalty is now applied to the ensuing kickoff (after the PAT) instead of being lost. Description shows "will apply to kickoff"

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
