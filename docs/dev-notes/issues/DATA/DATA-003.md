---
id: DATA-003
title: Add a PDF import backend for Paydirt charts
status: open
priority: Low
created-at: 2026-10-30
resolved-at:
closed-at:
tags:
  - deferred
---

## Description

`extract_charts.py` currently imports Excel `.xls` workbooks. Add PDF support
after the Bowl Bound chart extractor is stable enough to reuse. Paydirt charts
use a different play catalog from Bowl Bound, so the PDF reader must map the
extracted chart columns and result symbols to Paydirt's play definitions.

## Resolution / verification

Keep the current `.xls` reader and dispatch PDF files to a separate PDF reader.
Adapt the Bowl Bound PDF parsing for Paydirt plays, then have both readers
produce the same normalized chart data for the existing validation and CSV
generation path. Do not convert PDFs to intermediate `.xls` workbooks.

Add synthetic tests for format dispatch, Paydirt play/result mapping, malformed
or ambiguous PDF data, and shared output generation. Compare extracted values
with the source charts before accepting a team. Update the chart-generator
guide with supported PDF layout and usage. Use only synthetic/public 2026 data
in unit tests; keep any private chart checks local.

## Comments

--- 2026-10-30 21:30 ---
Opened at the user's request; deferred until the Bowl Bound PDF extractor is
stable. The planned integration will parse PDFs directly and share the
normalized-output path with the existing `.xls` reader.
