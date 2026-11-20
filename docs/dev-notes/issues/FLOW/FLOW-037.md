---
id: FLOW-037
title: Advance kickoff fumble-recovery touchdowns to the conversion choice
status: closed
priority: High
target-release: v1.12.0
created-at: 2026-11-19
resolved-at: 2026-11-19
closed-at: 2026-11-19
tags:
  - bug
links:
commits:
---

## Description

Owner reported a browser game becoming unresponsive after the kicking team recovered a kickoff-return fumble for a touchdown. The score updated to 9-9 at Q2 2:13, but no extra-point choice appeared. Investigate the authoritative scoring/conversion state and browser transition; do not infer game rules from the play narrative. This blocks v1.12.0 pending reproduction and confirmation.

## Resolution / verification

- Add self-contained synthetic/public-2026 regressions for kicking-team kickoff fumble touchdowns, both human roles and ordinary return controls; demonstrate expected baseline failures before fixing the responsible layer. Verify an owed conversion remains playable and save/resume preserves it, then confirm the repaired sequence in the real browser engine. Retain focused coverage and complete release regression before pushing.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 15:50 ---
The core engine correctly identifies the recovering kicker, scores the touchdown and retains its owed-try obligation. The kickoff API omitted the shared follow-up arming used by scrimmage plays and penalty decisions, leaving the UI pending-conversion flag false. Before the adapter fix, four public-2026 API cases failed on the missing flag (ordinary return touchdowns and fumble touchdowns, each human role); nine controls passed. The narrow fix uses the existing engine-driven follow-up helper. Thirteen focused API cases then passed, including checkpoint restoration, a playable extra point, and rejection of a duplicate try. Additional browser and expired-regulation checks are in progress; this issue remains open.

--- 2026-11-19 15:51 ---
The owner saved the stuck game successfully. A diagnostic confirms that the pre-fix checkpoint can retain a false UI pending-try flag while the engine still authoritatively owes a conversion; reloading the old implementation does not repair it. Acceptance therefore includes narrow canonical-restore reconciliation from the engine obligation, preserving the touchdown, score, clock, possession and statistics without replay. Negative controls must prevent inventing a conversion when none is owed.

--- 2026-11-19 15:53 ---
Verified and closed after four actual-engine Chromium play cases: human home/away, each with a newly saved touchdown and an affected older missing-flag checkpoint. Every case played the kickoff-fumble touchdown, saved through the UI, removed the old backend session, resumed into a new session, preserved the entire engine state apart from the required PAT field placement, and took the visible extra point once. No score, clock, statistics or play history was replayed. Full backend: 682 passed (525 existing dependency/deprecation warnings), routes 89% coverage with changed paths and condition branches covered. PlayingPhase focused: 110 passed, 83.24% lines/83.95% branches; ordinary returns, both scoring owners, expired-regulation tries and duplicate rejection remain covered. Core characterization: 159 passed with unchanged engine rules. Receipts remain in ignored flow037 audit logs; full release regression and exact-commit CI remain publication gates.

--- 2026-11-19 20:44 ---
The owner confirmed the actual previously affected saved game now restores its owed extra-point action after a hard browser refresh: “good news, it worked after a hard refresh of the browser, XP was the first play on restore”. This adds owner live-play evidence to the existing test-first API/UI, canonical checkpoint recovery and real-browser regressions. The confirmation establishes that the owed try became available; it does not claim a subsequent XP result or an independent re-audit of every statistic. No touchdown replay or manual score entry was requested. Public-safe receipt: ignored `.ai-audits/release-1.12.1/owner-restored-try-confirmation.json`. Downloaded-native and first-launch security acceptance remain separate release gates.

--- 2026-11-19 21:01 ---
The owner subsequently reported completing that recovered game: “completed the game, SF won20-16”. This adds actual owner play-through-to-final evidence after the owed XP became available on restore. It does not yet establish that the final was durably saved or recorded in a season; the final-save confirmation question remains pending. Public-safe receipt: ignored `.ai-audits/release-1.12.1/owner-completed-game.json`.

--- 2026-11-19 21:01 ---
The owner checked the final save status for the completed SF20–PHI16 game and reported the exact banner: “Saved in this browser · 9:00:21 PM”. This supersedes the earlier pending save-status note: the browser reported final save success to the owner. It is owner-observed UI confirmation, not an independent post-final reload or library forensic audit. Season linking and season-result recording are not asserted. The ignored `owner-completed-game.json` receipt retains the final score, banner and verification boundaries.
