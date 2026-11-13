---
id: DATA-049
title: Bundle verified player rosters for 1977 and 2024 commentary
status: open
priority: Medium
target-release: v1.10.6
created-at: 2026-11-11
resolved-at:
closed-at:
tags:
  - release-planning
links:
commits:
---

## Description

Manual v1.10.5 UI testing found generic player references in the 1977 play log. The tracked release tree has no roster.json files for 1977 or 2024, while all 28 1983 teams have them. The commentary loader returns an empty roster when no file exists and uses generic position names. Source and bundle season-correct player names rather than borrowing players from other years.

## Resolution / verification

- Obtain attributable season/team-specific roster data for all 28 1977 teams and 32 2024 teams; document source coverage and review position assignments and actual season membership.
- Use synthetic/sample tests for roster loading, missing-roster fallback and cross-season cache isolation; keep historical roster validation in a standalone audit rather than historical-data-dependent unit tests.
- Verify actual roster files are included in all packaged builds and downloaded native assets. Exercise real-engine CLI and web commentary for both seasons and confirm names come from the selected team and season.
- Player names remain narration only and do not change chart probabilities, engine outcomes or gameplay RNG. Complete applicable chart metadata/provenance review and release validation without silently weakening immutable gates.

## Comments

--- 2026-11-11 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
