"""Runtime expectations may reuse unchanged source without trusting stale state."""
from __future__ import annotations

import ast
import builtins
import importlib
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def runtime_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[ModuleType, ModuleType, ModuleType, Path]]:
    name = "identity_" + tmp_path.name.replace("-", "_")
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text("")
    source = Path(__file__).resolve().parents[1] / "paydirt/chart_runtime_identity.py"
    (package / source.name).write_bytes(source.read_bytes())
    (package / "worker.py").write_text("LIMIT = 3\ndef step(value=1):\n    return value + 1\n")
    (package / "chart_engine_audit.py").write_text(
        "from .worker import step\n"
        "from .chart_runtime_identity import loaded_runtime_identity\n"
        "def audit():\n    return step()\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = importlib.import_module(name + ".chart_runtime_identity")
    audit = importlib.import_module(name + ".chart_engine_audit")
    worker = importlib.import_module(name + ".worker")
    try:
        yield identity, audit, worker, package
    finally:
        for key in list(sys.modules):
            if key == name or key.startswith(name + "."):
                sys.modules.pop(key)


def test_unchanged_source_is_not_reparsed_or_recompiled(
    runtime_package: tuple, monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity, _audit, _worker, package = runtime_package
    expected = identity.loaded_runtime_identity()
    parses, compiles, reads = [], [], []
    parse, compile_source, read = ast.parse, builtins.compile, Path.read_bytes

    def parse_counted(source: Any, filename: str = "<unknown>", *args: Any, **kwargs: Any) -> ast.AST:
        if str(filename).startswith(str(package)):
            parses.append(filename)
        return parse(source, filename, *args, **kwargs)

    def compile_counted(source: Any, filename: str, *args: Any, **kwargs: Any) -> Any:
        if str(filename).startswith(str(package)):
            compiles.append(filename)
        return compile_source(source, filename, *args, **kwargs)

    def read_counted(path: Path) -> bytes:
        if path.parent == package:
            reads.append(path.name)
        return read(path)

    monkeypatch.setattr(ast, "parse", parse_counted)
    monkeypatch.setattr(builtins, "compile", compile_counted)
    monkeypatch.setattr(Path, "read_bytes", read_counted)
    assert identity.loaded_runtime_identity() == expected
    assert {"chart_engine_audit.py", "chart_runtime_identity.py", "worker.py"} <= set(reads)
    assert parses == [], "Unchanged source expectations should reuse their parsed syntax"
    assert compiles == [], "Unchanged source expectations should reuse their compiled code"


def test_warm_expectations_reject_same_size_same_mtime_source_change(runtime_package: tuple) -> None:
    identity, _audit, _worker, package = runtime_package
    identity.loaded_runtime_identity()
    path = package / "worker.py"
    before = path.stat()
    path.write_text(path.read_text().replace("value + 1", "value + 2"))
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert path.stat().st_size == before.st_size
    with pytest.raises(RuntimeError, match="loaded code differs"):
        identity.loaded_runtime_identity()


@pytest.mark.parametrize("mutation", ["code", "defaults", "constant", "alias", "origin", "closure"])
def test_warm_expectations_still_check_live_objects(
    runtime_package: tuple, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    identity, audit, worker, _package = runtime_package
    identity.loaded_runtime_identity()
    if mutation == "code":
        monkeypatch.setattr(worker.step, "__code__", worker.step.__code__.replace(co_filename="/changed.py"))
    elif mutation == "defaults":
        monkeypatch.setattr(worker.step, "__defaults__", (2,))
    elif mutation == "constant":
        monkeypatch.setattr(worker, "LIMIT", 4)
    elif mutation == "alias":
        monkeypatch.setattr(audit, "step", lambda: 1)
    elif mutation == "origin":
        monkeypatch.setattr(worker, "__file__", "/changed.py")
    else:
        # A replacement closure must never inherit the cached source identity.
        value = 1
        monkeypatch.setattr(worker, "step", lambda: value)
    with pytest.raises(RuntimeError, match="Invalid loaded runtime"):
        identity.loaded_runtime_identity()


def test_warm_source_graph_follows_added_relative_dependency(runtime_package: tuple) -> None:
    identity, _audit, worker, package = runtime_package
    before = identity.loaded_runtime_identity()
    (package / "extra.py").write_text("def extra():\n    return 7\n")
    path = package / "worker.py"
    path.write_text(path.read_text() + "from .extra import extra\n")
    importlib.invalidate_caches()
    importlib.reload(worker)
    # Reload its consumer as well, preserving the required live alias identity.
    importlib.reload(sys.modules[worker.__package__ + ".chart_engine_audit"])
    after = identity.loaded_runtime_identity()
    assert "extra.py" in after["module_files"] and "extra.py" not in before["module_files"]
    assert before["definitions_sha256"] != after["definitions_sha256"]
