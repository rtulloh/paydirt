"""Tests for the chart-tuning command orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from paydirt.chart_tuning import TuningRunConfig, run_tuning


def test_tuning_runner_regenerates_candidates_and_uses_held_out_validation(
    tmp_path: Path,
) -> None:
    """The runner should tune on training seeds and validate the best profile separately."""
    config = TuningRunConfig.from_mapping(
        {
            "games_per_team_per_season": 16,
            "training_seed": 8306,
            "validation_seed": 908306,
            "max_iterations": 4,
            "targets": {
                "completion_rate": {"value": 0.65, "tolerance": 0.005},
            },
            "bounds": {
                "pass_completion_adjustment": {
                    "minimum": -0.08,
                    "maximum": 0.08,
                    "step": 0.005,
                }
            },
            "generator_command": [
                "generate",
                "--profile",
                "{profile}",
                "--output",
                "{candidate}",
            ],
            "training_command": [
                "simulate-training",
                "--season",
                "{candidate}",
                "--seasons",
                "{seasons}",
                "--seed",
                "{seed}",
                "--output",
                "{report}",
            ],
            "validation_command": [
                "simulate-validation",
                "--season",
                "{candidate}",
                "--seasons",
                "{seasons}",
                "--seed",
                "{seed}",
                "--output",
                "{report}",
            ],
        }
    )
    commands: list[list[str]] = []

    def execute(command: list[str], _log_path: Path) -> None:
        commands.append(command)
        if command[0] == "generate":
            return
        output = Path(command[command.index("--output") + 1])
        seasons = int(command[command.index("--seasons") + 1])
        candidate = Path(command[command.index("--season") + 1])
        profile = json.loads((candidate / "calibration-profile.json").read_text())
        completion = 0.65 if profile["pass_completion_adjustment"] >= 0.005 else 0.62
        output.write_text(
            json.dumps(
                {
                    "league": {"completion_rate": completion},
                    "teams": {
                        "AAA": {"team_games": seasons * 16},
                        "BBB": {"team_games": seasons * 16},
                    },
                }
            ),
            encoding="utf-8",
        )

    result = run_tuning(
        config,
        workspace=tmp_path / "tuning",
        training_seasons=64,
        validation_seasons=256,
        execute=execute,
    )

    assert result["selected_profile"]["pass_completion_adjustment"] == 0.005
    assert len(result["training_history"]) == 2
    assert result["validation"]["within_tolerance"] is True
    assert [command[0] for command in commands] == [
        "generate",
        "simulate-training",
        "generate",
        "simulate-training",
        "simulate-validation",
    ]
    assert "8306" in commands[1]
    assert "908306" in commands[-1]
    assert (tmp_path / "tuning" / "selected-profile.json").exists()
    assert (tmp_path / "tuning" / "tuning-report.json").exists()


def test_tuning_prefers_a_tolerance_passing_candidate_over_lower_raw_loss(
    tmp_path: Path,
) -> None:
    """A candidate that meets every tolerance should outrank a near miss."""
    config = TuningRunConfig.from_mapping(
        {
            "games_per_team_per_season": 1,
            "training_seed": 1,
            "validation_seed": 2,
            "max_iterations": 2,
            "targets": {
                "completion_rate": {"value": 0.65, "tolerance": 0.01},
                "interception_rate": {"value": 0.025, "tolerance": 0.01},
                "sack_rate": {"value": 0.065, "tolerance": 0.01},
            },
            "bounds": {
                "pass_completion_adjustment": {
                    "minimum": 0.0,
                    "maximum": 0.005,
                    "step": 0.005,
                }
            },
            "generator_command": ["generate", "{candidate}"],
            "training_command": ["train", "{candidate}", "{report}"],
            "validation_command": ["validate", "{candidate}", "{report}"],
        }
    )

    def execute(command: list[str], _log_path: Path) -> None:
        if command[0] == "generate":
            return
        candidate = Path(command[1])
        output = Path(command[2])
        profile = json.loads((candidate / "calibration-profile.json").read_text())
        adjusted = profile["pass_completion_adjustment"] > 0
        output.write_text(
            json.dumps(
                {
                    "league": {
                        "completion_rate": 0.65 if adjusted else 0.639,
                        "interception_rate": 0.034 if adjusted else 0.025,
                        "sack_rate": 0.074 if adjusted else 0.065,
                    },
                    "teams": {"AAA": {"team_games": 1}},
                }
            ),
            encoding="utf-8",
        )

    result = run_tuning(
        config,
        workspace=tmp_path / "passing-priority",
        training_seasons=1,
        validation_seasons=1,
        execute=execute,
    )

    assert result["training_history"][0]["assessment"]["loss"] < result[
        "training_history"
    ][1]["assessment"]["loss"]
    assert result["selected_profile"]["pass_completion_adjustment"] == 0.005
