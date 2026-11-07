"""An own-fumble advance preserves the series and accepted penalty rights."""
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def advance_game(home: bool, down: int, chart: dict[int, str]) -> PaydirtGameEngine:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, down, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    offense = game.state.possession_team
    offense.offense.line_plunge = {10: "F - 10"}
    offense.special_teams.punt = {10: "F - 10"}
    offense.peripheral.fumble_recovered_range = (10, 31)
    offense.special_teams.interception_return = chart
    game.state.defense_team.defense.modifiers = {("A", 5): {1: "0"}}
    return game


def run_advance(
    game: PaydirtGameEngine, play: PlayType, dice: list[int], procedure: bool = False,
) -> PlayOutcome:
    resolver_dice = [(10, "10")]
    if play == PlayType.PUNT:
        dice = [10, *dice]
    elif procedure:
        resolver_dice.append((dice[0], str(dice[0])))
        dice = dice[1:]
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in dice]) as rolls,
          patch("paydirt.play_resolver.roll_chart_dice", side_effect=resolver_dice),
          patch("paydirt.play_resolver.roll_defense_dice", return_value=(1, 1, 5)),
          patch("paydirt.game_engine.random.uniform", return_value=8)):
        method = game.run_play_with_penalty_procedure if procedure else game.run_play
        outcome = method(play, DefenseType.STANDARD)
    assert rolls.call_count == len(dice)
    return outcome


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.PUNT])
@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("token,automatic", [
    ("DEF 5", False), ("DEF 5Y", False),
    ("DEF 5X", True), ("DEF 10X", True), ("DEF 15", True), ("DEF 15X", True),
])
def test_accepted_return_penalty_keeps_its_automatic_first_down(
    play: PlayType, home: bool, procedure: bool, down: int, token: str, automatic: bool,
) -> None:
    game = advance_game(home, down, {11: token, 12: "0"})
    outcome = run_advance(game, play, [17, 11, 12], procedure)
    turnover = down == 4 and not automatic
    offense_stats = game.state.home_stats if home else game.state.away_stats
    defense_stats = game.state.away_stats if home else game.state.home_stats
    penalty_yards = 15 if "15" in token else 10 if "10" in token else 5
    spot = 30 + penalty_yards
    assert outcome.first_down is automatic
    assert outcome.turnover is turnover
    assert outcome.turnover_on_downs is turnover
    assert game.state.is_home_possession is (home != turnover)
    assert game.state.ball_position == (100 - spot if turnover else spot)
    assert game.state.down == (1 if automatic or turnover else 3)
    assert game.state.yards_to_go == (10 if automatic or turnover else 13)
    assert offense_stats.first_downs == int(automatic)
    assert defense_stats.penalties == 1
    assert defense_stats.penalty_yards == penalty_yards
    assert offense_stats.fumbles_lost == defense_stats.fumbles_lost == 0


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.PUNT])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("chart,dice", [
    ({11: "DEF 15", 12: "F", 13: "0"}, [17, 11, 12, 20]),
    ({11: "F", 15: "DEF 15", 16: "0"}, [17, 11, 17, 15, 16]),
    ({11: "DEF 15", 12: "DEF 5", 13: "0"}, [17, 11, 12, 13]),
])
def test_automatic_first_down_survives_live_and_nested_return_settlement(
    play: PlayType, down: int, chart: dict[int, str], dice: list[int],
) -> None:
    game = advance_game(True, down, chart)
    outcome = run_advance(game, play, dice)
    assert outcome.first_down and not outcome.turnover
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (45, 1, 10)
    assert game.state.home_stats.first_downs == 1
    assert game.state.away_stats.penalties == 1
    assert game.state.away_stats.penalty_yards == 15


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.PUNT])
@pytest.mark.parametrize("down", [2, 4])
def test_offsetting_return_fouls_do_not_award_automatic_first_down(play: PlayType, down: int) -> None:
    game = advance_game(True, down, {11: "DEF 15", 12: "OFF 5"})
    outcome = run_advance(game, play, [17, 11, 12])
    assert outcome.result.replay_down
    assert not outcome.first_down and not outcome.turnover
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, down, 8)
    assert game.state.home_stats.first_downs == game.state.away_stats.penalties == 0


def test_gate_has_preserved_series_return_penalty_controls() -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    report = audit_observer_conformance()
    cases = {check["case"] for check in report["checks"]}
    assert {
        f"{play}/{foul}/own-fumble-first-down"
        for play in ("PUNT", "LINE_PLUNGE") for foul in ("DEF 5X", "DEF 15")
    } <= cases


def test_gate_rejects_erased_return_penalty_first_down_rights(monkeypatch: pytest.MonkeyPatch) -> None:
    from paydirt.chart_engine_audit import audit_observer_conformance

    original = PaydirtGameEngine._roll_return_chart

    def erase(self: PaydirtGameEngine, *args: object, **kwargs: object) -> object:
        result = original(self, *args, **kwargs)
        result.automatic_first_down = False
        return result

    monkeypatch.setattr(PaydirtGameEngine, "_roll_return_chart", erase)
    report = audit_observer_conformance()
    assert not report["passed"]
    assert any("own-fumble-first-down" in error for error in report["errors"])


@pytest.mark.parametrize("token", ["DEF 5X", "DEF 15", "DEF 15X"])
def test_punt_double_foul_consumer_receives_return_first_down_rights(token: str) -> None:
    game = advance_game(True, 4, {})
    game.state.home_chart.special_teams.punt = {10: "DEF 5", 11: "40"}
    game.state.away_chart.special_teams.punt_return = {12: token, 13: "0"}
    with (patch("paydirt.game_engine.roll_chart_dice", side_effect=[(n, str(n)) for n in [10, 11, 12, 13]]),
          patch.object(game, "_handle_double_foul_penalty", wraps=game._handle_double_foul_penalty) as decision):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert decision.call_args.kwargs["penalty_b_has_auto_fd"] is True
    assert "OFFSETTING" in outcome.description
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (40, 4, 8)
