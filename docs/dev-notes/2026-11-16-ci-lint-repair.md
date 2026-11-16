# CI lint repair and push blocker

Investigation and local validation, November 16, 2026. This records a lint repair;
it does not certify a release or a completed full regression.

The Tests workflow for `d1019555d2b5bf2bfb9bff31835ae091f6902cb3`
([run 43876702924](https://github.com/rtulloh/paydirt/actions/runs/43876702924))
failed only in its Ruff job. All other jobs succeeded. The same 12 violations
were reproduced locally before editing.

The repair formats two import blocks, marks five unused unpacked values with
underscores, combines nested context managers and conditions, and removes an
integer cast around `round()`. The existing best-effort field-goal projection
catch-all retains its behavior with a documented, line-specific BLE001 exception.
No test assertions or expected outcomes changed. Player documentation is
unaffected because commands, rules and player behavior do not change.

Validation on Python 3.11: 188 focused core tests and 79 backend API tests passed;
the API run emitted eight Pydantic `dict()` deprecation warnings. Ruff and
`git diff --check` passed. Initial attempts with the default Python 3.9 failed
collection because that interpreter is unsupported. Python 3.12 lacked pytest;
the successful focused runs used the installed Python 3.11 environment.

## Push remains blocked

The separately required 1977 audit was run on Python 3.12 with the pinned policy,
original 72-repetition report, canonical and independently reproduced charts,
source map and public season. It failed with:

> Runtime differs from exact reviewed 1977 version-only identities

The fresh private receipt is
`.ai-audits/lint-fix-20261116-1977-acceptance.json`. The exact approved version-only
exception does not qualify the current 1.10.6 engine. Do not alter the policy or
relabel this failure. Resolve the runtime qualification through a reviewed route
before pushing, then run every required regression against the final candidate.
The full runner was started and interrupted during the core suite after this
blocking result; it did not complete. Its partial log is under
`.ai-audits/full-regression/20261116T203222Z/`.

The public 1983 released-chart audit passed separately, with its private receipt
at `.ai-audits/lint-fix-20261116-chart-quality-1983.json`. This result does not
replace the failed 1977 gate or establish unchanged gameplay identity.
