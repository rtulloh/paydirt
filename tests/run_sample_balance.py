#!/usr/bin/env python3
"""Paired public-team full-game balance check; real CLI/engine, no standings.

Uses the same medium AI on both sides to isolate team strength from difficulty.
Run from repository root: python3 tests/run_sample_balance.py --seeds 100
"""

import argparse
import contextlib
import io
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.run_full_season import validate_game
from tests.test_untimed_down_flow import run_seeded_cli_game


def evaluate(seeds: int) -> dict:
    """Run both home/away orientations for every seed with identical AI levels."""
    if seeds <= 0:
        raise ValueError("seeds must be positive")
    totals = Counter()
    for seed in range(20261017, 20261017 + seeds):
        for home, away in (("Thunderhawks", "Ironclads"), ("Ironclads", "Thunderhawks")):
            output = io.StringIO()
            try:
                with pytest.MonkeyPatch.context() as context, contextlib.redirect_stdout(output):
                    engine = run_seeded_cli_game(context, away, home, seed)
                validate_game(engine, output.getvalue())
                state = engine.state
                scores = {home: state.home_score, away: state.away_score}
                margin = scores["Thunderhawks"] - scores["Ironclads"]
                totals["games"] += 1
                totals["margin"] += margin
                totals["Thunderhawks_points"] += scores["Thunderhawks"]
                totals["Ironclads_points"] += scores["Ironclads"]
                totals["Thunderhawks_wins"] += int(margin > 0)
                totals["Ironclads_wins"] += int(margin < 0)
                totals["ties"] += int(margin == 0)
                for stats in (state.home_stats, state.away_stats):
                    assert stats.total_yards == stats.rushing_yards + stats.passing_yards - stats.sack_yards
            except Exception as error:
                raise RuntimeError(f"{away}@{home} seed={seed}: {error}") from error
    return dict(totals)


def main() -> None:
    """Print balance evidence and reject grossly lopsided or incomplete runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=100)
    args = parser.parse_args()
    totals = evaluate(args.seeds)
    n = totals["games"]
    print(f"{n} completed real-engine games, paired home/away; medium AI both sides; no standings saved.")
    for team in ("Thunderhawks", "Ironclads"):
        wins = totals.get(team + "_wins", 0)
        share = (wins + totals.get("ties", 0) / 2) / n
        points = totals[team + "_points"] / n
        print(f"{team}: {wins} wins; tie-adjusted win share {share:.1%}; {points:.2f} points/game")
        if args.seeds >= 50 and not .30 <= share <= .70:
            raise SystemExit(f"Sample-team balance failed: {team} win share outside 30–70%")
    print(f'Ties: {totals.get("ties", 0)}; mean Thunderhawks margin: {totals["margin"]/n:+.2f}')
    if args.seeds >= 50 and abs(totals["margin"] / n) > 7:
        raise SystemExit("Sample-team balance failed: average margin exceeds one touchdown")


if __name__ == "__main__":
    main()
