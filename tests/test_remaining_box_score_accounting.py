"""Signed yardage, sack and enforced-penalty regressions; no private charts."""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import TeamStats
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)
from tests.game_fixtures import make_sample_game
from tests.test_box_score_accounting import play


@pytest.fixture(params=[True, False], ids=["home-offense", "away-offense"])
def game(request: pytest.FixtureRequest) -> PaydirtGameEngine:
    engine = make_sample_game()
    engine.state.is_home_possession = request.param
    engine.state.quarter = 3
    engine.state.time_remaining = 10
    engine.state.ball_position = 50
    engine.state.down = 2
    engine.state.yards_to_go = 10
    return engine


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("play_type", [PlayType.OFF_TACKLE, PlayType.SHORT_PASS])
@pytest.mark.parametrize("yards", [-6, -1, 4, 12])
@pytest.mark.parametrize("recovers", [False, True])
def test_fumble_credits_pre_fumble_yards_to_original_offense(
    game: PaydirtGameEngine, procedure: bool, play_type: PlayType, yards: int, recovers: bool,
) -> None:
    offense = game.state.offense_stats
    defense = game.state.defense_stats
    result = PlayResult(
        ResultType.FUMBLE, yards=yards, fumble_resolved=True,
        fumble_recovered=recovers, fumble_recovery_roll=26 if recovers else 35,
    )
    outcome = play(game, result, play_type, procedure)
    assert outcome.turnover is (not recovers)
    assert offense.total_yards == yards
    assert offense.rushing_yards == (yards if play_type == PlayType.OFF_TACKLE else 0)
    assert offense.passing_yards == (yards if play_type == PlayType.SHORT_PASS else 0)
    assert offense.fumbles_lost == int(not recovers)
    assert defense.total_yards == defense.rushing_yards == defense.passing_yards == 0
    assert offense.sacks == 0  # No QB-time lookup: do not guess from a negative fumble.


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("down", [2, 4])
@pytest.mark.parametrize("play_type", [PlayType.OFF_TACKLE, PlayType.SHORT_PASS])
def test_signed_yardage_counts_even_on_turnover_on_downs(
    game: PaydirtGameEngine, procedure: bool, down: int, play_type: PlayType,
) -> None:
    game.state.down = down
    offense, defense = game.state.offense_stats, game.state.defense_stats
    play(game, PlayResult(ResultType.YARDS, yards=-3), play_type, procedure)
    assert offense.total_yards == -3
    assert defense.total_yards == 0
    assert offense.rushing_yards == (-3 if play_type == PlayType.OFF_TACKLE else 0)
    assert offense.passing_yards == (-3 if play_type == PlayType.SHORT_PASS else 0)


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("down", [2, 4])
def test_kneel_counts_negative_rushing_yards_without_a_sack(
    game: PaydirtGameEngine, procedure: bool, down: int,
) -> None:
    game.state.down = down
    offense, defense = game.state.offense_stats, game.state.defense_stats
    run = game.run_play_with_penalty_procedure if procedure else game.run_play
    outcome = run(PlayType.QB_KNEEL, DefenseType.STANDARD)
    assert outcome.yards_gained == -2
    assert offense.total_yards == offense.rushing_yards == -2
    assert defense.total_yards == 0
    assert offense.passing_yards == offense.sacks == offense.sack_yards == 0


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("kind", [ResultType.SACK, ResultType.QB_SCRAMBLE])
def test_sack_deducts_team_yards_but_not_gross_passing(
    game: PaydirtGameEngine, procedure: bool, kind: ResultType,
) -> None:
    offense, defense = game.state.offense_stats, game.state.defense_stats
    offense.passing_yards = offense.total_yards = 20
    play(game, PlayResult(kind, yards=-4), PlayType.MEDIUM_PASS, procedure)
    assert offense.sacks == 1
    assert offense.sack_yards == 4
    assert offense.total_yards == 16
    assert offense.passing_yards == 20
    assert offense.net_passing_yards == 16
    assert offense.rushing_yards == 0
    assert defense.total_yards == defense.sacks == 0


@pytest.mark.parametrize("procedure", [False, True])
@pytest.mark.parametrize("yards", [-6, 0, 4])
@pytest.mark.parametrize("recovers", [False, True])
def test_real_qb_time_fumble_classifies_sack_or_rush(
    game: PaydirtGameEngine, procedure: bool, yards: int, recovers: bool,
) -> None:
    offense, defense = game.state.offense_stats, game.state.defense_stats
    game.state.possession_team.offense.medium_pass[20] = "QT"
    game.state.possession_team.offense.qb_time[21] = f"F {yards:+d}"
    game.state.defense_team.defense.modifiers[("A", 1)] = {7: ""}
    game.state.possession_team.peripheral.fumble_recovered_range = (10, 32)
    run = game.run_play_with_penalty_procedure if procedure else game.run_play
    with (
        patch("paydirt.play_resolver.random.choice", side_effect=[1, 0]),
        patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(20, "O20"), (21, "QT21")]),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(26 if recovers else 35, "Recovery")),
    ):
        outcome = run(PlayType.MEDIUM_PASS, DefenseType.STANDARD)
    assert outcome.result.qb_scramble_dice == 21
    assert outcome.result.result_type == ResultType.FUMBLE
    assert offense.total_yards == yards
    assert offense.passing_yards == 0
    assert offense.sacks == int(yards <= 0)
    assert offense.sack_yards == (-yards if yards < 0 else 0)
    assert offense.rushing_yards == (yards if yards > 0 else 0)
    assert defense.total_yards == defense.sacks == 0


@pytest.mark.parametrize("code,position,expected", [
    ("OFF 15", 27, 13), ("OFF 15", 8, 4), ("OFF 10", 50, 10),
    ("DEF 15", 96, 2), ("DEF 5X", 96, 2),
])
@pytest.mark.parametrize("accept_play", [False, True])
def test_penalty_stats_use_enforced_distance_only(
    game: PaydirtGameEngine, code: str, position: int, expected: int, accept_play: bool,
) -> None:
    game.state.ball_position = position
    offense, defense = game.state.offense_stats, game.state.defense_stats
    result = PlayResult(ResultType.YARDS, yards=0)
    option = PenaltyOption(code.split()[0], code, int(code.split()[1].rstrip("X")), code, "X" in code)
    choice = PenaltyChoice(result, penalty_options=[option], offended_team="defense" if code.startswith("OFF") else "offense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    penalized = offense if code.startswith("OFF") else defense
    assert penalized.penalties == penalized.penalty_yards == 0
    outcome = game.apply_penalty_decision(pending, accept_play=accept_play)
    assert penalized.penalties == int(not accept_play)
    assert penalized.penalty_yards == (0 if accept_play else expected)
    assert outcome.yards_gained == (0 if accept_play else -expected if code.startswith("OFF") else expected)
    assert offense.total_yards == defense.total_yards == 0


@pytest.mark.parametrize("code,position,roll,expected", [
    ("OFF S", 27, 37, 13), ("DEF S", 96, 37, 2),
])
def test_legacy_half_distance_stats(
    game: PaydirtGameEngine, code: str, position: int, roll: int, expected: int,
) -> None:
    game.state.ball_position = position
    penalized = game.state.offense_stats if code.startswith("OFF") else game.state.defense_stats
    kind = ResultType.PENALTY_OFFENSE if code.startswith("OFF") else ResultType.PENALTY_DEFENSE
    with patch("paydirt.penalty_handler.roll_chart_dice", return_value=(roll, "Penalty")):
        outcome = play(game, PlayResult(kind, raw_result=code), PlayType.OFF_TACKLE, False)
    assert penalized.penalties == 1
    assert penalized.penalty_yards == expected
    assert abs(outcome.yards_gained) == expected


@pytest.mark.parametrize("code,position,return_yards,expected_penalty", [
    ("OFF 15", 43, 12, 15),  # Reported punt: lands at 17, returns to 29, penalty to 14.
    ("OFF 15", 55, 0, 2),
    ("DEF 15", 43, 12, 15),
])
def test_punt_return_penalty_counts_for_correct_team(
    game: PaydirtGameEngine, code: str, position: int, return_yards: int, expected_penalty: int,
) -> None:
    game.state.ball_position = position
    kicking, receiving = game.state.offense_stats, game.state.defense_stats
    game.state.possession_team.special_teams.punt[20] = "40"
    game.state.defense_team.special_teams.punt_return.update({21: code, 22: str(return_yards)})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(20, "Punt"), (21, "Penalty"), (22, "Return")]):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    penalized, other = (receiving, kicking) if code.startswith("OFF") else (kicking, receiving)
    assert penalized.penalties == 1
    assert penalized.penalty_yards == expected_penalty
    assert other.penalties == other.penalty_yards == 0
    assert kicking.total_yards == receiving.total_yards == 0
    assert "Penalty on return" in outcome.description


@pytest.mark.parametrize("compact", [False, True])
def test_box_score_labels_net_and_gross_passing_and_sacks_allowed(
    game: PaydirtGameEngine, compact: bool, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from paydirt import interactive_game as cli

    stats = game.state.offense_stats
    stats.rushing_yards, stats.passing_yards, stats.sack_yards = 195, 59, 4
    stats.total_yards, stats.sacks = 250, 1
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_box_score(game)
    output = capsys.readouterr().out
    for label, expected in [("Net Passing", 55), ("Gross Passing", 59), ("Sacks Allowed", 1)]:
        line = next(line for line in output.splitlines() if label in line)
        cells = [cell.strip() for cell in line.split("|")[2:4]]
        assert cells == (["0", str(expected)] if game.state.is_home_possession else [str(expected), "0"])


def test_net_passing_is_derived_without_changing_saved_gross_yards() -> None:
    stats = TeamStats(passing_yards=59, sack_yards=4)
    assert stats.net_passing_yards == 55
    stats.sack_yards += 6
    assert stats.net_passing_yards == 49
    assert stats.passing_yards == 59


@pytest.mark.parametrize("procedure", [False, True])
def test_audited_remaining_plays_produce_reconciled_box_score(
    procedure: bool, capsys: pytest.CaptureFixture[str],
) -> None:
    """Replay the missing accounting against synthetic, already-audited baselines."""
    from paydirt import interactive_game as cli

    engine = make_sample_game()
    engine.state.quarter, engine.state.time_remaining = 3, 10
    home, away = engine.state.home_stats, engine.state.away_stats
    home.rushing_yards, home.passing_yards, home.total_yards = 196, 59, 255
    home.first_downs, home.penalties, home.penalty_yards = 18, 5, 40
    away.rushing_yards, away.passing_yards, away.total_yards = 31, 204, 235
    away.first_downs, away.penalties, away.penalty_yards = 19, 7, 95

    def fumble(home_offense: bool, kind: PlayType, yards: int, kept: bool, qt: bool = False) -> None:
        engine.state.is_home_possession = home_offense
        engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 50, 2, 10
        result = PlayResult(
            ResultType.FUMBLE, yards=yards, fumble_resolved=True,
            fumble_recovered=kept, fumble_recovery_roll=26 if kept else 35,
            qb_scramble_dice=21 if qt else 0,
        )
        play(engine, result, kind, procedure)

    fumble(False, PlayType.OFF_TACKLE, 4, False)
    fumble(False, PlayType.SHORT_PASS, 12, False)
    fumble(False, PlayType.MEDIUM_PASS, 10, True)
    fumble(False, PlayType.SCREEN, 8, True)
    fumble(False, PlayType.MEDIUM_PASS, -6, True, qt=True)
    engine.state.is_home_possession = False
    engine.state.ball_position, engine.state.yards_to_go = 99, 1
    play(engine, PlayResult(ResultType.YARDS, yards=3), PlayType.LINE_PLUNGE, procedure)

    fumble(True, PlayType.OFF_TACKLE, -1, True)
    engine.state.is_home_possession = True
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 50, 2, 10
    play(engine, PlayResult(ResultType.QB_SCRAMBLE, yards=2), PlayType.MEDIUM_PASS, procedure)
    play(engine, PlayResult(ResultType.SACK, yards=-4), PlayType.MEDIUM_PASS, procedure)
    run = engine.run_play_with_penalty_procedure if procedure else engine.run_play
    run(PlayType.QB_KNEEL, DefenseType.STANDARD)

    engine.state.is_home_possession = True
    engine.state.ball_position, engine.state.down, engine.state.yards_to_go = 27, 2, 10
    result = PlayResult(ResultType.YARDS, yards=0)
    choice = PenaltyChoice(result, penalty_options=[PenaltyOption("OFF", "OFF 15", 15, "Offensive penalty")], offended_team="defense")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = engine.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    engine.apply_penalty_decision(pending, accept_play=False)

    engine.state.ball_position = 43
    engine.state.home_chart.special_teams.punt[20] = "40"
    engine.state.away_chart.special_teams.punt_return.update({21: "OFF 15", 22: "12"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(20, "Punt"), (21, "Penalty"), (22, "Return")]):
        engine.run_play(PlayType.PUNT, DefenseType.STANDARD)

    assert (away.first_downs, home.first_downs) == (21, 18)
    assert (away.total_yards, home.total_yards) == (264, 250)
    assert (away.rushing_yards, home.rushing_yards) == (36, 195)
    assert (away.passing_yards, home.passing_yards) == (234, 59)
    assert (away.net_passing_yards, home.net_passing_yards) == (228, 55)
    assert (away.penalties, home.penalties) == (8, 6)
    assert (away.penalty_yards, home.penalty_yards) == (110, 53)
    for stats in (away, home):
        assert stats.total_yards == stats.rushing_yards + stats.net_passing_yards
    cli.display_box_score(engine)
    output = capsys.readouterr().out
    for label, values in [("Total Yards", ["264", "250"]), ("Net Passing", ["228", "55"]), ("Penalty Yards", ["110", "53"])]:
        line = next(line for line in output.splitlines() if label in line)
        assert [cell.strip() for cell in line.split("|")[2:4]] == values


def test_net_passing_property_keeps_saved_stats_compatible() -> None:
    from dataclasses import asdict

    original = TeamStats(rushing_yards=195, passing_yards=59, total_yards=250, sack_yards=4)
    saved = asdict(original)
    assert "net_passing_yards" not in saved
    restored = TeamStats(**saved)
    assert restored.net_passing_yards == 55
    assert restored.passing_yards == 59


@pytest.mark.parametrize("offsetting", [False, True])
def test_clean_or_offsetting_punt_returns_do_not_add_penalty_stats(
    game: PaydirtGameEngine, offsetting: bool,
) -> None:
    game.state.ball_position = 43
    kicking, receiving = game.state.offense_stats, game.state.defense_stats
    game.state.possession_team.special_teams.punt[20] = "40"
    game.state.defense_team.special_teams.punt_return.update({21: "OFF 15" if offsetting else "12", 22: "DEF 10", 23: "12"})
    rolls = [(20, "Punt"), (21, "Return")]
    if offsetting:
        rolls += [(22, "Offsets"), (20, "Re-punt"), (23, "Clean return")]
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls):
        game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert kicking.penalties == receiving.penalties == 0
    assert kicking.penalty_yards == receiving.penalty_yards == 0


@pytest.mark.parametrize("code,position,expected_penalty,td", [("OFF 15", 55, 2, False), ("DEF 15", 43, 15, True)])
def test_punt_return_td_penalty_uses_catch_spot_or_deferred_enforcement(
    game: PaydirtGameEngine, code: str, position: int, expected_penalty: int, td: bool,
) -> None:
    game.state.ball_position = position
    kicking, receiving = game.state.offense_stats, game.state.defense_stats
    game.state.possession_team.special_teams.punt[20] = "40"
    game.state.defense_team.special_teams.punt_return.update({21: code, 22: "100"})
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(20, "Punt"), (21, "Penalty"), (22, "Return")]):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    penalized, other = (receiving, kicking) if code.startswith("OFF") else (kicking, receiving)
    assert penalized.penalties == 1
    assert penalized.penalty_yards == expected_penalty
    assert other.penalties == 0
    assert outcome.touchdown is td
    assert kicking.first_downs == receiving.first_downs == 0
    assert kicking.total_yards == receiving.total_yards == 0
    assert game.state.pending_kickoff_penalty_yards == (15 if td else 0)
    if not td:
        assert game.state.ball_position == 3  # Catch at own 5, half-distance penalty of 2.
