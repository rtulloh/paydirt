# Paydirt Football Board Game Simulation

A Python implementation of the classic Paydirt football board game, originally published by Avalon Hill.

## Download & Install

### Pre-built Releases (Recommended)

Download the latest release from the [GitHub Releases](https://github.com/rtulloh/paydirt/releases) page:

| Platform | File |
|----------|------|
| **macOS (Apple Silicon)** | `Paydirt-X.X.X-arm64.dmg` (M1, M2, M3, M4) |
| **macOS (Intel)** | `Paydirt-X.X.X-x86_64.dmg` |
| **Windows** | `PaydirtSetup.exe` (installer) or `paydirt.exe` (portable) |
| **Linux** | `Paydirt-x86_64.AppImage` |

#### macOS Installation Note
If you see "Paydirt is damaged and can't be opened":
- **Option 1**: Right-click the app → Open → Click "Open" in the dialog
- **Option 2**: Run in Terminal: `xattr -cr "/Applications/Paydirt.app"`

### Python Installation (Manual)

If you prefer to run from source or a pre-built executable isn't available for your platform:

```bash
# Clone or download this repository
cd paydirt

# Interactive game (Human vs CPU)
python -m paydirt
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--play` | Start interactive game mode |
| `-d easy\|medium\|hard` | Set CPU difficulty level |
| `--compact` | Use compact display (less verbose, recommended) |
| `--week N` | Specify week number for standings |
| `--load [file]` | Resume a saved game |
| `-auto team1 team2` | Run CPU vs CPU simulation |
| `--scaffold-season YEAR` | Generate season rules YAML file |
| `--home team` | Your team (e.g., `--home 2026/Thunderhawks`) |
| `--away team` | Opponent team (e.g., `--away 2026/Ironclads`) |
| `--playoff-game` | Use playoff overtime rules (no ties) |

### CPU Difficulty Levels

| Level | Description | CPU Behavior |
|-------|-------------|--------------|
| **Easy** | Conservative | Punts often, kicks FGs, rarely goes for it on 4th down |
| **Medium** | Balanced (default) | Standard NFL-like decisions |
| **Hard** | Aggressive | Goes for it on 4th down more, attempts long FGs, optimal play calling |

### Difficulty Settings Explained

#### Easy Mode

- **AI Helper**: Enabled by default - shows suggested plays based on your team's offensive chart analysis
- **CPU Aggression**: 0.3 (conservative)
- **4th Down**: Rarely goes for it, prefers to punt
- **Field Goals**: Conservative range, won't attempt long attempts
- **Onside Kicks**: Rarely attempts

**AI Helper Features**:
- Shows your top 3 plays ranked by success rate
- Provides situational tips (clock management, red zone, etc.)
- Displays average yards per play
- Toggle with `Z` key during play selection

#### Medium Mode (Default)

- **AI Helper**: Disabled by default
- **CPU Aggression**: 0.5 (balanced)
- **4th Down**: Standard NFL decision-making
- **Field Goals**: Normal range considerations
- **Onside Kicks**: Occasional surprise attempts

**Manual AI Helper**:
- Press `Z` during play selection to toggle AI Helper on/off
- Works in any difficulty mode

#### Hard Mode

- **AI Helper**: Disabled by default
- **CPU Aggression**: 0.7 (aggressive)
- **4th Down**: Aggressive - often goes for it
- **Field Goals**: Will attempt longer field goals
- **Onside Kicks**: More likely to surprise

**AI Analysis (for CPU)**:
- CPU uses team chart analysis to find optimal plays
- Tracks opponent tendencies to predict play calls
- Makes decisions based on down, distance, and game situation

### AI Helper Controls

| Key | Action |
|-----|--------|
| `Z` | Toggle AI Helper on/off (Easy mode only) |
| `?` | View full play menu (compact mode) |
| `/` | View game statistics |

### AI Helper Display Example

When enabled, the AI Helper shows before each play:

```
  === AI HELPER (Your Best Plays) ===
  ----------------------------------------
    1. Line Plunge - 91% success, 4.2 avg yards
    2. Off Tackle - 82% success, 3.7 avg yards
    3. Short Pass - 74% success, 4.9 avg yards

  Tip: 3rd & short - power runs are best here
  Recommended: Line Plunge (91% success)
```

The helper analyzes your team's offensive charts to find:
- **Success Rate**: Percentage of plays with positive yardage
- **Average Yards**: Mean yards gained per play
- **Situational Tips**: Context-aware advice for clock management, red zone, etc.

## How to Play

### Starting a Game

1. Run `python -m paydirt`
2. Select your team from the list (e.g., `1` for the first team)
3. Choose to play as Home or Away
4. The game begins with a kickoff

### Game Display

Each play shows:
```
  ============================================================
  Q1  |  14:32  |  AWY 0 - HOM 0
  ============================================================

  Ball on: own 25-yard line
  Down: 1st and 10
  Possession: HOM (YOU)
  Timeouts: HOM 3 | AWY 3
```

### Calling Plays on Offense

When you have the ball, you'll see a play menu:

```
  OFFENSIVE PLAY CALL
  ----------------------------------------
  RUNNING PLAYS:
    [1] Line Plunge      - Power run up the middle
    [2] Off Tackle       - Run between guard and tackle
    [3] End Run          - Sweep to the outside
    [4] Draw             - Delayed handoff

  PASSING PLAYS:
    [5] Screen           - Short pass behind the line
    [6] Short Pass       - Quick pass (5-10 yards)
    [7] Medium Pass      - Intermediate route (10-20 yards)
    [8] Long Pass        - Deep pass (20+ yards)
    [9] TE Short/Long    - Tight end route

  SPECIAL PLAYS:
    [Q] QB Sneak         - Sneak for 1 yard (defense can't respond)
    [H] Hail Mary        - Desperation pass (end of half only)
    [S] Spike Ball       - Stop clock, waste down (saves 20 sec)
    [K] QB Kneel         - Run out clock (-2 yards, 40 sec)

  OPTIONS:
    [N] No Huddle        - Hurry-up offense (saves time, penalty risk)
    [T] Call Timeout     - Stop clock after this play
    [/] Stats            - View current game statistics
    Add '+' for Out of Bounds (e.g., '5+' = stops clock, costs 5 yards)
    Add '-' for In Bounds (e.g., '5-' = keeps clock running, costs 5 yards)
```

**Enter a number (1-9) or letter (Q, H, S, K, N, T, /) to call your play.**

**Press Enter to accept the suggested default play** (shown at the bottom of the menu).

### Calling Plays on Defense

When the opponent has the ball:

```
  DEFENSIVE FORMATION
  ----------------------------------------
    [A] Standard         - Balanced defense
    [B] Short Yardage    - Stop the run
    [C] Spread           - Cover more receivers
    [D] Short Pass       - Defend quick passes
    [E] Long Pass        - Defend deep routes
    [F] Blitz            - Rush the QB (risky but rewarding)

    [T] Call Timeout     - Stop clock after this play
    [/] Stats            - View current game statistics
```

### 4th Down Decisions

On 4th down, you'll be asked:
- **[P] Punt** - Kick the ball away
- **[F] Field Goal** - Attempt a field goal (if in range)
- **[G] Go for it** - Try to convert

### After a Touchdown

Choose your extra point attempt:
- **[K] Kick** - Extra point (1 point, high success rate)
- **[2] Two-point** - Conversion attempt (2 points, risky)

**Note:** Whether the 2-point conversion is available depends on the season rules. Pre-1994 teams only have the extra point kick option. Rules are configured in `seasons/YYYY/YYYY.yaml` (see [Season Rules](#season-rules)).

### Kickoffs

On **every kickoff** (opening, halftime, and after scores), you can choose:
- **[K] Normal Kickoff** - Standard kick (default - press Enter)
- **[O] Onside Kick** - Attempt to recover (risky, recover on roll 13-20)

**Surprise Onside Kicks**: You can attempt an onside kick on the opening kickoff, just like the famous 1982 NFC Championship when the Packers surprised the Cowboys!

### Quick Play with Defaults

Throughout the game, you can **press Enter** to accept the suggested default choice:

| Situation | Default |
|-----------|---------|
| Home/Away selection | Home |
| Coin toss call | Heads |
| Win toss decision | Receive |
| Kickoff type | Regular kickoff |
| 4th down (deep) | Punt |
| 4th down (FG range) | Field Goal |
| Offense (short yardage) | Line Plunge |
| Offense (long yardage) | Medium Pass |
| Offense (medium) | End Run |
| Defense (short yardage) | Short Yardage (B) |
| Defense (long yardage) | Long Pass (E) |
| Defense (medium) | Standard (A) |

This makes it easy to play quickly while still having full control when you want it.

---

## Time Management

### Saving Time (When Trailing)

| Option | How to Use | Effect | Cost |
|--------|------------|--------|------|
| **No Huddle** | Press `N` to toggle | Previous play uses 20 sec instead of 40 | Penalty risk |
| **Spike Ball** | Press `S` | Stops clock immediately | Wastes a down |
| **Out of Bounds** | Add `+` to play (e.g., `5+`) | Guarantees 10-sec play | -5 yards |

### Killing Time (When Leading)

| Option | How to Use | Effect | Cost |
|--------|------------|--------|------|
| **QB Kneel** | Press `K` | Uses 40 seconds | -2 yards |
| **In Bounds** | Add `-` to play (e.g., `3-`) | Keeps clock running | -5 yards |
| **Run the ball** | Press `1-4` | Clock runs, safe plays | None |

### Timeouts

- Each team has **3 timeouts per half**
- **Add `T` to your play call** to call a timeout (e.g., `5T` or `AT`)
- Works on both offense and defense
- Calling a timeout **reduces the play's time to 10 seconds** (saves ~20 seconds)
- Only one timeout allowed per play
- Timeouts reset at halftime
- **2-minute warning** automatically stops the clock at 2:00 in Q2 and Q4

### Final Seconds Strategy

When less than 40 seconds remain and you need one more play:

| Situation | Best Option | Why |
|-----------|-------------|-----|
| Need to stop clock, have timeout | Call play + `T` | Play uses only 10 sec with timeout |
| Need to stop clock, no timeout | Spike Ball (`S`) | Uses only ~3 sec, wastes a down |
| Need TD, ~10 sec left | Hail Mary (`H`) | One shot at the end zone |

**Example**: 0:30 left, trailing by 4, ball at opponent's 35
1. Call `7T` (Medium Pass + Timeout) → Gain yards, clock stops at ~0:20
2. Call `8` (Long Pass) → Try for TD or get closer
3. If incomplete, clock stopped → one more play
4. If complete but short, call `S` (Spike) → Clock stops at ~0:05
5. Final play: `H` (Hail Mary) or `F` (Field Goal)

---

## Play Resolution

### How Plays Work

1. **You call a play** (offense) or **formation** (defense)
2. **Dice are rolled** for both offense and defense
3. **Charts are consulted** based on the dice results
4. **Priority Chart** combines the results to determine the outcome
5. **Yardage is applied** and the game state updates

### Result Types

| Result | Description |
|--------|-------------|
| **Yards** | Gain or loss of yardage |
| **Incomplete** | Pass falls incomplete, clock stops |
| **Interception** | Defense catches the ball, turnover |
| **Fumble** | Ball is loose, recovery determined by roll |
| **Touchdown** | 6 points! Choose PAT or 2-point conversion |
| **Safety** | Defense scores 2 points, gets the ball |
| **Penalty** | Yardage assessed, may replay down |

### Special Markers

- **Asterisk (*)** or **Dagger (†)** - Play ended out of bounds (clock stops in final minutes)
- **Breakaway** - Big play potential, extra yardage possible

---

## Strategy Tips

### On Offense

- **1st Down**: Mix runs and passes to keep defense guessing
- **3rd and Short**: Power runs (Line Plunge, Off Tackle) or QB Sneak
- **3rd and Long**: Medium/Long Pass, Screen, or Draw
- **Red Zone**: Short passes and power runs are safer
- **Goal Line**: QB Sneak or Line Plunge for 1 yard

### On Defense

- **1st/2nd Down**: Standard (A) is usually safe
- **3rd and Short**: Short Yardage (B) to stop the run
- **3rd and Long**: Long Pass (E) or Blitz (F)
- **Obvious Passing**: Short Pass (D) or Long Pass (E)
- **Late Game, Protecting Lead**: Spread (C) or Long Pass (E)

### Clock Management

- **Trailing late**: Use No Huddle, Spike Ball, Out of Bounds (+)
- **Leading late**: Use QB Kneel, In Bounds (-), run the ball
- **2-minute drill**: Quick passes to sidelines, spike if needed

---

## Game Rules

### Scoring

| Score | Points |
|-------|--------|
| Touchdown | 6 |
| Extra Point (kick) | 1 |
| Two-Point Conversion | 2 |
| Field Goal | 3 |
| Safety | 2 |

### Timing

- **4 quarters** of 15 minutes each
- **Each play** uses 5-40 seconds depending on result
- **Out of bounds** plays use only 10 seconds in final minutes
- **2-minute warning** stops clock at 2:00 in Q2 and Q4

### Downs

- **4 downs** to gain 10 yards for a first down
- **Turnover on downs** if you fail to convert on 4th down
- **Touchback** places ball at the 20-yard line

## Available Seasons

Teams are loaded from the `seasons/` directory. Each season includes a rules YAML file and team subdirectories with chart data.

### 2026 Season

A sample modern season with fictional teams for testing. Includes 2-point conversion and modern overtime rules.

---

## Adding Your Own Seasons

You can add your own season data to Paydirt. The application looks for seasons in two locations:

1. **Built-in seasons** - Bundled with the application
2. **User seasons directory** - Your custom seasons (takes precedence over built-in)

### User Seasons Directory Location

The user seasons directory location depends on your operating system:

| Platform | Directory Path |
|----------|---------------|
| **macOS** | `~/Library/Application Support/Paydirt/seasons/` |
| **Windows** | `%LOCALAPPDATA%\Paydirt\seasons\` |
| **Linux** | `~/.local/share/Paydirt/seasons/` |

### Adding a Season

1. **Create the user seasons directory** if it doesn't exist:

   **macOS/Linux:**
   ```bash
   mkdir -p ~/Library/Application\ Support/Paydirt/seasons/    # macOS
   mkdir -p ~/.local/share/Paydirt/seasons/                    # Linux
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:LOCALAPPDATA\Paydirt\seasons"
   ```

2. **Create a season folder** (e.g., `1983/`) inside the seasons directory

3. **Add required files** for each team:
   - `offense.csv` - Offensive play charts
   - `defense.csv` - Defensive formation charts
   - `special.csv` - Special teams charts

4. **Add optional team metadata**:
   - `team.yaml` - Team name, colors, location
   - `roster.json` - Player names for commentary

5. **Create the season rules file** (`1983.yaml`) in the season directory

### Season Directory Structure

```
seasons/
└── 1983/
    ├── 1983.yaml           # Season rules (required)
    └── Dolphins/
        ├── offense.csv     # Required
        ├── defense.csv     # Required
        ├── special.csv     # Required
        ├── team.yaml       # Optional: team metadata
        └── roster.json     # Optional: player names
```

### Example team.yaml

```yaml
team_name: Miami Dolphins
short_name: MIA
team_color: "#008E97"
team_mascot: Dolphin
city: Miami
state: FL
founded: 1966
history: "The perfect season team of 1972."
```

### Example roster.json

```json
{
  "qb": "Dan Marino",
  "rb": "Tony Nathan",
  "wr": "Mark Clayton",
  "k": "Uwe von Schamann"
}
```

### Importing from Excel Files

If you have team data in Excel format (`.xls`), use the `extract_charts.py` script to convert it. See [Importing Teams](#importing-teams) for details.

---

## Season Rules

Each season has a `YYYY.yaml` file in `seasons/YYYY/` that defines era-appropriate rules. The home team's season rules always apply, even in cross-season matchups.

### Rules Configuration

```yaml
season: 2026
two_point_conversion: true     # 2-point conversion available?
overtime:
  enabled: true
  format: modified_sudden_death # sudden_death or modified_sudden_death
  period_length_minutes: 10     # 15 (pre-2017) or 10 (2017+)
  max_periods_regular: 1        # Max OT periods in regular season (0 = unlimited)
  max_periods_playoff: 0        # Max OT periods in playoffs (0 = unlimited)
  can_end_in_tie_regular: true
  can_end_in_tie_playoff: false
  coin_toss_winner_receives: true
```

### Key Rule Changes by Era

| Era | Two-Point Conv | Overtime Format | OT Period |
|-----|---------------|-----------------|-----------|
| Pre-1994 | No | Sudden death | 15 min |
| 1994-2009 | Yes | Sudden death | 15 min |
| 2010-2016 | Yes | Modified sudden death | 15 min |
| 2017+ | Yes | Modified sudden death | 10 min |

### Creating a New Season

Use the scaffold command to generate a starter YAML file:

```bash
# Generate rules with era-appropriate defaults
python -m paydirt --scaffold-season 1995

# Overwrite existing file
python -m paydirt --scaffold-season 2026 --force
```

The scaffold auto-detects rules based on the year (2-point conversion, overtime format, period length).

---

## Importing Teams

The `extract_charts.py` script imports team data from Excel files into the CSV format used by the game.

### Requirements

- **Input format**: Excel files (`.xls`) — one file per team
- **Required Python package**: `xlrd` (for reading `.xls` files with formatting info)
  ```bash
  pip install xlrd==1.2.0
  ```
- **Sheet names**: Excel files must have `OFFENSE` and `DEFENSE` sheets

### Usage

```bash
# Import all teams from a directory
python extract_charts.py -i /path/to/excel/files -o seasons/2026

# Import a single team
python extract_charts.py -i /path/to/excel/files -o seasons/2026 -t TeamName.xls
```

### What It Does

For each Excel file, the script creates a team subdirectory with three CSV files:

| File | Contents |
|------|----------|
| `offense.csv` | Offensive play charts (dice rolls 10-39, all play types) |
| `defense.csv` | Defensive formation charts (formations A-F, sub-rows 1-5) |
| `special.csv` | Special teams charts (kickoff, punt, FG, extra point) |

The script also:
- Identifies BLACK cells (incomplete passes) from cell background colors
- Identifies RED cells (missed extra points) from cell background colors
- Extracts fumble recovery/lost ranges from column Q
- Handles parentheses number formats for defense chart values

### After Importing

After importing, you need to:

1. **Create `team.yaml`** in the team directory with team metadata:
   ```yaml
   team_name: Metro City Thunderhawks
   short_name: MCT
   team_color: "#0066CC"
   team_mascot: Thunderhawk
   city: Metro City
   state: IL
   founded: 1983
   history: "A balanced team with strong passing game and solid defense."
   ```

2. **Create `roster.json`** with player names for commentary:
   ```json
   {
     "qb": "Bob Griese",
     "rb": "Larry Csonka",
     "wr": "Paul Warfield",
     "k": "Garo Yepremian"
   }
   ```

3. **Create the season rules file** if it doesn't exist:
   ```bash
   python -m paydirt --scaffold-season 2026
   ```

---

## Save/Load Games

You can save your game at any time and resume later:

### Saving a Game
During play selection, type `save` to save the current game state:
```
Your play: save
Game saved to paydirt_save.json
```

### Resuming a Game
```bash
python -m paydirt --play --load --compact
```

The save file preserves:
- Score and quarter/time
- Field position, down, and distance
- Timeouts remaining
- Team statistics
- Scoring play history

---

## Season Standings

Track your season results with the standings system:

### Recording Games
After each game, you'll be prompted to record the result:
```
Record this game to season standings? (y/n): y
Game recorded: Week 1 - Giants 21 @ Redskins 28
```

Use `--week N` to specify the week number:
```bash
python -m paydirt --play --week 1 --compact
```

### Viewing Standings
```bash
# Show standings for a season
python -m paydirt.standings show 2026

# List all recorded games
python -m paydirt.standings games 2026
```

### Managing Results

Use `games` to see the numbered list of games, then reference the number with `edit` or `delete`:
```bash
# List all games (shows game numbers)
python -m paydirt.standings games 2026

# Edit a game's score by its number (from the games list)
python -m paydirt.standings edit 2026 1 --home-score 31

# Delete a game by its number (from the games list)
python -m paydirt.standings delete 2026 1
```

---

## Project Structure

```
paydirt/
├── paydirt/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point for python -m paydirt
│   ├── game_engine.py       # Main game engine (source of truth)
│   ├── play_resolver.py     # Play types and result resolution
│   ├── chart_loader.py      # Team chart CSV parsing
│   ├── season_rules.py      # Season rules YAML loading/config
│   ├── overtime_rules.py    # Overtime rules by era
│   ├── penalty_handler.py   # Penalty resolution per official rules
│   ├── computer_ai.py       # Computer opponent AI
│   ├── interactive_game.py  # Interactive CLI game mode
│   ├── commentary.py        # Play-by-play commentary
│   ├── save_game.py         # Game save/load functionality
│   ├── standings.py         # Season standings tracking
│   └── utils.py             # Shared utility functions
├── seasons/
│   ├── 2026/
│   │   ├── 2026.yaml        # Season rules (2-pt, modified OT)
│   │   └── TeamName/
│   │       ├── offense.csv
│   │       ├── defense.csv
│   │       ├── special.csv
│   │       ├── team.yaml    # Team metadata
│   │       └── roster.json  # Player names
│   └── ...
├── extract_charts.py        # Import teams from Excel files
├── standings/               # Season standings data (JSON)
└── tests/                   # Unit tests (1600+ tests)
```

---

## History

The original Paydirt was published by Avalon Hill and used team charts designed by Dr. Thomas R. Nicely, a mathematician. The game was known for its statistical accuracy in simulating NFL football.

This Python implementation faithfully recreates the original game mechanics including:
- **Priority Chart** for combining offensive and defensive results
- **Full Feature Method** penalty handling
- **Official dice** (Black + 2 White for offense, Red + Green for defense)
- **Special teams** charts for punts, kickoffs, field goals, and returns
- **Variable yardage** entries (DS, X, T1, T2, T3)
- **Clock management** rules (2-minute warning, out-of-bounds timing)

---

## Building Standalone Executables

To create standalone executables for Windows, macOS, and Linux, you need:

1. **Python 3.12 or 3.13** (PyInstaller does not yet support Python 3.15)
2. **PyInstaller** (`pip install pyinstaller`)
3. **Platform-specific tools**: NSIS (Windows), create-dmacOS), linuxdeploy (Linux)

### Quick Start

```bash
# Install compatible Python version (e.g., 3.12)
# Create virtual environment
python3.12 -m venv packaging_env
source packaging_env/bin/activate

# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller paydirt.spec --onefile --clean
```

### Automated Builds

The repository includes a GitHub Actions workflow (`.github/workflows/release.yml`) that builds executables for all platforms. Trigger a release by pushing a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Code Signing

For distribution, you'll need code signing certificates. Add them as GitHub repository secrets:
- `WINDOWS_CERTIFICATE` (base64-encoded .p12)
- `MACOS_CERTIFICATE` (base64-encoded .p12)
- `GPG_PRIVATE_KEY` (for Linux AppImage)

See the workflow file for details.

## License

This is a fan-made implementation for educational purposes. Paydirt is a trademark of its respective owners.
