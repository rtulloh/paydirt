# Paydirt Football Board Game Simulation

A Python implementation of the classic Paydirt football board game, originally published by Avalon Hill.

## Prerequisites

This project requires **Python 3.9 or higher**. Follow the instructions below for your operating system.

### macOS

macOS comes with Python pre-installed, but it may be an older version. To install the latest Python:

**Option 1: Using Homebrew (recommended)**
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Verify installation
python3 --version
```

**Option 2: Download from python.org**
1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download the macOS installer
3. Run the installer and follow the prompts

### Linux

Most Linux distributions include Python. To install or update:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip

# Verify installation
python3 --version
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip

# Verify installation
python3 --version
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip

# Verify installation
python3 --version
```

### Windows

**Option 1: Microsoft Store (easiest)**
1. Open the Microsoft Store
2. Search for "Python 3.12" (or latest version)
3. Click "Get" to install

**Option 2: Download from python.org**
1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download the Windows installer
3. **Important:** Check "Add Python to PATH" during installation
4. Run the installer and follow the prompts

**Verify installation:**
```cmd
python --version
```

### Verify Your Installation

After installing, verify Python is working:
```bash
# macOS/Linux
python3 --version

# Windows
python --version
```

You should see output like `Python 3.12.x` (or higher).

---

## Overview

Paydirt is a football simulation game where you select an NFL team and call plays against a computer opponent. The outcome of each play is determined by dice rolls and team-specific charts that reflect each team's real-world strengths and weaknesses.

## Quick Start

```bash
cd paydirt

# Interactive game (Human vs CPU)
python -m paydirt

# Interactive game with difficulty setting
python -m paydirt --play -d hard

# Compact display mode (recommended)
python -m paydirt --play --compact

# Specify week for standings
python -m paydirt --play --week 1 --compact

# Resume a saved game
python -m paydirt --play --load --compact

# Auto game (CPU vs CPU) - great for testing
python -m paydirt -auto Bears Cowboys
```

Select your team, choose home or away, select CPU difficulty, and start playing!

### Command Line Options

| Option | Description |
|--------|-------------|
| `--play` | Start interactive game mode |
| `-d easy\|medium\|hard` | Set CPU difficulty level |
| `--compact` | Use compact display (less verbose, recommended) |
| `--week N` | Specify week number for standings |
| `--load [file]` | Resume a saved game |
| `-auto team1 team2` | Run CPU vs CPU simulation |

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
- **[2] Two-point** - Conversion attempt (2 points, risky) - *Only available for 1994+ teams*

**Note:** The 2-point conversion was introduced to the NFL in 1994. When playing with teams from earlier seasons (e.g., 1983), only the extra point kick option is available.

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

## Available Teams

Teams are loaded from the `seasons/` directory. The 1983 season includes:

| Team | Location |
|------|----------|
| Cardinals | St. Louis |
| Bears | Chicago |
| Broncos | Denver |
| Browns | Cleveland |
| Buccaneers | Tampa Bay |
| Chargers | San Diego |
| Chiefs | Kansas City |
| Colts | Baltimore |
| Cowboys | Dallas |
| Dolphins | Miami |
| Eagles | Philadelphia |
| Falcons | Atlanta |
| 49ers | San Francisco |
| Giants | New York |
| Jets | New York |
| Lions | Detroit |
| Oilers | Houston |
| Packers | Green Bay |
| Patriots | New England |
| Raiders | Los Angeles |
| Rams | Los Angeles |
| Redskins | Washington |
| Saints | New Orleans |
| Seahawks | Seattle |
| Steelers | Pittsburgh |
| Vikings | Minnesota |

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
python -m paydirt.standings show 1983

# List all recorded games
python -m paydirt.standings games 1983
```

### Managing Results
```bash
# Add a game manually
python -m paydirt.standings add 1983 Redskins 28 Giants 21 --week 1

# Edit a game result
python -m paydirt.standings edit 1983 1 --home-score 31

# Delete a game
python -m paydirt.standings delete 1983 1
```

---

## Project Structure

```
paydirt/
├── paydirt/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point for python -m paydirt
│   ├── game_engine.py       # Main game engine
│   ├── play_resolver.py     # Play types and result resolution
│   ├── chart_loader.py      # Team chart CSV parsing
│   ├── penalty_handler.py   # Penalty resolution per official rules
│   ├── computer_ai.py       # Computer opponent AI
│   ├── interactive_game.py  # Interactive CLI game mode
│   ├── commentary.py        # Play-by-play commentary
│   ├── save_game.py         # Game save/load functionality
│   ├── standings.py         # Season standings tracking
│   └── utils.py             # Shared utility functions
├── seasons/
│   └── 1983/                # 1983 NFL season team data
│       ├── TeamName/
│       │   ├── offense.csv      # Offensive play charts
│       │   ├── defense.csv      # Defensive play charts
│       │   ├── special_teams.csv # Kicking/return charts
│       │   └── roster.json      # Player roster
│       └── ...
├── standings/               # Season standings data (JSON)
└── tests/                   # Unit tests (982 tests)
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

## License

This is a fan-made implementation for educational purposes. Paydirt is a trademark of its respective owners.
