"""Exercise the standalone checker with synthetic subprocess output, not private teams."""

import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


def synthetic_output(overtime: int = 0, banner: bool = True) -> str:
    """Build a regulation or multi-OT final table in the CLI display format."""
    labels = ["1Q", "2Q", "3Q", "4Q"] + [
        "OT" if index == 1 else f"OT{index}" for index in range(1, overtime + 1)
    ]
    away = [0, 3, 0, 7] + [0] * overtime
    home = [0, 0, 7, 0] + [0] * overtime
    if overtime:
        away[3] = 4
        away[-1] = 6
    score = f"FINAL SCORE\n------------\nAWAY '26 {sum(away)} - HOME '26 {sum(home)}\n" if banner else ""
    return (
        score + "FINAL STATISTICS\n"
        + f"| TEAM | {' '.join(labels)} | TOTAL |\n"
        + "|----------------------------------------|\n"
        + f"| AWAY '26 | {' '.join(map(str, away))} | {sum(away)} |\n"
        + f"| HOME '26 | {' '.join(map(str, home))} | {sum(home)} |\n"
    )


def run_checker(output: str, capsys: pytest.CaptureFixture, returncode: int = 0) -> tuple[int, str]:
    result = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=output, stderr="")
    script = Path(__file__).with_name("run_all_games.py")
    code = 0
    with patch("subprocess.run", return_value=result) as child:
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as error:
            code = error.code
    assert child.call_count == 14
    return code, capsys.readouterr().out


@pytest.mark.parametrize("overtime", [0, 1, 2, 3])
@pytest.mark.parametrize("banner", [False, True])
def test_checker_accepts_all_periods(
    overtime: int, banner: bool, capsys: pytest.CaptureFixture,
) -> None:
    code, output = run_checker(synthetic_output(overtime, banner), capsys)
    assert code == 0
    assert "ALL GAMES PASSED!" in output
    assert "ERROR" not in output and "WARNING" not in output
    assert "SUMMARY: 14 games played" in output


@pytest.mark.parametrize("overtime", [0, 1, 2])
def test_checker_rejects_incorrect_period_total(
    overtime: int, capsys: pytest.CaptureFixture,
) -> None:
    text = synthetic_output(overtime).replace(" | 7 |\n", " | 8 |\n")
    assert text != synthetic_output(overtime)
    code, output = run_checker(text, capsys)
    assert code != 0
    assert "ERRORS FOUND" in output
    assert "ALL GAMES PASSED!" not in output


@pytest.mark.parametrize("text,returncode", [
    ("", 0),
    ("Traceback: synthetic child exception", 0),
    (synthetic_output(), 5),
    (synthetic_output().split("FINAL STATISTICS")[0], 0),
    (synthetic_output().replace("| HOME '26 | 0 0 7 0 | 7 |", ""), 0),
    (synthetic_output().replace("| AWAY '26 | 0 3 0 7 | 10 |",
                                "| AWAY '26 | 0 3 7 | 10 |"), 0),
    (synthetic_output().replace("| AWAY '26 | 0 3 0 7 | 10 |",
                                "| AWAY '26 | 0 3 0 7 0 | 10 |"), 0),
])
def test_checker_exits_nonzero_for_incomplete_or_failed_games(
    text: str, returncode: int, capsys: pytest.CaptureFixture,
) -> None:
    code, output = run_checker(text, capsys, returncode)
    assert code != 0
    assert "ERRORS FOUND" in output
    assert "ALL GAMES PASSED!" not in output
