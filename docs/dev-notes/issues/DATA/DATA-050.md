---
id: DATA-050
title: Use season-aware player availability and roles in roster commentary
status: open
priority: Low
target-release:
created-at: 2026-11-11
resolved-at:
closed-at:
tags:
  - exploratory
links:
commits:
---

## Description

Static season-wide player lists can name the wrong participants when comparing a simulated matchup with its actual historical game, especially when the starting quarterback changed. Players may be benched, injured, traded, signed or released during the season. Explore roster metadata describing team membership, availability and role over dates/weeks so commentary can prefer the appropriate starter and exclude players who were not on that team or unavailable for the selected game context. Distinguish a historical-week replay from an exhibition using a full-season or cumulative snapshot; a current roster alone does not describe every earlier game.

## Resolution / verification

- Define an extensible roster schema for stable player identity, season/team membership intervals, position, starter/backup role and availability intervals, with source attribution and explicit unknown values.
- Define how game date/week and selected chart snapshot determine eligible names, including trades between teams, midseason starter changes, injuries and returns, byes and postseason boundaries. Preserve full-season exhibition behavior through a documented policy.
- Use authoritative historical participation or starting-lineup evidence where available; distinguish confirmed absence from missing data. Do not infer injury, benching or a start merely from absence in play-by-play.
- Keep the core engine responsible for eligible participant identity and pass its descriptions to CLI/web. Initially scope this to narration eligibility and role selection; any player-strength, injury simulation or chart-probability changes need a separately reviewed design.
- Preserve compatibility with existing simple roster files and saved games, recording the selected roster context or version where needed for consistent continuation. Use generic position names when no supported eligible player is known.
- Add test-first synthetic/sample regressions for a quarterback change, injured-player exclusion and return, a traded player before/after membership changes, unknown metadata, and cross-team/season/week cache isolation. Verify named participants in actual CLI/web historical-context play tests without consuming gameplay RNG for narration.

## Comments

--- 2026-11-11 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
