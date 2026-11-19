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


def test_source_bound_team_capture_decorator_is_valid_runtime() -> None:
    from paydirt.chart_runtime_identity import loaded_runtime_identity

    receipt = loaded_runtime_identity()
    assert "team_stats.py" in receipt["module_files"]
    assert len(receipt["definitions_sha256"]) == 64


@pytest.mark.parametrize("mutation", [
    "wrapper_code", "wrapper_defaults", "wrapper_globals", "original_code",
    "original_defaults", "original_globals", "forged_wrapped", "closure_target",
])
def test_team_capture_verifies_wrapper_and_original_independently(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    from types import FunctionType

    from paydirt.chart_runtime_identity import loaded_runtime_identity
    from paydirt.game_engine import PaydirtGameEngine

    wrapper = PaydirtGameEngine.kickoff
    original = wrapper.__wrapped__

    def cell(value: Any) -> Any:
        return (lambda: value).__closure__[0]

    if mutation == "wrapper_code":
        monkeypatch.setattr(wrapper, "__code__", wrapper.__code__.replace(co_filename="/forged.py"))
    elif mutation == "wrapper_defaults":
        monkeypatch.setattr(wrapper, "__defaults__", (True,))
    elif mutation == "wrapper_globals":
        replacement = FunctionType(wrapper.__code__, dict(wrapper.__globals__), closure=wrapper.__closure__)
        replacement.__dict__.update(wrapper.__dict__)
        monkeypatch.setattr(PaydirtGameEngine, "kickoff", replacement)
    elif mutation == "original_code":
        monkeypatch.setattr(original, "__code__", original.__code__.replace(co_filename="/forged.py"))
    elif mutation == "original_defaults":
        monkeypatch.setattr(original, "__defaults__", (False, False))
    elif mutation == "original_globals":
        replacement = FunctionType(original.__code__, dict(original.__globals__), argdefs=original.__defaults__)
        monkeypatch.setattr(wrapper, "__wrapped__", replacement)
        altered = FunctionType(wrapper.__code__, wrapper.__globals__, closure=(cell(replacement),))
        altered.__dict__.update(wrapper.__dict__)
        monkeypatch.setattr(PaydirtGameEngine, "kickoff", altered)
    elif mutation == "forged_wrapped":
        monkeypatch.setattr(wrapper, "__wrapped__", lambda: None)
    else:
        altered = FunctionType(wrapper.__code__, wrapper.__globals__, closure=(cell(lambda: None),))
        altered.__dict__.update(wrapper.__dict__)
        monkeypatch.setattr(PaydirtGameEngine, "kickoff", altered)
    with pytest.raises(RuntimeError, match="Invalid loaded runtime"):
        loaded_runtime_identity()


@pytest.mark.parametrize("constant", ["MAX_FIELDS", "SIGNED_TEAM_FIELDS", "PASS_PLAYS"])
def test_capture_helper_policy_constants_are_source_bound(
    monkeypatch: pytest.MonkeyPatch, constant: str,
) -> None:
    from paydirt import offense_stats, team_stats
    from paydirt.chart_runtime_identity import loaded_runtime_identity

    loaded_runtime_identity()
    if constant != "PASS_PLAYS":
        monkeypatch.setattr(team_stats, constant, frozenset())
        with pytest.raises(RuntimeError, match="loaded constant differs"):
            loaded_runtime_identity()
    else:
        # Preserve shared import identity: the policy set itself changed.
        before = set(offense_stats.PASS_PLAYS)
        try:
            offense_stats.PASS_PLAYS.clear()
            with pytest.raises(RuntimeError, match="loaded constant differs"):
                loaded_runtime_identity()
        finally:
            offense_stats.PASS_PLAYS.update(before)


def test_capture_helper_cannot_execute_with_foreign_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import FunctionType

    from paydirt import team_stats
    from paydirt.chart_runtime_identity import loaded_runtime_identity

    original = team_stats._commit
    altered = FunctionType(original.__code__, {**original.__globals__, "add": lambda *args: None},
                           original.__name__, original.__defaults__, original.__closure__)
    monkeypatch.setattr(team_stats, "_commit", altered)
    with pytest.raises(RuntimeError, match="loaded globals differ"):
        loaded_runtime_identity()


def test_capture_receipt_is_stable_across_python_hash_seeds() -> None:
    import json
    import subprocess

    program = (
        "import json; from paydirt.chart_runtime_identity import loaded_runtime_identity; "
        "print(json.dumps(loaded_runtime_identity(), sort_keys=True))"
    )
    receipts = []
    for seed in ("1", "42"):
        completed = subprocess.run(
            [sys.executable, "-c", program], check=True, capture_output=True, text=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        receipts.append(json.loads(completed.stdout))
    assert receipts[0] == receipts[1]
    assert {"team_stats.py", "offense_stats.py", "kicking_stats.py"} <= set(receipts[0]["module_files"])


def test_capture_factory_cannot_execute_with_foreign_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import FunctionType

    from paydirt import game_engine, team_stats
    from paydirt.chart_runtime_identity import loaded_runtime_identity

    original = team_stats.capture_team_play
    altered = FunctionType(original.__code__, dict(original.__globals__), original.__name__)
    monkeypatch.setattr(team_stats, "capture_team_play", altered)
    monkeypatch.setattr(game_engine, "capture_team_play", altered)
    with pytest.raises(RuntimeError, match="loaded globals differ"):
        loaded_runtime_identity()



@pytest.mark.parametrize("tampered", [False, True])
def test_team_capture_accepts_python310_compiled_nested_name(
    monkeypatch: pytest.MonkeyPatch, tampered: bool,
) -> None:
    from paydirt import chart_runtime_identity as identity

    path = Path(identity.__file__).resolve().with_name("team_stats.py")
    identity._source_expectations(path)
    data, tree, dependencies, compiled = identity._source_cache[path]
    compiled = dict(compiled)
    qualified_key = "capture_team_play.<locals>.wrapped"
    fallback_key = "capture_team_play.wrapped"
    if qualified_key in compiled:
        compiled[fallback_key] = compiled.pop(qualified_key)
    assert fallback_key in compiled
    if tampered:
        compiled["capture_team_play.wrapped"] = {"not-the-source-wrapper-hash"}
    # Python 3.10 lacks co_qualname and the existing recursive compiler index
    # therefore spells the same verified source code with this qualified key.
    monkeypatch.setitem(identity._source_cache, path, (data, tree, dependencies, compiled))
    if tampered:
        with pytest.raises(RuntimeError, match="loaded capture wrapper differs"):
            identity.loaded_runtime_identity()
    else:
        assert identity.loaded_runtime_identity()["definitions_sha256"]
