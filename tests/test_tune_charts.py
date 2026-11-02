"""Tests for the public chart-tuning command."""

from __future__ import annotations

import json
from pathlib import Path


def test_tune_charts_cli_uses_standard_training_and_validation_samples(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The command should default to the documented 64/256 season plan."""
    import tune_charts

    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "games_per_team_per_season": 17,
                "training_seed": 8306,
                "validation_seed": 908306,
                "max_iterations": 1,
                "targets": {
                    "completion_rate": {"value": 0.65, "tolerance": 0.01}
                },
                "bounds": {
                    "pass_completion_adjustment": {
                        "minimum": -0.08,
                        "maximum": 0.08,
                        "step": 0.005,
                    }
                },
                "generator_command": ["generate", "{profile}"],
                "training_command": ["train", "{report}"],
                "validation_command": ["validate", "{report}"],
            }
        ),
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    def fake_run(config_value, **kwargs):
        observed.update(kwargs)
        return {
            "selected_profile": {"pass_completion_adjustment": 0.005},
            "validation": {"within_tolerance": True, "loss": 0.25},
        }

    monkeypatch.setattr(tune_charts, "run_tuning", fake_run)

    assert tune_charts.main(
        ["--config", str(config), "--workspace", str(tmp_path / "work")]
    ) == 0
    assert observed["training_seasons"] == 64
    assert observed["validation_seasons"] == 256
    assert "validation passed" in capsys.readouterr().out.lower()
