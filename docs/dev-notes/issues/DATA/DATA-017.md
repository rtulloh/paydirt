---
id: DATA-017
title: Public play-by-play classification totals disagree with official source counts
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
tags:
  - reproduced
  - chart-audit
---

## Description

Independent regeneration reproduces all 180 promoted CSVs, but extraction
facts disagree with official aggregate statistics. The 1983 manifest records
629 interceptions versus 620, 1,207 sacks versus 1,215, and 775 field-goal
attempts versus 771. The 2024 manifest records 1,306 sacks versus 1,314.
The 1983 FGA excess is one each for Bears, Cardinals, Dolphins and Rams; these
classified attempts are consumed by calibration inputs. No reviewed exclusion
or duplicate-event reconciliation has been established.

[Source audit evidence](../../generated-source-consistency-audit.md). Reviewed
public contracts make these disagreements blocking findings rather than
silently claiming source fidelity from reproducibility.

## Resolution / verification

Trace counted, nullified, repeated and unattributed plays using public source
records. Establish documented reconciliations or fix adapters test-first using
synthetic source rows. Recompute normalized totals, reviewed contracts and
charts from source/profile, then rerun source and current-engine gates. Do not
change official targets to match faulty extraction.

## Comments

--- 2026-11-05 16:35 ---
Opened from the user-requested generated-chart accuracy and release-gate audit.
The gate records the defect; no production/chart-data correction or push occurred.

--- 2026-11-05 21:46 ---
The official December 11 Denver gamebook independently identifies the missing
credited sack as the own-recovered snap fumble at source play 167 (pages 3/9).
A generic optional source-fact input binds unchanged raw HTML/play hashes and
reviewed document/page identities; it does not hard-code a team, revise targets
or turn credited loss into physical initial F severity. The fresh 224-game
classification totals are 1,215 sacks, 620 interceptions and 771 FG attempts.
The added event has unknown physical initial gain, remains without a fabricated
QT sample, and retains a passing fumble recovered by its own team. There are
now twelve unknown-severity sack occurrences and 39 unresolved recoveries; source
chart generation/acceptance remains blocked pending those required recovery facts.
Do not close from occurrence reconciliation alone; fresh candidates and all
source/mechanics/engine acceptance remain outstanding.

--- 2026-11-05 22:26 ---
The reviewed 224-game source ledger now reproduces with zero unknown recoveries
and zero missing required completion/run gains. All 28 team sack/INT/FGA totals
remain correct. The latest source checkpoint passes 7,366 root tests/eight
existing skips/82% coverage. This is not candidate acceptance: 25 sacks have
unknown physical severity, F conditional limitations remain, and neutral-profile
chart regeneration stops at a pressure feasibility failure. Keep open.
