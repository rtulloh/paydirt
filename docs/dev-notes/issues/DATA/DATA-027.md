---
id: DATA-027
title: Opponent yard adjustment changes QB Time sack and scramble classes
status: open
priority: High
created-at: 2026-11-05
resolved-at:
closed-at:
tags:
  - reproduced
  - regression-test
---

## Description

Independent root/Astra synthetic reproductions show QB Time adjustment moving
numeric and initial-fumble outcomes across the engine's sack/scramble boundary.
Two offenses each have twenty minus-one-yard sacks against one defense and twenty
plus-one-yard scrambles against another. The shared additive yard fit and rounding
turn all forty into numeric zero, erasing every sack. Other controls change zero
scrambles into losses and positive fumbles into sacks, or F0 sacks into rushes.
Aggregate pressure calibration does not justify these mechanism changes.

## Resolution / verification

Regressions precede any production correction. The proposed minimal constraint
preserves each source QB Time event class when shifting its severity: numeric
negative remains at most minus one; numeric zero/positive stays nonnegative;
nonpositive initial fumbles remain sacks; positive initial fumbles remain rushes.
Whole flags stay attached. Primary fumble gains have no such QB-class constraint.
Clamping is a disclosed model limit, not source evidence or severity accuracy.

No release approval follows. Fresh source candidates, pressure diagnostics,
training and the full charter are required; keep open.

## Comments

--- 2026-11-05 21:12 ---
The temporary minus-one floor above is superseded by the reviewed DATA-029
representation. Numeric/explicit sacks may now reach `SACK 0[*]` while retaining
class; numeric zero remains scramble. F0 retains its real fumble/sack behavior.
Two token expectations and the root zero-severity/clamp diagnostic expectations
changed explicitly for this supported representation, after new failing cases.
Source/adjusted/selected class counts, boundary clamps and proposed/applied gain
changes remain disclosed. This does not establish NFL fumble-credit equivalence.

--- 2026-11-05 21:10 ---
Confirmed separately from DATA-025 narrative contamination and DATA-026 prefix
sampling. The original source classes, official targets and reserved seeds stay
unchanged. No per-team fitting table or transition mechanism is proposed.
