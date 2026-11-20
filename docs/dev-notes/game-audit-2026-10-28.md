# Supplied-game audit — 2026-10-28

**Developer investigation, not implemented changes or player guidance.**

## Evidence and limits

Reviewed a user-supplied local game log, including decisions, penalties,
halftime, final statistics and AI analysis. The log does not identify its
build/commit or RNG state. Current source
inspection and synthetic probes corroborate causes but are not a claim
of exact deterministic replay. The source log and historical charts stay
local; this note includes no raw narrative or private chart cells. No
gameplay fix, standings write, push, tag or release was performed.

## Reconciliation

- Score changes, both period-score tables and scoring entries agree.
- Human yardage: 263 = 21 rushing + 242 passing. CPU: 230 = 89 + 141.
- Human/CPU turnovers: 1/2; interception and lost-fumble subtotals agree
  with the visible events. No sacks were recorded.
- Enforced penalties: human 4/47 yards; CPU 4/35 yards. Declined and
  offsetting penalties do not inflate these totals.
- Learning: 56 human run/pass calls = 16 runs + 40 passes; the one FG
  and three punts are excluded. Overall learning counts are correct.
- CPU run/pass calls: 47, all nine primary choices represented; the
  largest share is 10/47 (21.3%). This single game does not show a
  dominant offensive-call problem or establish a human win-rate estimate.
- Opening/second-half receiving order is consistent. No crash or
  contradictory possession announcement was found.

## Findings for a decision, not automatic fixes

| Ticket | Priority | Finding | Assessment |
| --- | --- | --- | --- |
| [AI-019](https://github.com/rtulloh/paydirt/issues/21) | Medium | Every late-Q4 model defense is E; the model branch precedes situational policies. | Existing ticket updated. Six selections include one punt; determinism/bypass confirmed, not that every call was wrong. |
| [AI-012](https://github.com/rtulloh/paydirt/issues/14) | Medium | Third-and-27 Line Plunge while protecting an 11-point lead with over nine minutes left. | Existing review case updated, not a proven bad decision. The call ranks fourth of nine in the bounded chart-only utility; conservative strategy and unresolved outcomes matter. |
| [TRACE-003](https://github.com/rtulloh/paydirt/issues/209) | Medium | Called modifiers are absent from compact call echoes. | Existing ticket updated; effects alone cannot recover the original request. |
| [TRACE-004](https://github.com/rtulloh/paydirt/issues/210) | Medium | Offsetting scrimmage penalties omit their rolls/foul sequence. | Existing issue newly observed; ten-second replay and down/spot are otherwise consistent. |
| [AI-007](https://github.com/rtulloh/paydirt/issues/9) | Low/deferred | Incompletions consume 40 seconds at Q4 2:00 and 26 seconds at Q4 0:28. | Current code applies the generic 25-45-second timer to incompletions too. This explains the observations but does not establish conformity with the official Timing Chart. |
| [AUD-023](https://github.com/rtulloh/paydirt/issues/60) | Low | Startup repeats identical team-name/nickname components. | New ticket, confirmed with a synthetic 2026 object. |
| [AUD-024](https://github.com/rtulloh/paydirt/issues/61) | Low | Tendency summary prints exact-looking distances for aggregated bands. | New ticket. Four third-and-4-6 calls are printed as third-and-5 although only two were exact third-and-5. |
| [TRACE-009](https://github.com/rtulloh/paydirt/issues/215) | Medium/investigating | TD from Q2 0:45, try and kickoff recovery are followed by halftime without intermediate clock charges. | New dedicated issue. A lost snap is unproven: current TD/kickoff ranges can exhaust 45 seconds or leave time, and actual draws are missing. |
| [DATA-002](https://github.com/rtulloh/paydirt/issues/70) | Low | A player who died before the season appears in the installed historical commentary roster. | New dedicated issue. Local data provenance and public historical fact verified; the private roster is untouched. |

For the user's four follow-up findings, the dedicated open records are
AI-007 (incomplete timing), TRACE-009 (halftime clock ambiguity), DATA-002
(historical roster mismatch), and AUD-023 (duplicate headings). Clock
review should establish authoritative timing rules and expose applied
elapsed-time evidence before changing behavior. AI-019 remains a separate
coaching priority. No new High-priority gameplay defect is established.

## Resolved-ticket review

Issue-specific full-game evidence supports closing:

- **AI-010:** learning excludes the four special-team choices.
- **AUD-004:** seven goal-to-go headers have one position separator.
- **AUD-010:** ordinary own-recovery text separates pre-fumble yards,
  recovery at spot and net gain without inventing an extra advance.
- **AUD-012:** accepted PI has one automatic-first-down announcement.
- **AUD-013:** incomplete penalty previews/menus/results are explicit,
  while true zero-yard plays still say No gain.
- **STAT-002:** the Q1-ending TD/PAT is assigned wholly to Q1 in both
  period tables and the scoring summary.

Partial evidence only: AUD-011 confirms new-game but not resumed-game
turnover-on-downs announcements; RULE-014 confirms an ordinary lost kickoff
fumble but not its remaining chained/choice variants; RULE-017 sees only
a non-advance first-down control, not the reported mid-series defect.
Those remain resolved, not closed. Other resolved conversion, return-chain,
spike and end-of-half tickets lack their defining event in this game;
a complete game is not sufficient evidence for closing them.
