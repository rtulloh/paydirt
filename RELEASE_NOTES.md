# Paydirt Release Notes

## v1.9.2

### Trace Accuracy and Developer Validation

- Preserve raw punt-return chart cells, so punt-return fumbles display the actual `R:<die>→"F"` result rather than a blank placeholder.
- Preserve the defense-chart row in ordinary fumble traces and omit `Ret:0→0` when no fumble-return chart roll occurred.
- Correctly retain punt-return metadata when resolving a penalty decision after a return fumble.
- Define a full test run in the contributor guide as including the full-season runner and both public and local AI audits, not pytest alone.

### Validation

- Core: 5,420 passed, 8 existing local-data skips; backend: 218; frontend: 255 passed, 1 existing skip; build and Playwright browser games passed.
- Full game runner: 14/14; generated season: 224/224 regular-season games and 9/9 playoff games; historical reproductions: 10/10.
- AI audits reconciled: public 32/32 with no concentration warnings and local 448/448 with four advisory concentration warnings. Private charts and audit reports remain local.

`1.9.2` is a bug-fix and trace-correctness release. The existing `v1.9.1` tag is preserved as immutable history.

## v1.9.1

### Return Rules and Special Teams

- Roll kickoff distance and kickoff return separately; traces now show the real `KO:` and `RT:` rolls, including return rerolls and `RT:none` when a kick is not returned.
- Apply OFF/DEF return-chart penalties consistently across kickoff, punt, interception, fumble-advance, and blocked-kick returns. Return penalties are automatically enforced from the end of the return, with half-the-distance handling and no penalty touchdown.
- Resolve return fumbles with recovery rolls and support chained kickoff/interception/fumble returns. Recovery rolls 17–19 and 37–39 use the interception-return chart; ordinary fumble recovery 39 is no longer an automatic touchdown.
- Nullify offsetting return fouls correctly: re-kick kicks, replay turnover/blocked-kick downs from the previous spot, and consume ten seconds.

### Halftime, Web Flow, and Data Quality

- Make halftime and second-half kickoff ownership engine-owned across CLI, resume, web API, and browser UI; persist the opening kicker in saves and surface `halftime_pending` in web state.
- Correct web kickoff and penalty-decision flows, including final-try game endings and engine-generated return previews.
- Normalize stray source-workbook characters when extracting special-teams CSV cells; blank cells such as the Cardinals Int. Return backtick become zero-yard results with a loader warning.
- Replace the monolithic developer tracker with per-issue files, generated status index, priorities, links, timestamps, resolved/closed lifecycle, and validation tests.

### Validation

- Core: 5,417 passed, 8 existing skips; backend: 218; frontend: 254 passed, 1 existing skip; build and Playwright browser games passed.
- Full game runner: 14/14; generated season: 224/224 regular-season games and 9/9 playoff games; historical reproductions: 10/10.
- AI audits reconciled: public 32/32 and local 448/448. Private charts and play-test logs remain local and are not included in release artifacts.

`1.9.1` is a bug-fix and rules-correctness release; the existing `v1.9.0` tag is preserved as immutable history.

## v1.8.1
