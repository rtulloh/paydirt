# Development, Testing, and Packaging

[Documentation index](README.md) · [Project home](../README.md)

## Development Setup

The core CLI requires Python 3.10+ and PyYAML. Install test tools in your virtual environment:

```sh
python -m pip install pyyaml pytest pytest-cov ruff
python -m pytest tests/ -q -o addopts= --tb=short
```

For browser development, follow the [web setup guide](../paydirt-web/README.md).
Backend dependencies are separate from core dependencies. The release workflow currently uses Python 3.10 and Node.js 20;
use a Python version compatible with the pinned backend packages and available wheels.

## Architecture and Project Structure

The core engine is authoritative for game rules, state, scoring, descriptions, and timing.
The CLI and web frontend display engine decisions rather than reconstructing outcomes or implementing their own rules.

| Location | Purpose |
|----------|---------|
| `paydirt/game_engine.py` | Core rules and game flow |
| `paydirt/play_resolver.py`, `priority_chart.py`, `penalty_handler.py` | Play, priority, and penalty resolution |
| `paydirt/chart_loader.py` | CSV chart loading |
| `paydirt/season_rules.py`, `overtime_rules.py` | Season configuration and overtime |
| `paydirt/computer_ai.py`, `ai_analysis.py` | CPU decisions and chart coaching |
| `paydirt/interactive_game.py` | CLI presentation and user choices |
| `paydirt/commentary.py` | Play-by-play presentation |
| `paydirt/save_game.py`, `standings.py` | CLI persistence and results |
| `paydirt-web/backend/` | FastAPI adapter around the core engine |
| `paydirt-web/frontend/` | React browser UI |
| `seasons/2026/` | Public fictional sample data |
| `extract_charts.py` | [Excel-to-CSV chart generator](chart-generator.md) |
| `tests/` | Core unit tests and standalone integration runners |

## Test-First Changes

For behavior changes, add self-contained regressions first, demonstrate their intended failures,
then fix the implementation and rerun focused and relevant broader suites.
Use synthetic data or public 2026 teams only in unit tests. Private charts must not become hidden test dependencies.
Documentation-only changes do not require invented behavior failures; documentation-loading changes do.

[AGENTS.md](../AGENTS.md) is authoritative for agent workflow and the full mandatory pre-push checklist.
Run **all** of its listed checks before every push, including release/tag pushes, and disclose existing skips and warnings.
Do not treat the quick unit-test command above as full release validation.

- Core and backend pytest suites, frontend tests, production build, and Ruff.
- [Browser regression](../paydirt-web/frontend/e2e/README.md): two complete real-engine games, including clean new-game state.
- `tests/run_all_games.py`: standalone game integration checks.
- `tests/run_full_season.py`: generated 224-game regular season, nine-game playoffs, and historical reproductions.
- `tests/run_ai_audit.py`: full generated Hard-vs-Hard seasons and legacy balanced comparisons; review [play-selection/balance evidence](ai-auditing.md), not just final scores.
- Clean tracked-files-only unit tests, so ignored local data cannot mask CI failures.

Historical integration runners need private local 1983 data and never export it. The generated season is not the
historical schedule or results. Regular-season ties are allowed by rules; tied playoff finals are failures.
All 224 regular games and nine playoff games must pass before pushing.

## Building Standalone Applications

Use [.github/workflows/release.yml](../.github/workflows/release.yml) as the current build recipe,
not an assumed list of platform/signing tools. It builds the frontend, copies it to backend `web_static/`,
installs PyInstaller and backend dependencies, then runs:

```sh
pyinstaller paydirt.spec --clean
```

Prepare the frontend assets and Python dependencies first, following the workflow.
Do not add `--onefile` when using the spec file; the spec defines executable packaging.
Platform packaging uses NSIS for the Windows installer, `create-dmg` and
`packaging/macos/create_app.sh` on macOS, and `packaging/linux/create_appimage.sh` on Linux.
Build on the target platform. The workflow does not currently implement the certificate-secret signing recipe
previously shown in the README; do not assume a build is signed.

The specs bundle only public 2026 season data, Markdown guides, and documentation images.
The backend assembles the offline User Guide from the canonical player files in `docs/`.
Relative links between those player guides become in-app anchors; contributor-only documents link to GitHub.
No separately maintained copy of the player manual is needed.

## Releases

The workflow builds releases on `v*` tags and also supports manual dispatch.
Tags are immutable: always choose a new, increasing version; never delete and recreate a failed release tag.
Before creating or pushing a release, follow all [required validation](../AGENTS.md#required-full-regression-before-any-push)
and the project's versioning instructions. [Release notes](../RELEASE_NOTES.md) remain separate from the user manual.

## Project Background

Paydirt was published by Avalon Hill, with team charts designed by mathematician Dr. Thomas R. Nicely.
This implementation models chart/priority resolution, Full Feature Method penalties, the offensive and defensive dice,
special teams, variable-yardage entries, and clock-management procedures.
It is a fan-made project; the original game's names and trademarks belong to their respective owners.

## Pending penalty outcomes

`run_play_with_penalty_procedure` returns a provisional `PlayOutcome` with
`pending_penalty_decision=True` while the offended team chooses. Nothing has been
applied: the spot, down, score, statistics, and `touchdown` flag are unchanged, and
`touchdown` stays `False`. `PlayOutcome.projected_touchdown` estimates whether
accepting the play would score, for CPU decisions and audits only. UI layers must
not place the ball for a try or kickoff, change `pending_pat`, or infer a score
until `apply_*_penalty_decision` returns a finalized outcome.
