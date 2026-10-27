#!/usr/bin/env python3
"""Paired single-snap pressure-policy stress test using only public 2026 teams.

Run from the repository root: python3 tests/run_trailing_defense.py --samples 500
Reports evidence, not a claim of better win rate. Offense sees the formation;
its adaptive profile counters B with draw and F with screen. No files are saved.
Add --synthetic-defense for an exaggerated illustrative run-stop/counter case;
the default uses the actual public sample charts.
"""

import argparse
import random
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.computer_ai import create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def configure_synthetic_defense(game: PaydirtGameEngine) -> None:
    """Illustrate run stops versus visible counters, not a real team's strength.

    A contains all three plays. B sells out against plunge. F gambles: frequent
    plunge losses but occasional eight-yard gains, with large counter exposure.
    """
    for chart in (game.state.home_chart.defense, game.state.away_chart.defense):
        for row in range(1, 6):
            chart.modifiers[("A", row)] = {1: "(4)", 4: "(3)", 5: "(3)"}
            chart.modifiers[("B", row)] = {1: "(-1)", 4: "(9)", 5: "(10)"}
            chart.modifiers[("F", row)] = {1: "(-3)" if row <= 2 else "(8)", 4: "(12)", 5: "(15)"}


def evaluate(samples: int, synthetic_defense: bool = False) -> list[dict]:
    """Compare paired engine seeds, both public matchups, and visible counters."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    original_rng = random.getstate()
    rows = []
    try:
        template = make_sample_game("Thunderhawks", "Ironclads")
        if synthetic_defense:
            configure_synthetic_defense(template)
        for down, distance in ((1, 10), (3, 2), (3, 10)):
            for deficit in (9, 21):
                for profile in ("plunge", "draw", "screen", "visible-counter"):
                    for policy in ("A-only", "mixed"):
                        totals = Counter()
                        for home_offense in (False, True):
                            for sample in range(samples):
                                game = deepcopy(template)
                                state = game.state
                                state.is_home_possession = home_offense
                                state.home_score, state.away_score = ((deficit, 0) if home_offense else (0, deficit))
                                state.quarter, state.time_remaining = 4, 4.0
                                state.ball_position, state.down, state.yards_to_go = 40, down, distance
                                # Same engine seed per paired case; the mixed AI
                                # uses a separate deterministically derived stream.
                                random.seed(20261017 + sample)
                                ai = create_computer_ai("hard", game, cpu_is_home=not home_offense)
                                formation = ai.select_defense(game) if policy == "mixed" else DefenseType.STANDARD
                                totals[formation.value] += 1
                                plays = {"plunge": PlayType.LINE_PLUNGE, "draw": PlayType.DRAW, "screen": PlayType.SCREEN}
                                if profile == "visible-counter":
                                    play = {DefenseType.STANDARD: PlayType.LINE_PLUNGE,
                                            DefenseType.SHORT_YARDAGE: PlayType.DRAW,
                                            DefenseType.BLITZ: PlayType.SCREEN}[formation]
                                else:
                                    play = plays[profile]
                                stats = state.offense_stats
                                outcome = game.run_play_with_penalty_procedure(play, formation)
                                if outcome.pending_penalty_decision:
                                    # The same existing CPU penalty policy chooses
                                    # for the offended side in both experiments.
                                    accept, index = ai.should_accept_penalty(outcome, True, home_offense)
                                    outcome = game.apply_penalty_decision(outcome, accept, index or 0)
                                assert not outcome.pending_penalty_decision
                                assert stats.total_yards == stats.rushing_yards + stats.passing_yards - stats.sack_yards
                                totals["n"] += 1
                                totals["yards"] += stats.total_yards
                                totals["nonpositive"] += int(stats.total_yards <= 0 and not outcome.penalty_applied)
                                totals["first_down"] += int(outcome.first_down or (outcome.touchdown and not outcome.turnover))
                                totals["explosive"] += int(stats.total_yards >= 15 or (outcome.touchdown and not outcome.turnover))
                                totals["takeaway"] += int(outcome.turnover or outcome.safety)
                                # After possession flips, translate the next spot
                                # back to the original offense's perspective.
                                end_spot = state.ball_position if state.is_home_possession == home_offense else 100 - state.ball_position
                                if outcome.safety or (outcome.touchdown and outcome.turnover):
                                    end_spot = 0
                                elif outcome.touchdown:
                                    end_spot = 100
                                totals["field_advance"] += end_spot - 40
                        rows.append(dict(down=down, distance=distance, deficit=deficit,
                                         profile=profile, policy=policy, **totals))
        return rows
    finally:
        random.setstate(original_rng)


def main() -> None:
    """Print aggregate metrics; never use private chart data or save standings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=500, help="Seeds per public matchup and case")
    parser.add_argument("--synthetic-defense", action="store_true",
                        help="Replace blank sample defenses with an illustrative A/B/F tradeoff")
    args = parser.parse_args()
    charts = "SYNTHETIC A/B/F tradeoffs on public offense" if args.synthetic_defense else "Public 2026 sample charts"
    print(f"{charts}; paired engine seeds; one snap, not full drives or games.")
    print("Nonpositive is a stop proxy, not a drive-stop rate. Field delta includes penalties and returns.")
    print("down dist deficit offense          policy       n  A/B/F           yards  fieldΔ  nonpos%   FD%  big%  take%")
    for row in evaluate(args.samples, args.synthetic_defense):
        n = row["n"]
        mix = "/".join(str(row.get(key, 0)) for key in "ABF")
        print(f'{row["down"]:4} {row["distance"]:4} {row["deficit"]:7} {row["profile"]:16} '
              f'{row["policy"]:7} {n:5} {mix:15} {row["yards"]/n:5.2f} {row["field_advance"]/n:7.2f} '
              f'{100*row["nonpositive"]/n:7.1f} {100*row["first_down"]/n:5.1f} '
              f'{100*row["explosive"]/n:5.1f} {100*row["takeaway"]/n:6.1f}')


if __name__ == "__main__":
    main()
