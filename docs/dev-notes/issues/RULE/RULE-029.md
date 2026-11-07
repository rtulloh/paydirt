---
id: RULE-029
title: Interception chart spots on or beyond the offense end line score touchdowns instead of safeties
status: open
priority: High
created-at: 2026-11-06
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

The interception handler treated every spot at or behind the offense goal line
as a defensive touchdown. Rule VI-12-E-iii distinguishes spots on or behind the
own end line: the ball is out of play, a lateral out of the end zone, and scores
a safety. Such a spot cannot become a defensive catch or return consultation.

## Resolution / verification

A narrow local fix applies the safety before switching possession, retains the
safety victim for the free kick from its 20, and records neither an interception
turnover nor a return roll. Legal in-end-zone touchdowns and defensive end-zone
automatic touchbacks remain covered. The retained-play path also now follows
the normal-play invariant that INT depth is catch geometry, not offensive gain.
Keep open pending issue-specific play-test evidence and the required final
frozen-candidate regression. No prior campaign qualifies the changed runtime.

## Comments

--- 2026-11-06 16:19 ---
The promoted public-fixture baseline has fourteen behavior failures and eighteen
passing controls after correcting the retained-play fixture signature. Twelve
failures cover end-line safety behavior through direct, normal and retained-play
paths on both possession sides; two expose retained-play INT depth as gain.
The focused interception/return/box-score run passes 360 cases after correction.
No existing expectation or skip changes. The saved rules receipt and baseline/
focused logs remain ignored under release-readiness/return-model-resolution-01.
This is local implementation evidence, not source-model acceptance or release
readiness. Review of resolved tickets found no new full-game evidence authorizing
closure of this or unrelated issues.
