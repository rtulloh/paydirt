# Paydirt Documentation

[Project home](../README.md) · [Downloads](https://github.com/rtulloh/paydirt/releases) · [Release notes](../RELEASE_NOTES.md)

## Start Playing

1. [Install Paydirt](installation.md): downloads, source installation, and platform troubleshooting.
2. [Use the browser interface](web-interface.md), or [play in the terminal](playing.md).
3. Choose [CPU difficulty and coaching](ai-difficulty.md).
4. Learn [clock management](clock-management.md) and [saving games and standings](saved-games-and-standings.md).
5. Use the [priority chart reference](priority-chart.md) to understand combined results, with worked examples.

## Teams and Data

- [Seasons and rules](seasons.md): data locations, CSV layout, team metadata, rosters, and season YAML.
- [Chart generation and Excel import](chart-generator.md): estimate charts from season data or convert existing Excel charts.
- [Two-phase chart generation workflow](chart-generation-workflow.md): generate, train, validate, promote, and prepare a season for playtesting.

Published builds include generated 1983 and 2024 charts plus the fictional 2026 sample. See the
[chart attribution](../CHART_ATTRIBUTION.md); keep original charts, source workbooks, raw data, and historical logs local.

## Development

- [Development guide](development.md): architecture, testing, packaging, and release entry points.
- [Web setup](../paydirt-web/README.md): frontend and backend development.
- [Published application checks](release-testing.md): native runtime acceptance of actual release-page downloads.
- [Browser regression](../paydirt-web/frontend/e2e/README.md): two full real-engine games.
- [AI audit harness](ai-auditing.md): reproducible game/season play-selection and play-balance testing.
- [Historical season runner](historical-seasons.md): selected-year actual calendars/results, generated charts and distinct postseason modes.
- [Generated chart release gate](chart-validation.md): source consistency, weighted tactics, event allocation and current-engine accuracy checks.
- [AGENTS.md](../AGENTS.md): authoritative agent workflow and mandatory pre-push checks.

## Testing and Design Notes

Create all future development notes only under `docs/dev-notes/`. Read the [developer-only disclaimer](dev-notes/README.md); these are not player manuals or promises of implemented features:

- [Issue tracker](dev-notes/issue-tracker.md): developer priorities, status, and resolution history.
- [AI play-testing](dev-notes/ai-playtesting.md): an experiment evaluating dice-weighted Hard analysis.
- [Replayable game logs](dev-notes/replayable-game-logs.md): debugging requirements and deferred replay work.

## Keeping These Docs Current

Each topic has one canonical guide. Link to it rather than duplicating its instructions.
Screenshots live in `docs/images/`. Player guides are also assembled into the app's offline User Guide;
when adding a player topic, update the backend's `GUIDE_PAGES` list and its guide tests.
