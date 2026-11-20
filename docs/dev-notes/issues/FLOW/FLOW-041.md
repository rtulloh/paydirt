---
id: FLOW-041
title: Seal the completed macOS app bundle before creating its DMG
status: open
priority: High
target-release: v1.12.1
created-at: 2026-11-19
resolved-at:
closed-at:
tags:
  - packaging
links:
commits:
---

## Description

The published v1.12.0 ARM macOS application fails codesign --verify --deep --strict: code has no resources but signature indicates they must be present. The packaging script wraps a PyInstaller ad-hoc signed executable in a new bundle with Info.plist and resources, but does not sign that completed bundle. Retain v1.12.0 unchanged and ship the correction under v1.12.1.

## Resolution / verification

- Sign the completed app bundle ad hoc after all resources and Info.plist are written, then require deep strict verification before copying it into DMG staging.
- Exercise successful assembly and injected signing/verification failures with portable tests; confirm an isolated copy of the downloaded ARM artifact verifies after the same signing operation.
- Verify freshly published v1.12.1 macOS artifacts on supported architectures and record first-launch security behavior. Ad-hoc signing is not Developer ID signing or notarization and does not guarantee Gatekeeper acceptance.

## Comments

--- 2026-11-19 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-19 19:59 ---
Confirmed the published ARM bundle fails deep strict signature verification. Before changing packaging, two portable assembly regressions failed because DMG staging received an unsigned bundle. The corrected script signs the completed bundle and verifies it before staging; successful assembly and injected signing/verification failures now pass. The focused packaging suites pass 23 tests (the unchanged Python packaging module has 100% statement/branch coverage; the shell command paths are exercised by the assembly regressions).

An isolated copy of the downloaded ARM app passes deep strict verification after the exact new ad-hoc signing command. Changing a sealed license resource then fails verification, and restoring its bytes passes. Neither the original download nor an installed app was modified, and no quarantine setting was changed. This is signature repair evidence, not successful application startup or Gatekeeper acceptance. Keep this ticket open until freshly published v1.12.1 macOS artifacts are qualified on supported architectures, with signing/notarization limitations disclosed.
