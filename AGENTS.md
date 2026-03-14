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

## Project Structure

```
paydirt/
├── __init__.py          # Package init, version
├── models.py            # Data classes, enums
├── game.py              # Main game class
├── game_engine.py       # Extended game logic
├── teams.py             # Team management
├── team_charts.py       # Play resolution charts
├── play_resolver.py     # Play outcome resolution
├── priority_chart.py    # Priority chart parsing
├── penalty_handler.py   # Penalty processing
├── cli.py               # Command-line interface
├── cli_charts.py        # Chart display utilities
├── interactive_game.py  # Interactive game loop
├── computer_ai.py       # CPU opponent AI
├── ai_analysis.py       # AI analysis helpers
├── commentary.py        # Play-by-play commentary
├── save_game.py         # Save/load functionality
├── standings.py         # League standings
├── overtime_rules.py    # Overtime handling
├── play_events.py       # Play event tracking
├── simulate_week.py    # Season simulation
└── utils.py            # Utility functions

tests/
├── test_*.py           # Unit tests (50+ files, 1400+ tests)
└── run_all_games.py    # Integration test runner
```

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