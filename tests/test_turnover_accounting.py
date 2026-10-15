"""Statistical turnovers are real interceptions/lost fumbles, not possession changes."""

import json
from itertools import chain, repeat
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome, TeamStats
from paydirt.interactive_game import display_box_score
from paydirt.play_resolver import DefenseType, PlayType
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


@pytest.fixture
def game() -> PaydirtGameEngine:
    engine = make_sample_game()
    for chart in (engine.state.home_chart, engine.state.away_chart):
        chart.defense.modifiers.clear()
        chart.peripheral.fumble_recovered_range = (10, 19)
        chart.special_teams.interception_return[22] = "0"
        chart.special_teams.interception_return[37] = "TD"
    return engine


def execute(game: PaydirtGameEngine, play: PlayType, flow: str,
            recovery: int = 22, accept_play: bool = True) -> PlayOutcome:
    rolls = [(16, "synthetic")]
    if flow == "declined-penalty":
        rolls.insert(0, (14, "synthetic penalty"))
    with (
        patch("paydirt.play_resolver.roll_chart_dice",
              side_effect=chain(rolls, repeat((recovery, "synthetic recovery")))),
        patch("paydirt.play_resolver.random.choice", side_effect=lambda choices: choices[0]),
        patch("paydirt.game_engine.roll_chart_dice", return_value=(recovery, "synthetic")),
        patch("paydirt.game_engine.roll_white_dice", return_value=(2, "synthetic")),
    ):
        if flow == "direct":
            return game.run_play(play, DefenseType.STANDARD)
        outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
        if flow == "declined-penalty":
            assert outcome.pending_penalty_decision
            assert game.state.offense_stats.turnovers == 3
            assert game.state.offense_stats.interceptions_thrown == 2
            assert game.state.offense_stats.fumbles_lost == 1
            outcome = game.apply_penalty_decision(outcome, accept_play=accept_play)
        assert not outcome.pending_penalty_decision
        return outcome


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined-penalty"])
@pytest.mark.parametrize("raw,position,recovery,down,ints,fumbles", [
    ("INT 10", 50, 22, 1, 1, 0),
    ("INT 10", 95, 22, 1, 1, 0),  # Interception touchback.
    ("INT 10", 50, 37, 1, 1, 0),  # Pick-six.
    ("F -2", 50, 22, 1, 0, 1),
    ("F +1", 99, 22, 1, 0, 1),  # Opponent's goal line.
    ("F +11", 99, 22, 1, 0, 1),  # Beyond opponent's end line.
    ("F -2", 1, 22, 1, 0, 1),  # Defense recovers for a touchdown.
    ("F +2", 50, 37, 1, 0, 1),  # Fumble return touchdown.
    ("F +2", 50, 16, 1, 0, 0),  # Offense recovers and advances zero yards.
    ("F +2", 50, 16, 4, 0, 0),  # Own recovery, then turnover on downs.
    ("F -2", 1, 16, 1, 0, 0),  # Own recovery for a safety.
    ("0", 50, 22, 4, 0, 0),  # Ordinary turnover on downs.
])
def test_each_applied_loss_counts_once_for_original_offense(
    game: PaydirtGameEngine, home: bool, flow: str, raw: str,
    position: int, recovery: int, down: int, ints: int, fumbles: int,
) -> None:
    state = game.state
    state.is_home_possession = home
    state.ball_position, state.down, state.yards_to_go = position, down, 10
    state.home_stats = TeamStats(turnovers=3 if home else 5,
                                interceptions_thrown=2 if home else 4, fumbles_lost=1)
    state.away_stats = TeamStats(turnovers=5 if home else 3,
                                interceptions_thrown=4 if home else 2, fumbles_lost=1)
    offense, defense = state.offense_stats, state.defense_stats
    state.possession_team.offense.medium_pass.update({14: "OFF 5", 16: raw})
    state.possession_team.special_teams.interception_return[16] = "0"
    outcome = execute(game, PlayType.MEDIUM_PASS, flow, recovery)
    assert offense.interceptions_thrown == 2 + ints
    assert offense.fumbles_lost == 1 + fumbles
    assert offense.turnovers == 3 + ints + fumbles
    assert defense.turnovers == 5
    assert defense.interceptions_thrown == 4 and defense.fumbles_lost == 1
    assert offense.turnovers == offense.interceptions_thrown + offense.fumbles_lost
    if ints or fumbles:
        assert outcome.turnover
        assert state.is_home_possession is not home


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("raw", ["INT 10", "F +2"])
def test_accepted_penalty_cancels_provisional_loss(
    game: PaydirtGameEngine, home: bool, raw: str,
) -> None:
    state = game.state
    state.is_home_possession = home
    state.ball_position = 50
    state.offense_stats.turnovers = 3
    state.offense_stats.interceptions_thrown = 2
    state.offense_stats.fumbles_lost = 1
    state.possession_team.offense.medium_pass.update({14: "OFF 5", 16: raw})
    outcome = execute(game, PlayType.MEDIUM_PASS, "declined-penalty", accept_play=False)
    assert outcome.penalty_applied and not outcome.turnover
    assert state.is_home_possession is home
    assert (state.offense_stats.turnovers, state.offense_stats.interceptions_thrown,
            state.offense_stats.fumbles_lost) == (3, 2, 1)
    assert state.defense_stats.turnovers == 0


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure"])
@pytest.mark.parametrize("recovery,expected", [(16, 0), (22, 1)])
def test_qb_sneak_fumble_counts_only_when_lost(
    game: PaydirtGameEngine, home: bool, flow: str, recovery: int, expected: int,
) -> None:
    state = game.state
    state.is_home_possession = home
    state.ball_position = 50
    state.possession_team.offense.line_plunge[16] = "F"
    stats = state.offense_stats
    # Sneak's initial chart roll and recovery both use the engine dice function.
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (16, "synthetic sneak"), (recovery, "synthetic recovery"),
    ]):
        if flow == "direct":
            game.run_play(PlayType.QB_SNEAK, DefenseType.STANDARD)
        else:
            game.run_play_with_penalty_procedure(PlayType.QB_SNEAK, DefenseType.STANDARD)
    assert stats.fumbles_lost == expected
    assert stats.turnovers == expected
    assert stats.interceptions_thrown == 0


@pytest.mark.parametrize("play,position,raw", [
    (PlayType.PUNT, 50, "40*"), (PlayType.FIELD_GOAL, 70, "0"),
])
@pytest.mark.parametrize("home", [False, True])
def test_non_statistical_special_teams_possession_changes(
    game: PaydirtGameEngine, home: bool, play: PlayType, position: int, raw: str,
) -> None:
    state = game.state
    state.is_home_possession = home
    state.ball_position, state.down = position, 4
    field = "punt" if play == PlayType.PUNT else "field_goal"
    getattr(state.possession_team.special_teams, field)[16] = raw
    with (
        patch("paydirt.game_engine.roll_chart_dice", return_value=(16, "synthetic")),
        patch("paydirt.play_resolver.roll_chart_dice", return_value=(16, "synthetic")),
    ):
        game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
    assert state.is_home_possession is not home
    assert state.home_stats.turnovers == state.away_stats.turnovers == 0


@pytest.mark.parametrize("home", [False, True])
def test_cli_uses_engine_turnover_total(
    game: PaydirtGameEngine, home: bool, capsys: pytest.CaptureFixture,
) -> None:
    # Legacy aggregate-only statistics have no complete component breakdown.
    stats = game.state.home_stats if home else game.state.away_stats
    stats.turnovers = 4
    display_box_score(game)
    line = next(line for line in capsys.readouterr().out.splitlines() if "Turnovers" in line)
    cells = [cell.strip() for cell in line.split("|") if cell.strip()]
    assert cells == ["Turnovers", "0" if home else "4", "4" if home else "0"]


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("stored,ints,fumbles", [(0, 2, 1), (12, 1, 1), (3, 2, 1), (9, 0, 0)])
def test_load_repairs_component_complete_turnover_totals(
    game: PaydirtGameEngine, tmp_path: Path, home: bool, stored: int, ints: int, fumbles: int,
) -> None:
    path = tmp_path / "game.json"
    save_game(game, str(path))
    data = json.loads(path.read_text())
    key = "home_stats" if home else "away_stats"
    data[key].update(turnovers=stored, interceptions_thrown=ints, fumbles_lost=fumbles)
    path.write_text(json.dumps(data))
    loaded, *_ = load_game(str(path))
    stats = loaded.state.home_stats if home else loaded.state.away_stats
    assert stats.turnovers == ints + fumbles
    assert (stats.interceptions_thrown, stats.fumbles_lost) == (ints, fumbles)
    save_game(loaded, str(path))
    saved = json.loads(path.read_text())
    assert saved["version"] == data["version"] == 1
    assert saved[key]["turnovers"] == ints + fumbles
    assert set(saved[key]) == set(data[key])


@pytest.mark.parametrize("home", [False, True])
def test_legacy_aggregate_only_survives_play_and_repeated_round_trips(
    game: PaydirtGameEngine, tmp_path: Path, home: bool,
) -> None:
    path = tmp_path / "legacy.json"
    save_game(game, str(path))
    data = json.loads(path.read_text())
    data["is_home_possession"] = home
    key = "home_stats" if home else "away_stats"
    data[key] = {"turnovers": 4}
    path.write_text(json.dumps(data))
    loaded, *_ = load_game(str(path))
    assert loaded.state.offense_stats.turnovers == 4
    loaded.state.possession_team.offense.medium_pass[16] = "INT 10"
    stats = loaded.state.offense_stats
    execute(loaded, PlayType.MEDIUM_PASS, "procedure")
    assert (stats.turnovers, stats.interceptions_thrown, stats.fumbles_lost) == (5, 1, 0)
    for _ in range(2):
        save_game(loaded, str(path))
        loaded, *_ = load_game(str(path))
        stats = loaded.state.home_stats if home else loaded.state.away_stats
        assert (stats.turnovers, stats.interceptions_thrown, stats.fumbles_lost) == (5, 1, 0)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("partial,expected", [
    ({"turnovers": 4, "interceptions_thrown": 1}, 4),
    ({"interceptions_thrown": 2}, 2),
    ({"fumbles_lost": 1}, 1),
    ({}, 0),
])
def test_incomplete_legacy_breakdowns_preserve_known_counts(
    game: PaydirtGameEngine, tmp_path: Path, home: bool, partial: dict, expected: int,
) -> None:
    path = tmp_path / "partial.json"
    save_game(game, str(path))
    data = json.loads(path.read_text())
    key = "home_stats" if home else "away_stats"
    data[key] = partial
    path.write_text(json.dumps(data))
    for _ in range(2):
        loaded, *_ = load_game(str(path))
        stats = loaded.state.home_stats if home else loaded.state.away_stats
        assert stats.turnovers == expected
        assert stats.interceptions_thrown == partial.get("interceptions_thrown", 0)
        assert stats.fumbles_lost == partial.get("fumbles_lost", 0)
        save_game(loaded, str(path))
