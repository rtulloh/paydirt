# Punt return-chain commentary

November 2, 2026. Implemented presentation correction; verification is tracked in
[AUD-025](issues/AUD/AUD-025.md). Private play-test logs stay local.

The reported touchdown is valid. A public/synthetic reproduction follows this sequence:

| Step | Result |
|---|---|
| Punt from HOME 32 | 44 yards, landing at AWAY 24 |
| First return | Six yards to AWAY 30, followed by a fumble |
| Recovery 38 | Returning team loses the ball; HOME recovers |
| Fumble-return cell 37 | HOME reaches the goal line, 30 yards from recovery |

The old narrative attached the first six-yard return to the final stored position. That position
represents the entire chain and is clamped to 99 after a touchdown, producing a misleading
one-yard-line destination. The touchdown, scoring team, recovered possession, and lost-fumble
statistic already agree with the dice.

The engine now separates the initial return from the recovery notes and final outcome. Its message
states that the six yards occurred before a fumble, names the recovery team at the actual fumble
spot, and names the scoring team or final possessing team separately. The raw 37-yard cell remains
in the trace; it is enough to cover the 30 yards to the goal. Ordinary return touchdowns also avoid
a destination at the opponent's one and carry the engine's scoring-team field.

Compact and full CLI views display the engine narrative without the extra guessed kicking-team
recovery or duplicate/misclassified touchdown announcement. One prior test expectation relied on
that invented recovery line; it now verifies the full supplied engine description and rejects the
invented line. Gameplay controls preserve score, possession, final spot, fumble losses, and every
consumed roll in both directions and after a declined punt foul.

No player controls or rules change, so the player guide requires no update. The running game's
already recorded touchdown remains valid; the corrected text appears after loading the updated
code in a subsequent process.

Validation: the new public/synthetic matrix failed in 26 intended presentation cases while 22
controls already passed. The fix passes all 48 cases and 529 focused checks. The complete core
suite passes 6,444 tests with eight existing local-data skips; backend passes 279 tests with 20
existing Pydantic deprecation warnings. Ruff passes. Real CLI integration completes thirteen
historical reproductions, 224 generated regular-season games, and nine postseason games with no
playoff tie. A separate public Hard/balanced audit completes 32 games, reconciles 4,367 calls, and
raises no concentration warnings. Private integration outputs remain ignored. Nothing is committed
or pushed, and charts need no regeneration.
