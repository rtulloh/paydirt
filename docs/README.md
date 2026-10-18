# Paydirt Documentation

[Project home](../README.md) · [Downloads](https://github.com/rtulloh/paydirt/releases) · [Release notes](../RELEASE_NOTES.md)

## Start Playing

1. [Install Paydirt](installation.md): downloads, source installation, and platform troubleshooting.
2. [Use the browser interface](web-interface.md), or [play in the terminal](playing.md).
3. Choose [CPU difficulty and coaching](ai-difficulty.md).
4. Learn [clock management](clock-management.md) and [saving games and standings](saved-games-and-standings.md).

## Teams and Data

- [Seasons and rules](seasons.md): data locations, CSV layout, team metadata, rosters, and season YAML.
- [Chart generator / Excel importer](chart-generator.md): generate game CSV files from existing Excel charts using `extract_charts.py`.

Only the public fictional 2026 teams are distributed. Keep private charts, source workbooks, and historical logs local.

## Development

- [Development guide](development.md): architecture, testing, packaging, and release entry points.
- [Web setup](../paydirt-web/README.md): frontend and backend development.
- [Browser regression](../paydirt-web/frontend/e2e/README.md): two full real-engine games.
- [AGENTS.md](../AGENTS.md): authoritative agent workflow and mandatory pre-push checks.

## Testing and Design Notes

Create all future development notes only under `docs/dev-notes/`. Read the [developer-only disclaimer](dev-notes/README.md); these are not player manuals or promises of implemented features:

- [AI play-testing](dev-notes/ai-playtesting.md): an experiment evaluating dice-weighted Hard analysis.
- [Replayable game logs](dev-notes/replayable-game-logs.md): debugging requirements and deferred replay work.

## Keeping These Docs Current

Each topic has one canonical guide. Link to it rather than duplicating its instructions.
Screenshots live in `docs/images/`. Player guides are also assembled into the app's offline User Guide;
when adding a player topic, update the backend's `GUIDE_PAGES` list and its guide tests.
