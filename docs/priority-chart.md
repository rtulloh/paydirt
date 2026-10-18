# Priority Chart Reference

[Documentation index](README.md) · [How plays resolve](playing.md#play-resolution) · [Clock management](clock-management.md)

An offensive chart entry is **not the final play result**. The priority chart combines it with the
selected defensive entry before the engine applies secondary rolls, penalties, field position, and clock rules.
This reference describes the categories used by Paydirt's implementation; it is not a reproduction of private team charts.

## Reading the Symbols

| Symbol | Meaning |
|--------|---------|
| `+n` / Oyg | Ordinary yardage gained, such as `5` |
| `-n` / Oyl | Ordinary yardage lost, such as `-2` |
| NO GAIN / NO CHG | Zero offensive gain / no defensive adjustment; typically `0` in CSV |
| `B` | Breakaway: a secondary breakaway-column roll may be required |
| `TD` | Offensive touchdown entry, still subject to priority |
| `(n)` | A parenthesized defensive value that replaces ordinary offensive results; `[ n ]` notation is also supported without the spaces |
| `(TD)` | Defensive chart awards a touchdown to the **offense**, unless a higher-priority procedure intervenes |
| `QT` | Resolve a secondary QB-time column roll; it is not automatically a successful scramble |
| BLACK | Incomplete pass if the final priority is BLACK; on a running play, no gain |
| `INT n` | Interception at the specified depth, followed by the interception-return procedure |
| `F`, `F+n`, `F-n` | Fumble procedure; recovery determines whether possession changes |
| `BK` | Blocked-kick procedure on the appropriate special-teams play |
| `OFF`, `DEF`, `PI` | Offensive penalty, defensive penalty, or pass interference |

Parentheses matter: ordinary defensive `4` adds to ordinary offensive yardage, while defensive `(4)`
replaces it. Do not confuse a defensive chart outcome with a score or gain by the defending team.

## Combining Offense and Defense

Choose the **offensive row** and **defensive column**. Check the higher-priority procedures below first.

The ASCII reference below is copied from the opening documentation in `paydirt/priority_chart.py`,
with only the Python comment prefixes removed. Its original notation and layout are preserved.

```text
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| OFF \ DEF |  Oyg   |  Oyl   | NO CHG | (#)  | (#)  | (TD) | QR | QT | BLACK | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| Oyg or B  |  ADD   |  ADD   |yg OR B | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| Oyl       |  ADD   |  ADD   |  Oyl   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| NO GAIN   |  Oyg   |  Oyl   |NO GAIN | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| TD        |   TD   |   TD   |   TD   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| QR        |  ADD   |   QR   |   QR   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| QT        |   QT   |   QT   |   QT   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| BLACK     |  INC   |  INC   |  INC   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT |
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| INT       |  INT   |  INT   |  INT   | (#)  | (#)  | (TD) | QR | QT |  INC  | INT*|
+-----------+--------+--------+--------+------+------+------+----+----+-------+-----+
| F or BK   |       FUMBLE/BLOCKED KICK PRIORITY OVER ALL BUT PENALTY               |
+-----------+-----------------------------------------------------------------------+
| DEF/OFF/PI|                   PENALTIES ALWAYS TAKE PRIORITY                     |
+-----------+-----------------------------------------------------------------------+
*INT Shortest Yards
```

- **ADD:** add signed yardage. A loss is negative, not another positive gain.
- **Keep gain / B:** preserve the offensive entry. Ordinary yardage does not create a breakaway.
- **B with ADD:** the breakaway procedure still applies, with the defensive yardage adjustment.
- **Use (n):** replace the offensive entry with that signed number; do not add both values.
- **INC:** incomplete on a pass; BLACK priority on a run instead means no gain.
- **QT:** roll on the QB-time column and resolve that result, including any further procedure it requires.
- **Shorter INT depth:** if both entries are interceptions, use the shorter depth, not the sum.

**Source-chart notation:** Oyg means yards gained; Oyl means yards lost; `(#)` means a parenthesized
number; QR means quarterback rush; QT means quarterback time. The source reference repeats the `(#)`
column heading; both are reproduced as written.

**Implementation caveat:** the ASCII reference includes QR, but the current implementation does not
have a distinct QR category. Do not assume that a separate QR procedure is implemented.

## Higher-Priority Procedures

1. **Penalties:** `OFF`, `DEF`, and `PI` trigger their penalty procedures. Resolve the offered options,
   acceptance/declination, enforcement, and any required reroll; a penalty marker is not simply ordinary yardage.
2. **Fumbles and blocked kicks:** these procedures take priority over ordinary results, including parenthesized
   numbers and touchdowns, except where the penalty procedure governs. A fumble is **not automatically a turnover**.
   The engine determines recovery and any subsequent advancement.
3. Otherwise, use the offense/defense combination above.

This table selects the controlling result. It is not a substitute for goal-line limits, recovery and return rolls,
penalty enforcement, or the [timing procedures](clock-management.md).

## Worked Priority Examples

These examples use synthetic entries, before other game-state adjustments. They are not guaranteed outcomes of any play call.

| Offense entry | Defense entry | Controlling result | Why |
|---------------|---------------|--------------------|-----|
| `5` | `-2` | Gain of 3 yards | ADD: `5 + (-2) = 3` |
| `-3` | `-2` | Loss of 5 yards | ADD: `-3 + (-2) = -5` |
| `8` | `(4)` | Gain of 4 yards | Parentheses replace 8; this is not a 12-yard gain |
| `BLACK` | `(4)` | Gain of 4 yards | The parenthesized defensive value overrules BLACK; the pass is not incomplete |
| `B` | `(4)` | Gain of 4 yards, no breakaway roll | Parentheses overrule B |
| `8` | `BLACK` | Incomplete pass | On a pass, defensive BLACK overrules the apparent eight-yard gain |
| `BLACK` | `QT` | Resolve the QB-time column | Defensive QT overrules BLACK; a secondary result is still required |
| `INT 20` | `INT 10` | Interception 10 yards downfield | Use the shorter interception depth, then resolve the return |
| `TD` | `(-2)` | Loss of 2 yards, not a touchdown | Parentheses overrule the offensive TD entry |
| `F` | `(TD)` | Resolve a fumble, not an automatic touchdown | Fumble procedure has priority; recovery is not assumed |

### Example with an Out-of-Bounds Designation

Suppose a called `7+` produces offensive BLACK and defensive `(4)`:

1. Priority selects **four yards**, not an incompletion.
2. If the designation's five-yard cost applies, `4 - 5 = -1`: a **one-yard loss**, not zero.
3. The engine applies the eligible sideline timing and any other applicable adjustments.

The chart result and modifier cost are separate steps. Read the final engine outcome, not either raw entry alone.
