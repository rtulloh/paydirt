---
id: FLOW-022
title: Web UI cannot start and watch an AI-versus-AI game
status: open
priority: Low
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - requested
links:
  - FLOW-021
---

## Description

Allow players to start and watch a complete AI-versus-AI game from the web UI, as they can already do with the CLI auto-game runner. Make this discoverable during game setup for players who do not use the command-line interface. Community suggestion: add an AI-vs-AI / spectator choice to the existing dropdown where players select which team to control.

## Resolution / verification
- Offer AI vs AI as a game mode during setup, preferably through an explicit "AI vs AI (watch game)" option in the existing team-control dropdown, with season, home/away teams, and difficulty selection for each coach.
- Keep human team-control choices clear and allow starting this mode entirely from the UI without entering CLI commands.
- Use the shared core engine and existing AI factory for both teams; keep gameplay decisions out of the frontend.
- Support the entire game, including kickoffs, penalties, conversions, halftime, overtime, final score and box score.
- Provide pause/resume and single-play advancement, with a controllable viewing pace.
- Keep the play-by-play and charts available while watching; prevent duplicate execution from repeated clicks or requests.
- Support saving/resuming a watched game where existing save functionality permits it.
- Allow the completed result to use the shared standings-recording flow when that feature is implemented (FLOW-021).
- Add test-first coverage using synthetic/public teams, including a complete real-engine browser game with both coaches controlled by AI.

This is a separately scoped UI feature; it does not change the ongoing AI-026 historical-fidelity acceptance criteria.

## Comments

--- 2026-11-08 14:24 ---
Requested by the owner. Moved from mistakenly created GitHub issue #2 to the
repository tracker; implementation remains pending. GitHub is not the tracker for
this request. No release commitment or gameplay change accompanies this ticket.

--- 2026-11-08 21:29 ---
Owner requested Low priority after Facebook feedback from Neil Skrabec. Neil
asked whether AI vs AI was coming, learned that the CLI already supports
`--auto` and difficulty selection, and asked what CLI means and how to change
the command line. His proposed UI was: "Could this eventually just be added to
set up screen drop down where you choose team you play as?"

Recorded the requested setup-dropdown placement and discoverability rationale
in this existing ticket rather than creating a duplicate. Lowered priority from
Medium to Low per the owner's request. No release commitment or implementation
change accompanies this update.
