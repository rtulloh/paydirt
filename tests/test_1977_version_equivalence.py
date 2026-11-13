"""Synthetic exact-byte controls for the reviewed release-version equivalence."""

import hashlib
import subprocess
from copy import deepcopy

import pytest

from paydirt import chart_release_gate as gate


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(files: dict[str, bytes]) -> str:
    return sha(
        b"".join(name.encode() + b"\0" + data + b"\0" for name, data in sorted(files.items()))
    )


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    files = {
        "__init__.py": b'__version__ = "old"\n',
        "__main__.py": b'version = "old"\n',
        "game.py": b"x = 1\n",
    }
    package = tmp_path / "paydirt"
    package.mkdir()
    for name, data in files.items():
        (package / name).write_bytes(data)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "synthetic baseline",
    )
    updated = {
        name: data.replace(b'"old"', b'"new"') if name.startswith("__") else data
        for name, data in files.items()
    }
    for name, data in updated.items():
        (package / name).write_bytes(data)
    pin = {
        "commit": git("rev-parse", "HEAD"),
        "season": 2026,
        "report_fingerprint": fingerprint(files),
        "actual_fingerprint": fingerprint(updated),
        "files": {
            name: (sha(files[name]), sha(updated[name])) for name in files if name.startswith("__")
        },
    }
    identity = {"python": "synthetic", "definitions_sha256": "same"}
    report = {
        "metadata": {
            "engine_fingerprint": fingerprint(files),
            "runtime_identity": identity,
            "worker_runtime_identities": [identity] * 72,
            "repetitions": 72,
        }
    }
    monkeypatch.setattr(gate, "VERSION_ONLY_1977_RUNTIME", pin, raising=False)
    monkeypatch.setattr(gate, "__file__", str(package / "chart_release_gate.py"))
    monkeypatch.setattr(
        gate,
        "engine_fingerprint",
        lambda: fingerprint({p.name: p.read_bytes() for p in package.glob("*.py")}),
    )
    monkeypatch.setattr(gate, "loaded_runtime_identity", lambda: deepcopy(identity), raising=False)
    return tmp_path, report, updated


def check(runtime, season=2026):
    helper = getattr(gate, "_version_only_1977_validation_view", None)
    assert callable(helper), "Exact version-only equivalence is not implemented"
    return helper(runtime[0], runtime[1], season)


def test_exact_version_only_view_preserves_raw_evidence(runtime):
    original = deepcopy(runtime[1])
    view, receipt = check(runtime)
    assert runtime[1] == original
    assert view["metadata"]["engine_fingerprint"] != original["metadata"]["engine_fingerprint"]
    assert receipt["report_engine_fingerprint"] == original["metadata"]["engine_fingerprint"]
    assert receipt["actual_engine_fingerprint"] == view["metadata"]["engine_fingerprint"]
    assert receipt["unchanged_source_files"] == 1
    assert len(receipt["accepted_version_files"]) == 2


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "version",
        "extra",
        "missing",
        "symlink",
        "runtime",
        "worker",
        "report",
        "season",
        "root",
        "baseline",
    ],
)
def test_every_unreviewed_difference_fails(runtime, mutation):
    root, report, _ = runtime
    package = root / "paydirt"
    if mutation == "source":
        (package / "game.py").write_text("x = 2\n")
    elif mutation == "version":
        (package / "__init__.py").write_text('__version__ = "future"\n')
    elif mutation == "extra":
        (package / "extra.py").write_text("x = 1\n")
    elif mutation == "missing":
        (package / "game.py").unlink()
    elif mutation == "symlink":
        (root / "copy.py").write_bytes((package / "game.py").read_bytes())
        (package / "game.py").unlink()
        (package / "game.py").symlink_to(root / "copy.py")
    elif mutation == "runtime":
        report["metadata"]["runtime_identity"] = {}
    elif mutation == "worker":
        report["metadata"]["worker_runtime_identities"] = [{}] * 72
    elif mutation == "report":
        report["metadata"]["engine_fingerprint"] = "wrong"
    elif mutation == "baseline":
        gate.VERSION_ONLY_1977_RUNTIME["commit"] = "0" * 40
    elif mutation == "root":
        runtime = (root / "other", report, {})
    with pytest.raises(ValueError):
        check(runtime, season=0 if mutation == "season" else 2026)


def test_current_identity_needs_no_allowance(runtime):
    runtime[1]["metadata"]["engine_fingerprint"] = gate.engine_fingerprint()
    view, receipt = check(runtime)
    assert view is runtime[1]
    assert receipt is None
