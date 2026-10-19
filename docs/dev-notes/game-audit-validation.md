# Eight-finding game audit repair: validation record

Developer working record, **implemented but uncommitted**, 2026-10-19. Not a release
promise. See the [issue tracker](issue-tracker.md) and
[semantic audit guide](../ai-auditing.md#semantic-checks-and-coverage).
Private charts and original narrative logs remain local; none are reproduced here.

## Scope and baseline

The eight findings are AI-014, STAT-002, AUD-009 through AUD-013, and AUD-002.
The correct BLACK lookup/priority behavior and existing rushing/passing accounting
were not changed. Earlier uncommitted presentation repairs remain intact. No
standings, commit, tag, push, or release changes were made.

Tests preceded production changes:

- Scoring/decision baseline: **44 expected failures, 32 passing controls**. Real
  enforcement tests catch opponent TDs preserved by declining a replay penalty;
  pending goal-line gains must advertise the provisional TD before choosing.
  Inverse offensive/defensive-score decisions keep CPU scores. Conversion cases
  catch PAT points allocated to the next quarter; QB-time cases catch pass prose
  despite correctly credited rushing stats.
- Presentation/full-loop baseline: **38 expected failures, 96 passing controls**.
  These cover ordinary fumble-recovery wording, incomplete labels, duplicate PI
  and turnover announcements, and non-scoring breakaway promises.
- Additional controls cover special-teams scoring-side flags, public save/resume,
  failed PATs, untimed scoring, kickoff/halftime/endgame availability, no-try OT,
  core receiver-selection RNG compatibility, and actual synthetic offense-nine
  plus defense-BLACK resolution through penalty rerolls. Two-point controls test
  period logging with a resolved try, not the complete two-point play mechanics.
- New test setup errors were corrected, not counted as product failures: a missing
  required defense field; omitted initial possession; nonexistent attempt-stat
  fields; and expecting no kickoff after Q1/Q3 rather than only halftime/endgame.
  A post-try save control completes setup for kickoff before saving, matching
  the supported scoring-sequence lifecycle. This does not certify arbitrary
  mid-try saves; a raw end-zone position still reconstructs a pending score.

## Explicit changes to existing test expectations

- The complete new/resumed CLI turnover test now requires **exactly one** final
  banner for a real failed fourth down, rather than merely its presence.
  Accepted/offsetting replay controls still require no banner. The previous check
  missed the duplicate from the caller.
- The positive-breakaway commentary test now requires the stated 25-yard gain and
  forbids touchdown promises instead of requiring one of five old phrases that
  included nobody-catching-him language. Exhaustive deterministic template controls
  supplement, rather than rely on, its repeated random samples.
- No historical seed, game count, score expectation, untimed-event requirement,
  existing skip, or gameplay assertion was relaxed in this repair. Earlier local
  cleanup expectation changes remain documented separately in the tracker.

## Semantic audit validation

The existing audit runner now checks scorer-aware penalty choices and resolved QB
scramble narration/stat deltas/scoring team. It also checks incomplete yardage,
ordinary scrimmage fumble-at-spot wording, and conversion period ownership. It
reports counts and unexercised events separately from game/accounting completion.
Injected wrong scoring periods, pass narratives, passing-stat attribution, and
scoring teams fail deterministic audit-helper tests. Read-only/RNG controls pass.

Initial local semantic runs exposed **checker scope errors**, not new game defects:

1. First run: 380/448 passed; the scrimmage wording oracle wrongly included punt
   return fumbles. Synthetic special-teams controls reproduced this false alarm
   before narrowing the oracle to scrimmage calls.
2. Next run: 444/448 passed; four safety results were incorrectly required to use
   ordinary non-scoring recovery wording. A synthetic safety control failed before
   excluding scoring safeties from that specific wording oracle. Existing safety
   outcome/scoring tests remain unchanged.
3. Final run: **448/448 passed**, including the added scramble-stat/scorer checks.
   Failed-run summaries remain in ignored local reports. Checker exceptions are
   not silently classified as gameplay failures or hidden with skipped tests.

## Final regression results

- Core: **5,075 passed, eight existing skips, 75% coverage**.
- Backend: **191 passed**; frontend: **250 passed, one existing skip**; build passed.
- Real-engine browser suite passed both home/receiving and away/kicking complete
  games, clean new-game state, and offline help. Final guide/lint checks are also
  run after documentation edits.
- Source-only snapshot: **5,058 core passed, 25 existing skips**, **191 backend
  passed**. Only tracked public 2026 season files and proposed test additions were
  copied; no ignored historical charts, standings, or local audit reports.
- Integration: **14 standalone games**, **nine historical reproductions**,
  **224 generated regular-season games**, and **nine playoffs** passed. No tied
  playoff final. All previous historical event requirements remain intact.
- AI audits: public **32/32 games, 3,818 calls**; local **448/448 games, 52,686 calls**.
  Every call/result/situation total reconciles; **22,901** recorded probability
  vectors are normalized and contain the selected play.
- Public semantic coverage: one scoring penalty choice, **zero** scramble TDs,
  481 incompletes, 13 ordinary fumble recoveries at spot. Zero scramble coverage
  is explicit, not a claim the random batch exercised it.
- Local semantic coverage: **255** scoring penalty choices, **19** scramble TDs
  with matching rushing/scorer deltas, 6,260 incompletes, 732 ordinary recoveries.
  Deterministic synthetic/public cases provide mandatory missing-event coverage.

Existing skips and warnings remain disclosed: historical-fixture unit-test debt,
Pydantic deprecations, top-level Ruff configuration deprecation,
outdated Browserslist, and the existing frontend skip. No new skips were added.

## Concentration advisories and limits

Reviewed all three local ordinary-group advisories with counts, alternatives,
comparable-situation streaks, and chart strengths; none is a universal frequency cap.
Detailed private-derived diagnostics stay in ignored local reports.

- Two balanced-policy third-and-11+ groups: 32/42 calls, three distinct calls,
  largest share 50%, longest comparable streak three/two. Long passing is a strong
  conditional chart alternative, but the small samples and the legacy policy's
  limited alternatives still warrant monitoring, not a claim of optimal play.
- One Hard second-and-11+ group: 32 calls, eight distinct calls, medium pass 50%,
  longest comparable streak two. Medium passing is among the stronger primary
  conditional-yardage calls; per-call medium weights ranged 5.9–37.0% (mean 25.5%)
  with seven to nine eligible calls. Observed concentration exceeds average policy
  weight in this small sample; retain it for follow-up rather than changing tests
  or imposing a cap. Chart summaries exclude important outcomes and are not
  defense-specific conversion odds.

A passing season is **not** a comprehensive coaching/narrative audit. Selected-call
observations omit subsequent kickoff chains; deterministic CLI tests own final
announcement counts. Player identity, all action/stat combinations, broad penalty
valuation, full two-point mechanics, and replay-trace completeness are not certified
by these checks. STAT-001, AI-001/002, AI-013 and TRACE work remain separate. The CPU
penalty correction intentionally changes future seeded trajectories; presentation
repairs preserve gameplay RNG, including the legacy core receiver-name draw.
