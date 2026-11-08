---
id: FLOW-022
title: Web UI cannot start and watch an AI-versus-AI game
status: open
priority: Medium
created-at: 2026-11-08
resolved-at:
closed-at:
tags:
  - requested
links:
  - FLOW-021
---

## Description

Allow players to start and watch a complete AI-versus-AI game from the web UI, as they can already do with the CLI auto-game runner.

## Resolution / verification
- Offer AI vs AI as a game mode during setup, with season, home/away teams, and difficulty selection for each coach.
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
