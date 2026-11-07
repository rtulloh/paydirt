"""Portable staging preserves input bytes and rejects unsafe archive members."""
from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def public_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "public-bundle"
    for name, data in {"inputs/synthetic/source.csv": "Public synthetic input\n", "recipe.json": "{}",
                       "contract.json": "{}", "template/2026/2026.yaml": "season: 2026\n"}.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    files = {path.relative_to(bundle).as_posix(): digest(path) for path in bundle.rglob("*") if path.is_file()}
    (bundle / "inventory.json").write_text(json.dumps({"schema_version": 1, "files": files}))
    return bundle


def archive_module() -> object:
    module = importlib.import_module("paydirt.chart_source_bundle")
    assert hasattr(module, "pack_chart_sources") and hasattr(module, "unpack_chart_sources"), "Maintained safe source staging is required"
    return module


def test_source_archive_is_deterministic_and_relocates_complete_bound_bytes(public_bundle: Path) -> None:
    module = archive_module()
    first, second = (public_bundle.parent / name for name in ("first.tar.gz", "second.tar.gz"))
    packed = module.pack_chart_sources(public_bundle, first)
    assert packed["sha256"] == digest(first)
    assert packed["release_certified"] is False
    module.pack_chart_sources(public_bundle, second)
    assert first.read_bytes() == second.read_bytes()
    destination = public_bundle.parent / "relocated"
    staged = module.unpack_chart_sources(first, packed["sha256"], destination)
    assert staged["release_certified"] is False
    assert {path.relative_to(destination).as_posix(): path.read_bytes() for path in destination.rglob("*") if path.is_file()} == {
        path.relative_to(public_bundle).as_posix(): path.read_bytes() for path in public_bundle.rglob("*") if path.is_file()}


@pytest.mark.parametrize("mutation", ["changed-bytes", "invalid-inventory", "extra-file", "symlink", "existing-archive", "archive-in-bundle"])
def test_packing_preserves_existing_files_and_rejects_unbound_sources(public_bundle: Path, mutation: str) -> None:
    module = archive_module()
    archive = public_bundle.parent / "source.tar.gz"
    if mutation == "changed-bytes": (public_bundle / "inputs/synthetic/source.csv").write_text("Changed\n")
    elif mutation == "invalid-inventory": (public_bundle / "inventory.json").write_text('{"schema_version":1,"files":{},"files":{}}')
    elif mutation == "extra-file": (public_bundle / "extra.txt").write_text("Unbound\n")
    elif mutation == "symlink": (public_bundle / "link").symlink_to(public_bundle / "recipe.json")
    elif mutation == "existing-archive": archive.write_text("Preserve\n")
    elif mutation == "archive-in-bundle": archive = public_bundle / "source.tar.gz"
    before = {path: path.read_bytes() for path in public_bundle.parent.rglob("*") if path.is_file()}
    with pytest.raises((ValueError, OSError)):
        module.pack_chart_sources(public_bundle, archive)
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize("mutation", [
    "wrong-digest", "invalid-digest", "existing-destination", "symlink-destination", "traversal", "absolute",
    "backslash", "normalized-alias", "duplicate", "symlink", "hardlink", "device", "directory",
    "file-parent", "missing-inventory", "changed-member", "unexpected-member",
])
def test_staging_rejects_unsafe_or_changed_archives_without_writing_outside_destination(
    public_bundle: Path, mutation: str,
) -> None:
    module = archive_module()
    archive = public_bundle.parent / "source.tar.gz"
    members = [(path.relative_to(public_bundle).as_posix(), path.read_bytes(), tarfile.REGTYPE)
               for path in public_bundle.rglob("*") if path.is_file()]
    if mutation == "traversal": members += [("../outside.txt", b"Unsafe", tarfile.REGTYPE)]
    elif mutation == "absolute": members += [(str(public_bundle.parent / "outside.txt"), b"Unsafe", tarfile.REGTYPE)]
    elif mutation == "backslash": members += [("inputs\\alias.txt", b"Unsafe", tarfile.REGTYPE)]
    elif mutation == "normalized-alias": members += [("inputs/./alias.txt", b"Unsafe", tarfile.REGTYPE)]
    elif mutation == "duplicate": members += [members[0]]
    elif mutation in {"symlink", "hardlink", "device", "directory"}:
        kind = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "device": tarfile.CHRTYPE, "directory": tarfile.DIRTYPE}[mutation]
        members += [("inputs/unsafe", b"", kind)]
    elif mutation == "file-parent": members += [("inputs", b"Collision", tarfile.REGTYPE)]
    elif mutation == "missing-inventory": members = [member for member in members if member[0] != "inventory.json"]
    elif mutation == "changed-member": members = [(name, b"Changed" if name.endswith("source.csv") else data, kind) for name, data, kind in members]
    elif mutation == "unexpected-member": members += [("private-reference.csv", b"Unbound", tarfile.REGTYPE)]
    with tarfile.open(archive, "w:gz") as stream:
        for name, data, kind in members:
            member = tarfile.TarInfo(name); member.type = kind; member.size = len(data)
            member.linkname = "../outside.txt" if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE} else ""
            stream.addfile(member, io.BytesIO(data))
    expected = digest(archive)
    destination = public_bundle.parent / "staged"
    if mutation == "wrong-digest": expected = "0" * 64
    elif mutation == "invalid-digest": expected = "invalid"
    elif mutation == "existing-destination": destination.mkdir(); (destination / "keep.txt").write_text("Preserve\n")
    elif mutation == "symlink-destination": destination.symlink_to(public_bundle, target_is_directory=True)
    before = {path: path.read_bytes() for path in public_bundle.parent.rglob("*") if path.is_file()}
    with pytest.raises((ValueError, OSError, tarfile.TarError)):
        module.unpack_chart_sources(archive, expected, destination)
    assert not (public_bundle.parent / "outside.txt").exists()
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize("valid", [True, False])
def test_staging_cli_reports_real_verdict_without_certifying_readiness(
    public_bundle: Path, capsys: pytest.CaptureFixture, valid: bool,
) -> None:
    import importlib.util
    assert importlib.util.find_spec("scripts.stage_chart_sources") is not None, "CI needs a maintained archive-staging command"
    module = archive_module()
    cli = importlib.import_module("scripts.stage_chart_sources")
    archive = public_bundle.parent / "source.tar.gz"
    module.pack_chart_sources(public_bundle, archive)
    destination = public_bundle.parent / "staged"
    assert cli.main(["--archive", str(archive), "--sha256", digest(archive) if valid else "0" * 64,
                     "--destination", str(destination)]) == (0 if valid else 1)
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is valid and report["release_certified"] is False
    if not valid:
        assert report["errors"] and not destination.exists()


@pytest.mark.parametrize("workflow", ["test.yml", "release.yml"])
def test_quality_workflows_stage_pinned_sources_and_regenerate_before_the_gate(workflow: str) -> None:
    text = (Path(__file__).resolve().parents[1] / ".github/workflows" / workflow).read_text()
    quality = text[text.index("  chart-quality:"):].split("\n  build:")[0]
    assert "scripts/stage_chart_sources.py" in quality, "Source bytes must be staged before the component gate"
    assert "scripts/prepare_chart_sources.py" in quality
    assert quality.index("scripts/stage_chart_sources.py") < quality.index("scripts/prepare_chart_sources.py") < quality.index("scripts/audit_generated_charts.py")
    assert "CHART_SOURCES_" in quality and "--sha256" in quality
    assert "--engine-only" not in quality and "continue-on-error" not in quality


@pytest.mark.parametrize("workflow", ["test.yml", "release.yml"])
@pytest.mark.parametrize("url, sha", [("", ""), ("https://example.invalid/reviewed.tar.gz", ""), ("", "0" * 64)])
def test_workflow_missing_approval_bindings_fails_before_download(
    tmp_path: Path, workflow: str, url: str, sha: str,
) -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows" / workflow
    job = yaml.safe_load(workflow_path.read_text())["jobs"]["chart-quality"]
    step = next(step for step in job["steps"] if "scripts/stage_chart_sources.py" in step.get("run", ""))
    script = step["run"].replace("${{ matrix.season }}", "2026")
    environment = dict(os.environ, SOURCE_URL=url, SOURCE_SHA256=sha)
    result = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=environment,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "repository variables are required" in result.stderr
    assert not (tmp_path / ".ai-audits").exists()
