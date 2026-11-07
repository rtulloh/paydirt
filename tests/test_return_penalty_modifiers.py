"""Modifier coverage at actual return contexts uses only synthetic public teams."""
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.chart_audit import audit_chart_decoder
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game
from tests.test_chart_decoder_audit import rows, write_rows


@pytest.fixture
def return_chart(tmp_path: Path) -> Path:
    destination = tmp_path / "Ironclads"
    shutil.copytree(Path("seasons/2026/Ironclads"), destination)
    return destination


@pytest.mark.parametrize("column", [2, 4])
@pytest.mark.parametrize("token", ["DEF 5X", "DEF 15X", "DEF 5Y"])
def test_new_series_return_modifiers_have_explicit_decoder_coverage(
    return_chart: Path, column: int, token: str,
) -> None:
    path = return_chart / "special.csv"
    values = rows(path)
    values[1][column] = token
    write_rows(path, values)
    census = audit_chart_decoder(return_chart)
    assert census["passed"] and census["fully_supported"], census["errors"]
    label = "special_teams." + ("kickoff_return" if column == 2 else "punt_return")
    assert "new_series_penalty_modifier" in census["columns"][label]["exact_masses"]


@pytest.mark.parametrize("token", ["DEF 5X", "DEF 15X", "DEF 5Y"])
def test_shared_interception_fumble_return_modifiers_have_decoder_coverage(
    return_chart: Path, token: str,
) -> None:
    path = return_chart / "special.csv"
    values = rows(path)
    values[1][5] = token
    write_rows(path, values)
    census = audit_chart_decoder(return_chart)
    assert census["passed"] and census["fully_supported"], census["errors"]
    assert "preserved_series_penalty_modifier" in census["columns"][
        "special_teams.interception_return"
    ]["exact_masses"]


@pytest.mark.parametrize("kind", ["punt", "kickoff"])
@pytest.mark.parametrize("home_kicks", [False, True])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("token", ["DEF 5X", "DEF 15X", "DEF 5Y"])
@pytest.mark.parametrize("ending,recovery,advance", [
    ("3", None, 0), ("F + 3", 20, 0),
    ("F + 3", 17, 4), ("F + 3", 35, 0),
])
def test_real_kick_returns_start_new_series_including_retained_fumble_chains(
    kind: str, home_kicks: bool, down: int, token: str, ending: str,
    recovery: int | None, advance: int,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home_kicks
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, down, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    kicking = game.state.home_chart if home_kicks else game.state.away_chart
    receiving = game.state.away_chart if home_kicks else game.state.home_chart
    kicking.special_teams.punt = {10: "40"}
    kicking.special_teams.kickoff = {10: "55"}
    for team in (kicking, receiving):
        team.peripheral.fumble_recovered_range = (10, 31)
        team.special_teams.interception_return = {14: "4"}
    receiving.special_teams.punt_return = {11: token, 12: ending}
    receiving.special_teams.kickoff_return = {11: token, 12: ending}
    dice = [10, 11, 12]
    if recovery is not None:
        dice.append(recovery)
    if recovery == 17:
        dice.append(14)
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = (game.kickoff(kicking_home=home_kicks) if kind == "kickoff"
                   else game.run_play(PlayType.PUNT, DefenseType.STANDARD))
    assert rolls.call_count == len(dice)
    assert not outcome.pending_penalty_decision
    assert game.state.is_home_possession is (not home_kicks)
    start = 20 if kind == "punt" else 10
    penalty = 15 if "15" in token else 5
    assert game.state.ball_position == start + 3 + advance + penalty
    assert (game.state.down, game.state.yards_to_go) == (1, 10)
    assert game.state.home_stats.penalties == int(home_kicks)
    assert game.state.away_stats.penalties == int(not home_kicks)
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert game.state.home_stats.first_downs == game.state.away_stats.first_downs == 0
