"""Compound source fumbles cannot be silently counted as one offensive event."""
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.nflverse_play_by_play import classify_nflverse_rows


def source_row(kind: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-compound",
        "play_id": 1, "posteam": "AAA", "defteam": "BBB", "play_type": "pass",
        "pass_attempt": 1, "complete_pass": 1, "yards_gained": 7, "air_yards": 5,
        "fumble": 1, "fumble_lost": 1, "fumbled_1_team": "AAA",
        "desc": "Carrier fumbles once.",
    }
    if kind == "sack":
        row.update(sack=1, complete_pass=0, yards_gained=-7)
    elif kind == "run":
        row.update(play_type="run", pass_attempt=0, complete_pass=0, rush_attempt=1,
                   run_location="left", run_gap="end")
    row.update(overrides)
    return row


@pytest.mark.parametrize("kind", ["completion", "sack", "run"])
@pytest.mark.parametrize("second_team", ["AAA", "BBB"])
def test_second_source_fumble_requires_event_level_support(kind: str, second_team: str) -> None:
    result = classify_nflverse_rows([source_row(kind, fumbled_2_team=second_team)])
    assert not result.fumbles, "A partial single-event ledger must not imply compound support"
    assert result.diagnostics["multiple_fumble_sequences"] == 1
    assert any(f["field"] == "fumble_ownership" for f in result.unsupported_fields)


@pytest.mark.parametrize("kind", ["completion", "sack", "run"])
def test_second_fumbler_id_with_unknown_team_remains_unsupported(kind: str) -> None:
    result = classify_nflverse_rows([source_row(kind, fumbled_2_player_id="synthetic-carrier")])
    assert not result.fumbles
    assert any(f["field"] == "fumble_ownership" for f in result.unsupported_fields)


@pytest.mark.parametrize("kind", ["completion", "sack", "run"])
def test_single_fumble_keeps_existing_calibration_support(kind: str) -> None:
    result = classify_nflverse_rows([source_row(kind, fumbled_2_team="", fumbled_2_player_id="")])
    assert [(e.team, e.unit, e.lost) for e in result.fumbles] == [
        ("AAA", "rushing" if kind == "run" else "passing", True),
    ]
    assert not result.unsupported_fields


def test_generation_rejects_compound_fumbles_before_fitting(tmp_path: Path) -> None:
    import generate_nflverse_charts as command

    row = source_row("run", fumbled_2_team="BBB")
    source = tmp_path / "source.csv"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    mapping = tmp_path / "teams.json"
    mapping.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
    with (patch.object(command, "adjust_empirical_offense",
                       side_effect=AssertionError("unsupported input reached fitting")) as fitting,
          pytest.raises(ValueError, match="Unsupported source fields")):
        command.main(["--pbp", str(source), "--stats-dir", str(tmp_path / "stats"),
                      "--template-season", str(tmp_path / "template"), "--team-map", str(mapping),
                      "--output", str(tmp_path / "output"), "--audit-dir", str(tmp_path / "audit")])
    fitting.assert_not_called()
    assert not (tmp_path / "output" / "generation-manifest.json").exists()
    ledger = json.loads((tmp_path / "audit" / "unsupported-source-fields.json").read_text())
    assert len(ledger) == 1 and ledger[0]["field"] == "fumble_ownership"


@pytest.mark.parametrize("kind", ["completion", "sack", "run", "interception"])
def test_second_fumbler_name_alone_requires_event_support(kind: str) -> None:
    overrides: dict[str, object] = {
        "fumbled_2_team": "", "fumbled_2_player_id": "",
        "fumbled_2_player_name": "Second Carrier",
    }
    if kind == "interception":
        overrides.update(interception=1, complete_pass=0, yards_gained=0,
                         fumbled_1_team="BBB", return_team="BBB", return_yards=5)
    result = classify_nflverse_rows([source_row(kind, **overrides)])
    assert not result.fumbles
    assert result.diagnostics["multiple_fumble_sequences"] == 1
    assert len(result.unsupported_fields) == 1
    assert result.unsupported_fields[0]["field"] == "fumble_ownership"


@pytest.mark.parametrize("kind", ["completion", "sack", "run"])
@pytest.mark.parametrize("name", ["", None, "NA", "nan"])
def test_missing_second_name_does_not_invent_a_compound_event(
    kind: str, name: str | None,
) -> None:
    result = classify_nflverse_rows([source_row(kind, fumbled_2_player_name=name)])
    assert [(event.team, event.unit, event.lost) for event in result.fumbles] == [
        ("AAA", "rushing" if kind == "run" else "passing", True),
    ]
    assert not result.unsupported_fields


@pytest.mark.parametrize("changes", [
    {"fumble_recovery_2_team": "AAA"},
    {"desc": "Carrier FUMBLES, recovered by AAA-Carrier. Carrier to AAA 37 for 1 yard. "
             "Carrier FUMBLES, recovered by AAA-Teammate."},
])
def test_incomplete_second_identity_cannot_hide_another_fumble(changes: dict) -> None:
    result = classify_nflverse_rows([source_row("run", **changes)])
    assert result.diagnostics["multiple_fumble_sequences"] == 1
    assert not result.fumbles
    assert result.unsupported_fields


def test_reversed_narrative_is_not_counted_as_another_retained_fumble() -> None:
    result = classify_nflverse_rows([source_row(
        "run", desc="Carrier FUMBLES. The play was reviewed, and the play was REVERSED. "
                    "Carrier FUMBLES, recovered by BBB-Defender.",
    )])
    assert not result.unsupported_fields
    assert len(result.fumbles) == 1


def test_muff_is_not_automatically_a_second_credited_fumble() -> None:
    result = classify_nflverse_rows([source_row(
        "run", desc="Carrier MUFFS the exchange. Carrier FUMBLES, recovered by BBB-Defender.",
    )])
    assert not result.unsupported_fields
    assert len(result.fumbles) == 1


@pytest.mark.parametrize("suffix", [
    "Fumble forced by Defender.", "Fumble was not forced.",
    "The Replay Official reviewed the fumble ruling, and the play was Upheld.",
])
def test_fumble_metadata_is_not_another_occurrence(suffix: str) -> None:
    result = classify_nflverse_rows([source_row(
        "run", desc=f"Carrier FUMBLES, recovered by BBB-Defender. {suffix}",
    )])
    assert not result.unsupported_fields
    assert len(result.fumbles) == 1
