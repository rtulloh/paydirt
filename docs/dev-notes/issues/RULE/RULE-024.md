---
id: RULE-024
title: Missed field goals always transfer at the kick spot instead of using season-specific rules
status: closed
priority: High
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: 2026-11-02
tags:
  - reproduced
  - season-rules
---

## Description

The latest manual 1983 game misses a 52-yard field goal snapped from the
opponent's 35. The receiving team starts at its own 42, using the holder's
seven-yard offset, rather than its own 35. The engine always uses the
kick spot, with no season-rule switch.

The [Pro Football Hall of Fame's rule history](https://www.profootballhof.com/football-history/general-history-chronology-1960-to-1979)
records the 1974 change to give the receiving team the line of scrimmage
after misses beyond the 20. Its [kicking history](https://www.profootballhof.com/news/nfl-kickers-up-up-and-away)
dates the change to the spot of the missed kick to 1994. Thus the observed
spot matches the later rule, not this game's 1983 season.

## Resolution / verification

Core season rules choose the missed-kick receiving spot: own twenty before
1974, line of scrimmage with a twenty-yard floor in 1974–1993, and kick spot
with that floor from 1994. Direct and declined-foul unblocked misses use the
same helper; blocked-kick rules are unchanged.

Test-first baseline: twenty expected failures and sixteen passing controls,
including both teams, era boundaries, floor and declined choices. Generic
FG tests now use public-era 2026 because their unchanged assertions describe
modern kick-spot placement. A 64-game public-chart audit with synthetic era
overrides confirmed 34 historical-era and 39 modern-era missed-kick spots.
The maintained season guide cites the Hall of Fame's rule-change history.

## Comments

--- 2026-11-02 10:15 ---
Found in the completed manual game and reproduced independently using public
sample teams. The seven-yard difference is a rules issue, not generated-chart
yardage or a display conversion error. No alternative final score is claimed.

--- 2026-11-02 10:50 ---
Included in the pending local fix commit. Issue-specific full-game evidence
is recorded above; private charts and narrative logs remain ignored.
