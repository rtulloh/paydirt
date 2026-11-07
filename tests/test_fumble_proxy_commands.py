"""Experimental proxy CLI wiring and retained provenance use synthetic 2026 only."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tests.test_fumble_source_projection import PROXY, reviewed_credit
from tests.test_generate_nflverse_charts import _play, _stats


@pytest.mark.parametrize("compound", [False, True])
def test_nflverse_command_retains_proxy_ledger_and_rejects_compound(
    tmp_path: Path, compound: bool,
) -> None:
    import generate_nflverse_charts as command

    stats, template = tmp_path / "stats", tmp_path / "template"
    stats.mkdir()
    template.mkdir()
    (template / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n")
    for name, short in (("Alphas", "AAA"), ("Betas", "BBB")):
        (stats / f"{name}.json").write_text(json.dumps(_stats(name, short)))
        (template / name).mkdir()
    mapping = tmp_path / "teams.json"
    mapping.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
    rows = [_play(i, "AAA" if i < 13 else "BBB", "BBB" if i < 13 else "AAA") for i in range(1, 25)]
    for i in (0, 12):
        rows[i].update(fumble=1, fumble_lost=0, yards_gained=0, fumbled_1_team=rows[i]["posteam"])
    if compound:
        rows[0]["fumbled_2_team"] = "AAA"
    source = tmp_path / "plays.csv"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set().union(*(row.keys() for row in rows))))
        writer.writeheader()
        writer.writerows(rows)
    audit, output = tmp_path / "audit", tmp_path / "output"
    argv = ["--pbp", str(source), "--stats-dir", str(stats), "--template-season", str(template),
            "--team-map", str(mapping), "--audit-dir", str(audit), "--output", str(output),
            "--fumble-gain-policy", PROXY]
    if compound:
        with pytest.raises(ValueError, match="Unsupported source fields"):
            command.main(argv)
        assert not (output / "generation-manifest.json").exists()
        unsupported = json.loads((audit / "unsupported-source-fields.json").read_text())
        assert any(record["field"] == "fumble_ownership" for record in unsupported)
    else:
        assert command.main(argv) == 0
        manifest = json.loads((output / "generation-manifest.json").read_text())
        assert manifest["fumble_gain_model"]["policy"] == PROXY
        assert manifest["fumble_gain_model"]["projected_events"] == 2
        assert manifest["fumble_gain_model"]["physical_initial_truth_verified"] is False
    ledger = json.loads((audit / "fumble-gain-projections.json").read_text())
    assert ledger["policy"] == PROXY
    assert len(ledger["events"]) == (1 if compound else 2)
    assert all(event["source_facts"]["physical_initial_yards"] is None for event in ledger["events"])
    assert all(event["modeled_gain_basis"] == "credited_proxy" for event in ledger["events"])


def test_pfr_directory_retains_reviewed_credit_and_projection_ledger(tmp_path: Path, monkeypatch) -> None:
    import generate_pfr_charts as command
    from paydirt.pfr_event_reconciliation import load_event_reconciliations

    game, _facts = reviewed_credit(tmp_path)
    source_dir = tmp_path / "html"
    source_dir.mkdir()
    (source_dir / f"{game.game_id}.html").write_bytes(b"synthetic raw HTML")
    monkeypatch.setattr(command, "parse_pfr_boxscore", lambda _text, _identity: game)
    ledger = tmp_path / "ledger.json"
    plays, _fg, fumbles, _diagnostics, games, _rows = command._classify_directory(
        source_dir, None, 8306, ledger,
        event_reconciliations=load_event_reconciliations(tmp_path / "events.json"),
        fumble_gain_policy=PROXY,
    )
    assert games == 1 and len(fumbles) == len(plays) == 1
    record = json.loads(ledger.read_text())
    assert record["fumble_gain_policy"] == PROXY
    gain = record["games"][0]["fumble_gain_projections"][0]
    assert gain["source_facts"]["physical_initial_yards"] is None
    assert gain["source_facts"]["credited_yards"] == gain["modeled_initial_yards"] == 0
    assert record["games"][0]["event_reconciliations"][0]["credited_kind"] == "rushing"


def test_pfr_command_binds_explicit_proxy_before_classification(tmp_path: Path, monkeypatch) -> None:
    import generate_pfr_charts as command

    class StopAfterBinding(Exception):
        pass

    mapping = tmp_path / "teams.json"
    mapping.write_text('{"FOX": "Synthetic"}')
    def classify(*_args, **kwargs):
        assert kwargs["fumble_gain_policy"] == PROXY
        raise StopAfterBinding
    monkeypatch.setattr(command, "_classify_directory", classify)
    with pytest.raises(StopAfterBinding):
        command.main(["--html-dir", str(tmp_path), "--stats-dir", str(tmp_path),
                      "--template-season", str(tmp_path), "--team-map", str(mapping),
                      "--output", str(tmp_path / "output"), "--audit-dir", str(tmp_path / "audit"),
                      "--fumble-gain-policy", PROXY])
