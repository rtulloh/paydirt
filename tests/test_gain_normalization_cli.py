"""Both source commands reproduce derived gains without hand-edited factors."""
import csv
import importlib
import json
from pathlib import Path

import pytest

from tests.test_generate_nflverse_charts import _play, _stats
from tests.test_pfr_play_by_play import _game_html, _row


def source_inputs(tmp_path: Path, source: str) -> tuple[list[str], Path]:
    stats = tmp_path / "stats"
    template = tmp_path / "2026-template"
    stats.mkdir()
    template.mkdir()
    (template / "2026.yaml").write_bytes(
        (Path(__file__).resolve().parents[1] / "seasons/2026/2026.yaml").read_bytes())
    for team, short in (("Alphas", "AAA"), ("Betas", "BBB")):
        (stats / f"{team}.json").write_text(json.dumps(_stats(team, short)))
        (template / team).mkdir()
    mapping = tmp_path / "mapping.json"
    if source == "nflverse":
        mapping.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
        pbp = tmp_path / "plays.csv"
        rows = [_play(i, "AAA" if i < 13 else "BBB", "BBB" if i < 13 else "AAA")
                for i in range(1, 25)]
        with pbp.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        flags = ["--pbp", str(pbp)]
        schedule = [{"away": "Alphas", "home": "Betas"}]
    else:
        mapping.write_text(json.dumps({"PHI": "Alphas", "SFO": "Betas"}))
        html = tmp_path / "html"
        html.mkdir()
        game = _game_html(_row(1, "1", "10", "PHI 20",
                              '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 4 yards'))
        (html / "202609010alpha.htm").write_text(game)
        (html / "202609020beta.htm").write_text(
            game.replace("PHI", "TMP").replace("SFO", "PHI").replace("TMP", "SFO"))
        flags = ["--html-dir", str(html)]
        schedule = [{"away": "Alphas", "home": "Betas"},
                    {"away": "Betas", "home": "Alphas"}]
    contract = tmp_path / "source-contract.json"
    contract.write_text(json.dumps({
        "season": 2026, "schedule": schedule,
        "targets": {metric: {"value": value, "tolerance": .01} for metric, value in (
            ("completion_rate", .65), ("interception_rate", .02), ("sack_rate", .07),
            ("yards_per_pass_attempt", 7.5), ("rushing_yards_per_attempt", 4.5))},
    }))
    return [*flags, "--stats-dir", str(stats), "--template-season", str(template),
            "--team-map", str(mapping)], contract


@pytest.mark.parametrize("source", ["nflverse", "pfr"])
def test_source_fixture_generates_without_normalization(tmp_path: Path, source: str) -> None:
    module = importlib.import_module(f"generate_{source}_charts")
    arguments, _ = source_inputs(tmp_path, source)
    output = tmp_path / "2026-control"
    assert module.main([*arguments, "--output", str(output),
                        "--audit-dir", str(tmp_path / "audit")]) == 0
    assert {path.name for path in output.iterdir() if path.is_dir()} == {"Alphas", "Betas"}


@pytest.mark.parametrize("source", ["nflverse", "pfr"])
def test_normalized_source_command_reproduces_complete_csvs(tmp_path: Path, source: str) -> None:
    module = importlib.import_module(f"generate_{source}_charts")
    arguments, contract = source_inputs(tmp_path, source)
    manifests = []
    for attempt in (1, 2):
        output, audit = tmp_path / f"2026-final-{attempt}", tmp_path / f"audit-{attempt}"
        options = (["--output", str(output), "--audit-dir", str(audit),
                    "--gain-normalization-contract", str(contract)] if attempt == 1 else [
                        f"--output={output}", f"--audit-dir={audit}",
                        f"--gain-normalization-contract={contract}"])
        assert module.main([*arguments, *options]) == 0
        manifest = json.loads((output / "generation-manifest.json").read_text())
        recipe = manifest["gain_normalization"]
        assert recipe["fit_accepted"] is False
        assert recipe["training"]["repetitions"] == 16
        assert recipe["training"]["validation_passed"] is True
        assert recipe["source_contract_sha256"]
        assert set(recipe["derivation"]["cohort"]) == {"Alphas", "Betas"}
        assert all(team["gain_normalization"]["protected_mass_preserved"]
                   for team in manifest["teams"].values())
        assert "normalization_contract/source-contract.json" in manifest["input_hashes"]
        assert (audit / "gain-normalization-training.json").is_file()
        manifests.append(manifest)
    assert manifests[0] == manifests[1]
    for path in (tmp_path / "2026-final-1").glob("*/*.csv"):
        assert path.read_bytes() == (tmp_path / "2026-final-2" / path.relative_to(
            tmp_path / "2026-final-1")).read_bytes()
