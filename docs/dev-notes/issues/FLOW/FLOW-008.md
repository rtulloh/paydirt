---
id: FLOW-008
title: Web load_replay reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession
status: open
priority: Medium
created-at: 2026-10-19
resolved-at: 
closed-at:
tags:
  - code-read
---

## Description

Web `load_replay` reconstructs state by scanning history text ("touchdown", "extra point", …) and switches possession; a TD is inferred from `ball_position >= 100`.

## Resolution / verification

Persist authoritative flags with the replay; stop parsing text.

## Comments

--- 2026-10-19 00:00 ---
Migrated from the single-file tracker (status at migration: Open (code-read)).

--- 2026-10-30 15:09 ---
Broader save/resume evidence from the public 2026 API: saving a Hard game with
seven home first downs, OT1 in progress, first possession complete, and a
known opening kicker, then loading the `/api/game/save-replay` response,
created a Medium game with zero first downs, no overtime, incomplete first
possession and no recorded opening kicker. `load_replay` creates a fresh engine
and restores only a subset of state. This can change later gameplay and box
scores; it is distinct from bit-for-bit RNG replay. Browser SAVE GAME and SAVE
REPLAY both construct partial snapshots and use the same loader. SAVE GAME's
handler also omits `pendingPat` even though the store accepts it; current UI
buttons are disabled while a PAT, kickoff or penalty decision is pending.

Further API/UI boundary gaps: a replay whose team fields are string IDs returns
500 because `.get("id")` runs before the documented string fallback. The
browser's `loadGame()` returns success before its fetch finishes and only logs
asynchronous failures, unlike `loadReplay()` which reports them. Add round-trip
tests for phase, engine/score state, difficulty and statistics, malformed and
legacy inputs, and visible load errors; decide and document which browser
snapshots can safely resume, rather than inventing missing historical state.
Separately, a new Hard game reports top-level `difficulty: hard` but nested
`game_state.difficulty: medium` because `game_state_to_response` never sets
that field. Cover state-response difficulty as well as persistence.
