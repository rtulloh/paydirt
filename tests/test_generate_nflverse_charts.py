"""Integration tests for the nflverse play-by-play chart command."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path


def _stats(team_name: str, short_name: str) -> dict[str, object]:
    """Return a compact synthetic season-stat payload."""
    return {
        "season": 2026,
        "team_name": team_name,
        "short_name": short_name,
        "offense": {
            "rushing": {"attempts": 100, "yards": 450, "fumbles": 2, "fumbles_lost": 1},
            "passing": {"attempts": 100, "completions": 65, "yards": 750},
        },
        "defense": {
            "rushing": {"attempts": 100, "yards": 430},
            "passing": {"attempts": 100, "completions": 62, "yards": 700},
        },
    }


def _play(play_id: int, offense: str, defense: str) -> dict[str, object]:
    """Return one nflverse-shaped regular-season rushing row."""
    return {
        "season_type": "REG",
        "game_id": "2026_01_AAA_BBB",
        "play_id": play_id,
        "posteam": offense,
        "defteam": defense,
        "play_type": "run",
        "desc": "Runner middle for 4 yards",
        "yards_gained": 4,
        "run_location": "middle",
        "run_gap": "guard",
        "qb_scramble": 0,
        "rush_attempt": 1,
        "pass_attempt": 0,
        "air_yards": "",
        "complete_pass": 0,
        "incomplete_pass": 0,
        "interception": 0,
        "sack": 0,
        "touchdown": 0,
        "return_touchdown": 0,
        "fumble": 0,
        "fumble_lost": 0,
        "out_of_bounds": 0,
        "penalty": 0,
        "penalty_team": "",
        "penalty_yards": "",
        "penalty_type": "",
        "field_goal_result": "",
        "kick_distance": "",
        "return_team": "",
        "return_yards": "",
        "punt_blocked": 0,
        "punt_fair_catch": 0,
        "punt_out_of_bounds": 0,
        "punt_downed": 0,
        "touchback": 0,
    }


def test_nflverse_chart_command_generates_opponent_adjusted_charts(tmp_path: Path) -> None:
    """The command should turn nflverse rows into empirical team charts and audits."""
    from generate_nflverse_charts import main

    stats_dir = tmp_path / "stats"
    template_dir = tmp_path / "template"
    output_dir = tmp_path / "output"
    audit_dir = tmp_path / "audit"
    stats_dir.mkdir()
    for team_name, abbreviation in (("Alphas", "AAA"), ("Betas", "BBB")):
        (template_dir / team_name).mkdir(parents=True)
        (template_dir / team_name / "roster.json").write_text("{}\n", encoding="utf-8")
        (stats_dir / f"{team_name}.json").write_text(
            json.dumps(_stats(team_name, abbreviation)),
            encoding="utf-8",
        )
    (template_dir / "2026.yaml").write_text(
        "season: 2026\ntwo_point_conversion: true\n",
        encoding="utf-8",
    )

    rows = [
        *(_play(play_id, "AAA", "BBB") for play_id in range(1, 13)),
        *(_play(play_id, "BBB", "AAA") for play_id in range(13, 25)),
    ]
    pbp_path = tmp_path / "play_by_play_2026.csv.gz"
    with gzip.open(pbp_path, "wt", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    team_map = tmp_path / "team-map.json"
    team_map.write_text(
        json.dumps({"AAA": "Alphas", "BBB": "Betas"}),
        encoding="utf-8",
    )
    profile_path = tmp_path / "calibration-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "run_yard_multiplier": 1.1,
                "pass_completion_adjustment": 0.02,
                "pass_interception_adjustment": -0.003,
                "pass_pressure_adjustment": 0.004,
                "pass_yard_multiplier": 1.08,
            }
        ),
        encoding="utf-8",
    )

    result = main(
        [
            "--pbp",
            str(pbp_path),
            "--stats-dir",
            str(stats_dir),
            "--template-season",
            str(template_dir),
            "--team-map",
            str(team_map),
            "--output",
            str(output_dir),
            "--audit-dir",
            str(audit_dir),
            "--calibration-profile",
            str(profile_path),
            "--run-yard-multiplier",
            "0.75",
        ]
    )

    assert result == 0
    assert (output_dir / "Alphas" / "offense.csv").exists()
    assert (output_dir / "Betas" / "defense.csv").exists()
    assert (output_dir / "Alphas" / "roster.json").exists()
    assert (output_dir / "2026.yaml").exists()
    assert (audit_dir / "Alphas.csv").exists()
    manifest = json.loads((output_dir / "generation-manifest.json").read_text())
    assert manifest["source"] == "nflverse regular-season play-by-play"
    assert manifest["games"] == 1
    assert manifest["source_rows"] == 24
    assert manifest["opponent_adjustment"]["model"] == (
        "league additive offense plus defense effects"
    )
    assert manifest["opponent_adjustment"]["run_yard_multiplier"] == 0.75
    assert manifest["teams"]["Alphas"]["empirical_outcomes"] == 12
    assert manifest["teams"]["Alphas"]["generated_empirical_outcomes"] == 12
    assert manifest["teams"]["Alphas"]["fallback_columns"] == 0
