"""Synthetic CLI controls; never load historical charts or audit reports."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def cli():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_1977_release.py"
    spec = importlib.util.spec_from_file_location("audit_1977_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    paths = {name: root / name for name in ["season", "public", "stats", "reproduced"]}
    for directory in paths.values():
        directory.mkdir()
    for name in ["contract.json", "engine.json", "engine.json.gz", "policy.json"]:
        (root / name).write_text("synthetic input")
    source = root / "raw.html"
    source.write_text("synthetic source")
    mapping = root / "inputs.json"
    mapping.write_text(json.dumps({"play_by_play/raw.html": "raw.html"}))
    output = root / "audit.json"
    arguments = ["--root", str(root), "--season-dir", str(paths["season"]),
                 "--contract", str(root / "contract.json"), "--engine-report", str(root / "engine.json"),
                 "--policy", str(root / "policy.json"), "--public-season-dir", str(paths["public"]),
                 "--stats-dir", str(paths["stats"]), "--reproduced-dir", str(paths["reproduced"]),
                 "--input-files", str(mapping), "--output", str(output)]
    return root, paths, mapping, output, arguments


def stub_gate(cli, monkeypatch, result):
    calls = []
    def gate(*args, **kwargs):
        calls.append((args, kwargs))
        return result
    monkeypatch.setattr(cli, "audit_statistical_release_exception", gate)
    return calls


@pytest.mark.parametrize("report", ["engine.json", "engine.json.gz"])
def test_computes_gate_from_input_paths_and_writes_exclusive_report(cli, inputs, monkeypatch, report):
    root, paths, _, output, args = inputs
    args[args.index("--engine-report") + 1] = str(root / report)
    calls = stub_gate(cli, monkeypatch, {"passed": True, "release_certified": False})
    assert cli.main(args) == 0
    assert json.loads(output.read_text()) == {"passed": True, "release_certified": False}
    assert calls == [((root, paths["season"], root / "contract.json", root / report, root / "policy.json"),
                      {"public_dir": paths["public"], "stats_dir": paths["stats"],
                       "reproduced_dir": paths["reproduced"],
                       "input_files": {"play_by_play/raw.html": root / "raw.html"}})]


@pytest.mark.parametrize("passed", [False, 1, "yes", None])
def test_only_exact_true_passes(cli, inputs, monkeypatch, passed):
    _, _, _, output, args = inputs
    calls = stub_gate(cli, monkeypatch, {"passed": passed})
    assert cli.main(args) != 0
    assert len(calls) == 1
    assert json.loads(output.read_text())["passed"] == passed


def test_never_overwrites_existing_output(cli, inputs, monkeypatch):
    _, _, _, output, args = inputs
    output.write_text("preserve")
    calls = stub_gate(cli, monkeypatch, {"passed": True})
    assert cli.main(args) != 0
    assert output.read_text() == "preserve"
    assert calls == []


@pytest.mark.parametrize("directory", ["season", "public", "stats", "reproduced"])
def test_output_cannot_pollute_input_directories(cli, inputs, monkeypatch, directory):
    _, paths, _, _, args = inputs
    output = paths[directory] / "new.json"
    args[-1] = str(output)
    calls = stub_gate(cli, monkeypatch, {"passed": True})
    assert cli.main(args) != 0
    assert not output.exists()
    assert calls == []


def test_output_cannot_create_an_absent_mapped_source(cli, inputs, monkeypatch):
    root, _, mapping, _, args = inputs
    output = root / "not-yet-created.html"
    mapping.write_text(json.dumps({"raw/source": output.name}))
    args[-1] = str(output)
    calls = stub_gate(cli, monkeypatch, {"passed": True})
    assert cli.main(args) != 0
    assert not output.exists()
    assert calls == []


@pytest.mark.parametrize("text", ['[]', '{}', '{"a":null}', '{"":"a"}', '{"a":""}',
                                  '{"a":"one","a":"two"}', 'not json'])
def test_rejects_invalid_source_mapping(cli, inputs, monkeypatch, text):
    _, _, mapping, output, args = inputs
    mapping.write_text(text)
    calls = stub_gate(cli, monkeypatch, {"passed": True})
    assert cli.main(args) != 0
    assert calls == []
    assert not output.exists()


def test_rejects_supplied_component_results(cli, inputs, monkeypatch):
    _, _, _, output, args = inputs
    calls = stub_gate(cli, monkeypatch, {"passed": True})
    with pytest.raises(SystemExit) as error:
        cli.main([*args, "--component-results", "fake.json"])
    assert error.value.code != 0
    assert calls == []
    assert not output.exists()


def test_output_cannot_make_an_absent_source_into_directory(cli, inputs, monkeypatch):
    root, _, mapping, _, args = inputs
    source = root / "missing.html"
    mapping.write_text(json.dumps({"raw/source": source.name}))
    args[-1] = str(source / "audit.json")
    calls = stub_gate(cli, monkeypatch, {"passed": False})
    assert cli.main(args) != 0
    assert not source.exists()
    assert calls == []
