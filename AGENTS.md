# AGENTS.md - Paydirt Development Guide

This file provides guidelines for AI agents working on the Paydirt codebase.

## Project Overview

Paydirt is a Python simulation of the classic Paydirt football board game. It uses only the Python standard library - no external dependencies required (except pytest for testing).

## Machine Reset Deadline

The owner will reset this machine to factory defaults on **December 4, 2026**.
Before that date, preserve important work in GitHub or in a folder in the owner's
[Google Drive](https://drive.google.com/drive/u/1/my-drive). A local copy alone
does not satisfy this requirement. Verify remote copies before considering work
preserved, and follow the required regression gates before any Git push.

Include uncommitted work and important ignored/local-only data in preservation
planning, especially `.ai-audits/` evidence, private chart/source material, saved
games and standings. Keep private charts, raw sources and historical logs out of
GitHub; preserve them in a private Drive folder. Record the actual destination and
verification status; do not claim backups are complete until verified.

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
from the repository root. A "full test run" or "full regression" explicitly includes
both the generated full-season runner and the public/local AI play-selection audits
below; pytest alone is not sufficient. Do not push if any command fails; investigate
and fix failures first. Disclose existing skips and warnings rather than hiding them.

```bash
python3 -m pytest tests/ -q -o addopts= --tb=short -rs --cov=paydirt --cov-report=term
(cd paydirt-web/backend && python3 -m pytest tests/ -q -o addopts= --tb=short)
(cd paydirt-web/frontend && npm test -- --run)
(cd paydirt-web/frontend && npm run build)
(cd paydirt-web/frontend && npm run test:e2e)
ruff check paydirt/ tests/ paydirt-web/backend/
python3 tests/run_all_games.py
python3 tests/run_full_season.py
python3 tests/run_ai_audit.py --season 2026 --weeks 16 --seed 8306 --compare-balanced --output .ai-audits/public-season.json
python3 tests/run_ai_audit.py --season 1983 --weeks 16 --seed 8306 --compare-balanced --output .ai-audits/local-season.json --csv .ai-audits/local-season.csv
python3 -m paydirt.released_chart_regression_audit --season 1983 --output .ai-audits/chart-quality-1983.json
python3 -m paydirt.released_chart_regression_audit --season 2024 --output .ai-audits/chart-quality-2024.json
```

### One-command runner

`python3 scripts/run_full_regression.py` runs every command above in order,
streams per-step logs, and prints a compact pass/fail summary. `--list` shows the
plan without running; `--only`/`--skip` narrow it; `--clean-checkout` adds the
tracked-files-only unit run. Logs and `summary.json`/`summary.md` are written to
ignored `.ai-audits/full-regression/`. Prefer asking the owner to run this script
and share the summary instead of running the suite step by step in an agent
session; it covers the twelve commands above plus the private 1983 AI audit when
escrow charts exist. It does not replace the separate manual gates below (1977
release-policy audit, per-issue tracker review, published-artifact verification).
The browser step puts the regression interpreter's directory first on `PATH`, so
the isolated E2E API always runs on the same Python environment as the rest of the
run. Install that environment's backend and test dependencies, including the
test-only `httpx<0.28`, and install Chromium once
(`cd paydirt-web/frontend && npx playwright install chromium`).

**Released charts and new charts have distinct gates.** The two commands above
apply to public 1983/2024 charts from the immutable v1.10.3 commit
`1467b11e151fe9981177890e2a7a6b805402b3f0`. They verify exact chart, metadata,
sanitized provenance and contract bytes, public mechanics and unchanged core/backend
gameplay implementation. The owner-reviewed DATA-047 allowance accepts only the exact
1983 short_name corrections LAC → SD (Chargers), ARI → STL (Cardinals) and
OAK → LA (Raiders), bound to that baseline and the complete original/corrected
team.yaml bytes. Receipts list accepted corrections and both hashes; all other
metadata edits still fail. Frontend changes require actual review and the full real-engine
browser regression; this chart gate does not verify frontend implementation identity. Existing historical-fit exceptions remain exceptions, not strict
passes. Full gameplay and AI regression remains mandatory. This route does not
claim fresh source reproduction or historical-fit qualification.

Any new or regenerated season must instead pass strict source/reproduction and
applicable minimum-sample fit qualification with `scripts/audit_generated_charts.py`
and its reviewed source-bound contract. It cannot declare itself previously
released. Changed gameplay fails the released gate and requires reviewed paired
regression evidence against the immutable baseline before this route can be
extended; do not silently add exclusions or fall back to a weaker check. See
[released chart regression](docs/released-chart-regression.md). Private source
inventories and historical logs remain in ignored local audit storage.

The owner's explicit 1977 finite-search authorization permits a narrow, reviewed,
hash-bound statistical release exception for the best canonically generated and
characterized candidate. Record the actual missed bounds and owner authorization;
never relabel failed strict fit as passing or alter tolerances. Source identity,
reproduction, sample requirements, mechanics, screen-INT, gameplay, full regression
and downloaded native-install checks remain mandatory. This is specific to the
[1977 release goal](docs/dev-notes/1977-calibration-release-goal.md), not a generic
new-season bypass.


When the 1977 set is included, also run the separately reviewed
`scripts/audit_1977_release.py` command documented in
[released chart regression](docs/released-chart-regression.md#exact-1977-statistical-acceptance),
using the immutable pinned policy and its exact canonical, independent
reproduction, source-contract and minimum-72-repetition execution evidence.
Retain a fresh ignored acceptance receipt for each regression. A missing policy,
changed chart/source/runtime, incomplete public season or nonstatistical failure
blocks pushing. Its passing release-policy receipt does not relabel strict fit
misses as passes or replace any command above. The owner-authorized statistical
exceptions and all actual failed bounds must remain visible in the public season
notes and manifest. Raw private source paths and inventories stay local.

For corrective v1.10.5 only, the owner-approved 1977 version-metadata equivalence
retains the immutable policy and original execution report. The gate verifies all
55 fingerprinted source files against v1.10.4 commit
`a35153c26c8efbd07cd87d012e812520082e21e1`: 53 remain byte-identical; only the
exact full-file hashes for `paydirt/__init__.py` and `paydirt/__main__.py` may
change their 1.10.4 version literals to 1.10.5. Complete original/actual engine
fingerprints and identical Python 3.12 loaded/worker identities remain required.
The receipt discloses the derived validation view and both identities; raw report
bytes and statistical failures remain unchanged. Every other source/runtime edit
still blocks, and this does not waive any nonstatistical or full-regression gate.

**Play-selection and play-balance audit is part of full regression**, not merely
a final-score check. The audit commands exercise Hard-vs-Hard and legacy balanced
auto AI on the same independently seeded generated schedules. Require every game
to complete and reconcile audit totals, then inspect per-team/down/distance/mode
call shares, distinct calls, and comparable-situation repetition streaks. Review
concentration warnings with sample counts and chart strengths; they are advisory,
not universal play-frequency caps or grounds for weakening tests. Record any
questionable decisions/findings in the developer tracker, even when all games
complete. At the end of every play-test and audit review, inspect the per-issue
tracker for resolved tickets with newly confirmed evidence; add timestamped
comments and close tickets when the audit demonstrates that the issue no longer
occurs. Do not close a ticket from unit tests alone when play-test confirmation
is required. The 1983 AI audit uses public generated charts in `seasons/1983`.
The separate private integration/reproduction runners explicitly use
`.ai-audits/escrow/1983-private-charts/`. Preserve the private AI comparison too:

```bash
python3 tests/run_ai_audit.py --season "$PWD/.ai-audits/escrow/1983-private-charts" --weeks 16 --seed 8306 --compare-balanced --output .ai-audits/private-season.json --csv .ai-audits/private-season.csv
```

Keep reports in ignored `.ai-audits/`; never commit/export private charts or
narrative logs. The generated audit schedule is regular-season only;
it supplements, never replaces, the existing nine-playoff-game regression. See
[AI audit harness](docs/ai-auditing.md) for commands and interpretation.

`npm run test:e2e` is a required part of full regression, not an optional smoke
check. It must complete both real-engine browser games (human home/receiving,
then away/kicking), including halftime, final-score screens, and clean new-game
state. Install Chromium once with `npx playwright install chromium` from
`paydirt-web/frontend` (on Linux, use `--with-deps`). The backend dependencies
must also be installed. Playwright defaults to ports 8000 and 5173. If either is occupied, use free
isolated ports, for example `PAYDIRT_E2E_BACKEND_PORT=18000
PAYDIRT_E2E_FRONTEND_PORT=15173 npm run test:e2e`, rather than stopping an
installed app or potential saved-game session. Playwright starts and stops only
its own isolated services using public 2026 teams. Missing browsers/services or reaching the action limit are failures, not
reasons to skip this check. See `paydirt-web/frontend/e2e/README.md` for details.

`tests/run_full_season.py [YEAR]` runs the selected year's actual regular-season
calendar followed by a postseason seeded from simulated standings. No argument
selects 1983 (224 regular games, nine playoff games); 2024 has 272 regular games
and thirteen playoff games. It prefers available generated charts, accepts explicit
chart/source paths, and fails before games if actual fixtures/results, membership,
charts or source-year rules are missing. Developer charts are optional for this
historical-results audit. The separate 14-game runner still requires local data.
See [historical season validation](docs/historical-seasons.md) for commands,
provenance, selected-action accounting and the distinct historical-playoff replay
mode. Historical outcomes and champions are diagnostics, never forced results.

Seeds use simulated winning fraction, point differential, points scored and team
name: declared regression tiebreaks, not the full official NFL procedure. The
1983 bracket prevents divisional rematches before conference championships; the
2024 bracket has one bye per conference and reseeds the divisional round. Final
scoring/box and termination checks remain mandatory; tied playoff finals fail.
Failed games do not advance teams, missing dependent games fail, and regular-season
failures prevent a simulated postseason. Reports bind source/chart/runtime identity,
retain failures and stay in ignored `.ai-audits/`. All sixteen existing private
1983 reproductions, including two mandatory untimed-down scenarios, run additionally
when their original local charts exist. Their absence is explicitly not applicable
for a generated-chart historical audit. The old rotating 1983 calendar is available
only with `--generated-regression` as an additional regression. Official tiebreak
qualification, complete per-action proof and repeated-season probabilities remain
unverified; this runner does not waive source-fit or the rest of full regression.

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

## Documentation Maintenance

Keep documentation up to date in the same change as the behavior it describes.
When changing gameplay, AI/coaching, controls, commands, API behavior, dependencies,
data formats, installation, or packaging, review and update the affected guides.
If no documentation update is needed, state why in the change summary.

- Keep `README.md` a concise landing page; detailed instructions belong in `docs/`.
- Use `docs/README.md` as the documentation index and link to each canonical topic
  instead of duplicating instructions across files.
- Create all future development notes (experiments, investigations, and proposed
  designs) **only in `docs/dev-notes/`**, never in the repository root or elsewhere
  in `docs/`. Clearly distinguish them from implemented features and current
  player guidance. Keep maintained user/developer reference guides in `docs/`.
- Verify examples against the current implementation. Use synthetic data or public
  2026 sample teams for examples. Publish only reviewed chart-generator outputs with
  attribution; never publish private developer charts, workbooks, raw source data, or
  historical logs.
- When moving or renaming documentation, update references, relative links,
  heading anchors, and image paths. Run `python3 -m pytest tests/test_documentation.py`.
- Player guides also power the offline in-app User Guide. Keep the backend
  `GUIDE_PAGES` list, frontend navigation, and packaging specs consistent with
  documentation changes; run guide/API tests and browser checks when affected.

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
    call_timeout: bool = False,               # T modifier
    call_defensive_timeout: bool = False      # pre-snap defensive AT request
) -> PlayOutcome:
```

The engine internally:
1. Executes the play
2. Resolves any pending penalty choice before applying clock-saving procedures
3. Applies a useful defensive timeout before any planned spike; otherwise checks the offensive modifier
4. Sets `outcome.spike_used`, `outcome.timeout_used`, and `outcome.defensive_timeout_used` flags

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
- Charges an additional down. A first-down call plus applied spike leaves third down, even after a first-down gain.
- A pending foul preserves the S and defensive AT requests; only a retained, eligible play applies them.
- A useful available defensive timeout wins before a planned spike, saving its down; unavailable timeouts cannot cancel a spike.
- A newly reached two-minute warning requires neither procedure. Restoring first-half time also restores first-half timeout budgets.

**Code locations:**
- Modifier parsing: `interactive_game.py:_get_human_offense_play_compact()` lines ~475-485
- Spike/down application: `game_engine.py:_apply_requested_spike()`
- Clock adjustment: `game_engine.py:_apply_spike()`
- Skip conditions: `_apply_requested_spike()` and `_should_apply_spike_after_play()`

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

Prefix every Git commit message with the applicable release or milestone tag,
followed by a colon and a concise description. Use the target release or milestone
for the work, for example: `v1.10.3: Improve third-down matchup selection`.

### Required test of published release artifacts

After publishing a release, download the actual assets from that release and
verify the packaged applications, not a development checkout or development
server. Do not declare the release healthy from CI success or asset presence
alone. For each supported platform/architecture, record artifact name/hash,
platform, launch result and the following smoke-check evidence:

- Install or extract and launch the downloaded application using its normal
  entry point in an environment without the source checkout on its import path.
- Verify every bundled season exposes its expected team list in the UI and API;
  an empty list, HTTP error, model-initialization error or startup fallback fails.
- Select two bundled teams and start a game; confirm game state and charts load.
- Inspect startup/request logs for errors, and verify normal shutdown.

Exercise macOS first-launch security behavior on a freshly downloaded artifact;
record signing/notarization or quarantine limitations rather than treating an
already trusted local executable as proof of a clean install. If a target cannot
be tested, disclose that verification gap and arrange a target-platform check.
If published-asset verification fails, treat it as a release defect and prioritize
a repair. Retain the failed artifact/tag as immutable history and use the next
unused tag for the correction. This post-publication check supplements pre-push
regression; it does not silently replace it.

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
