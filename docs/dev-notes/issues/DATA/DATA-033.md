---
id: DATA-033
title: Return-penalty modifiers lack an explicit consumer interpretation
status: closed
priority: Medium
created-at: 2026-11-06
resolved-at: 2026-11-06
closed-at: 2026-11-06
tags:
  - investigating
  - chart-audit
links:
  - RULE-027
---

## Description

The stricter raw decoder census finds `DEF 15X` in three current public generated
1983 punt-return charts: Bengals, Colts and Dolphins. The physical chart masses
are respectively 4/216, 5/216 and 8/216. The shared return consumer reads the
numeric penalty but does not preserve the first-down modifier. Generic generator
grammar accepts that syntax; acceptance alone does not verify its semantics.

This is an interpretation/coverage finding, not yet proof of a wrong final
ordinary punt-return state. A new possession already starts a new series, which
can make an automatic-first-down flag redundant. Own-fumble advances and chained
returns need separate analysis before calling the flag harmless or changing
generation. The same audit distinguishes numeric penalties from S/R penalty
table tokens that these special consumers do not resolve.

## Resolution / verification

Establish the supported return-marker semantics and relevant retained/nullified
contexts with synthetic controls before any behavior change. Do not remove the
flag, relax the decoder or declare historical accuracy merely to turn the three
diagnostics green. Preserve the current raw results, their hashes and weighted
mass in ignored chart-confidence evidence. No reference corpus was opened.

## Comments

--- 2026-11-06 01:35 ---
The public candidate census covers every physical column for all 60 teams.
Twenty-five 1983 teams and all 32 2024 teams have no raw decoder errors; the
three return modifiers remain explicit failures pending interpretation. The
decoder's broader consumer controls first fail 12 cases, then pass 73 tests.
Two additional edge regressions expose an undisclosed blank default and numeric
overflow, followed by 75 focused passes after correction. These checks do not
establish the full weighted/stateful reference benchmark or release readiness.

--- 2026-11-06 01:56 ---
The census is now enforced inside the existing generated-source component and
required by the combined gate. Five expected assertions fail before integration,
with two passing controls: unsupported kickoff/return tokens previously pass
source validation, and a source pass without any decoder evidence reaches the
combined gate. The QT fallback already fails structural validation; its added
control requires an explicit decoder finding too. All 158 affected source,
decoder and gate tests then pass. Positive synthetic gate fixtures now include
the required decoder check; no existing assertion is weakened. Current three
`X` findings remain failures pending interpretation, not exceptions or edited
chart cells. No private/reference or reserved-seed corpus was opened.

--- 2026-11-06 02:06 ---
Context analysis distinguishes the columns. A real kickoff/punt return always
starts a new series, including the tested retained/lost fumble chains. Ninety-six
synthetic engine controls pass for both teams, second/fourth down, numeric/own/
lost/nested return outcomes and defensive modifiers. Six new census assertions
fail first because these legitimate new-series modifiers lack an explicit
category. The census now records their exact mass separately; chart bytes are
unchanged. A replay of 44 complete training games involving the three affected
teams observes four natural modified returns, all with correctly assessed yards
and a new first down. These repeat training seeds, not independent exposure.
The Bengals' modifier cell is not naturally encountered in this subset.

The shared interception-return column has a real additional defect: an own
fumble advance retains the original series, but accepted defensive first-down
rights disappear. A synthetic second-down call becomes third down; the analogous
fourth-down call incorrectly loses possession. The [reprinted rulebook](https://www.rulespal.com/paydirt/rulebook),
VI-4(C) and VI-10, supports keeping the penalty's automatic first down while
resolving an own recovery. This is a rules-state issue, separate from DATA-030's
pending yardage-credit design.

Corrected test-first fixtures show 60 behavior failures and 87 passing controls.
The first new fixture incorrectly assumed both entry points roll recovery in the
engine; the penalty-procedure entry point predetermines it in the resolver. That
fixture is corrected without changing an existing test. Added gate/decoder and
explicit-marker controls then show 81 expected failures and 247 passing controls.
The shared-column marker checks now require support after the core fix; the
unsupported-token mutants use return-table codes instead, preserving rejection
assertions. No modifier is removed from a generated chart or accepted without
stateful evidence. Keep this issue open through correction and current-runtime
play confirmation.

Separately, four FG table-penalty controls expose a known five-yard placeholder
instead of table resolution. The raw census now discloses that limitation and
blocks a generated-source pass for it. There are zero such cells in the current
60 public candidates. After those decoder changes, all 240 affected checks pass;
new own-fumble first-down regressions remain red pending their production fix.

--- 2026-11-06 02:14 ---
The core fix now retains first-down rights beside each accepted return penalty,
including live/nested fumble settlement and the punt double-foul consumer. It
reuses the existing penalty-option parser and does not change the pending
physical/credited fumble-yardage design. The original behavior baseline is
60 failures/87 controls; the expanded gate/decoder/explicit-marker baseline is
81 failures/247 controls. Three further integration controls fail first because
punt double-foul handling hardcodes the return's first-down right to false.

All 1,063 affected gameplay, return-chain, punt, decoder and gate tests then pass.
The one deliberate unreadable-token warning in that run is now explicitly
asserted by its negative fixture; its three source controls pass with no
unexpected warning. The existing gate-census expectation changes from 18 to 22
for four new rushing/punt own-recovery controls. An erased-rights mutant fails.
The formerly unsupported defensive-marker fixtures now require support because
that behavior is implemented and tested; return-table tokens remain rejection
controls. No prior behavioral assertion or skip is weakened.

Fresh runtime `871af55a…` completes all 224/272 training games with 34/48 retained
punt snap fumbles and reconciled accounting. This repeats the development seed
and remains one repetition per cohort, below final exposure. Backend tests pass
322 with 21 existing Pydantic deprecation warnings. The full core run of 8,110
passes/eight existing skips completed before this new first-down fix; it cannot
certify this runtime. RULE-027 separately records remaining same-team cross-
chart choices and offset timing/replay metadata. Keep this issue open through
those combination checks and issue-specific current full-game confirmation.

--- 2026-11-06 02:38 ---
At runtime `671f712b…`, the full-game punt-foul review confirms four ordinary same-team return-foul assessments and ten genuine ten-second replay outcomes. These are combination controls; they do not supply a decisive own-recovery-short-of-the-sticks automatic-first-down example. The core checkpoint passes 8,405/eight existing skips, with 26 conformance controls. Keep open through that specific full-game confirmation and the remaining RULE-027/DATA-034 combinations; source/decoder passes alone are insufficient.

--- 2026-11-06 03:43 ---
The fixed 64-schedule development census at `f0cfc25a…` completes all 31,744
games with reconciled accounting and no findings. Its 8,416 observed own-fumble
advances include four retained advances short of the sticks with accepted
first-down rights. Two are decisive second-down cases: Chargers/Patriots seed
62352044 starts 2nd-and-17 at 44, fumbles five yards back and finishes at 54 with
1st-and-10; Giants/Commanders seed 42287408 starts 2nd-and-nine at 29, fumbles
twelve yards back and finishes at 32 with 1st-and-10. Both retain possession,
record exactly one first down and preserve the accepted fifteen-yard foul. The
other two first-down-call cases are passing controls, not proof of down reset.
The observer wrappers add no dice, choices or state changes; the first 496 games
match uninstrumented receipts exactly. This is targeted play-test evidence, not
final source-fit or unwrapped worker attestation. Complete core validation at that
runtime passed 8,873/eight existing skips. DATA-034's combination scope is closed;
RULE-027 retains a separate legacy-policy question. Close this issue's modifier/
own-recovery-rights scope on the decisive full-game proof. Fixes remain local and
uncommitted. DATA-030 and the newly confirmed DATA-035 source attribution defect
remain open; no source-credit model or release acceptance is approved.
