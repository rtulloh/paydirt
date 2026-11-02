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
- [AI play-testing](ai-playtesting.md)
- [Chart generator tuning tool](chart-generator-tuning-tool.md): reproducible engine calibration workflow and sample-size guidance.
- [Statistical Paydirt chart generator](statistical-chart-generator.md): investigation,
  probability model, 1983 validation, limitations, and recommended multi-seed analysis.
- [Replayable game logs](replayable-game-logs.md)
- [Punt return-chain commentary](punt-return-commentary.md): separate first-return yardage, fumble recovery, and the final scoring/possession narrative.
- [Eight-finding game audit validation](game-audit-validation.md): uncommitted fixes, test-first evidence, semantic coverage, and remaining limits.

## Adding Notes

Create all future development notes **only in this folder**, and link them here.
State their status and distinguish observations and proposals from implemented
behavior. Update the canonical guides when a change becomes supported; do not
make users depend on development notes. Never include private charts, workbooks,
or historical game logs.

- [Generated chart completeness audit](generated-chart-completeness-audit.md): systematic feature review, fixes, source omissions, and matched engine evidence.
- [November 2 manual game audit](game-audit-2026-11-02.md): reconciled generated-chart game statistics, clock and era-rule findings, and ticket review.
- [November 2 release readiness](release-readiness-2026-11-02.md): test-first fixes, remaining investigations and pre-push evidence.
