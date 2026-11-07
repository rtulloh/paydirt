# Two-point conversion completion investigation

Implementation and validation notes for [RULE-001](issues/RULE/RULE-001.md),
[STAT-003](issues/STAT/STAT-003.md), [FLOW-018](issues/FLOW/FLOW-018.md), and
linked [RULE-007](issues/RULE/RULE-007.md). This is developer evidence, not
release qualification. No push, tag, or release is authorized.

The engine resolves the actual chart and return chain on an isolated conversion
state. Only the final two-point score and explicit zero-charge clock trace reach
the live game. The original state/statistics objects, possession, geometry,
periods, warnings, overtime state and ordinary play/call histories stay intact.
Exceptions cannot leave live state at the try spot. The try score receives its
preceding touchdown's explicit period/time context; PAT kicks use that context
as well. AI-022's separate conversion observation and selectors remain intact.

The API publishes explicit conversion success and defensive points. Its response
uses the engine's resulting kickoff/final phase. The browser retains season
eligibility through update/start/load and displays explicit success rather than
parsing GOOD from a description that can contain NO GOOD.

Test-first receipts in ignored `.ai-audits/two-point-completion-01/`: engine
22 expected failures and one passing ordinary-touchdown control; API 12 expected
failures and one passing season-prohibition control; UI one expected failed-try
display failure and nine passing controls. Extra API result-field regressions
fail before those fields are added. No historical chart fixtures were used.

The existing retained-fumble/incompletion conversion regression formerly
required its result in the ordinary play log. That expectation was wrong under
STAT-003: it now requires an empty ordinary log/history and zero charged time.
Dedicated resolver regressions still verify the retained incompletion subtype.
Additional fumble scenarios initially used unsupported `F 2` notation; the
fixture was corrected to canonical `F+2`, `F+0`, and `F-100` before validation.
No production behavior was changed to accept the invalid fixture notation.

Current focused checks: 410 core regressions (including nine additional fumble/
late-exception controls), 27 API cases, and ten frontend cases pass. Full backend
411 and frontend 345 pass. Five actual-engine browser cases cover success and
failure from either human side plus stale eligibility clearing. Four additional
compiled-build cases confirm exact scores, zero time/accounting/history changes,
correct kickoff receiver, both timeout counts and no page errors at independent
review service `http://127.0.0.1:8157` (original owner services are preserved).
Four more compiled-build cases at Q4 0:00 confirm the final screen, exact score,
zero accounting/time changes and no kickoff for either human side. The required
complete browser suite passes all eighteen cases, including both complete real
games, halftime, final screens and clean new-game state. The clean public,
tracked-source snapshot passes all 10,166 core, 411 backend and 345 frontend
tests without ignored private data.

The completion audit added ten actual API cases for halftime success/failure/
defensive return and normal/final-0:00 defensive-return routing, from either human
side. All ten fail against the saved old engine for the expected extra touchdown,
clock charge or wrong-team defensive score, while the season-prohibition control
passes. All ten pass with the repair, including the second-half kicker/receiver
and explicit touchdown-period attribution. No further production change was
needed. The isolated baseline loader forwards return-dice calls to the patched
canonical module so the old and current engines receive the same return roll.

A backend rerun exposed an existing random-fixture failure in
`test_no_huddle_persistence_across_plays`: an interception with a pending penalty
made its second execute request illegal. Its failed receipt is retained. The
test now uses synthetic public-team midfield/chart controls, retains both HTTP
200 assertions and adds actual engine-call flags `[True, False]`, two recorded
plays and exact field progress. This strengthens its intended per-play huddle
check without changing production code, weakening expectations or adding skips.

Standalone integration passes all 14 matchups. The actual 1983 season passes
224 regular games, nine postseason games with no tied finals, and all sixteen
available historical reproductions. Public/local AI audits pass 32/32 and 448/448;
all 4,878/65,212 calls and 217/3,181 groups reconcile. AI-009 records the three
legacy-balanced advisories and resolved-ticket review. Source charts/private
narratives remain local and ignored.

The two required generated-chart audit commands currently fail their explicit
source-preparation prerequisite before simulation. Their receipts are failures,
not skips or qualifications; existing freezes/contracts/bindings remain intact.
Supplementary current-engine diagnostics complete 14,336/14,336 games for 1983
and 17,408/17,408 for 2024 but fail historical fit with 46 and 71 metric errors
respectively. Both are explicitly uncertified. An independently seeded full
schedule comparison against the saved old engine yields identical gameplay,
scores, statistics and selected calls for both seasons, with zero two-point
attempts in either runtime. These chart-fit residuals are not evidence of a
conversion regression or an effect of this repair.

The required main core coverage run passes all 10,166 tests, with 85% total
coverage and 93% engine coverage. Every mandatory command has run; full regression
is not green because both chart source gates fail. Existing warnings include
twenty-one backend Pydantic deprecations (twenty in the clean snapshot), stale
Browserslist data, browser color-
environment notices and seventeen npm dependency-audit findings in the clean
snapshot (one low, five moderate, eight high and three critical). No tests were
skipped. Tickets remain open while the fix is uncommitted; committed-fix and
play-test status must be recorded
separately. Earlier chart qualification receipts retain their original engine
identity and are not new-code evidence.
