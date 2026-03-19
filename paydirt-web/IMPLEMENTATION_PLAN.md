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

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/seasons` | GET | List available seasons |
| `/api/teams?season=X` | GET | List teams for a season |
| `/api/game/new` | POST | Start a new game |
| `/api/game/state/{id}` | GET | Get current game state |
| `/api/game/play` | POST | Execute a play |

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
```

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
- [ ] Ball movement animation on field
- [ ] Scoreboard flash effects on score change
- [ ] Play-by-play log
- [ ] Timeout functionality
- [ ] Special teams (punt, FG, kickoff)
- [ ] Halftime / game over screens
- [ ] Sound effects for TDs, turnovers, etc.

**Tests:**
- [ ] Ball animates to correct position
- [ ] Ball stops at boundary (0 or 100)
- [ ] Score flash animation triggers
- [ ] Timeout decrements counter
- [ ] Punt executes correctly
- [ ] Field goal distance calculation
- [ ] Kickoff with touchback
- [ ] Halftime transitions correctly
- [ ] Game over shows final score
- [ ] Play-by-play entries added

---

### Phase 7: E2E Testing & Deployment
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
