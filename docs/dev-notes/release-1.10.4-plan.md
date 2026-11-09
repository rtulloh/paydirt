# Release 1.10.4 plan

Status: scoped follow-up work after the published 1.10.3 missing-teams repair.
This is a development plan, not shipped behavior or a release-readiness claim.

## Ticket-fixer scope

[VAL-023](issues/VAL/VAL-023.md) is explicitly assigned to the release ticket
fixer. Investigate and correct Windows native shutdown verification or the
application behavior, according to evidence. The user wants platform problems
addressed before they affect players. Keep the original missing-teams repair
verified; do not confuse that fixed bug with the separate shutdown question.

The existing low-reasoning release fixer continues this work. Require test-first
synthetic/public-2026 regressions for changed behavior, actual Codex review per
change, and native Windows installer plus portable verification. Reuse immutable
v1.10.3 assets to diagnose the current problem without rebuilding unnecessarily.
A harness fix must still prove normal exit, the shutdown marker, a released port
and no surviving owned processes; forced cleanup remains a failed check.

If an application correction is needed, test the resulting packaged candidate on
Windows. Published release assets must subsequently pass the post-publication
native smoke checks in AGENTS.md, with platform and first-launch security limits
explicit. Preserve logs, hashes, failed attempts and receipts. Mark resolved on
an implemented fix; close only after the issue-specific native acceptance.
Do not publish a new release merely to diagnose or repair the smoke harness.

## Season work and scope boundaries

The previously discussed new season is 1977, contingent on obtaining accessible
reviewed sources; see [1977 feasibility](1977-season-feasibility.md). It remains
blocked by acquisition, and no generated 1977 season is claimed. The proposed
periodically refreshed real 2026 season is a separate idea awaiting concrete
implementation scope and source qualification. AI-026 remains Low and excluded.

This assignment does not authorize unrelated ticket fixes, broad AI experiments,
or automatically carry the urgent 1.10.3 full-regression waiver into 1.10.4.
Follow current AGENTS.md push/release requirements unless explicitly superseded.

## VAL-023 diagnostic candidate

The first candidate changes only the acceptance harness, not packaged gameplay or application code. Before native launch it explicitly enables inheritable Windows Ctrl-C handling, records the console's process membership when delivering the event, and runs a minimal Python console comparison with the inherited-ignore flag enabled and disabled. Microsoft documents that child processes inherit the Ctrl-C-ignore attribute; this is a hypothesis until native controls and the actual unchanged installer/portable assets prove it. The deliberately ignored minimal process may require negative-control cleanup, which is recorded separately and never qualifies the application shutdown.

Two new synthetic API success/error controls failed before the explicit-enable helper was added, then all thirteen focused smoke tests passed. Native execution requires a changed workflow/script push; the earlier urgent 1.10.3 full-regression waiver does not authorize that push under current AGENTS.md. Prepare and review the candidate before requesting a narrow diagnostic-only exception; no new release/tag or product repair is justified yet.

Actual Codex review required the ignored negative control to remain alive after Ctrl-C delivery; a new differential regression failed before enforcing this, then passed. An inconclusive control comparison stops the experiment rather than attributing a later pass to the hypothesis. Another test-first check rejects abnormal application exit even when the port disappears; the existing HTTP-error control now explicitly models exit status zero, without weakening its assertion.
