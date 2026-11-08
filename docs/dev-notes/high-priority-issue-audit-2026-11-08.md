# Open High-priority issue audit — 2026-11-08

Reviewed all ten open High-priority tickets remaining after DATA-038 was moved
to Low. Compared current committed code, original failure reports, later source
and game evidence, public manifests, and existing focused regressions. No game
logic, charts, saved standings, acceptance bounds or generation guards changed.
No full regression, source regeneration or historical simulation was launched.

Four implementation fixes move to resolved pending their specific closing
verification. Four remaining enhancements/modeling/validation gaps move to
Medium. Two reproduced defects remain open High. No ticket is closed by this
review. Resolved dates identify the latest relevant committed release-fix date,
not a claim that this review or a new play test ran on that date.

| Ticket | Status after review | Priority | Finding |
| --- | --- | --- | --- |
| [DATA-017](issues/DATA/DATA-017.md) | resolved | High | Historical review already reconciled the 1983 totals to 1,215 sacks, 620 interceptions and 771 field-goal attempts. |
| [DATA-028](issues/DATA/DATA-028.md) | resolved | High | The source gate checks required-field coverage and ledger identity. |
| [DATA-032](issues/DATA/DATA-032.md) | resolved | High | Current punt snap-fumble regressions pass. |
| [DATA-035](issues/DATA/DATA-035.md) | resolved | High | Historical raw-input review removed exactly five false offensive entries while preserving their INT/return representations; current ownership and joint-adapter controls pass. |
| [AI-026](issues/AI/AI-026.md) | open | Medium | This is an optional coaching capability improvement over the released fair own-offense-chart/history baseline, not evidence that games cannot be played correctly. |
| [DATA-030](issues/DATA/DATA-030.md) | open | Medium | Source facts and modeled statistical classes are now explicitly separated, including the user-authorized historical proxy and uniform fitting-only exclusion policy. |
| [DATA-036](issues/DATA/DATA-036.md) | open | Medium | This remains a real compound-event projection limitation: the corrected modern screen has five compound plays, not the original four, and a historical omitted secondary occurrence is documented. |
| [VAL-019](issues/VAL/VAL-019.md) | open | Medium | Year-selected actual calendars, generated-chart support, 1983/2024 postseason formats, failure handling and source/chart identity checks are implemented and exercised. |
| [STAT-004](issues/STAT/STAT-004.md) | open | High | Fresh synthetic in-memory review reproduces the mismatch: display_games sorts week 1 ahead of an earlier-inserted week 2 record, while edit/delete still index season.games in insertion order. |
| [VAL-009](issues/VAL/VAL-009.md) | open | High | Fresh temporary synthetic-directory reproduction confirms _find_season_dir accepts a directory outside configured roots; replay team lookup also joins request-derived paths without resolved containment. |

## Evidence and limits

- Current committed fixes inspected in the source adapters, source eligibility
  gate, punt engine branches, historical runner, standings CLI and API routes.
  Relevant integration commits include `8c0bb8b`, `57c544d`, and `2b5a141`.
- 239 focused punt/return ownership/compound/source-gate/historical-runner/
  standings checks passed; 417 parser/reconciliation/generation/joint-adapter/
  archive/bundle checks passed. No skips or warnings in these runs.
- STAT-004 reproduced with two synthetic in-memory games inserted out of week
  order: displayed game 1 differs from the record edit/delete index 1 selects.
- VAL-009 reproduced with patched configured roots and temporary synthetic
  directories. Lookup accepted an outside directory; no file contents were read.
  Detailed inputs are deliberately omitted from this public-facing note.
- Both public manifests disclose reviewed baseline reproduction followed by
  INT-only migration, explicitly not full corrected-source requantization.
  Those receipts must not be used to close outstanding corrected-source work.
- Existing historical fitting disclosures retain 15 exclusions out of 727
  fumble events. This is an accepted modeled scope, not exact historical truth.
  Compound projection and physical-versus-credited movement remain unfinished.
- Priority reflects remaining player impact and accepted scope, not a claim
  that small source populations have measured zero statistical influence.

Resolved tickets retain their original final-qualification requirements. New
issue-specific play-test/source evidence is necessary before closure; passing
unit checks alone has not closed anything here.
