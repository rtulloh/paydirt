# AGENTS.md - Paydirt Web Development Guide

This file provides guidelines for AI agents working on the Paydirt Web codebase.

## Project Overview

Paydirt Web is a web-based interface for the Paydirt football board game. It consists of:
- A FastAPI backend (Python) that interfaces with the core Paydirt game engine
- A React frontend (JavaScript/JSX) with Vite bundler
- Zustand for state management
- Tailwind CSS for styling

## Build/Lint/Test Commands

### Running Tests

#### Backend Tests
```bash
# From paydirt-web/backend directory
pytest

# Run a single test file
pytest tests/test_api.py

# Run a single test function
pytest tests/test_api.py::test_health_check

# Run tests with verbose output
pytest -v
```

#### Frontend Tests
```bash
# From paydirt-web/frontend directory
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Linting

#### Backend Linting
The backend uses ruff for linting:
```bash
# From paydirt-web/backend directory
ruff check .
```

#### Frontend Linting
The frontend uses ESLint for linting:
```bash
# From paydirt-web/frontend directory
npm run lint
```

### Development Commands

#### Start Both Services
```bash
# From paydirt-web directory
./start.sh
```

#### Start Backend Only
```bash
# From paydirt-web/backend directory
uvicorn main:app --reload --port 8000
```

#### Start Frontend Only
```bash
# From paydirt-web/frontend directory
npm run dev
```

## Code Style Guidelines

### Backend (Python)

#### Naming Conventions
- **Classes**: PascalCase (e.g., `PaydirtGameEngine`, `Team`, `GameState`)
- **Functions/Variables**: snake_case (e.g., `load_team_info`, `game_state_to_response`, `get_play_type_from_key`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `SEASONS_DIR`)
- **Pydantic Models**: PascalCase with "Response" or "Request" suffix (e.g., `NewGameRequest`, `GameStateResponse`)

#### Type Hints
- Always use type hints for function parameters and return types
- Use built-in types (`int`, `str`, `bool`, `list`, `dict`) or typing module (`Optional`, `List`, `Dict`)
- Use Pydantic models for request/response validation
- Example:
  ```python
  def load_team_info(season_dir: Path, team_id: str) -> Team:
  ```

#### Imports
- Group imports: standard library, third-party, local/application
- Use absolute imports from project root when needed
- Example:
  ```python
  from fastapi import APIRouter, HTTPException
  from pydantic import BaseModel
  from typing import Optional, List, Dict, Any
  from pathlib import Path
  import yaml
  import random
  import uuid
  from datetime import datetime
  
  import sys
  sys.path.insert(0, str(Path(__file__).parent.parent.parent))
  
  from paydirt.game_engine import PaydirtGameEngine
  ```

#### Docstrings
Use Google-style docstrings with `Args` and `Returns`:
```python
def load_team_info(season_dir: Path, team_id: str) -> Team:
    """
    Load team information from YAML file.
    
    Args:
        season_dir: Path to the season directory
        team_id: Team identifier
        
    Returns:
        Team object with team information
    """
```

#### Error Handling
- Use `HTTPException` for API errors with appropriate status codes
- Always include descriptive messages:
  ```python
  raise HTTPException(status_code=404, detail=f"Season '{season}' not found")
  ```
- Use specific exception types, not bare `except:`

### Frontend (React/JavaScript)

#### Naming Conventions
- **Components**: PascalCase (e.g., `PlayLog`, `KickoffPlay`, `Scoreboard`)
- **Functions/Variables**: camelCase (e.g., `playLog`, `kickoffPlay`, `scoreboard`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SAVE_FILE`)
- **CSS Classes**: kebab-case (e.g., `play-log`, `kickoff-play`)

#### Type Hints (if using TypeScript)
- Use TypeScript interfaces for props and state
- Example:
  ```typescript
  interface PlayLogProps {
    plays: Play[];
    onPlayClick: (playId: string) => void;
  }
  ```

#### Imports
- Group imports: React, third-party, local/components
- Use relative imports for local components
- Example:
  ```javascript
  import React from 'react';
  import { useStore } from 'zustand';
  import './PlayLog.css';
  
  import PlayLogEntry from './PlayLogEntry';
  ```

#### Component Structure
- Use functional components with hooks
- Keep components small and focused
- Separate concerns: presentational vs container components
- Example:
  ```javascript
  import React from 'react';
  import { useStore } from 'zustand';
  
  const PlayLog = () => {
    const plays = useStore(state => state.plays);
    
    return (
      <div className="play-log">
        {plays.map(play => (
          <PlayLogEntry key={play.id} play={play} />
        ))}
      </div>
    );
  };
  
  export default PlayLog;
  ```

#### Styling
- Use Tailwind CSS utility classes
- Follow existing styling patterns in the codebase
- Use CSS modules or styled-components for component-specific styles when needed

#### State Management
- Use Zustand for global state
- Keep state minimal and normalized
- Derive state when possible instead of storing redundant data
- Example:
  ```javascript
  import create from 'zustand';
  
  const useGameStore = create((set, get) => ({
    gameState: null,
    setGameState: (state) => set({ gameState: state }),
    // ... other state properties and actions
  }));
  ```

#### Testing
- Use Jest and React Testing Library for frontend tests
- Test component behavior, not implementation details
- Mock external dependencies (API calls, etc.)
- Example:
  ```javascript
  import { render, screen } from '@testing-library/react';
  import userEvent from '@testing-library/user-event';
  import PlayLog from './PlayLog';
  
  test('displays plays correctly', () => {
    const plays = [{ id: '1', description: 'Test play' }];
    render(<PlayLog plays={plays} />);
    expect(screen.getByText('Test play')).toBeInTheDocument();
  });
  ```

### Rules
- Never modify the base paydir game engine without first confirming with the user
- Always write unit tests for every change you make
- Check code coverage when tests or code are added. Aim for 80% or better coverage
- Always run the linter and unit tests before commit of changes

## Architecture: Core Engine is Source of Truth

The core game engine (`paydirt/game_engine.py`) is the authoritative source of truth for all game decisions. All game logic, rules, and state management live in the core engine.

**Important: Use core game tests as reference for UI behavior**

The core game unit tests (`paydirt/tests/`) document how game rules should work. When implementing or debugging UI features, consult these tests to understand:
- What data the engine returns for each play type
- How penalties, turnovers, scoring, and special situations are handled
- What fields are available in game state responses
- Expected behavior for edge cases

For example:
- `tests/test_play_resolver.py` shows how play outcomes are calculated
- `tests/test_game_engine.py` shows kickoff, scoring, and penalty handling
- `tests/test_computer_ai.py` shows CPU decision logic

The UI should respect and support everything the core engine provides.

**What the frontend should do:**
- Display game state as returned by the backend (which calls the core engine)
- Present player choices when the engine indicates a decision is needed
- Send player selections back to backend for the engine to resolve

**What the frontend should NOT do:**
- ❌ Parse dice descriptions to extract play results
- ❌ Calculate field position from raw ball_position integers
- ❌ Determine possession from who was on offense last play
- ❌ Generate play result descriptions
- ❌ Implement game rules or validate game state

**Example flow for a fumble:**
1. Frontend sends play call to backend
2. Backend calls core engine to execute play
3. Core engine determines fumble, who recovered, returns, etc.
4. Backend returns full description: `"FUMBLE! 5 yards before fumble - Defense recovers at the 35 (OPP ball) | Recovery: 38"`
5. Frontend displays this description as-is without parsing or recalculating

**The backend (routes.py) is a thin API layer:**
- It should call core engine methods and return their results
- It should not implement game rules or make game decisions
- It should not transform or parse game state - just pass through what the engine provides

## Project Structure

```
paydirt-web/
├── backend/           # FastAPI backend
│   ├── main.py        # App entry point
│   ├── routes.py      # API routes
│   ├── tests/         # Backend tests
│   └── requirements.txt
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── store/       # Zustand state
│   │   ├── styles/      # Tailwind CSS
│   │   └── App.jsx      # Main app
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── start.sh          # Launch script
├── README.md         # Project overview
└── AGENTS.md         # This file
```

## Key Dependencies

### Backend
- Python 3.12+ (required for FastAPI prebuilt wheels)
- FastAPI
- Pydantic
- Uvicorn
- PyYAML
- Paydirt game engine (imported from parent directory)

### Frontend
- Node.js 18+
- React 18+
- Vite
- Zustand
- Tailwind CSS
- React Testing Library
- Jest

## Running the Game

```bash
# Start both services
./start.sh

# Or run each service separately:
# Terminal 1 - Backend (Python 3.12)
cd paydirt-web/backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd paydirt-web/frontend
npm run dev
```

Access the application at: **http://localhost:5173**

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/seasons` | GET | List available seasons |
| `/api/teams?season=X` | GET | List teams for a season |
| `/api/game/new` | POST | Start a new game |
| `/api/game/state/{game_id}` | GET | Get current game state |
| `/api/game/coin-toss` | POST | Process coin toss |
| `/api/game/execute` | POST | Execute a play |
| `/api/game/kickoff` | POST | Perform kickoff |
| `/api/game/cpu-play` | POST | Get CPU play selection |
| `/api/game/cpu-4th-down-decision/{game_id}` | GET | Get CPU 4th down decision |
| `/api/game/pat-choice/{game_id}` | GET | Get PAT choice info |
| `/api/game/extra-point` | POST | Attempt extra point |
| `/api/game/two-point` | POST | Attempt two-point conversion |
| `/api/game/penalty-decision` | POST | Apply penalty decision |
| `/api/game/{game_id}` | DELETE | Delete game |

## Development Status

Refer to `IMPLEMENTATION_PLAN.md` for detailed development phases and status.

## Common Issues and Solutions

### Import Path Issues
The backend modifies sys.path to import from the parent paydirt directory:
```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'paydirt'))
```
This is marked as a potential bug in the code. A better long-term solution would be to properly package the paydirt game engine as a dependency.

### Python Version Requirements
The backend requires Python 3.12+ due to FastAPI dependency requirements. Ensure you have the correct Python version installed.

### CORS Configuration
The backend is configured to allow requests from `http://localhost:5173` and `http://127.0.0.1:5173` for frontend development. Adjust these in production as needed.
