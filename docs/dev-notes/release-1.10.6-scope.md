# Release 1.10.6 scope discussion

Planning record, 2026-11-11. This is a proposed scope, not a claim that changes are implemented or qualified.

## Selected work

- [FLOW-023](issues/FLOW/FLOW-023.md): choose an end-zone interception return during play, after catch location is known and before return dice.
- [DATA-048](issues/DATA/DATA-048.md): move fictional teams from `seasons/2026` to `seasons/sample`; exclude samples from season play while preserving explicit demo/test access and existing saves.
- [AI-024](issues/AI/AI-024.md): use engine-derived field-goal make probabilities from the actual kicking chart, combined with game situation and season aggression. Preserve urgent scoring decisions and validate against the released baseline.
- [FLOW-007](issues/FLOW/FLOW-007.md): share engine-driven modifier messages between new and resumed CLI games; test applied/skipped spikes and timeouts. Reproduce other reported loop differences before fixing them; a wholesale loop merge is not required.
- [AI-002](issues/AI/AI-002.md): compare engine-projected penalty outcomes from the defense's perspective, including actual enforcement, down/distance, score, clock and timeout context. Test the first-and-25 versus second-and-10 case and situational exceptions; preserve AI-001's first-down comparisons. This covers the defensive subset of AI-018, not its entire remaining scope.

## Recommended additional fixes

- [AI-029](issues/AI/AI-029.md): account for remaining scoring distance and time on last-possession fourth downs.
- [RULE-011](issues/RULE/RULE-011.md): configure kickoff position by season rather than a universal constant.
- [RULE-012](issues/RULE/RULE-012.md): apply season-appropriate final-touchdown try rules.
- [AUD-016](issues/AUD/AUD-016.md): reproduce and correct away-player play-log team labels if still present.

Reproduce older findings before changing production code. Add meaningful failing synthetic/sample tests first. Resolved tracker entries require issue-specific play-test confirmation before closure.

## New season decision

The owner prefers adding the current NFL season. As of this discussion, that is the ongoing 2026 season. Decide between a clearly labeled, date-bound 2026 season-to-date snapshot and the completed 2025 season. Do not represent partial data as completed-season qualification. A snapshot requires reviewed source coverage, sample and validation policy; current complete-season gates cannot silently be waived. Keep the fictional sample set distinct from actual 2026 NFL teams.

## Release validation

Gameplay changes require reviewed paired regression evidence against the immutable released-chart baseline; the existing unchanged-gameplay route does not automatically authorize them. Preserve the exact 1977 statistical exceptions and source/reproduction requirements. Complete the repository full regression, clean tracked-only unit checks, and downloaded native-package verification for the resulting candidate.

## Additional manual-install finding

[DATA-049](issues/DATA/DATA-049.md), targeted to v1.10.6: bundle verified player rosters for 1977 and 2024. The released tree contains no roster.json files for either season; all 28 1983 teams have them. Missing files trigger generic position names in commentary. Source season-correct names and verify packaged CLI/web narration without changing gameplay probabilities or RNG.

## Existing-ticket review, 2026-11-11

AI-002 and AI-017 persist in direct synthetic decision probes; AI-002 additionally ran both resulting engine alternatives. AI-018 is partially fixed by AI-001/52dc98d: equivalent first downs use actual enforced spots. Its broader nominal-yard/down/clock evaluation remains open. FLOW-007's spike request execution was already fixed by SPIKE-002; only presentation/parity and remaining loop differences belong in new scope. FLOW-006, AI-024, AI-029, RULE-012 and AUD-016 still have the relevant code paths; this review does not newly claim full play-test reproduction for them. See timestamped per-ticket comments for evidence and limits. Existing focused penalty/spike suites: 188 passed. No production changes were made during this review.
