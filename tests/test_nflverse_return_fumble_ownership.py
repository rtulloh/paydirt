"""Keep interception-return fumbles out of offensive fumble calibration."""
import pytest

from paydirt.nflverse_play_by_play import classify_nflverse_rows


def fumble_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-source",
        "play_id": 1, "posteam": "ARI", "defteam": "BUF", "play_type": "pass",
        "pass_attempt": 1, "interception": 1, "complete_pass": 0, "incomplete_pass": 0,
        "yards_gained": 0, "air_yards": 12, "pass_length": "short",
        "fumble": 1, "fumble_lost": 0, "fumbled_1_team": "BUF",
        "return_team": "BUF", "return_yards": 7,
        "desc": "Pass intercepted. Returner fumbles after a 7 yard return.",
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize("lost", [0, 1])
@pytest.mark.parametrize("return_team", ["BUF", ""])
def test_returner_fumble_does_not_become_an_offensive_passing_fumble(
    lost: int, return_team: str,
) -> None:
    season = classify_nflverse_rows([fumble_row(fumble_lost=lost, return_team=return_team)])
    assert [(p.team, p.chart, p.result) for p in season.plays] == [
        ("BUF", "interception_return", "F + 7"), ("ARI", "medium_pass", "INT 12"),
    ]
    assert season.event_counts["ARI"]["interceptions"] == 1
    assert not season.fumbles, "Offensive calibration excludes the returner's fumble"
    assert not season.unsupported_fields
    assert season.diagnostics["interception_return_fumbles"] == 1


@pytest.mark.parametrize("fumbler", ["", None, "ZZZ"])
def test_unknown_interception_fumble_ownership_is_not_assigned_to_original_offense(
    fumbler: str | None,
) -> None:
    season = classify_nflverse_rows([fumble_row(fumbled_1_team=fumbler)])
    assert not season.fumbles
    assert any(p["field"] == "fumble_ownership" for p in season.unsupported_fields)
    assert season.diagnostics["unknown_interception_fumble_ownership"] == 1


@pytest.mark.parametrize("first,second", [("ARI", "BUF"), ("BUF", "ARI")])
def test_fumbles_by_both_teams_require_separate_event_support(first: str, second: str) -> None:
    season = classify_nflverse_rows([fumble_row(fumbled_1_team=first, fumbled_2_team=second)])
    assert not season.fumbles
    assert any(p["field"] == "fumble_ownership" for p in season.unsupported_fields)


@pytest.mark.parametrize("lost", [0, 1])
def test_offense_fumble_before_interception_is_an_unsupported_sequence(lost: int) -> None:
    season = classify_nflverse_rows([fumble_row(fumbled_1_team="ARI", fumble_lost=lost)])
    assert not season.fumbles
    assert any(p["field"] == "fumble_ownership" for p in season.unsupported_fields)


@pytest.mark.parametrize("kind", ["completion", "sack", "run"])
def test_ordinary_offensive_fumbles_keep_existing_ownership(kind: str) -> None:
    overrides: dict[str, object] = {
        "interception": 0, "fumbled_1_team": "ARI", "fumble_lost": 1, "return_team": "",
        "desc": "Offensive player fumbles. Opponent recovers.",
    }
    if kind == "completion":
        overrides.update(complete_pass=1, yards_gained=7)
    elif kind == "sack":
        overrides.update(sack=1, yards_gained=-7)
    else:
        overrides.update(play_type="run", pass_attempt=0, rush_attempt=1, run_location="left",
                         run_gap="end", yards_gained=7)
    season = classify_nflverse_rows([fumble_row(**overrides)])
    assert [(e.team, e.unit, e.lost) for e in season.fumbles] == [
        ("ARI", "rushing" if kind == "run" else "passing", True),
    ]
    assert not season.unsupported_fields
