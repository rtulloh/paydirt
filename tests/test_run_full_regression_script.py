"""Regression coverage for scripts/run_full_regression.py.

These tests stay synthetic: they never execute the real suite, never read
private chart material and never touch the ignored local audit storage.
"""

from __future__ import annotations

from pathlib import Path

from paydirt.chart_release_gate import required_regression_commands
from scripts.run_full_regression import (
    StepResult,
    choose_ports,
    conditional_skip_reason,
    main,
    regression_steps,
    summarize,
)

ROOT = Path(__file__).resolve().parents[1]


def test_steps_cover_every_release_gate_command() -> None:
    steps = {step.name: step for step in regression_steps(ROOT)}
    expected = required_regression_commands(released_charts=True)
    assert set(expected) <= set(steps)
    for name, (cwd, argv) in expected.items():
        assert steps[name].cwd == cwd
        assert steps[name].argv == argv


def test_released_chart_steps_use_released_audit() -> None:
    steps = {step.name: step for step in regression_steps(ROOT)}
    argv = steps["chart_1983"].argv
    assert "paydirt.released_chart_regression_audit" in argv
    assert "audit_generated_charts.py" not in " ".join(argv)


def test_private_ai_step_targets_escrow_charts(tmp_path: Path) -> None:
    steps = {step.name: step for step in regression_steps(tmp_path)}
    argv = steps["private_ai"].argv
    assert argv[argv.index("--season") + 1] == str(
        tmp_path / ".ai-audits" / "escrow" / "1983-private-charts"
    )
    assert str(tmp_path / ".ai-audits" / "private-season.json") in argv


def test_private_ai_skips_without_escrow_charts(tmp_path: Path) -> None:
    steps = {step.name: step for step in regression_steps(tmp_path)}
    assert conditional_skip_reason(steps["private_ai"], tmp_path) is not None
    escrow = tmp_path / ".ai-audits" / "escrow" / "1983-private-charts"
    escrow.mkdir(parents=True)
    assert conditional_skip_reason(steps["private_ai"], tmp_path) is None
    assert conditional_skip_reason(steps["core"], tmp_path) is None


def test_default_ports_need_no_override_when_free() -> None:
    assert choose_ports(probe=lambda port: True) == {}


def test_occupied_default_ports_get_isolated_replacements() -> None:
    env = choose_ports(probe=lambda port: port not in (8000, 5173))
    assert env["PAYDIRT_E2E_BACKEND_PORT"] != "8000"
    assert env["PAYDIRT_E2E_FRONTEND_PORT"] != "5173"
    assert env["PAYDIRT_E2E_BACKEND_PORT"] != env["PAYDIRT_E2E_FRONTEND_PORT"]


def test_summarize_reports_failure_and_nonzero_exit() -> None:
    results = [
        StepResult(name="core", status="pass", seconds=1.25, returncode=0),
        StepResult(
            name="lint",
            status="fail",
            seconds=0.5,
            returncode=1,
            log_path=Path("lint.log"),
            tail=["E501 line too long"],
        ),
    ]
    text, code = summarize(results)
    assert code == 1
    assert "FAIL" in text
    assert "lint" in text
    assert "E501 line too long" in text


def test_summarize_all_skipped_is_success() -> None:
    results = [
        StepResult(name="core", status="pass", seconds=0.1, returncode=0),
        StepResult(name="private_ai", status="skip", seconds=0.0, reason="charts absent"),
    ]
    text, code = summarize(results)
    assert code == 0
    assert "SKIP" in text
    assert "charts absent" in text


def test_dry_run_plans_without_executing(tmp_path: Path, capsys) -> None:
    code = main(["--dry-run", "--only", "core"], root=tmp_path)
    assert code == 0
    output = capsys.readouterr().out
    assert "pytest" in output
    assert not (tmp_path / ".ai-audits").exists()


def test_list_mode_names_every_step(tmp_path: Path, capsys) -> None:
    code = main(["--list"], root=tmp_path)
    assert code == 0
    output = capsys.readouterr().out
    for name in required_regression_commands(released_charts=True):
        assert name in output
    assert "private_ai" in output


def test_clean_checkout_step_is_opt_in() -> None:
    default_steps = {step.name for step in regression_steps(ROOT)}
    assert "clean_core" not in default_steps
    opted_in = {step.name for step in regression_steps(ROOT, include_clean_checkout=True)}
    assert "clean_core" in opted_in


def test_only_and_skip_filter_steps(tmp_path: Path, capsys) -> None:
    assert main(["--dry-run", "--only", "core,lint"], root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "core" in output
    assert "lint" in output
    assert "full_season" not in output

    assert main(["--dry-run", "--only", "core,lint", "--skip", "lint"], root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "core" in output
    assert "lint" not in output


def test_unknown_step_name_is_a_usage_error(tmp_path: Path, capsys) -> None:
    assert main(["--dry-run", "--only", "not_a_step"], root=tmp_path) == 2
    assert "not_a_step" in capsys.readouterr().err