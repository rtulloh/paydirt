"""Punt commentary describes the initial return and later recovery separately."""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from tests.game_fixtures import make_sample_game


def resolve_punt(
    kicking_home: bool, recovery: int = 38, advance: int = 37,
    flow: str = 'procedure', return_cell: str = 'F + 6',
) -> tuple[PaydirtGameEngine, PlayOutcome, str, str]:
    """Use public charts with synthetic cells and the reported four-roll sequence."""
    game = make_sample_game()
    game.state.is_home_possession = kicking_home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 32, 4, 4
    kicker = game.state.possession_team
    receiver = game.state.defense_team
    kicker.special_teams.punt.update({19: 'DEF 5', 20: '44'})
    receiver.special_teams.punt_return[15] = return_cell
    receiver.peripheral.fumble_recovered_range = (10, 27)
    kicker.special_teams.interception_return[24] = str(advance)
    receiver.special_teams.interception_return[24] = str(advance)
    rolls = [19] if flow == 'declined' else []
    rolls += [20, 15]
    if return_cell.startswith('F'):
        rolls.append(recovery)
        if recovery in (17, 18, 19, 37, 38, 39):
            rolls.append(24)
    with (
        patch('paydirt.game_engine.roll_chart_dice', side_effect=[(roll, f'Roll {roll}') for roll in rolls]) as dice,
        patch('paydirt.game_engine.random.uniform', return_value=6),
    ):
        run = game.run_play if flow == 'direct' else game.run_play_with_penalty_procedure
        outcome = run(PlayType.PUNT, DefenseType.STANDARD)
        if flow == 'declined':
            assert outcome.pending_penalty_decision
            outcome = game.apply_punt_penalty_decision(outcome, False)
    assert dice.call_count == len(rolls)
    return game, outcome, kicker.peripheral.short_name, receiver.peripheral.short_name


@pytest.mark.parametrize('kicking_home', [False, True])
@pytest.mark.parametrize('flow', ['direct', 'procedure', 'declined'])
@pytest.mark.parametrize('advance,spot,touchdown', [(10, 80, False), (37, 99, True)])
def test_reported_punt_recovery_has_correct_game_state(
    kicking_home: bool, flow: str, advance: int, spot: int, touchdown: bool,
) -> None:
    game, outcome, kicker, _ = resolve_punt(kicking_home, advance=advance, flow=flow)
    assert game.state.is_home_possession is kicking_home
    assert game.state.ball_position == spot
    assert outcome.touchdown is touchdown
    assert game.state.home_score == (6 if kicking_home and touchdown else 0)
    assert game.state.away_score == (6 if not kicking_home and touchdown else 0)
    receiver_stats = game.state.away_stats if kicking_home else game.state.home_stats
    assert receiver_stats.fumbles_lost == receiver_stats.turnovers == 1
    if touchdown:
        assert game.state.scoring_plays[-1].team == kicker
    for fact in ('Ret:15→"F + 6"', 'R:38→"lost"', f'FR:24→"{advance}"'):
        assert fact in outcome.description


@pytest.mark.parametrize('kicking_home', [False, True])
@pytest.mark.parametrize('flow', ['direct', 'procedure', 'declined'])
@pytest.mark.parametrize('advance', [10, 37])
def test_punt_does_not_attach_initial_return_yards_to_later_recovery_spot(
    kicking_home: bool, flow: str, advance: int,
) -> None:
    game, outcome, kicker, receiver = resolve_punt(kicking_home, advance=advance, flow=flow)
    assert 'returned 6 yards before a fumble' in outcome.description
    assert f'FUMBLE on the return at {receiver} 30! {kicker} recovers' in outcome.description
    assert 'returned 6 yards to' not in outcome.description
    if outcome.touchdown:
        assert f'{kicker} scores a TOUCHDOWN!' in outcome.description
        assert outcome.result.scoring_team == kicker
        assert f'{receiver} 1' not in outcome.description
    else:
        assert f'{kicker} ball at {receiver} 20' in outcome.description
        assert not outcome.touchdown and not game.state.scoring_plays


@pytest.mark.parametrize('kicking_home', [False, True])
@pytest.mark.parametrize('compact', [False, True])
@pytest.mark.parametrize('recovery,advance', [(20, 0), (17, 10), (38, 10), (38, 37)])
def test_cli_uses_engine_recovery_and_scoring_narrative_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    kicking_home: bool, compact: bool, recovery: int, advance: int,
) -> None:
    game, outcome, kicker, receiver = resolve_punt(kicking_home, recovery, advance)
    monkeypatch.setattr(cli, 'COMPACT_MODE', compact)
    cli.display_play_result(
        game, outcome, PlayType.PUNT, DefenseType.STANDARD,
        game.state.home_chart if kicking_home else game.state.away_chart, kicking_home,
    )
    text = capsys.readouterr().out
    assert outcome.description in text
    assert f'>> {kicker} recovers and keeps possession!' not in text
    assert text.upper().count('TOUCHDOWN') == int(outcome.touchdown)
    assert 'PUNT RETURN TOUCHDOWN' not in text
    assert f'FUMBLE on the return at {receiver} 30!' in text
    assert game.state.is_home_possession is (not kicking_home if recovery < 28 else kicking_home)


@pytest.mark.parametrize('kicking_home', [False, True])
@pytest.mark.parametrize('compact', [False, True])
def test_ordinary_return_remains_at_receivers_30(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    kicking_home: bool, compact: bool,
) -> None:
    game, outcome, _, receiver = resolve_punt(kicking_home, return_cell='6')
    assert not outcome.touchdown and not outcome.safety
    assert game.state.is_home_possession is not kicking_home
    assert game.state.ball_position == 30
    assert f'returned 6 yards to {receiver} 30' in outcome.description
    monkeypatch.setattr(cli, 'COMPACT_MODE', compact)
    cli.display_play_result(game, outcome, PlayType.PUNT, DefenseType.STANDARD,
                            game.state.home_chart if kicking_home else game.state.away_chart, kicking_home)
    assert outcome.description in capsys.readouterr().out


@pytest.mark.parametrize('kicking_home', [False, True])
@pytest.mark.parametrize('compact', [False, True])
def test_ordinary_return_touchdown_names_receiver_without_one_yard_destination(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    kicking_home: bool, compact: bool,
) -> None:
    game, outcome, kicker, receiver = resolve_punt(kicking_home, return_cell='TD')
    assert outcome.touchdown and game.state.is_home_possession is not kicking_home
    assert f'{receiver} scores a TOUCHDOWN!' in outcome.description
    assert outcome.result.scoring_team == receiver
    assert f'{kicker} 1' not in outcome.description
    monkeypatch.setattr(cli, 'COMPACT_MODE', compact)
    cli.display_play_result(game, outcome, PlayType.PUNT, DefenseType.STANDARD,
                            game.state.home_chart if kicking_home else game.state.away_chart, kicking_home)
    assert capsys.readouterr().out.upper().count('TOUCHDOWN') == 1
