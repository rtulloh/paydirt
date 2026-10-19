#!/usr/bin/env python3
"""Run testing-only play-selection audits; see docs/ai-auditing.md."""

import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Optional

# Support execution from the repository root without installing test utilities.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paydirt.packaging import get_seasons_path
from tests.ai_audit import DIFFICULTIES, GameSpec, game_seed, generated_schedule, make_report, run_games


def main(argv: Optional[list[str]] = None) -> int:
    """Return nonzero on any incomplete game; concentration warnings are advisory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("teams", nargs="*", metavar="TEAM", help="away then home, e.g. 2026/Ironclads 2026/Thunderhawks")
    parser.add_argument("--season", help="audit every team in this local season directory")
    parser.add_argument("--weeks", type=int, default=16, help="generated regular-season weeks (default 16)")
    parser.add_argument("--games", type=int, default=1, help="repeat a single matchup this many times")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, default="hard", help="both teams unless overridden (default hard)")
    parser.add_argument("--away-difficulty", choices=DIFFICULTIES)
    parser.add_argument("--home-difficulty", choices=DIFFICULTIES)
    parser.add_argument("--seed", type=int, default=8306, help="master seed; report records derived per-game seeds")
    parser.add_argument("--play-limit", type=int, default=500)
    parser.add_argument("--compare-balanced", action="store_true", help="also run identical seeded matchups using legacy auto AI")
    parser.add_argument("--output", type=Path, default=Path(".ai-audits/latest.json"))
    parser.add_argument("--csv", type=Path, help="optional situation summary CSV, not raw chart data")
    args = parser.parse_args(argv)
    if args.games < 1 or args.weeks < 1 or args.play_limit < 1:
        parser.error("games, weeks and play-limit must be positive")
    if args.csv is not None and args.csv.resolve() == args.output.resolve():
        parser.error("JSON and CSV outputs must be different paths")
    away_level = args.away_difficulty or args.difficulty
    home_level = args.home_difficulty or args.difficulty
    if args.season:
        if args.teams or args.games != 1:
            parser.error("--season cannot be combined with matchup teams or --games")
        directory = get_seasons_path() / args.season
        if not directory.is_dir():
            parser.error("season directory does not exist")
        teams = [f"{args.season}/{path.name}" for path in directory.iterdir()
                 if path.is_dir() and (path / "team.yaml").is_file()]
        try:
            specs = generated_schedule(teams, args.weeks, args.seed, away_level, home_level)
        except ValueError as error:
            parser.error(str(error))
    else:
        if len(args.teams) != 2:
            parser.error("provide away and home teams, or --season")
        try:
            specs = [GameSpec(*args.teams, game_seed(args.seed, f"repeat={number}"),
                              away_level, home_level) for number in range(1, args.games + 1)]
        except ValueError as error:
            parser.error(str(error))
    if args.compare_balanced:
        specs += [replace(spec, away_difficulty="balanced", home_difficulty="balanced")
                  for spec in specs]
    report = make_report(run_games(specs, args.play_limit))
    report["run"] = {"master_seed": args.seed, "comparison": args.compare_balanced,
                     "schedule": "generated regular season" if args.season else "repeated matchup"}
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if args.csv is not None:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            fields = ("team", "difficulty", "mode", "down", "distance_band", "calls",
                      "largest_share", "distinct_plays", "longest_streak", "small_sample",
                      "play_counts", "primary_play_shares")
            with args.csv.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                for group in report["summary"]["situations"]:
                    writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
                                     for key, value in group.items()})
    except OSError as error:
        print(f"Could not write audit report: {error}", file=sys.stderr)
        return 1
    summary = report["summary"]
    print(f"AI audit: {summary['passed']}/{summary['games']} passed; {summary['calls']} calls; "
          f"{len(summary['warnings'])} observational concentration warnings. Standings persistence disabled.")
    for game in report["games"]:
        if game["status"] != "passed":
            config = game["config"]
            print(f"FAIL {config['away']}@{config['home']} seed={config['seed']}: {game['error']}", file=sys.stderr)
    for difficulty in sorted({group["difficulty"] for group in summary["situations"]}):
        groups = [group for group in summary["situations"]
                  if group["difficulty"] == difficulty and group["mode"] == "ordinary"]
        largest = sorted(groups, key=lambda group: (
            group["small_sample"], -group["largest_share"], group["team"]))[:5]
        print(f"{difficulty}: ordinary-down concentration samples (inspect JSON/CSV for every situation)")
        for group in largest:
            print(f"  {group['team']} {group['down']}&{group['distance_band']} "
                  f"n={group['calls']} largest={group['largest_share']:.1%} "
                  f"distinct={group['distinct_plays']} streak={group['longest_streak']}"
                  + (" [small sample]" if group["small_sample"] else ""))
    print(f"Report: {args.output}. Review play selection/balance separately from scores; no universal usage cap.")
    return int(summary["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
