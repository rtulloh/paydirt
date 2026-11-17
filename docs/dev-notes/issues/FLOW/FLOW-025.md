---
id: FLOW-025
title: Kickoff penalty menu duplicates the decline option and offers three choices
status: open
priority: Medium
target-release: v1.10.7
created-at: 2026-11-13
resolved-at:
closed-at:
tags:
  - reproduced
links:
  - FLOW-024
commits:
---

## Description

The CLI kickoff-penalty prompt showed [1] Accept PLAY result and then two engine options: [2] Accept PENALTY: Re-kick and [3] Accept PENALTY: Decline penalty, take the kickoff result. Options [1] and [3] are the same outcome. The [3] label is also self-contradictory: it starts with "Accept PENALTY" but its text is a decline. The engine's kickoff PenaltyChoice includes both an accept and a decline option, while handle_penalty_decision separately offers the play result as option 1. The web penalty panel may present the same duplication and prefix issue.

## Resolution / verification

- Present one accept-penalty choice for a kickoff foul plus the existing play-result/decline choice, without changing kickoff rules or the engine's apply_kickoff_penalty_decision behavior. The decline choice must use decline wording, not an "Accept PENALTY" prefix, and must not duplicate option 1. Add a CLI regression asserting the menu has no duplicate decline option and check the web panel for the same wording and duplication. Do not change penalty enforcement.

## Comments

--- 2026-11-13 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-13 20:50 ---
Owner review of the FLOW-024 replay: the decline choice is understandable as
the opposite of the re-kick, but its "[3] Accept PENALTY: Decline penalty"
prefix is self-contradictory. Recorded separately from the safety-possession
fix. No change to kickoff rules or penalty enforcement is intended.

--- 2026-11-17 18:15 ---
Deferred to v1.10.7 during the v1.10.6 release review. This is a prompt wording
and duplicate-choice presentation issue; the underlying kickoff enforcement is
unchanged. It does not block the gameplay and AI fixes qualified for v1.10.6.
