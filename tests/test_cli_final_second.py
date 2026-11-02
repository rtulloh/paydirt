"""A genuine final second must remain playable in both CLI entry points."""

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("entry_point", ["new", "resume"])
@pytest.mark.parametrize("seconds", [0, 1, 1.0016277568145004])
def test_cli_preserves_the_engine_final_second(monkeypatch, capsys, entry_point: str, seconds: float) -> None:
    game = make_sample_game()

    def prepare() -> None:
        game.state.quarter, game.state.time_remaining = 4, seconds / 60
        game.state.home_score, game.state.away_score = 7, 0
        game.state.is_home_possession = True
        game.state.game_over = seconds == 0

    prepare()
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr("builtins.input", lambda *args: "")
    monkeypatch.setattr(cli, "_offer_record_to_standings", lambda **kwargs: None)
    monkeypatch.setattr(cli, "get_human_offense_play", lambda *args: (
        PlayType.SHORT_PASS, False, False, False, False, False,
    ))
    monkeypatch.setattr(cli, "computer_select_defense", lambda *args: DefenseType.STANDARD)
    calls = []

    def incomplete(*args) -> PenaltyChoice:
        calls.append(True)
        return PenaltyChoice(PlayResult(ResultType.INCOMPLETE))

    monkeypatch.setattr("paydirt.game_engine.resolve_play_with_penalties", incomplete)
    if entry_point == "resume":
        monkeypatch.setattr(cli, "get_save_info", lambda _: {
            "saved_at": "test", "away_team": "AWAY", "home_team": "HOME",
            "away_score": 0, "home_score": 7, "quarter": 4, "time_remaining": seconds / 60,
        })
        monkeypatch.setattr(cli, "load_game", lambda _: (game, False, True, None))
        cli.resume_game("test-save.json", compact=True)
    else:
        charts = iter([game.state.home_chart, game.state.away_chart])
        monkeypatch.setattr(cli, "select_team", lambda *args, **kwargs: next(charts))
        monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
        monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)

        def kickoff(*args, **kwargs) -> PlayOutcome:
            prepare()
            return PlayOutcome(PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS))

        monkeypatch.setattr(game, "kickoff", kickoff)
        cli.run_interactive_game(compact=True)
    assert len(calls) == int(seconds > 0)
    assert game.state.game_over
    assert game.state.time_remaining == 0
    assert "FINAL" in capsys.readouterr().out
