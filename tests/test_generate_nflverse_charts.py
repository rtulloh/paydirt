"""Integration tests for the nflverse play-by-play chart command."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import pytest


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
        "two_point_attempt": 0,
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


def test_nflverse_chart_command_generates_opponent_adjusted_charts(tmp_path: Path, monkeypatch) -> None:
    """The command should turn nflverse rows into empirical team charts and audits."""
    import generate_nflverse_charts as command
    from generate_nflverse_charts import main

    original_generate = command.generate_team_charts
    pressure_models = []

    def generate_with_shared_pressure(*args, **kwargs):
        assert kwargs.get("neutral_pressure") is not None
        pressure_models.append(kwargs["neutral_pressure"])
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(command, "generate_team_charts", generate_with_shared_pressure)

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
    assert pressure_models
    assert all(model is pressure_models[0] for model in pressure_models)
    assert manifest["neutral_pressure_model"] == pressure_models[0].evidence
    assert manifest["source"] == "nflverse regular-season play-by-play"
    assert all(team.get("primary_layout", {}).get("invariants_passed") is True
               for team in manifest["teams"].values())
    assert manifest["games"] == 1
    assert manifest["source_rows"] == 24
    assert manifest["conversion_population"]["structured_flag_rows"] == 24
    assert manifest["conversion_population"]["unknown_flag_rows"] == 0
    assert manifest["conversion_population"]["excluded_count"] == 0
    assert json.loads((audit_dir / "excluded-conversions.json").read_text()) == []
    assert manifest["opponent_adjustment"]["model"] == (
        "league additive offense plus defense effects"
    )
    assert manifest["opponent_adjustment"]["run_yard_multiplier"] == 0.75
    assert manifest["teams"]["Alphas"]["empirical_outcomes"] == 12
    assert manifest["teams"]["Alphas"]["generated_empirical_outcomes"] == 12
    assert manifest["teams"]["Alphas"]["fallback_columns"] == 0


@pytest.mark.parametrize("missing", ["gain", "recovery"])
def test_generation_refuses_unsupported_required_source_fields(tmp_path: Path, missing: str) -> None:
    from generate_nflverse_charts import main

    stats_dir, template = tmp_path / "stats", tmp_path / "template"
    stats_dir.mkdir()
    template.mkdir()
    (template / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n")
    for team, short in (("Alphas", "AAA"), ("Betas", "BBB")):
        (stats_dir / f"{team}.json").write_text(json.dumps(_stats(team, short)))
        (template / team).mkdir()
    team_map = tmp_path / "teams.json"
    team_map.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
    rows = [_play(i, "AAA" if i < 13 else "BBB", "BBB" if i < 13 else "AAA") for i in range(1, 25)]
    if missing == "gain":
        rows[0]["yards_gained"] = ""
    else:
        rows[0].update(fumble=1, fumble_lost="")
    pbp = tmp_path / "plays.csv"
    fields = sorted(set().union(*(row.keys() for row in rows)))
    with pbp.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Unsupported source fields"):
        main(["--pbp", str(pbp), "--stats-dir", str(stats_dir), "--template-season", str(template),
              "--team-map", str(team_map), "--output", str(tmp_path / "output"),
              "--audit-dir", str(tmp_path / "audit")])
    assert not (tmp_path / "output" / "generation-manifest.json").exists()
