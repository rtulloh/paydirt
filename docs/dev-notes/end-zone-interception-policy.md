# Own-end-zone interception return preference

Implementation and qualification notes for [RULE-030](https://github.com/rtulloh/paydirt/issues/193).
The official rulebook's VI-12-E/F distinguishes catch geometry from the
coach's own-end-zone choice. Both the implementation worker and owner reviewed
the complete saved page independently. The source PDF and scan identities
remain in ignored release-readiness evidence.

The engine defaults argument-free callers to automatic touchback. The browser
game always asks the human at game time and has no pre-game return setting; the
CPU decides at the same point with the situation policy. Engine/audit callers may
still declare `return` or `touchback` for controlled runs, and legacy boolean
preferences keep that meaning. Core saves retain any unresolved pending decision.
Absent legacy save keys still default to false/automatic touchback.

For the human, the engine records the catch geometry and score/clock, then returns
`pending_end_zone_interception_return_decision` without changing possession,
stats or the clock and without rolling return dice. `apply_end_zone_interception_return_decision`
resolves it exactly once. Requested spikes and defensive timeouts survive the
pause. The CPU uses the same depth/score/clock policy as CLI and web; it never
inspects return dice.

An interception at or beyond the defender's end line is first marked nine
yards deep under E-i. A return counts all depth; failing to cross the goal
line is a touchback. Shared return rolls retain fumble recovery, foul rerolls,
offsetting replay and scoring behavior. A fumble reaching the returner's own
end line is out of play before recovery dice. The offense's raw end-line
lateral/safety and a catch in the offense's live end zone retain their separate
existing boundaries.

Synthetic/public-2026 tests cover both possession sides, normal and retained
play paths, default controls, goal/end-line geometry, failed escapes,
touchdowns, kept/lost live end-zone fumbles, out-of-play fumbles, fouls,
offsetting replay, cached returns, API role mapping and legacy save defaults.
FLOW-023 adds goal-line, one-yard-deep and deep pending decisions, leading and
trailing auto-policy cases, unaffected field interceptions, single-resolution
accounting, preserved spike requests and pending save/RNG round trips. No
historical data is used in collected tests. The new behavior changes runtime
identity, so prior campaign receipts cannot qualify the changed runtime.

This restores representability, not empirical source acceptance. Observed
end-zone returns can be legal under the elective return rule; their presence
alone does not identify a historical coach's choice or qualifying recovery
dice. Zero-gain/touchback outcomes do not distinguish election from failed
escape. Unknown conditional ordinary gains, tails, losses and recovery
entitlements remain unknown. Existing model/source holds and gates remain.


The resolved `ReturnChain` is an optional typed field on `PlayResult`, retained
with the in-memory penalty result. Reapplying it preserves possession,
accepted fouls and lost-fumble counters instead of treating a net yard count as
the complete play. Numeric-only cached results remain compatible, including
zero yards with populated return dice. Tests restore the pre-play state twice
and reapply the same chain without mutating it or accumulating counters.

Existing core saves now serialize an unresolved interception decision as the
play data plus the dice RNG state captured at deferral. Loading restores both, so
the return roll matches the uninterrupted game; resolving it does not duplicate
dice, turnovers, clock changes or statistics. Browser replays still serialize
visible game state rather than unresolved choices and the UI disables replay
saves while a decision is pending. The live pending API response and save
response remain JSON serializable, and the original pending choice retains its
typed chain for live resolution.

Five existing blocked-kick/snap safety parameter cases formerly supplied a
recovery roll after `F -100` crossed the own end line. Their dice lists now
end at that out-of-play fumble, under VI-12-D-iii/F-ii. All scoring, possession,
spot and narration assertions remain. The backend modifier fixture now uses a
fixed public-team kickoff roll because random kickoff fouls/turnovers could
leave its required human-offense setup incomplete; its offense assertion stays.

The maintained audit now accepts `--attempt-end-zone-interception-returns` to
declare attempts for both physical teams; its default remains automatic
touchback. Worker task/result identity, report metadata and per-game preferences
bind the option. Saved report reuse requires the requested mode to match.
The modern ordered generator separately accepts `--fumble-range-policy` with
`measured_diagnostic_v1` (existing default) or `source_primary_v1`. The latter
uses corrected primary source recovery counts without the measured override;
both modes still validate the complete exposure and measured-range receipt.
The joint ledger and manifest bind the selection and actual applied pairs.
These options do not settle unknown source conditional targets or accept the
historical 173 class, four snap/recovery and three association holds, plus
Morgan's separately missing occurrence. The parent agent performs final
integrated and frozen-candidate qualification; the human owner receives the
compact visual review and release decision.
