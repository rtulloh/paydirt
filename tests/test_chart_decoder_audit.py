"""Decoder coverage uses raw public/synthetic bytes, not private chart fixtures."""

from __future__ import annotations

import csv
import shutil
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import pytest

import paydirt.chart_audit as audit
from paydirt.chart_loader import load_team_chart
from paydirt.play_resolver import chart_roll_weights, resolve_qb_scramble


@pytest.fixture
def chart_dir(tmp_path: Path) -> Path:
    destination = tmp_path / "2026/Ironclads"
    shutil.copytree(Path("seasons/2026/Ironclads"), destination)
    return destination


def check(directory: Path) -> dict:
    function = getattr(audit, "audit_chart_decoder", None)
    assert callable(function), "Reference comparison requires raw decoder/fallback coverage"
    return function(directory)


def rows(path: Path) -> list[list[str]]:
    with path.open(newline="") as stream:
        return list(csv.reader(stream))


def write_rows(path: Path, values: list[list[str]]) -> None:
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(values)


def test_public_chart_decoder_covers_every_physical_column_without_mutation(
    chart_dir: Path,
) -> None:
    before = {path: path.read_bytes() for path in chart_dir.iterdir() if path.is_file()}
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False and result["fully_supported"] is True
    assert len(result["columns"]) == 73
    assert set(result["files"]) == {"offense.csv", "defense.csv", "special.csv"}
    assert result["aliases"] == {"special_teams.fumble_return": "special_teams.interception_return"}
    for label, column in result["columns"].items():
        assert column["physical_denominator"] == (36 if label.startswith("defense.") else 216)
        assert sum(Fraction(*mass) for mass in column["exact_masses"].values()) == 1
    assert all(path.read_bytes() == data for path, data in before.items())


@pytest.mark.parametrize(
    "file,mutation",
    [
        ("offense.csv", "duplicate"),
        ("defense.csv", "duplicate"),
        ("special.csv", "duplicate"),
        ("offense.csv", "out-of-range"),
        ("special.csv", "out-of-range"),
        ("defense.csv", "bad-formation"),
        ("defense.csv", "bad-subrow"),
        ("offense.csv", "ignored-extra-cell"),
        ("defense.csv", "ignored-extra-cell"),
        ("special.csv", "ignored-extra-cell"),
        ("offense.csv", "short-header"),
        ("offense.csv", "no-data"),
        ("defense.csv", "no-data"),
        ("special.csv", "no-data"),
        ("offense.csv", "missing-file"),
        ("defense.csv", "missing-file"),
        ("special.csv", "missing-file"),
    ],
)
def test_loader_omissions_cannot_disappear_from_decoder_census(
    chart_dir: Path, file: str, mutation: str
) -> None:
    path = chart_dir / file
    values = rows(path)
    if mutation == "duplicate":
        values.insert(2, values[1].copy())
    elif mutation == "out-of-range":
        values[1][0] = "40"
    elif mutation == "bad-formation":
        values[1][1] = "Z"
    elif mutation == "bad-subrow":
        values[1][2] = "6"
    elif mutation == "ignored-extra-cell":
        values[1].append("UNREAD_DATA")
    elif mutation == "short-header":
        values[0] = values[0][:3]
    elif mutation == "no-data":
        values = values[:1]
    if mutation == "missing-file":
        path.unlink()
    else:
        write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"] and result["errors"]
    assert result["release_certified"] is False


@pytest.mark.parametrize(
    "column,token",
    [(1, "DS"), (1, "INC"), (1, "BOGUS"), (1, "10†"), (1, "+5"), (1, "1.5"), (10, "F + 2")],
)
def test_primary_neutral_fallbacks_and_ignored_secondary_flags_are_visible(
    chart_dir: Path, column: int, token: str
) -> None:
    path = chart_dir / "offense.csv"
    values = rows(path)
    values[1][column] = token
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"] and not result["fully_supported"]
    assert any("roll 10" in error for error in result["errors"])


def test_known_qt_fallback_has_exact_physical_mass_and_matches_core(chart_dir: Path) -> None:
    path = chart_dir / "offense.csv"
    values = rows(path)
    values[1][11] = "OFF 5"
    write_rows(path, values)
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    assert result["fully_supported"] is False and result["limitations"]
    column = result["columns"]["offense.qb_time"]
    assert Fraction(*column["exact_masses"]["secondary_random_fallback"]) == Fraction(
        chart_roll_weights()[10], 216
    )
    with patch("paydirt.play_resolver.random.randint", return_value=-5) as rng:
        assert resolve_qb_scramble(load_team_chart(str(chart_dir)).offense, 10).yards == -5
        rng.assert_called_once_with(-5, 10)


@pytest.mark.parametrize("token", ["OFF S", "OFF R", "DEF S", "DEF R"])
def test_field_goal_table_penalties_disclose_the_existing_placeholder(
    chart_dir: Path,
    token: str,
) -> None:
    from paydirt.play_resolver import _create_penalty_option

    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][6] = token
    write_rows(path, values)
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    assert not result["fully_supported"]
    assert any("placeholder" in limitation for limitation in result["limitations"])
    column = result["columns"]["special_teams.field_goal"]
    assert Fraction(*column["exact_masses"]["penalty_placeholder"]) == Fraction(
        chart_roll_weights()[10], 216
    )
    assert _create_penalty_option(token).yards == 5


def test_blank_primary_and_missing_row_are_separate_known_defaults(chart_dir: Path) -> None:
    path = chart_dir / "offense.csv"
    values = rows(path)
    values[1][1] = ""
    values = [row for row in values if not row or row[0] != "39"]
    values.extend([["# Recovered", "10-27"], ["# Lost", "28-39"]])
    write_rows(path, values)
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    column = result["columns"]["offense.line_plunge"]
    assert column["blank_cell_probability"] == pytest.approx(chart_roll_weights()[10] / 216)
    assert column["missing_row_probability"] == pytest.approx(chart_roll_weights()[39] / 216)
    assert Fraction(*column["exact_masses"]["engine_default"]) == Fraction(
        chart_roll_weights()[10] + chart_roll_weights()[39], 216
    )
    assert not result["fully_supported"]


def test_blank_punt_default_is_visible_without_a_missing_row(chart_dir: Path) -> None:
    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][3] = ""
    write_rows(path, values)
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    assert not result["fully_supported"]
    assert any("blank" in limitation for limitation in result["limitations"])


def test_numeric_decoder_overflow_is_a_failure_report_not_an_exception(chart_dir: Path) -> None:
    path = chart_dir / "offense.csv"
    values = rows(path)
    values[1][1] = "9" * 400 + ".5"
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"] and result["errors"]


def test_special_normalization_cannot_hide_original_stray_characters(chart_dir: Path) -> None:
    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][2] = "20`"
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"] and result["loader_warnings"]
    assert result["columns"]["special_teams.kickoff_return"][
        "normalization_probability"
    ] == pytest.approx(chart_roll_weights()[10] / 216)


def test_extra_point_unknown_is_not_silently_a_success(chart_dir: Path) -> None:
    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][7] = "MISS"
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"]
    assert any("extra_point" in error for error in result["errors"])


@pytest.mark.parametrize(
    "column,token",
    [
        (1, "+65"),
        (1, "-5"),
        (1, "OFF S"),
        (1, "ob"),
        (3, "OFF R"),
        (3, "DEF 10Y"),
        (3, "bk -3"),
        (4, "OFF S"),
        (5, "OFF R"),
    ],
)
def test_special_consumer_fallbacks_do_not_receive_generic_grammar_passes(
    chart_dir: Path,
    column: int,
    token: str,
) -> None:
    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][column] = token
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"] and not result["fully_supported"]
    assert any("roll 10" in error for error in result["errors"])


@pytest.mark.parametrize(
    "column,token", [(1, "TB"), (1, "out"), (3, "40+"), (3, "F - 10"), (4, "TD"), (5, "TD")]
)
def test_special_legacy_tokens_supported_by_actual_consumers_are_censused(
    chart_dir: Path,
    column: int,
    token: str,
) -> None:
    path = chart_dir / "special.csv"
    values = rows(path)
    values[1][column] = token
    write_rows(path, values)
    result = check(chart_dir)
    assert result["passed"], result["errors"]
    assert result["fully_supported"]


def test_recovery_flags_cannot_disagree_with_the_effective_ranges(chart_dir: Path) -> None:
    path = chart_dir / "offense.csv"
    values = rows(path)
    values[1][12] = "L"
    write_rows(path, values)
    result = check(chart_dir)
    assert not result["passed"]
    assert any("recovery" in error for error in result["errors"])


def test_decoder_rejects_symlinked_input_without_reading_its_target(
    chart_dir: Path, tmp_path: Path
) -> None:
    path = chart_dir / "special.csv"
    target = tmp_path / "preserve.csv"
    path.rename(target)
    path.symlink_to(target)
    result = check(chart_dir)
    assert not result["passed"] and any("regular" in error for error in result["errors"])


def test_decoder_detects_files_changed_while_loading(
    chart_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = audit.load_team_chart

    def change(path: str) -> object:
        chart = original(path)
        with (Path(path) / "offense.csv").open("a") as stream:
            stream.write("# Mutation after loading\n")
        return chart

    monkeypatch.setattr(audit, "load_team_chart", change)
    result = check(chart_dir)
    assert not result["passed"] and any("changed" in error.lower() for error in result["errors"])
