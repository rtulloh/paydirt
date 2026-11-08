# Developer Notes

**These notes are for the developer only. They are not end-user documentation.**

This folder contains experiments, investigations, debugging observations, and
proposed designs. Notes may be incomplete, historical, superseded, or describe
work that has not been implemented. They are not a specification of current
behavior, a supported workflow, or a commitment to deliver a feature. Verify
claims against the current code and tests before relying on them.

For installation, gameplay, supported features, and maintained reference guides,
use the [documentation index](../README.md).

## Notes

- [Issue tracker](issue-tracker.md): priorities, current status, and resolution/verification history.
- [v1.10.2 scope and verification](release-1.10.2-scope.md): interception-location audit, fourth-down urgency, faster tests and reliable release publication.
- [v1.10.3 simulation-improvement plan](release-1.10.3-plan.md): AI-026 scope, controlled paired-season experiments, and outcome exit criteria after 1.10.2.
- [AI play-testing](ai-playtesting.md)
- [Chart generator tuning tool](chart-generator-tuning-tool.md): reproducible engine calibration workflow and sample-size guidance.
- [Statistical Paydirt chart generator](statistical-chart-generator.md): investigation,
  probability model, 1983 validation, limitations, and recommended multi-seed analysis.
- [Replayable game logs](replayable-game-logs.md)
- [Punt return-chain commentary](punt-return-commentary.md): separate first-return yardage, fumble recovery, and the final scoring/possession narrative.
- [Eight-finding game audit validation](game-audit-validation.md): uncommitted fixes, test-first evidence, semantic coverage, and remaining limits.
- [Chart-confidence charter](chart-confidence-agent-charter.md) and [implementation evidence](chart-confidence-implementation.md): active acceptance contract and recorded checkpoints; release held.
- [Fumble source-credit experiment](fumble-source-credit-proposal.md): opt-in credited-yard proxy implementation, nullable physical facts and outstanding source/fit evidence.
- [Source and representation review decisions](chart-source-model-review-decisions.md): bounded source-tier proxy experiment, retained-fumble/incompletion semantics and remaining shared-return model review.
- [Historical source completion boundary](historical-source-completion-boundary.md): owned zero-credit snap implementation, complete-census hold and proposed missing-data decision.
- [Public-only unit fixture cleanup](public-unit-fixture-cleanup.md): restored historical-independent loader, discovery, roster and season-rule checks, with changed expectations and clean-snapshot evidence.
- [November 6 chart release preparation](chart-release-preparation-2026-11-06.md): component regression checkpoints, restored frontend coverage and remaining final-candidate requirements.
- [Retained fumble followed by incompletion](retained-fumble-incompletion-engine.md): implemented primary passing subtype, penalty lifetime, typed observer interface and test-first evidence.
- [Compound-fumble source reconciliation](compound-fumble-source-reconciliation.md): official event ownership evidence, current rejection boundary and unresolved chart projection.
- [Source-driven gain proposal](source-driven-gain-normalization-proposal.md): unwired, synthetic-tested cohort math and ordinary-gain components; complete training recipe and real fitting remain unimplemented/unaccepted.
- [Compound-fumble projection proposal](compound-fumble-projection-proposal.md): unimplemented event ownership, conditional return exposure and shared-chart assumptions for parent review.
- [Game-to-season qualification plan](game-to-season-qualification-plan.md): staged game accounting, source-year season/postseason checks and unopened repeated-season study.
- [Hard AI chart-response baseline](hard-ai-chart-response-baseline.md): controlled own/opponent chart probes, verified data flow and unimplemented correction questions.
- [Formation risk census](formation-risk-census.md): all-60 exact priority/secondary diagnostics, stateful controls and explicit terminal-risk limits.
- [General chart placement audit](general-chart-placement-audit.md): all-result clustering across 60 displayed teams and a separate diagnostic, exact relocation witnesses and protected-table limits.
- [Exact-mass primary allocation](exact-mass-primary-allocation.md): local DATA-041 correction, viewer-color objective, bounded witnesses and pending all-team qualification.
- [End-zone interception preference](end-zone-interception-policy.md): implemented per-team coaching choice, return-chain replay evidence and separate source qualification holds.
- [Generated defense pattern census](generated-defense-pattern-census.md): all-cell repetition and weighted engine checks across current teams, separate candidates and generated artifacts; interception stripes and fixed depth support remain explicit.

## Adding Notes

Create all future development notes **only in this folder**, and link them here.
State their status and distinguish observations and proposals from implemented
behavior. Update the canonical guides when a change becomes supported; do not
make users depend on development notes. Never include private charts, workbooks,
or historical game logs.

- [Generated chart completeness audit](generated-chart-completeness-audit.md): systematic feature review, fixes, source omissions, and matched engine evidence.
- [November 2 manual game audit](game-audit-2026-11-02.md): reconciled generated-chart game statistics, clock and era-rule findings, and ticket review.
- [November 6 web game audit](game-audit-2026-11-06.md): confirmed CPU timeout use, reproduced endgame coaching concerns, and save/resume evidence limits.
- [November 2 release readiness](release-readiness-2026-11-02.md): test-first fixes, remaining investigations and pre-push evidence.
