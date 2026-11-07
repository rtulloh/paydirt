"""A selected punt foul keeps its own yardage, first-down rights and down."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("fouls,selected,automatic", [
    (["DEF 5X", "DEF 10"], "DEF 10", False),
    (["DEF 10", "DEF 5X"], "DEF 10", False),
    (["DEF 5Y", "DEF 15"], "DEF 15", True),
    (["DEF 15", "DEF 5Y"], "DEF 15", True),
    (["DEF 5Y", "DEF 5X"], "DEF 5X", True),
    (["DEF 5X", "DEF 5Y"], "DEF 5X", True),
    (["DEF 15"], "DEF 15", True),
    (["DEF 5Y"], "DEF 5Y", False),
    (["DEF 5X"], "DEF 5X", True),
    (["OFF 5"], "OFF 5", False),
])
def test_selected_previous_spot_foul_has_no_borrowed_first_down_rights(
    home: bool, down: int, fouls: list[str], selected: str, automatic: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, down, 20
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.possession_team.special_teams.punt = dict(enumerate([*fouls, "40"], start=10))
    game.state.defense_team.special_teams.punt_return = {20: "0"}
    dice = [*range(10, 11 + len(fouls)), 20]
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls:
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == len(dice)
    assert pending.pending_penalty_decision
    option = pending.penalty_choice.penalty_options[0]
    assert option.auto_first_down is automatic
    assert option.raw_result == selected
    with (patch("paydirt.game_engine.roll_chart_dice") as rolls,
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        outcome = game.apply_punt_penalty_decision(pending, True)
    rolls.assert_not_called()
    yards = int(selected.split()[1].rstrip("XY"))
    spot = 40 - yards if selected.startswith("OFF") else 40 + yards
    distance = 10 if automatic else 60 - spot
    assert game.state.is_home_possession is home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (
        spot, 1 if automatic else down, distance,
    )
    assert outcome.first_down is automatic
    assert game.state.offense_stats.first_downs == int(automatic)
    fouler = game.state.offense_stats if selected.startswith("OFF") else game.state.defense_stats
    other = game.state.defense_stats if selected.startswith("OFF") else game.state.offense_stats
    assert (fouler.penalties, fouler.penalty_yards) == (1, yards)
    assert other.penalties == 0
    assert not outcome.pending_penalty_decision
    assert game.play_log == [outcome]


def test_selected_foul_contract_uses_existing_penalty_parser() -> None:
    from paydirt.play_resolver import _create_penalty_option

    assert _create_penalty_option("DEF 15").auto_first_down
    assert not _create_penalty_option("DEF 5Y").auto_first_down


def test_selecting_explicit_decline_option_keeps_the_return() -> None:
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 20
    game.state.home_chart.special_teams.punt = {10: "DEF 5", 11: "40"}
    game.state.away_chart.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 20]]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    with patch("paydirt.game_engine.roll_chart_dice") as rolls:
        outcome = game.apply_punt_penalty_decision(pending, True, penalty_index=1)
    rolls.assert_not_called()
    assert not game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (20, 1, 10)
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    assert not outcome.pending_penalty_decision and not outcome.penalty_applied


def test_gate_checks_selected_previous_spot_penalty_rights() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    cases = {check["case"] for check in report["checks"]}
    assert {"PUNT/DEF 15/previous-first-down", "PUNT/DEF 5X->DEF 10/selected-rights"} <= cases


def test_gate_rejects_borrowed_punt_first_down_rights(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt import game_engine
    from paydirt.chart_engine_audit import audit_observer_conformance

    original = game_engine._create_penalty_option

    def corrupt(raw: str) -> object:
        option = original(raw)
        if raw == "DEF 10":
            option.auto_first_down = True
        return option

    monkeypatch.setattr(game_engine, "_create_penalty_option", corrupt)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("selected-rights" in error for error in report["errors"])
