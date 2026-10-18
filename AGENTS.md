# AGENTS.md - Paydirt Development Guide

This file provides guidelines for AI agents working on the Paydirt codebase.

## Project Overview

Paydirt is a Python simulation of the classic Paydirt football board game. It uses only the Python standard library - no external dependencies required (except pytest for testing).

## Build/Lint/Test Commands

### Running Tests

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_game.py

# Run a single test function
pytest tests/test_game.py::TestPaydirtGame::test_kickoff

# Run tests matching a pattern
pytest -k "test_kickoff"

# Run with coverage
pytest --cov=paydirt --cov-report=term-missing

# Run with verbose output (configured in pyproject.toml)
pytest -v --tb=short
```

### Required Full Regression Before Any Push

Before **every push**, including tag/release pushes, run all of the following
from the repository root. Do not push if any command fails; investigate and fix
failures first. Disclose existing skips and warnings rather than hiding them.

```bash
python3 -m pytest tests/ -q -o addopts= --tb=short -rs --cov=paydirt --cov-report=term
(cd paydirt-web/backend && python3 -m pytest tests/ -q -o addopts= --tb=short)
(cd paydirt-web/frontend && npm test -- --run)
(cd paydirt-web/frontend && npm run build)
(cd paydirt-web/frontend && npm run test:e2e)
ruff check paydirt/ tests/ paydirt-web/backend/
python3 tests/run_all_games.py
python3 tests/run_full_season.py
```

`npm run test:e2e` is a required part of full regression, not an optional smoke
check. It must complete both real-engine browser games (human home/receiving,
then away/kicking), including halftime, final-score screens, and clean new-game
state. Install Chromium once with `npx playwright install chromium` from
`paydirt-web/frontend` (on Linux, use `--with-deps`). The backend dependencies
must also be installed. Stop development servers on ports 8000 and 5173 first;
Playwright starts and stops its own isolated services using public 2026 teams
only. Missing browsers/services or reaching the action limit are failures, not
reasons to skip this check. See `paydirt-web/frontend/e2e/README.md` for details.

`tests/run_full_season.py` runs a deterministic, generated 16-week/224-game
1983 schedule followed by a ten-team/nine-game postseason through real engine
rules, dice, and CLI flow. It is **not** the historical NFL schedule or results.
Playoff seeds use the generated regular-season standings: three division winners
and two wildcards per conference, ranked by winning percentage, point differential,
points scored, then team name (deterministic regression tiebreakers, not the full
NFL tiebreaking procedure). Divisional matchups avoid same-division opponents.
It checks final game/untimed-down flags, period and scoring-log totals, rejects
kickoffs after game end, and fails any tied playoff final. Regular-season ties
remain valid under the season rules. Both phases print pass/fail, overtime, and
tie totals; playoffs also print round results and the champion. Failed playoff
games do not advance either team; dependent games are reported as not played.
It never saves standings. Failures include the matchup and seed for reproduction,
and the script exits nonzero. Playoffs do not run after regular-season failures.
The runner requires pytest and private, local-only 1983 team data; these files
are intentionally ignored and must never be committed or exported. It also runs
seven historical full-game reproductions outside the unit suite.

**When writing unit tests, use only synthetic fixtures or the public sample
teams under `seasons/2026/`. Never load or depend on any other season data,
even if it is available locally.** Do not introduce fixtures, parametrized cases,
or skip guards that rely on private/historical seasons (including 1972 or 1983).
Do not skip unit regressions to hide missing private data. Keep private-chart
integration checks in standalone local scripts outside unit-test collection.
Before pushing, also verify unit tests in a clean, tracked-files-only checkout
so ignored local data cannot mask CI failures.
All 224 regular-season games and all nine playoff games must pass before pushing;
a partial run is not sufficient, and no playoff game may finish tied.

### Test Configuration (from pyproject.toml)

- Test path: `tests/`
- Test file pattern: `test_*.py`
- Test function pattern: `test_*`

### Linting

The project uses ruff for linting (evidenced by `.ruff_cache`). Run via:

```bash
ruff check paydirt/ tests/
```

## Code Style Guidelines

### Naming Conventions

- **Classes**: PascalCase (e.g., `PaydirtGame`, `Team`, `GameState`)
- **Functions/Variables**: snake_case (e.g., `run_play`, `ball_position`, `get_field_position_description`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `DEFAULT_SAVE_FILE`)
- **Enums**: PascalCase with descriptive values (e.g., `PlayType.RUN_LEFT`)

### Type Hints

- Always use type hints for function parameters and return types
- Use built-in types (`int`, `str`, `bool`, `list`, `dict`) or typing module (`Optional`, `List`, `Dict`)
- Example:
  ```python
  def kickoff(self, receiving_team_is_home: bool = False) -> dict:
  ```

### Imports

- Use relative imports within the package (e.g., `from .models import Team`)
- Group related imports with parentheses:
  ```python
  from .models import (
      GameState, Team, PlayType, DefenseType, PlayOutcome, PlayResult
  )
  ```

### Docstrings

Use Google-style docstrings with `Args` and `Returns`:

```python
def kickoff(self, receiving_team_is_home: bool = False) -> dict:
    """
    Perform a kickoff to start the game or half.
    
    Args:
        receiving_team_is_home: True if home team receives
        
    Returns:
        Dict with kickoff result details
    """
```

### Data Classes & Models

Use `@dataclass` for simple data models (from `paydirt/models.py`):

```python
@dataclass
class PlayOutcome:
    result: PlayResult
    yards: int = 0
    description: str = ""
    turnover: bool = False
```

### Error Handling

- Use `ValueError` for invalid argument values
- Use generic `Exception` with re-raising for file I/O errors
- Always include descriptive messages:
  ```python
  raise ValueError(f"Unsupported save file version: {version}")
  ```
- Use specific exception types, not bare `except:`

### Code Organization

- Keep related functionality together in modules
- Main modules: `game.py`, `models.py`, `teams.py`, `team_charts.py`, `play_resolver.py`
- CLI in `cli.py`, game engine in `game_engine.py`
- Tests mirror source structure in `tests/` directory

### Required Test-First Workflow

For bug fixes and new behavior, write the test cases **before changing production
code**. This is the default requirement; the user should not need to repeat it
in prompts.

1. Add self-contained regressions that express the intended behavior, using
   synthetic fixtures or the public sample teams only. Include relevant edge
   cases and passing controls.
2. Run the new tests against the unchanged implementation. Demonstrate that
   they fail for the expected behavior, not because of broken fixtures, missing
   data, or unrelated setup errors. Report the baseline failures and controls.
3. Make the production fix, then rerun the focused tests and relevant regression
   suites. Follow the full validation checklist above before any push.
4. Disclose every change to an existing test expectation and explain why the
   previous expectation was wrong. Never weaken assertions or add skips simply
   to make a failing implementation pass.

If a meaningful failing test cannot be written or run, explain the limitation
and obtain explicit approval before proceeding with the production change.
Documentation-only and release-metadata changes do not require inventing a
failing behavior test; run applicable existing checks instead.

### Test Style

- Use pytest fixtures for setup:
  ```python
  @pytest.fixture
  def home_team(self):
      return Team(name="Home Team", abbreviation="HOM", ...)
  ```
- Test class naming: `Test<ClassName>`
- Use `unittest.mock.patch` for mocking dice rolls
- Test file naming: `test_<module>.py`

## Architecture Principles

### Core Game Engine is Source of Truth

The core game engine (`paydirt/game_engine.py`) is the authoritative source of truth for all game decisions. This means:

1. **All game logic lives in the core engine** - Rules, play resolution, state management, and game flow are handled exclusively by the core engine
2. **UI layers just display** - Frontends (CLI, web) should query the core engine for game state and display results, not make game decisions
3. **Descriptions come from the core** - Play result descriptions (including who recovered fumbles, penalty details, scoring info) are generated by the core engine and passed to UI layers
4. **No game logic in UI** - Frontends should never implement game rules, determine play outcomes, or modify game state directly

**What this means in practice:**
- **Don't recalculate** - If the engine returns "5 yards gained", display "5 yards gained" — don't recalculate from raw dice rolls
- **Don't transform data** - Display the team's name as returned, not a version you create
- **Don't validate game rules** - The engine handles down/distance, possession changes, scoring — UI just shows the result
- **Tests live with logic** - Unit tests for game rules belong in the core engine's test suite, not in frontend tests

**Anti-patterns to avoid:**
- ❌ Parsing dice descriptions in frontend to extract play results
- ❌ Calculating field position from raw ball_position integers
- ❌ Determining possession from who was on offense last play
- ❌ Generating play result descriptions in the UI layer

For the web frontend (`paydirt-web/`), this means:
- Backend API calls the core game engine for all game operations
- Frontend receives game state and descriptions from backend
- Frontend displays what the core engine provides, it does not interpret or re-calculate

## Project Structure

```
paydirt/
├── __init__.py          # Package init, version
├── models.py            # Data classes, enums
├── game.py              # Main game class
├── game_engine.py       # Extended game logic (SOURCE OF TRUTH)
├── teams.py             # Team management
├── team_charts.py       # Play resolution charts
├── play_resolver.py     # Play outcome resolution
├── priority_chart.py    # Priority chart parsing
├── penalty_handler.py   # Penalty processing
├── cli.py               # Command-line interface (display only)
├── cli_charts.py        # Chart display utilities
├── interactive_game.py  # Interactive game loop (queries engine)
├── computer_ai.py       # CPU opponent AI
├── ai_analysis.py       # AI analysis helpers
├── commentary.py        # Play-by-play commentary
├── save_game.py         # Save/load functionality
├── standings.py         # League standings
├── season_rules.py      # Season rules YAML loading/config
├── overtime_rules.py    # Overtime handling (legacy, used by season_rules)
├── play_events.py       # Play event tracking
├── simulate_week.py    # Season simulation
└── utils.py             # Utility functions

extract_charts.py        # Import teams from Excel (.xls) files

seasons/
├── YYYY/
│   ├── YYYY.yaml        # Season rules (2-pt conversion, overtime format)
│   └── TeamName/
│       ├── offense.csv
│       ├── defense.csv
│       ├── special.csv
│       ├── team.yaml    # Team metadata
│       └── roster.json  # Player names for commentary

tests/
├── test_*.py           # Unit tests (50+ files, 1400+ tests)
└── run_all_games.py    # Integration test runner
```

## Season Rules

Each season directory must have a `YYYY.yaml` file defining era-appropriate rules. The game engine loads these on startup and enforces them throughout the game.

### Loading

Season rules are loaded by the game engine in `__init__`:

```python
# paydirt/game_engine.py
from .season_rules import load_season_rules

# Home team's season directory determines rules (even in cross-season matchups)
season_dir = Path(home_chart.team_dir).parent
self.season_rules = load_season_rules(season_dir)
```

If no YAML file exists, `load_season_rules` raises `FileNotFoundError`. Use `python -m paydirt --scaffold-season YYYY` to generate starter files.

### Rule Fields

```yaml
season: 1983
two_point_conversion: false     # Is 2-point conversion available?
overtime:
  enabled: true
  format: sudden_death          # sudden_death | modified_sudden_death
  period_length_minutes: 15
  max_periods_regular: 1
  max_periods_playoff: 0
  can_end_in_tie_regular: true
  can_end_in_tie_playoff: false
  coin_toss_winner_receives: true
```

### Accessing Rules

```python
# In game engine
self.season_rules.two_point_conversion  # bool
self.get_overtime_rules()               # -> OvertimeRules
self.get_season_rules()                 # -> dict (for API)

# In interactive_game.py
game.season_rules.two_point_conversion  # replaces hardcoded year >= 1994 checks
```

### Web API

```
GET /api/season-rules?season=1983
GET /api/game/pat-choice/{game_id}  # can_go_for_two from season rules
```

## Play Modifiers

Offensive plays can have modifiers appended to affect clock behavior. Modifiers are parsed in `_get_human_offense_play_compact()` and `get_human_offense_play()` in `interactive_game.py`.

### Available Modifiers

| Modifier | Syntax | Effect | Cost |
|----------|--------|--------|------|
| Out of Bounds | `7+` | Guarantees 10-sec play in final minutes | 5 yards |
| In Bounds | `7-` | Forces clock to keep running | 5 yards |
| Timeout | `7T` | Stops clock after play (uses timeout) | Uses timeout |
| Spike | `7S` | Spikes ball after play to stop clock | Uses a down |

### Simplified API

All modifiers are now handled by the core game engine through `run_play_with_penalty_procedure()`. The API accepts `call_spike` and `call_timeout` parameters:

```python
def run_play_with_penalty_procedure(
    self,
    play_type: PlayType,
    defense_type: DefenseType,
    out_of_bounds_designation: bool = False,  # + modifier
    in_bounds_designation: bool = False,      # - modifier
    no_huddle: bool = False,
    call_spike: bool = False,                 # S modifier
    call_timeout: bool = False                # T modifier
) -> PlayOutcome:
```

The engine internally:
1. Executes the play
2. Checks if modifier should apply (based on outcome)
3. Adjusts clock accordingly
4. Sets `outcome.spike_used` or `outcome.timeout_used` flags

**Example (web backend):**
```python
result = engine.run_play_with_penalty_procedure(
    offense_play, defense_play,
    out_of_bounds_designation=request.out_of_bounds,
    call_spike=request.call_spike,
    call_timeout=request.call_timeout
)
# Result has spike_used/timeout_used flags set
```

### Spike Modifier Implementation

The spike modifier (`S`) allows the two-minute drill: run a play, spike to stop the clock, then kick a field goal.

**Key mechanics:**
- Play + spike time is capped at 20 seconds total
- If play would have taken >17 seconds, it's reduced to 17, then 3 seconds for spike
- Only applies when clock is running (skipped after incomplete, OOB, or turnover)
- Does NOT advance down (play already did that)

**Code locations:**
- Modifier parsing: `interactive_game.py:_get_human_offense_play_compact()` lines ~475-485
- Spike application: `game_engine.py:_apply_spike()` method
- Skip conditions: `game_engine.py:_should_apply_spike_after_play()` method

**Example scenario (20 seconds left, need FG):**
1. Call `7S` (Medium Pass + Spike)
2. Pass completes for 5 yards (uses ~25 sec normally)
3. Spike modifier caps play at 17 sec + 3 sec spike = 20 sec total
4. Time remaining: 0 sec → game ends, OR if play was fast enough, time for FG

### Modifiers Combined

Multiple modifiers can be combined:
- `7+S` = Medium Pass + Out of Bounds + Spike
- `7ST` = Medium Pass + Spike + Timeout (timeout takes precedence)

## Importing Teams

Use `extract_charts.py` to import team data from Excel files (`.xls` format only). The script requires `xlrd==1.2.0` for reading Excel formatting (cell colors for incomplete passes, red extra points).

```bash
pip install xlrd==1.2.0

# Import all teams
python extract_charts.py -i /path/to/excel -o seasons/1983

# Import single team
python extract_charts.py -i /path/to/excel -o seasons/1983 -t TeamName.xls
```

After importing, create `team.yaml` and `roster.json` in the team directory, and ensure `seasons/YYYY/YYYY.yaml` exists.

## Key Dependencies

- Python 3.10+
- pytest (for testing)
- pytest-cov (for coverage)
- Standard library only (no pip dependencies for runtime)

## Running the Game

```bash
# Interactive game
python -m paydirt

# Run simulation
python -m paydirt --simulate

# List available teams
python -m paydirt --teams
```

## Releases and Tagging

When creating releases:

- **Always increment tag numbers** - Don't delete and recreate tags. If a build fails, fix the issue and create the next tag number (e.g., if `v1.0.0-beta.70` fails, push the fix and create `v1.0.0-beta.71`)
- **Tags are immutable history** - Deleting tags can cause confusion with existing references and breaks the audit trail
- **CI runs on tag push** - The release workflow (`.github/workflows/release.yml`) triggers on `v*` tags

```bash
# Get the latest tag
git tag --list 'v*' | sort -V | tail -1

# Create and push a new tag (always increment, never reuse)
git tag v1.0.0-beta.71 && git push origin v1.0.0-beta.71
```