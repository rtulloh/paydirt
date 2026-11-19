#!/usr/bin/env python3
"""Run the complete AGENTS.md pre-push regression and report a compact summary.

The command list is not duplicated here: the canonical steps come from
``paydirt.chart_release_gate.required_regression_commands(released_charts=True)``,
which is the same list the release gate audits. This script adds isolated E2E
ports, streamed per-step logs and a one-screen pass/fail summary suitable for
pasting into a session. Routine steps use public 1983/2024/2026 data only.

Typical use::

    python3 scripts/run_full_regression.py            # everything
    python3 scripts/run_full_regression.py --list     # plan only
    python3 scripts/run_full_regression.py --only core,lint

Logs and summaries are written under ignored ``.ai-audits/full-regression/``.
The script exits 0 only when every required step passes; ``2`` means the plan or
preflight was invalid and nothing ran.

Deliberately not automated:
- the 1977 release-policy audit (needs 11 explicit evidence paths, see
  docs/released-chart-regression.md#exact-1977-statistical-acceptance);
- per-issue tracker review after play-test/audit confirmation;
- publishing, tagging and published-artifact download verification.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paydirt.chart_release_gate import required_regression_commands

DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173
ISOLATED_BACKEND_BASE = 18000
ISOLATED_FRONTEND_BASE = 15173
TAIL_LINES = 15


@dataclass(frozen=True)
class Step:
    """One regression command with its working directory relative to the root."""

    name: str
    cwd: str
    argv: Sequence[str]
    note: str = ""


@dataclass
class StepResult:
    """Outcome of one executed, skipped or failed-to-start step."""

    name: str
    status: str  # "pass" | "fail" | "skip"
    seconds: float
    returncode: int | None = None
    log_path: Path | None = None
    reason: str = ""
    tail: list[str] = field(default_factory=list)


def regression_steps(
    root: Path,
    *,
    python: str = sys.executable,
    include_clean_checkout: bool = False,
) -> list[Step]:
    """Return the ordered regression plan for ``root`` without executing anything."""
    steps: list[Step] = []
    for name, (cwd, argv) in required_regression_commands(released_charts=True).items():
        steps.append(Step(name=name, cwd=cwd, argv=list(argv)))
    if python != sys.executable:
        steps = [
            Step(name=step.name, cwd=step.cwd, argv=[python if part == sys.executable else part for part in step.argv],
                 note=step.note)
            for step in steps
        ]
    if include_clean_checkout:
        steps.append(
            Step(
                name="clean_core",
                cwd=".",
                argv=[python, "scripts/run_full_regression.py", "--internal-clean-core"],
                note="Candidate work-tree checkout unit run; tracked files only, so ignored data cannot mask CI failures.",
            )
        )
    return steps


def conditional_skip_reason(step: Step, root: Path) -> str | None:
    """Return why ``step`` cannot run here, or ``None`` when it is applicable."""
    return None


def _port_free(port: int) -> bool:
    """Probe both localhost families without reusing another process's address."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
        except OSError as error:
            if family == socket.AF_INET6 and error.errno in (
                errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT, errno.EADDRNOTAVAIL,
            ):
                continue  # IPv6 localhost is unavailable on this machine.
            return False
    return True


def choose_ports(probe: Callable[[int], bool] | None = None) -> dict[str, str]:
    """Honor an explicit free pair; otherwise retain defaults or find isolation.

    Both PAYDIRT_E2E_*_PORT values must be distinct decimal ports in 1..65535.
    ``probe(port)`` reports whether both localhost addresses are bindable. Probes
    cannot reserve ports: the services still detect a race when they start.
    """
    is_free = probe or _port_free
    names = ("PAYDIRT_E2E_BACKEND_PORT", "PAYDIRT_E2E_FRONTEND_PORT")
    explicit = [os.environ.get(name) for name in names]
    if any(value is not None for value in explicit):
        if not all(value and value.isascii() and value.isdecimal() for value in explicit):
            raise ValueError("Both PAYDIRT_E2E ports must be decimal port numbers")
        ports = [int(value) for value in explicit]
        if any(not 1 <= port <= 65535 for port in ports) or len(set(ports)) != 2:
            raise ValueError("E2E ports must be distinct and in 1..65535")
        if not all(is_free(port) for port in ports):
            raise ValueError("Explicit E2E port pair is occupied; select available ports")
        return dict(zip(names, map(str, ports)))
    if is_free(DEFAULT_BACKEND_PORT) and is_free(DEFAULT_FRONTEND_PORT):
        return {}

    chosen: dict[str, str] = {}
    used: set[int] = set()
    for name, base in zip(names, (ISOLATED_BACKEND_BASE, ISOLATED_FRONTEND_BASE)):
        for port in range(base, min(base + 500, 65536)):
            if port not in used and is_free(port):
                chosen[name] = str(port)
                used.add(port)
                break
        else:
            raise ValueError(f"No available E2E port in isolation range beginning {base}")
    return chosen


def summarize(results: Sequence[StepResult]) -> tuple[str, int]:
    """Render the compact final report and the process exit code."""
    labels = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}
    lines = ["", "Regression summary", "=================="]
    width = max((len(result.name) for result in results), default=0)
    for result in results:
        detail = result.reason
        if result.status == "fail" and result.log_path is not None:
            detail = f"log: {result.log_path}"
        elif result.status == "pass" and result.log_path is not None:
            detail = str(result.log_path)
        lines.append(
            f"{labels.get(result.status, result.status):4}  {result.name.ljust(width)}  "
            f"{result.seconds:7.1f}s  {detail}"
        )
    failures = [result for result in results if result.status == "fail"]
    for result in failures:
        if result.tail:
            lines.append("")
            lines.append(f"--- {result.name} (log: {result.log_path}) ---")
            lines.extend(result.tail)
    counts = {status: sum(1 for r in results if r.status == status) for status in labels}
    lines.append("")
    lines.append(
        f"{counts['pass']} passed, {counts['fail']} failed, {counts['skip']} skipped"
    )
    if failures:
        lines.append("Do not push: resolve every failure above, then rerun this script.")
    lines.append("")
    return "\n".join(lines), 0 if not failures else 1


def _print_plan(steps: Sequence[Step], root: Path) -> None:
    print(f"Full regression plan for {root}")
    for step in steps:
        reason = conditional_skip_reason(step, root)
        state = f"SKIP ({reason})" if reason else "run"
        print(f"  {step.name:12} [{state}]  (cd {step.cwd} && {' '.join(step.argv)})")
        if step.note:
            print(f"  {'':12}  note: {step.note}")


def browser_environment(base: dict[str, str], python: str) -> dict[str, str]:
    """Return ``base`` with the regression interpreter's directory first on ``PATH``.

    ``playwright.config.js`` starts the isolated E2E API with ``python3`` from
    ``PATH``. That must be the same interpreter running the rest of the regression;
    an unrelated system ``python3`` can carry different dependency versions and make
    the real API fail with misleading chart or conversion errors.
    """
    env = dict(base)
    bindir = str(Path(python).parent)
    current = env.get("PATH", "")
    env["PATH"] = bindir + (os.pathsep + current if current else "")
    return env


def _stream_step(step: Step, root: Path, log_path: Path, env: dict[str, str],
                 timeout: float) -> StepResult:
    started = time.monotonic()
    tail: list[str] = []
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"# {' '.join(step.argv)}\n# cwd={root / step.cwd}\n")
        if timeout > 0:
            try:
                completed = subprocess.run(
                    list(step.argv),
                    cwd=root / step.cwd,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
                output = completed.stdout + completed.stderr
            except subprocess.TimeoutExpired as expired:
                output = (expired.stdout or "") + (expired.stderr or "")
                log.write(output if isinstance(output, str) else "")
                log.write(f"\n# TIMEOUT after {timeout:.0f}s\n")
                return StepResult(
                    name=step.name,
                    status="fail",
                    seconds=time.monotonic() - started,
                    returncode=None,
                    log_path=log_path,
                    reason=f"timed out after {timeout:.0f}s",
                )
            log.write(output)
            process = subprocess.CompletedProcess(step.argv, completed.returncode)
            print(output, end="" if output.endswith("\n") else "\n")
        else:
            process = subprocess.Popen(
                list(step.argv),
                cwd=root / step.cwd,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                print(line, end="")
                tail.append(line.rstrip("\n"))
                tail = tail[-TAIL_LINES:]
            process.wait()
    if timeout > 0:
        tail = output.splitlines()[-TAIL_LINES:]
    return StepResult(
        name=step.name,
        status="pass" if process.returncode == 0 else "fail",
        seconds=time.monotonic() - started,
        returncode=process.returncode,
        log_path=log_path,
        tail=[] if process.returncode == 0 else tail,
    )


def _preflight(root: Path) -> list[str]:
    problems: list[str] = []
    if sys.version_info < (3, 10):
        problems.append(f"Python 3.10+ required; running {sys.version.split()[0]}")
    frontend = root / "paydirt-web" / "frontend"
    if not (frontend / "node_modules").is_dir():
        problems.append(f"Missing {frontend / 'node_modules'}; run: (cd paydirt-web/frontend && npm ci)")
    if not (frontend / "node_modules" / "@playwright" / "test").exists():
        problems.append("Playwright test package missing; run: (cd paydirt-web/frontend && npm ci)")
    return problems


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run a read-only git command in ``root`` and fail loudly on error."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def export_candidate_tree(root: Path, target: Path) -> None:
    """Copy the candidate work tree to ``target``: tracked files only.

    The export is the code under review, so it includes uncommitted work: staged
    and unstaged edits to tracked files, tracked deletions, and new
    untracked-but-not-ignored files such as a just-written test. Ignored files
    are excluded, so local chart material and saved games cannot mask a CI
    failure, and submodules are skipped because their contents are not tracked
    by this repository's tree.

    Args:
        root: Git work tree to export.
        target: Empty directory to receive the tracked files.

    Raises:
        RuntimeError: ``root`` is not the top of a Git work tree.
    """
    top = _git(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise RuntimeError(
            f"clean checkout requires a git work tree: {root} "
            f"({top.stderr.decode(errors='replace').strip()})"
        )
    if Path(top.stdout.decode().strip()).resolve() != root.resolve():
        raise RuntimeError(f"{root} is not the top of a git work tree")

    listed = _git(root, "ls-files", "-z", "--stage")
    if listed.returncode != 0:
        raise RuntimeError(listed.stderr.decode(errors="replace").strip())
    paths: list[Path] = []
    for entry in listed.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, _, raw_path = entry.partition(b"\t")
        mode = metadata.split(b" ")[0].decode()
        if mode == "160000":  # submodule commit, not a file in this tree
            continue
        paths.append(Path(raw_path.decode()))

    # New work is part of the candidate too, but ignored local data is not.
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard")
    if untracked.returncode != 0:
        raise RuntimeError(untracked.stderr.decode(errors="replace").strip())
    paths.extend(Path(raw.decode()) for raw in untracked.stdout.split(b"\0") if raw)

    target.mkdir(parents=True, exist_ok=True)
    for relative in paths:
        source = root / relative
        if not source.exists() and not source.is_symlink():
            continue  # staged or tracked file deleted in the candidate work tree
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)


def clean_core_checkout(root: Path) -> int:
    """Run core unit tests from a tracked-files-only export of the candidate.

    The export comes from the work tree, not ``HEAD``, so running the script
    before committing still validates the changes under review. The caller is
    told when the export contains uncommitted tracked changes.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="paydirt-clean-") as tmp:
        checkout = Path(tmp) / "checkout"
        export_candidate_tree(root, checkout)
        dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
        if dirty.returncode != 0:
            print(dirty.stderr.decode(errors="replace"), file=sys.stderr)
            return dirty.returncode
        summary = dirty.stdout.decode().strip()
        print(
            "clean checkout: exporting the candidate work tree"
            + (f" with uncommitted tracked changes:\n{summary}" if summary else " at HEAD")
        )
        return subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short"],
            cwd=checkout,
            check=False,
        ).returncode


def main(argv: Sequence[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="Print the ordered plan and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; never execute steps.")
    parser.add_argument("--only", help="Comma-separated step names to run.")
    parser.add_argument("--skip", help="Comma-separated step names to skip.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failing step.")
    parser.add_argument("--clean-checkout", action="store_true",
                        help="Also run core unit tests from a tracked-files-only export of the candidate work tree.")
    parser.add_argument("--timeout", type=float, default=0,
                        help="Per-step timeout in seconds (0 disables; disables live streaming when set).")
    parser.add_argument("--log-dir", type=Path, help="Override the ignored .ai-audits/full-regression log root.")
    parser.add_argument("--internal-clean-core", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    base_root = (root or ROOT).resolve()
    if args.internal_clean_core:
        return clean_core_checkout(base_root)

    steps = regression_steps(base_root, include_clean_checkout=args.clean_checkout)
    by_name = {step.name: step for step in steps}
    if args.only:
        requested = [name.strip() for name in args.only.split(",") if name.strip()]
        unknown = [name for name in requested if name not in by_name]
        if unknown:
            print(f"Unknown step name(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Available: {', '.join(by_name)}", file=sys.stderr)
            return 2
        steps = [by_name[name] for name in requested]
    if args.skip:
        skipped = {name.strip() for name in args.skip.split(",") if name.strip()}
        steps = [step for step in steps if step.name not in skipped]

    if args.list or args.dry_run:
        _print_plan(steps, base_root)
        return 0

    problems = _preflight(base_root)
    if problems:
        for problem in problems:
            print(f"PREFLIGHT: {problem}", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_root = args.log_dir or base_root / ".ai-audits" / "full-regression" / stamp
    log_root.mkdir(parents=True, exist_ok=True)
    try:
        port_env = choose_ports()
    except ValueError as error:
        print(f"PREFLIGHT: {error}", file=sys.stderr)
        return 2
    if port_env:
        print(f"Browser regression port overrides: {port_env}")

    results: list[StepResult] = []
    for step in steps:
        reason = conditional_skip_reason(step, base_root)
        if reason:
            print(f"SKIP {step.name}: {reason}")
            results.append(StepResult(name=step.name, status="skip", seconds=0.0, reason=reason))
            continue
        print(f"RUN  {step.name}: {' '.join(step.argv)}", flush=True)
        env = dict(os.environ)
        if step.name == "browser":
            env.update(port_env)
            env = browser_environment(env, sys.executable)
        result = _stream_step(step, base_root, log_root / f"{step.name}.log", env, args.timeout)
        results.append(result)
        print(f"{result.status.upper():4} {step.name} ({result.seconds:.1f}s)", flush=True)
        if result.status == "fail" and args.fail_fast:
            break

    text, code = summarize(results)
    print(text)
    summary_md = log_root / "summary.md"
    summary_md.write_text(text, encoding="utf-8")
    (log_root / "summary.json").write_text(
        json.dumps(
            {
                "log_dir": str(log_root),
                "exit_code": code,
                "port_overrides": port_env,
                "steps": [
                    {
                        "name": result.name,
                        "status": result.status,
                        "seconds": round(result.seconds, 2),
                        "returncode": result.returncode,
                        "reason": result.reason,
                        "log": str(result.log_path) if result.log_path else None,
                    }
                    for result in results
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Logs: {log_root}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
