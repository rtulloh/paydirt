#!/usr/bin/env python3
"""Run the complete AGENTS.md pre-push regression and report a compact summary.

The command list is not duplicated here: the canonical steps come from
``paydirt.chart_release_gate.required_regression_commands(released_charts=True)``,
which is the same list the release gate audits. This script adds the local-only
Private 1983 AI comparison, isolated E2E ports, streamed per-step logs and a
one-screen pass/fail summary suitable for pasting into a session.

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
import json
import os
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
ESCROW_PRIVATE_CHARTS = Path(".ai-audits/escrow/1983-private-charts")


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
    escrow = (root / ESCROW_PRIVATE_CHARTS).resolve()
    steps.append(
        Step(
            name="private_ai",
            cwd=".",
            argv=[
                python,
                "tests/run_ai_audit.py",
                "--season",
                str(escrow),
                "--weeks",
                "16",
                "--seed",
                "8306",
                "--compare-balanced",
                "--output",
                str((root / ".ai-audits/private-season.json").resolve()),
                "--csv",
                str((root / ".ai-audits/private-season.csv").resolve()),
            ],
            note="Private 1983 charts; skipped when the escrow directory is absent.",
        )
    )
    if include_clean_checkout:
        steps.append(
            Step(
                name="clean_core",
                cwd=".",
                argv=[python, "scripts/run_full_regression.py", "--internal-clean-core"],
                note="Tracked-files-only checkout unit run (ignored data cannot mask CI failures).",
            )
        )
    return steps


def conditional_skip_reason(step: Step, root: Path) -> str | None:
    """Return why ``step`` cannot run here, or ``None`` when it is applicable."""
    if step.name == "private_ai":
        escrow = (root / ESCROW_PRIVATE_CHARTS).resolve()
        if not escrow.is_dir():
            return f"private charts absent ({escrow}); not applicable to generated-chart audits"
    return None


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def choose_ports(probe: Callable[[int], bool] | None = None) -> dict[str, str]:
    """Return E2E port overrides only when the Playwright defaults are occupied.

    ``probe(port)`` must report whether the port is bindable (free).
    """
    is_free = probe or _port_free
    if is_free(DEFAULT_BACKEND_PORT) and is_free(DEFAULT_FRONTEND_PORT):
        return {}

    chosen: dict[str, str] = {}
    for env_name, base in (
        ("PAYDIRT_E2E_BACKEND_PORT", ISOLATED_BACKEND_BASE),
        ("PAYDIRT_E2E_FRONTEND_PORT", ISOLATED_FRONTEND_BASE),
    ):
        port = base
        while port < base + 500 and not is_free(port):
            port += 1
        chosen[env_name] = str(port)
    if chosen["PAYDIRT_E2E_BACKEND_PORT"] == chosen["PAYDIRT_E2E_FRONTEND_PORT"]:
        chosen["PAYDIRT_E2E_FRONTEND_PORT"] = str(int(chosen["PAYDIRT_E2E_FRONTEND_PORT"]) + 1)
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


def _clean_core_checkout(root: Path) -> int:
    """Run core unit tests from a tracked-files-only export of HEAD."""
    import tarfile
    import tempfile

    with tempfile.TemporaryDirectory(prefix="paydirt-clean-") as tmp:
        target = Path(tmp)
        archive = subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if archive.returncode != 0:
            print(archive.stderr.decode(errors="replace"), file=sys.stderr)
            return archive.returncode
        tar_path = target / "head.tar"
        tar_path.write_bytes(archive.stdout)
        with tarfile.open(tar_path) as bundle:
            if hasattr(tarfile, "data_filter"):
                bundle.extractall(target / "checkout", filter="data")
            else:  # Python 3.10 lacks extraction filters.
                bundle.extractall(target / "checkout")
        return subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "-o", "addopts=", "--tb=short"],
            cwd=target / "checkout",
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
                        help="Also run core unit tests from a tracked-files-only HEAD export.")
    parser.add_argument("--timeout", type=float, default=0,
                        help="Per-step timeout in seconds (0 disables; disables live streaming when set).")
    parser.add_argument("--log-dir", type=Path, help="Override the ignored .ai-audits/full-regression log root.")
    parser.add_argument("--internal-clean-core", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    base_root = (root or ROOT).resolve()
    if args.internal_clean_core:
        return _clean_core_checkout(base_root)

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
    port_env = choose_ports()
    if port_env:
        print(f"Default E2E ports busy; isolating browser regression on {port_env}")

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