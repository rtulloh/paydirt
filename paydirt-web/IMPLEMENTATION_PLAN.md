# Paydirt Web UI - Implementation Plan

## Overview

A web-based browser game that recreates the classic Paydirt board game experience with animated dice rolls, an authentic football field visualization, and interactive play selection for both human and CPU players.

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend Framework** | React 18+ | Component-based, excellent for game state management |
| **State Management** | Zustand | Lightweight, perfect for game state |
| **Animation** | Framer Motion | Smooth dice animations and transitions |
| **Styling** | Tailwind CSS + Custom CSS | Rapid UI development + authentic board game aesthetics |
| **Backend** | FastAPI (Python) | Reuse existing Paydirt game engine (`game_engine.py`, `play_resolver.py`) |
| **Real-time** | WebSocket (future) | For multiplayer support |

### Requirements
- **Frontend**: Node.js 18+
- **Backend**: Python 3.12+ (FastAPI requires prebuilt wheels)
- **Testing**: Vitest (frontend), pytest (backend), Playwright (E2E)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (React)                          │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │ Scoreboard  │ │   Field     │ │   Play Selection    │  │
│  │  (Fixed)    │ │  (Center)   │ │   (Bottom Panel)  │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Dice Display (Overlay/Modal)                ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│                    Zustand Game Store                        │
└─────────────────────────────┬───────────────────────────────┘
                              │ REST API (Thin Wrapper)
┌─────────────────────────────┴───────────────────────────────┐
│                    FastAPI Backend                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  THIN API LAYER - No custom game logic                 ││
│  │  - Forwards requests to game engine                    ││
│  │  - Serializes/deserializes responses                   ││
│  │  - Game state management (in-memory)                    ││
│  └──────────────────────────┬──────────────────────────────┘│
│                             │                               │
│  ┌──────────────────────────┴──────────────────────────────┐│
│  │  Paydirt Game Engine (SINGLE SOURCE OF TRUTH)          ││
│  │                                                          ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  ││
│  │  │game_engine │  │ computer_ai│  │ play_resolver  │  ││
│  │  │    .py     │  │    .py     │  │      .py       │  ││
│  │  └────────────┘  └────────────┘  └────────────────┘  ││
│  │                                                          ││
│  │  ALL game logic lives here - play resolution, penalties,││
│  │  PAT decisions, clock management, overtime, etc.        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Game Engine is Single Source of Truth**: All game logic MUST be in `game_engine.py`, `computer_ai.py`, or `play_resolver.py`. The CLI and web UI must behave identically.

2. **Thin API Layer**: `routes.py` MUST NOT contain custom game logic. It only:
   - Creates/manages game instances
   - Forwards user inputs to engine methods
   - Returns engine responses to frontend
   - Serializes/deserializes data

3. **Engine Methods as Interface**: The engine exposes methods for:
   - `run_play()` - Execute a play
   - `apply_decision()` - Apply user decisions (penalties, PAT choices, etc.)
   - `get_pending_decision()` - Check if user input is needed
   - `get_available_options()` - Get available choices

4. **AI Integration**: `computer_ai.py` is called by the engine. No custom AI logic should exist in `routes.py`.
┌─────────────────────────────────────────────────────────────┐
│                     Browser (React)                          │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │ Scoreboard  │ │   Field     │ │   Play Selection    │  │
│  │  (Fixed)    │ │  (Center)   │ │   (Bottom Panel)    │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Dice Display (Overlay/Modal)                ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│                    Zustand Game Store                        │
└─────────────────────────────┬───────────────────────────────┘
                              │ REST API
┌─────────────────────────────┴───────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Paydirt Game Engine (existing Python code)           │ │
│  │  - game_engine.py                                      │ │
│  │  - play_resolver.py                                    │ │
│  │  - computer_ai.py                                      │ │
│  │  - chart_loader.py                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Visual Design - Retro Board Game Aesthetic

### Color Palette
```css
:root {
  /* Field Colors */
  --field-green: #2d5a27;
  --field-stripe: #3d7a37;
  --yard-line: #ffffff;
  --endzone-red: #8B0000;
  --endzone-blue: #1E3A8A;

  /* Board/UI Colors */
  --board-bg: #D2691E;        /* Chocolate brown */
  --panel-bg: #F5DEB3;        /* Wheat */
  --panel-border: #8B4513;    /* Saddle brown */

  /* Scoreboard - LED Style */
  --led-bg: #1a1a2e;
  --led-red: #ff6b6b;
  --led-blue: #4ecdc4;
  --led-off: #333;

  /* Dice */
  --dice-black: #1a1a1a;
  --dice-white: #f0f0f0;
  --dice-red: #cc0000;
  --dice-green: #006600;
}
```

### Typography
```css
/* Scoreboard - LED/Scoreboard font */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap');
--font-scoreboard: 'Orbitron', monospace;

/* Panel headers */
--font-heading: 'Roboto Condensed', sans-serif;

/* Body text */
--font-body: 'Roboto', sans-serif;
```

---

## UI Components

### 1. Football Field Component

```
┌─────────────────────────────────────────────────────────────────┐
│ [HOME ENDZONE]                                                   │
│  ════════════════════════════════════════════════════════════    │
│                                                                  │
│   10    20    30    40    50    40    30    20    10             │
│ ────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼────────── │
│         │     │     │     │     │     │     │     │            │
│         │     │     │     │   ●─┼─────┼─────┤     │            │
│         │     │     │     │  BALL      │     │     │            │
│ ────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼────────── │
│                                                                  │
│  ════════════════════════════════════════════════════════════    │
│ [AWAY ENDZONE]                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Horizontal scrolling when ball is in end zones
- Animated ball marker that moves on play results
- Team-colored end zones (from `team.yaml`)
- Yard line numbers (10, 20, 30, 40, 50, then reverse)
- Hash marks between yard lines
- Grid pattern overlay (classic board game look)
- Arrow indicators showing possession direction

### 2. NFL-Style Scoreboard

```
┌────────────────────────────────────────────────────────────────────┐
│                     ⚽ PAYDIRT CLASSIC ⚽                           │
├────────────────┬───────────────────────┬──────────────────────────┤
│   HOME TEAM    │       SCORE           │       AWAY TEAM           │
│   EAGLES  ●    │      21 : 17         │       COWBOYS            │
│   PHI          │                       │       DAL                │
├────────────────┴───────────────────────┴──────────────────────────┤
│  Q4 │ 2:45 │  3rd & 8 at PHI 35  │  ○○●  │  ○○○                    │
│     │      │                      │ 2 LFT │ 3 LFT                    │
└───────────────────────────────────────────────────────────────────┘
```

**Elements:**
- LED-style score display (large, red glow)
- Team names with abbreviations
- Possession indicator (●) on team with ball
- Quarter display (I, II, III, IV)
- MM:SS game clock with pulse animation
- Down and distance (e.g., "3rd & 8")
- Field position (e.g., "at PHI 35")
- Timeout dots (filled = remaining, hollow = used)
- Team colors via helmet research (Phase 2+)

### 3. Play Selection Panels

**Offensive Plays:**
```
┌─────────────────────────────────────────┐
│     ⚈  SELECT YOUR PLAY  ⚈             │
├───────────┬───────────┬─────────────────┤
│   RUNS    │  PASSES   │    SPECIAL     │
├───────────┼───────────┼─────────────────┤
│ [1] Lt    │ [4] Shrt  │ [7] Punt      │
│ [2] Rt    │ [5] Med   │ [8] Fld Goal  │
│ [3] Mid   │ [6] Long  │ [9] Spike     │
│           │           │ [Q] QB Sneak   │
│           │           │ [K] Kneel      │
└───────────┴───────────┴─────────────────┘
```

**Defensive Formations:**
```
┌─────────────────────────────────────────┐
│    ⚔  SELECT DEFENSE  ⚔                │
├─────────┬─────────┬─────────┬──────────┤
│  [A]    │  [B]    │  [C]    │  [D]     │
│ NORMAL  │  BLITZ  │ PREVENT │ GOAL LINE│
│ Balanced│ All-Out │ Deep    │ Short Yd │
│         │  Rush   │  Pass   │ Stuff    │
└─────────┴─────────┴─────────┴──────────┘
```

### 4. Dice Display (Animated)

```
┌──────────────────────────────────────────────────────────────────┐
│  OFFENSIVE DICE                           DEFENSIVE DICE          │
│  ┌───────┐  ┌───────┐  ┌───────┐         ┌───────┐  ┌───────┐   │
│  │ ● ● ● │  │ ○   ○ │  │ ○ ○ ○ │         │ ● ● ● │  │ ○   ○ │   │
│  │ ●   ● │  │   ○   │  │ ○   ○ │         │ ●   ● │  │ ○   ○ │   │
│  │ ● ● ● │  │ ○   ○ │  │ ○ ○ ○ │         │ ● ● ● │  │ ○ ○ ○ │   │
│  └───────┘  └───────┘  └───────┘         └───────┘  └───────┘   │
│    BLACK     WHITE     WHITE               RED        GREEN       │
│      2         4         3                  1          1          │
│                     TOTAL: 27                   TOTAL: 2         │
└──────────────────────────────────────────────────────────────────┘
```

**Animation Sequence (2 seconds):**
1. **0.0s**: Panel slides up, dice appear
2. **0.2s**: All dice start shaking
3. **0.5s**: Black die settles
4. **0.7s**: First white die settles
5. **0.9s**: Second white die settles
6. **1.0s**: Offense total displayed
7. **1.2s**: Red die settles
8. **1.4s**: Green die settles
9. **1.6s**: Defense total displayed
10. **1.8s**: Result text appears

### 5. Team Selection Screen

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELECT YOUR TEAM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SEASON:  [1972]  [1983]  [2026]                               │
│                                                                  │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│   │   🪖    │ │   🪖    │ │   🪖    │ │   🪖    │ │   🪖    │  │
│   │  Eagles │ │ Cowboys │ │  Bears  │ │  Lions  │ │ Packers │  │
│   │   PHI   │ │   DAL   │ │   CHI   │ │   DET   │ │   GB    │  │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│                        ... more teams ...                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Season picker (reads from `seasons/` folder dynamically)
- Team grid with helmet placeholders
- Team colors from `team.yaml`
- CPU opponent auto-selected (or random)

---

## Game Flow

### New Game Flow
```
1. [Home Screen] - "NEW GAME" button
       ↓
2. [Team Selection]
   ├─> Select Season (from available folders)
   ├─> Select Your Team (grid of team cards)
   └─> CPU opponent auto-selected
       ↓
3. [Coin Toss] - Random assignment of home/away
       ↓
4. [Opening Kickoff] - Auto-execute, show result
       ↓
5. [Main Game Loop]
```

### Main Game Loop

```
┌─────────────────────────────────────────────────────────────┐
│                     MAIN GAME LOOP                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [A] Check Game State                                        │
│      ├─> Game Over? → Show final score                      │
│      ├─> Quarter over? → Halftime / Next Quarter           │
│      └─> Continue                                            │
│                                                              │
│  [B] Determine Active Player                                 │
│      ├─> Human on Offense? → Show offense plays              │
│      └─> Human on Defense? → Show defense plays            │
│                                                              │
│  [C] Play Selection                                         │
│      ├─> Human selects play (1-9, Q, K, P, F)              │
│      └─> CPU secretly selects (hidden until result)         │
│                                                              │
│  [D] AUTO-ROLL (when both plays selected)                   │
│      └─> Dice animate, reveal result                        │
│                                                              │
│  [E] Handle Result                                          │
│      ├─> Update ball position                               │
│      ├─> Update scoreboard                                  │
│      ├─> Check for touchdowns/turnovers                      │
│      └─> Log to play-by-play                                │
│                                                              │
│  [F] Loop to [A]                                             │
└─────────────────────────────────────────────────────────────┘
```

### CPU Play Revelation
- CPU's play is hidden until dice results are shown
- After results, both plays are revealed

---

## API Specification

### Design Principles

1. **Engine-Driven**: Every endpoint forwards to a game engine method
2. **Single Response Format**: All play results include `pending_decision` field
3. **No Custom Logic**: Backend is a thin wrapper, all game rules in engine

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/seasons` | GET | List available seasons |
| `/api/teams?season=X` | GET | List teams for a season |
| `/api/game/new` | POST | Start a new game |
| `/api/game/state/{id}` | GET | Get current game state |
| `/api/game/execute` | POST | Execute a play (offense + defense) |
| `/api/game/decision` | POST | Apply a user decision (PAT, penalty, etc.) |

### Response Format - Play Result

All play execution returns a standardized response:

```python
class PlayResult:
    result: str              # "breakaway", "incomplete", "touchdown", etc.
    yards: int               # Yards gained/lost
    description: str         # Human-readable description
    turnover: bool           # INT or FUMBLE occurred
    scoring: bool            # TD, FG, or Safety
    touchdown: bool          # Touchdown scored
    
    # Decision handling
    pending_decision: Optional[PendingDecision]  # If user needs to choose
    decision_type: Optional[str]  # "penalty", "pat", "kickoff", etc.
    
    # State updates
    new_ball_position: int
    new_down: int
    new_yards_to_go: int
    new_score_home: int
    new_score_away: int
    possession_changed: bool
    game_over: bool
    quarter_changed: bool
    half_changed: bool

class PendingDecision:
    type: str           # "penalty", "pat_kick", "pat_two_point", "onside_kick"
    description: str     # Human-readable prompt
    options: List[DecisionOption]  # Available choices
    offended_team: str   # "offense" or "defense"
```

### Request/Response Examples

```python
# POST /api/game/new
{
  "player_team": "Ironclads",
  "season": "2026"
}

# Response
{
  "game_id": "game_1234",
  "game_state": {
    "home_team": { "id": "Ironclads", "name": "Harbor Bay Ironclads" },
    "away_team": { "id": "Thunderhawks", "name": "..." },
    "home_score": 0,
    "away_score": 0,
    "quarter": 1,
    "time_remaining": 900,
    "possession": "home",
    "ball_position": 35,
    "down": 1,
    "yards_to_go": 10,
    "game_over": false
  }
}

# POST /api/game/execute
{
  "game_id": "game_1234",
  "player_play": "1",      # Line Plunge
  "cpu_play": "A"          # Standard defense
}

# Response (no decision needed)
{
  "result": "breakaway",
  "yards": 15,
  "description": "Line Plunge for 15 yards!",
  "pending_decision": null,
  ...
}

# Response (penalty - user must decide)
{
  "result": "penalty",
  "yards": 5,
  "description": "DEFENSIVE HOLDING - 5 yards",
  "pending_decision": {
    "type": "penalty",
    "description": "Accept penalty or take play result?",
    "options": [
      {"key": "accept", "label": "Accept Penalty"},
      {"key": "decline", "label": "Take Play Result (+5 yards, down counts)"}
    ],
    "offended_team": "offense"
  },
  ...
}

# POST /api/game/decision
{
  "game_id": "game_1234",
  "decision_type": "penalty",
  "choice": "accept"
}

# Response (touchdown - PAT decision)
{
  "result": "touchdown",
  "yards": 0,
  "description": "TOUCHDOWN!",
  "pending_decision": {
    "type": "pat",
    "description": "Extra Point - Kick or Go for 2?",
    "options": [
      {"key": "kick", "label": "Kick XP (1 pt)"},
      {"key": "two_point", "label": "Go for 2"}
    ],
    "offended_team": "offense",
    "can_go_for_two": true  # Season supports 2-point conversion
  },
  ...
}
```

---

## Architecture Refactoring (Current Phase)

### Goal: Ensure CLI and Web UI are 100% Consistent

The web UI should route ALL decisions through the existing game engine. When CLI behavior changes, web UI automatically inherits those changes.

### Current Issues to Fix

| Issue | Current Location | Should Be |
|-------|-----------------|-----------|
| PAT decisions (kick vs 2-point) | Custom logic in `routes.py` | Engine method |
| Penalty decisions | Custom logic in `routes.py` | Engine method |
| CPU AI for PAT choices | Duplicate in `routes.py` | `computer_ai.py` |
| CPU 4th down decisions | Uses engine, but decision logic separate | Engine method |

### Engine Methods Needed

The game engine should expose methods that handle ALL game situations:

```python
class PaydirtGameEngine:
    def run_play(self, offense_play, defense_play) -> PlayOutcome:
        """Execute a play. Returns outcome with pending_decision if user input needed."""
        
    def apply_decision(self, decision_type: str, choice: any) -> PlayOutcome:
        """Apply a user decision (penalty_accept, pat_choice, etc.)"""
        
    def get_pending_decision(self) -> Optional[PendingDecision]:
        """Returns any pending decision the user needs to make."""
        
    def get_touchdown_pat_info(self) -> dict:
        """Returns PAT info: can_go_for_two, cpu_should_go_for_two, etc."""
```

### Implementation Tasks

- [x] Audit game engine methods for game logic coverage
- [x] Add `get_touchdown_pat_info()` to engine
- [x] Refactor PAT logic from `routes.py` → engine
- [x] Refactor penalty decision logic from `routes.py` → engine
- [x] Simplify `routes.py` to thin API wrapper
- [x] Verify CLI and web UI use same engine methods
- [ ] Update frontend to use new engine-driven flow (in progress)

### Files to Modify

| File | Changes |
|------|---------|
| `paydirt/game_engine.py` | Add missing game logic methods |
| `paydirt/computer_ai.py` | Ensure all AI logic is here |
| `paydirt-web/backend/routes.py` | Remove custom game logic, use engine methods |
| `paydirt-web/frontend/src/App.jsx` | Update to use new API flow |

---

## Implementation Phases

### Phase 1: Project Setup ✅ (COMPLETE)
- [x] Create `paydirt-web/` directory structure
- [x] Set up React + Vite project
- [x] Install dependencies (zustand, framer-motion, tailwindcss)
- [x] Set up FastAPI backend with routing
- [x] Add CORS and health check endpoint
- [x] Create Zustand store
- [x] **Frontend tests: 8/8 passing**

**Tests:**
- Backend API endpoints respond correctly
- App renders without errors
- Zustand store initializes correctly

---

### Phase 2: Static UI Components
**Duration: Days 2-3**

**Tasks:**
- [x] Football Field component (static rendering)
- [x] Scoreboard component (LED style display)
- [x] Play selection panels (offense & defense)
- [x] Retro color scheme and styling
- [x] Basic layout with all panels visible

**Tests:**
- [x] Yard lines render at correct positions
- [x] Ball marker renders at correct yard line
- [x] Score displays correctly
- [x] Clock formats as MM:SS
- [x] Down/distance displays correctly
- [x] Timeout dots render for each team
- [x] All play buttons render
- [x] Keyboard shortcuts work (1-9, Q, K, etc.)

---

### Phase 3: Backend Integration
**Duration: Days 4-5**

**Tasks:**
- [x] API endpoints for game management
- [x] Integrate `game_engine.py` via Python imports
- [x] Connect to `chart_loader.py` for team charts
- [x] Implement `/api/teams` and `/api/seasons`
- [x] Game state synchronization
- [x] Play execution endpoint
- [x] CPU AI integration

**Tests:**
- [x] `/api/seasons` returns available seasons
- [x] `/api/teams?season=X` returns teams
- [x] `/api/game/new` creates valid game state
- [x] `/api/game/state` returns current state
- [x] `/api/game/execute` executes plays
- [x] Invalid team/season returns 404
- [x] Team list populates from API
- [x] Game state displays after new game

---

### Phase 4: Game Flow
**Duration: Days 6-7**

**Tasks:**
- [x] Team selection screen (dynamic from seasons folder)
- [x] Coin toss animation
- [x] Main game loop (offense → defense → roll → result)
- [x] CPU AI integration
- [x] Turnover handling (INT/FUM)
- [x] Score updates
- [x] Game over screen
- [x] Halftime screen
- [x] CPU play hidden until result

**Tests:**
- [x] Play execution returns valid result
- [x] CPU AI returns valid play type
- [x] Turnover switches possession
- [x] Touchdown updates score correctly
- [x] Game ends at correct conditions
- [x] Play selection sends correct API call
- [x] CPU play hidden until result
- [x] Score updates after touchdown
- [x] Coin toss animation works
- [x] Game over screen displays
- [x] Halftime screen displays

---

### Phase 5: Dice Animation
**Duration: Days 8-9**

**Tasks:**
- [x] Dice display component
- [x] Shake/tumble animation sequence
- [x] Staggered settle effect (200ms between dice)
- [x] Result reveal animation
- [ ] Sound effects integration (with mute toggle)

**Tests:**
- [x] Dice renders with correct colors
- [x] Dice shows correct pip pattern
- [x] Animation completes without error
- [x] Final values match API response

---

### Phase 6: Polish
**Duration: Days 10-11**

**Tasks:**
- [x] Play-by-play log
- [x] Timeout functionality
- [x] Special teams (punt, FG, kickoff)
- [x] Halftime / game over screens
- [ ] Ball movement animation on field
- [ ] Scoreboard flash effects on score change
- [ ] Sound effects for TDs, turnovers, etc.

**Tests:**
- [x] Timeout decrements counter
- [x] Punt executes correctly
- [x] Field goal distance calculation
- [x] Kickoff with touchback
- [x] Halftime transitions correctly
- [x] Game over shows final score
- [x] Play-by-play entries added
- [ ] Ball animates to correct position
- [ ] Ball stops at boundary (0 or 100)
- [ ] Score flash animation triggers

---

### Phase 7: Engine Integration (Consistency)
**Priority: HIGH - Ensures CLI and Web UI behave identically**

**Tasks:**
- [x] Audit game engine for missing methods
- [x] Add `should_go_for_two()` to `ComputerAI`
- [x] Add `get_touchdown_pat_info()` to game engine
- [x] Refactor PAT logic from routes.py → engine
- [x] Refactor penalty decisions from routes.py → engine  
- [x] Simplify routes.py to thin API wrapper
- [x] Verify CLI and Web UI use same engine methods
- [x] **FIXED**: Use `run_play_with_penalty_procedure` instead of `run_play` for proper penalty handling
- [ ] Verify CLI and Web UI behave identically (in progress)

**Tests:**
- [ ] All CLI behaviors work in Web UI
- [ ] PAT decision flow matches CLI
- [x] Penalty decision flow matches CLI (using correct engine method)
- [ ] CPU AI decisions match CLI

---

### Phase 8: E2E Testing & Deployment
**Duration: Day 12**

**Tasks:**
- [ ] Playwright E2E tests
- [ ] Full game flow test
- [ ] Cross-browser testing
- [ ] Documentation

**E2E Tests:**
- [ ] Full game from start to finish
- [ ] CPU turnover leads to score
- [ ] Game goes to overtime on tie
- [ ] All previous tests pass

---

## File Structure

```
paydirt-web/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── routes.py               # Game API routes
│   ├── models.py               # Pydantic models
│   ├── tests/
│   │   └── test_api.py         # Backend tests
│   ├── requirements.txt
│   └── setup.sh                # Setup script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Field/
│   │   │   │   ├── FootballField.jsx
│   │   │   │   ├── BallMarker.jsx
│   │   │   │   └── YardLines.jsx
│   │   │   ├── Scoreboard/
│   │   │   │   ├── Scoreboard.jsx
│   │   │   │   ├── ScoreDisplay.jsx
│   │   │   │   ├── ClockDisplay.jsx
│   │   │   │   └── DownDistance.jsx
│   │   │   ├── Plays/
│   │   │   │   ├── OffensePlays.jsx
│   │   │   │   └── DefensePlays.jsx
│   │   │   ├── Dice/
│   │   │   │   ├── DiceContainer.jsx
│   │   │   │   ├── Die.jsx
│   │   │   │   └── DiceDisplay.jsx
│   │   │   ├── Game/
│   │   │   │   ├── TeamSelect.jsx
│   │   │   │   ├── CoinToss.jsx
│   │   │   │   └── GameOver.jsx
│   │   │   └── Common/
│   │   │       ├── Button.jsx
│   │   │       └── Modal.jsx
│   │   ├── store/
│   │   │   └── gameStore.js    # Zustand store
│   │   ├── api/
│   │   │   └── client.js       # API client
│   │   ├── hooks/
│   │   │   └── useAudio.js     # Sound effects
│   │   ├── styles/
│   │   │   └── index.css       # Tailwind + custom
│   │   ├── App.jsx
│   │   ├── App.test.jsx        # 8 tests
│   │   ├── main.jsx
│   │   └── test/
│   │       └── setup.js
│   ├── public/
│   │   └── audio/
│   │       ├── dice_roll.mp3
│   │       ├── whistle.mp3
│   │       └── crowd.mp3
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── e2e/
│   └── game.spec.js            # Playwright tests
├── start.sh                    # Launch script
└── README.md
```

---

## Running the Application

### Prerequisites
- Node.js 18+
- Python 3.12+

### Setup

```bash
# Install frontend dependencies
cd paydirt-web/frontend
npm install

# Install Python 3.12 (if needed)
brew install python@3.12

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

### Start

```bash
# Start both services
cd paydirt-web
./start.sh

# Or separately:
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Access
**http://localhost:5173**

---

## Testing

```bash
# Frontend unit tests
cd frontend
npm test

# Backend tests (requires Python 3.12+)
cd backend
pytest

# E2E tests (Phase 7)
npx playwright test
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Dice Roll Trigger** | Auto-roll | When both plays selected, dice roll automatically |
| **CPU Play Visibility** | Hidden until results | Like real football - you don't see opponent's call |
| **Sound Effects** | Included with mute | Enhanced experience, user can disable |
| **Team Selection** | Dynamic from folder | Works for any seasons added to `seasons/` |
| **Visual Style** | Retro board game | Matches the Paydirt aesthetic |
| **Mobile Support** | Not in scope | Focus on desktop first |
| **Game Logic Location** | Engine is source of truth | CLI and Web UI must be 100% consistent |
| **Backend Role** | Thin API wrapper | No custom game logic in routes.py |
| **AI Location** | computer_ai.py | All AI decisions centralized |

---

## Game Engine Responsibilities

The `PaydirtGameEngine` class is the single source of truth for ALL game rules:

### Required Engine Methods

| Method | Purpose | Currently Exists? |
|--------|---------|-------------------|
| `run_play(offense, defense)` | Execute a play | Yes |
| `apply_penalty_decision(outcome, accept)` | Handle penalty choice | Yes |
| `attempt_extra_point()` | Kick PAT | Yes |
| `attempt_two_point(play, defense)` | 2-point conversion | Yes |
| `kickoff(kicking_home)` | Execute kickoff | Yes |
| `onside_kick(kicking_home)` | Execute onside kick | Yes |
| `select_offense(game)` | AI choose offense play | Yes (ComputerAI) |
| `select_defense(game)` | AI choose defense | Yes (ComputerAI) |
| `should_go_for_two(game)` | AI PAT decision | Yes (ComputerAI) |

### Decision Flow

```
Frontend → /execute → run_play() → PlayOutcome
                                      ↓
                              pending_decision?
                                      ↓
                              Yes → Frontend shows choice
                                      ↓
                              User selects → /decision → apply_XXX()
                                      ↓
                              No → Continue game
```

---

## Consistency Checklist

When adding features to CLI, verify Web UI:

- [ ] All new engine methods exposed via API
- [ ] All new decision types handled in frontend
- [ ] AI logic in `computer_ai.py`, not routes.py
- [ ] Same test scenarios pass in CLI and Web UI
- [ ] No hardcoded game rules in routes.py

---

## Future Enhancements

1. **Team Helmets**: Research NFL helmet images for visual enhancement
2. **Multiplayer**: WebSocket integration for real-time multiplayer
3. **Spectator Mode**: Watch other games in progress
4. **Season Mode**: Track records across multiple games
5. **Leaderboards**: Compare scores between sessions

---

## Notes

- The backend requires Python 3.12+ due to FastAPI dependencies
- Frontend tests are already working (8/8 passing)
- Backend tests are written but require Python 3.12+ to run
- The app reads teams dynamically from the `seasons/` folder
- For the beta, only the 2026 sample teams are available
