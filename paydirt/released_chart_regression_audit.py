"""Fail-closed regression for byte-identical, previously published chart seasons.

This is not new-chart source or historical-fit qualification. The trusted Git
objects bind the public sanitized provenance, charts, contracts and gameplay.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .chart_audit import audit_public_season

TRUSTED_RELEASES = {
    "v1.10.3": {
        "commit": "1467b11e151fe9981177890e2a7a6b805402b3f0",
        "seasons": {1983: ("seasons/1983-generated", 28), 2024: ("seasons/2024", 32)},
    },
}
# These tools generate or validate candidates; none is used to resolve a game.
GENERATION_VALIDATION_ONLY = frozenset({
    "paydirt/chart_generator.py", "paydirt/chart_source_bundle.py",
    "paydirt/generated_source_audit.py", "paydirt/historical_season.py",
    "paydirt/pfr_play_by_play.py", "paydirt/pfr_source_scope.py",
    "paydirt/released_chart_regression_audit.py", "paydirt/chart_release_gate.py",
})


def _git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), *args], stderr=subprocess.PIPE)


def _runtime_path(name: str) -> bool:
    return name.endswith(".py") and (name.startswith(("paydirt/", "paydirt-web/backend/")) or name == "paydirt_runner.py") and name not in GENERATION_VALIDATION_ONLY


def _has_symlink(root: Path, path: Path) -> bool:
    return any(part.is_symlink() for part in (path, *path.parents) if part != root and part.is_relative_to(root))


def _version_only(data: bytes, *, api_metadata: bool = False) -> str:
    tree = ast.parse(data)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "__version__" and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            node.value = ast.Constant(value="<release-version>")
    if api_metadata:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "FastAPI":
                for keyword in node.keywords:
                    if (keyword.arg == "version" and isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, str)):
                        keyword.value = ast.Constant(value="<release-version>")
    return ast.dump(tree, include_attributes=False)


def audit_released_season(root: Path, *, season: int) -> dict[str, Any]:
    """Check exact published inputs and unchanged gameplay, without private data."""
    root = Path(root).resolve()
    report: dict[str, Any] = {
        "passed": False, "season": season, "errors": [],
        "strict_fit_passed": False, "source_reproduction_checked": False,
        "historical_accuracy_checked": False, "gameplay_implementation_unchanged": False,
        "known_accuracy_exceptions": [],
        "frontend_implementation_identity_checked": False,
        "release_certified": False,
        "scope": "Unchanged published chart and authoritative engine/backend regression; frontend review and full browser/gameplay/AI regression additionally required",
    }
    selected = [(tag, entry) for tag, entry in TRUSTED_RELEASES.items() if season in entry["seasons"]]
    if len(selected) != 1:
        report["errors"].append("Season has no unique immutable released baseline; strict new-chart qualification required")
        return report
    tag, entry = selected[0]
    commit = entry["commit"]
    season_path, expected_teams = entry["seasons"][season]
    report.update({"baseline_tag": tag, "baseline_commit": commit})
    try:
        if _git(root, "rev-parse", f"refs/tags/{tag}^{{commit}}").decode().strip() != commit:
            raise ValueError("Release tag does not resolve to the pinned trusted commit")
        names = _git(root, "ls-tree", "-r", "--name-only", commit).decode().splitlines()
        season_names = {name for name in names if name.startswith(season_path + "/")}
        contract = f"config/chart-validation/{season}.json"
        if not season_names or contract not in names:
            raise ValueError("Trusted release lacks season or validation contract")
        actual = {str(path.relative_to(root)) for path in (root / season_path).rglob("*") if path.is_file() or path.is_symlink()}
        if actual != season_names:
            report["errors"].append("Season file inventory differs from trusted release")
        runtime = {name for name in names if _runtime_path(name)}
        current_runtime = {str(path.relative_to(root)) for directory in (root / "paydirt", root / "paydirt-web/backend") if directory.exists() for path in directory.rglob("*.py") if _runtime_path(str(path.relative_to(root)))}
        if (root / "paydirt_runner.py").exists():
            current_runtime.add("paydirt_runner.py")
        # Ignore bytecode/test cache directories, never arbitrary new runtime modules.
        current_runtime = {name for name in current_runtime if "/__pycache__/" not in name}
        if current_runtime != runtime:
            report["errors"].append("Gameplay implementation inventory changed; paired trusted-baseline qualification required")
        hashes = {}
        runtime_ok = current_runtime == runtime
        for name in sorted(season_names | {contract} | runtime):
            expected = _git(root, "show", f"{commit}:{name}")
            path = root / name
            actual_bytes = path.read_bytes() if path.is_file() and not _has_symlink(root, path) else None
            equal = actual_bytes == expected
            if name in {"paydirt/__init__.py", "paydirt/__main__.py", "paydirt-web/backend/main.py"} and actual_bytes is not None and not equal:
                api_metadata = name != "paydirt/__init__.py"
                equal = _version_only(actual_bytes, api_metadata=api_metadata) == _version_only(expected, api_metadata=api_metadata)
            if not equal:
                report["errors"].append(f"Trusted release content mismatch: {name}")
                if name in runtime:
                    runtime_ok = False
            if name in season_names or name == contract:
                hashes[name] = hashlib.sha256(expected).hexdigest()
        report["trusted_public_input_hashes"] = hashes
        report["gameplay_implementation_unchanged"] = runtime_ok
        trusted_contract = json.loads(_git(root, "show", f"{commit}:{contract}"))
        report["known_accuracy_exceptions"] = trusted_contract.get("known_accuracy_exceptions", [])
        if not report["errors"]:
            report["public_mechanics"] = audit_public_season(root / season_path, expected_teams=expected_teams)
            report["errors"].extend(report["public_mechanics"]["errors"])
    except (OSError, subprocess.CalledProcessError, ValueError, SyntaxError) as exc:
        report["errors"].append(str(exc))
    report["passed"] = not report["errors"]
    return report


def main(argv: list[str] | None = None) -> int:
    """Write a regression receipt; never emit private source inventories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if (not output.is_relative_to(root / ".ai-audits")
            or _has_symlink(root, args.output.absolute())
            or (output.exists() and output.stat().st_nlink != 1)):
        parser.error("Receipt output must remain under ignored .ai-audits/")
    result = audit_released_season(root, season=args.season)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Released season {args.season}: {'PASS' if result['passed'] else 'FAIL'}; {output}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
