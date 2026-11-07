"""Public/synthetic training recipes must measure the whole declared cohort."""
import importlib
import json
import shutil
from pathlib import Path

import pytest

from paydirt.chart_generator import TeamSeasonStats

PUBLIC = Path(__file__).resolve().parents[1] / "seasons/2026"


def inputs(tmp_path: Path) -> tuple[Path, dict[str, TeamSeasonStats]]:
    contract = tmp_path / "source-contract.json"
    contract.write_text(json.dumps({
        "season": 2026,
        "schedule": [{"away": "Ironclads", "home": "Thunderhawks"}],
        "targets": {metric: {"value": value, "tolerance": .001} for metric, value in (
            ("completion_rate", .65), ("interception_rate", .02), ("sack_rate", .07),
            ("yards_per_pass_attempt", 7), ("rushing_yards_per_attempt", 4.5))},
    }))
    stats = {}
    for name in ("Ironclads", "Thunderhawks"):
        import yaml
        short = yaml.safe_load((PUBLIC / name / "team.yaml").read_text())["short_name"]
        stats[name] = TeamSeasonStats.from_dict({
            "season": 2026, "team_name": name, "short_name": short,
            "offense": {"rushing": {"attempts": 400, "yards": 1800},
                        "passing": {"attempts": 500, "yards": 3500, "completions": 325}},
        })
    return contract, stats


def baseline_command(argv: list[str]) -> int:
    destination = Path(argv[argv.index("--output") + 1])
    assert "--gain-normalization-contract" not in argv
    shutil.copytree(PUBLIC, destination)
    (destination / "generation-manifest.json").write_text(json.dumps({
        "season": 2026, "teams": {name: {} for name in ("Ironclads", "Thunderhawks")},
        "calibration_profile": {},
    }))
    return 0


def test_public_baseline_fixture_has_complete_source_schedule(tmp_path: Path) -> None:
    contract, stats = inputs(tmp_path)
    assert set(stats) == {team for game in json.loads(contract.read_text())["schedule"]
                          for team in game.values()}
    assert all(row.offense.passing.attempts > 0 for row in stats.values())


def test_recipe_replays_fixed_complete_training_and_derives_every_team(tmp_path: Path) -> None:
    module = importlib.import_module("paydirt.gain_recipe")
    contract, stats = inputs(tmp_path)
    result = module.prepare_gain_recipe(
        baseline_command, ["--output", str(tmp_path / "final"), "--audit-dir", "unused",
                           "--gain-normalization-contract", str(contract)],
        audit_dir=tmp_path / "audit", contract_path=contract, stats=stats, workers=1)
    assert result["derivation"]["cohort"] == sorted(stats)
    assert result["training"]["repetitions"] == 16
    assert result["training"]["seed"] == 20261108
    assert result["training"]["games"] == 16
    assert result["training"]["validation_passed"] is True
    assert result["training"]["policy"] == "chart-focused"
    assert result["training"]["attempt_end_zone_interception_returns"] is True
    assert result["fit_accepted"] is False
    assert (tmp_path / "audit/gain-normalization-training.json").is_file()
    for metric in ("passing", "rushing"):
        assert set(result["derivation"]["metrics"][metric]["teams"]) == set(stats)


@pytest.mark.parametrize("mutation", [
    "missing_team", "wrong_season", "circular_identity", "missing_targets", "unknown_field",
])
def test_recipe_rejects_invalid_source_scope_before_generating(
    tmp_path: Path, mutation: str,
) -> None:
    module = importlib.import_module("paydirt.gain_recipe")
    contract, stats = inputs(tmp_path)
    data = json.loads(contract.read_text())
    if mutation == "missing_team":
        stats.pop("Ironclads")
    elif mutation == "wrong_season":
        data["season"] = 2025
    elif mutation == "circular_identity":
        data["generation_manifest_sha256"] = "0" * 64
    elif mutation == "missing_targets":
        del data["targets"]
    else:
        data["hand_multiplier"] = 1.1
    contract.write_text(json.dumps(data))
    def forbidden_command(argv: list[str]) -> int:
        pytest.fail("Unsupported inputs must fail before baseline generation")
    with pytest.raises(ValueError):
        module.prepare_gain_recipe(forbidden_command, [], audit_dir=tmp_path / "audit",
                                   contract_path=contract, stats=stats, workers=1)


def test_recipe_never_reuses_existing_training_outputs(tmp_path: Path) -> None:
    module = importlib.import_module("paydirt.gain_recipe")
    contract, stats = inputs(tmp_path)
    directory = tmp_path / "audit/gain-normalization-baseline"
    directory.mkdir(parents=True)
    marker = directory / "preserve"
    marker.write_text("existing evidence")
    with pytest.raises(ValueError, match="existing"):
        module.prepare_gain_recipe(baseline_command, [], audit_dir=tmp_path / "audit",
                                   contract_path=contract, stats=stats, workers=1)
    assert marker.read_text() == "existing evidence"
