"""Synthetic regressions for the interactive play-test log audit."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.commentary import TeamRoster
from paydirt.game_engine import PaydirtGameEngine
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PlayType
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


class ReachedEngine(Exception):
    """Stop the real interactive loop at its engine boundary."""


@pytest.mark.parametrize("resumed", [False, True])
@pytest.mark.parametrize("human_home", [False, True])
@pytest.mark.parametrize("down", [1, 4])
@pytest.mark.parametrize("hurry", [False, True])
def test_cpu_no_huddle_reaches_engine(
    monkeypatch: pytest.MonkeyPatch, resumed: bool, human_home: bool, down: int, hurry: bool,
) -> None:
    monkeypatch.setattr(cli, "COMPACT_MODE", True)
    monkeypatch.setattr(cli, "AI_HELPER_ENABLED", False)
    game = make_sample_game()
    game.state.is_home_possession = not human_home
    game.state.down = down
    ai = Mock(use_analysis=False)
    ai.select_offense_with_clock_management.return_value = (
        PlayType.SHORT_PASS, False, hurry, False, 0, False)
    monkeypatch.setattr(cli, "create_computer_ai", lambda *args, **kwargs: ai)
    monkeypatch.setattr(cli, "PaydirtGameEngine", lambda *args: game)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_game_status", lambda *args: None)
    monkeypatch.setattr(cli, "get_human_defense_play", lambda *args: (DefenseType.STANDARD, False))
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "_complete_touchdown_sequence", lambda game, outcome, *args: outcome)
    monkeypatch.setattr("builtins.input", lambda prompt="": (
        "A" if prompt == "\nYour choice: " and not human_home else ""))
    monkeypatch.setattr(cli.random, "choice", lambda choices: "TAILS")
    kickoff = SimpleNamespace(pending_penalty_decision=False, description="Synthetic kickoff")
    monkeypatch.setattr(game, "kickoff", lambda **kwargs: kickoff)
    charts = [game.state.home_chart, game.state.away_chart] if human_home else [
        game.state.away_chart, game.state.home_chart]
    monkeypatch.setattr(cli, "select_team", Mock(side_effect=charts))
    monkeypatch.setattr(cli, "get_save_info", lambda *args: {
        "saved_at": "test", "away_team": "AWAY", "home_team": "HOME", "away_score": 0, "home_score": 0,
        "quarter": 1, "time_remaining": 15})
    monkeypatch.setattr(cli, "load_game", lambda *args: (game, not human_home, human_home, None))
    captured = {}

    def play(*args: object, **kwargs: object) -> None:
        captured.update(kwargs)
        raise ReachedEngine

    monkeypatch.setattr(game, "run_play_with_penalty_procedure", play)
    with pytest.raises(ReachedEngine):
        if resumed:
            cli.resume_game("synthetic.save")
        else:
            cli.run_interactive_game()
    assert captured["no_huddle"] is hurry
    ai.select_offense_with_clock_management.assert_called_once_with(game)


def punt_game(
    home: bool, penalty: str = "", return_result: str = "F",
) -> tuple[PaydirtGameEngine, PlayOutcome]:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.down, game.state.yards_to_go = 26, 4, 12
    game.state.possession_team.special_teams.punt.update({16: penalty or "31", 17: "31"})
    game.state.defense_team.special_teams.punt_return[18] = return_result
    rolls = [(16, "punt")] + ([(17, "reroll")] if penalty else []) + [(18, "return")]
    if return_result == "F":
        # Explicitly lose the returner's fumble; a chart F is not an automatic loss.
        rolls.append((35, "recovery lost"))
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls):
        outcome = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    return game, outcome


@pytest.mark.parametrize("home", [False, True])
def test_punt_return_fumble_counts_against_receiver_only(home: bool) -> None:
    game, outcome = punt_game(home)
    assert game.state.is_home_possession is home
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (57, 1, 10)
    assert not outcome.turnover  # No loss by the original offense.
    assert game.state.offense_stats.turnovers == game.state.offense_stats.fumbles_lost == 0
    assert game.state.defense_stats.turnovers == game.state.defense_stats.fumbles_lost == 1
    assert outcome.result.punt_return_dice == 18


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("penalty", ["DEF 5", "DEF 5X", "OFF 10"])
@pytest.mark.parametrize("accept", [False, True])
def test_punt_penalty_does_not_disappear_on_return_fumble(home: bool, penalty: str, accept: bool) -> None:
    game, outcome = punt_game(home, penalty)
    assert outcome.pending_penalty_decision
    assert game.state.ball_position == 26 and game.state.down == 4
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
    assert "FUMBLE" in outcome.description
    assert outcome.penalty_choice.play_result.fumble_recovered
    assert outcome.result.punt_return_dice == 18
    result = game.apply_punt_penalty_decision(outcome, accept_penalty=accept)
    assert not result.pending_penalty_decision
    assert game.state.is_home_possession is home
    if accept:
        assert game.state.ball_position == (16 if penalty.startswith("OFF") else 31)
        assert game.state.down == (1 if penalty.endswith("X") else 4)
        assert game.state.yards_to_go == (10 if penalty.endswith("X") else (22 if penalty.startswith("OFF") else 7))
        assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
        fouler = game.state.offense_stats if penalty.startswith("OFF") else game.state.defense_stats
        assert fouler.penalties == 1
        assert fouler.penalty_yards == (10 if penalty.startswith("OFF") else 5)
    else:
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (57, 1, 10)
        assert game.state.defense_stats.turnovers == game.state.defense_stats.fumbles_lost == 1
        assert game.state.offense_stats.turnovers == 0
        assert "FUMBLE" in result.description
        # A second application must not double-credit the lost fumble.
        game.apply_punt_penalty_decision(result, accept_penalty=False)
        assert game.state.defense_stats.turnovers == 1
    assert len(game.play_log) == 1


@pytest.mark.parametrize("home", [False, True])
def test_ordinary_punt_is_not_a_statistical_turnover(home: bool) -> None:
    game, outcome = punt_game(home, return_result="4")
    assert game.state.is_home_possession is not home
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
    assert not outcome.turnover


@pytest.mark.parametrize("flow", ["direct", "procedure", "declined-penalty"])
@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.MEDIUM_PASS, PlayType.SCREEN, PlayType.TE_SHORT_LONG])
@pytest.mark.parametrize("home", [False, True])
def test_touchdown_outcome_keeps_the_logged_scorer(flow: str, play: PlayType, home: bool) -> None:
    game = make_sample_game()
    game.state.is_home_possession, game.state.ball_position = home, 99
    game.state.defense_team.defense.modifiers.clear()
    column = play.value.lower().replace(" ", "_")
    getattr(game.state.possession_team.offense, column).update({16: "5", 14: "OFF 5"})
    roster = TeamRoster(qb=["Test QB"], rb=["Runner One", "Runner Two"],
                        wr=["Receiver One", "Receiver Two"], te=["Tight One", "Tight Two"])
    rolls = ([(14, "penalty")] if flow == "declined-penalty" else []) + [(16, "gain")]
    with (patch("paydirt.game_engine.get_roster", return_value=roster),
          patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls),
          patch("paydirt.play_resolver.roll_white_dice", return_value=(1, "defense"))):
        if flow == "direct":
            outcome = game.run_play(play, DefenseType.STANDARD)
        else:
            outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
            if flow == "declined-penalty":
                assert outcome.pending_penalty_decision
                outcome = game.apply_penalty_decision(outcome, accept_play=True)
    assert outcome.touchdown
    score = game.state.scoring_plays[-1]
    assert score.description in outcome.description
    assert "1 yards" in score.description


@pytest.mark.parametrize("compact", [False, True])
def test_presenters_reuse_engine_touchdown_description(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, compact: bool,
) -> None:
    from paydirt.play_resolver import PlayResult, ResultType
    game = make_sample_game()
    description = "Test QB pass complete to Canonical Receiver for 1 yards. TOUCHDOWN"
    outcome = PlayOutcome(play_type=PlayType.MEDIUM_PASS, defense_type=DefenseType.STANDARD,
                          result=PlayResult(ResultType.YARDS, yards=1, raw_result="1"),
                          yards_gained=1, touchdown=True, description=description)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    with patch("paydirt.commentary.Commentary.generate", return_value="WRONG SCORER") as generate:
        cli.display_play_result(game, outcome, PlayType.MEDIUM_PASS, DefenseType.STANDARD,
                                game.state.home_chart, offense_was_home=False)
        assert description in capsys.readouterr().out
        assert ResultFormatter("AWAY", "HOME").format(outcome).commentary == description
    generate.assert_not_called()


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("penalty", ["DEF 5", "OFF 10"])
@pytest.mark.parametrize("decision", ["replay", "decline", "keep"])
def test_ordinary_punt_penalties_charge_only_applied_yardage(
    home: bool, penalty: str, decision: str,
) -> None:
    game, outcome = punt_game(home, penalty, return_result="4")
    assert outcome.pending_penalty_decision
    assert game.state.home_stats.penalties == game.state.away_stats.penalties == 0
    accept = decision != "decline"
    index = 1 if decision == "keep" and penalty.startswith("OFF") else 0
    result = game.apply_punt_penalty_decision(outcome, accept_penalty=accept, penalty_index=index)
    assert not result.pending_penalty_decision
    stats = game.state.home_stats if (home == penalty.startswith("OFF")) else game.state.away_stats
    assert stats.penalties == int(accept)
    assert stats.penalty_yards == ((10 if penalty.startswith("OFF") else 5) if accept else 0)
    assert game.state.home_stats.turnovers == game.state.away_stats.turnovers == 0
    if accept and index == 0:
        assert game.state.yards_to_go == (22 if penalty.startswith("OFF") else 7)


@pytest.mark.parametrize("penalty", ["DEF 5", "DEF 5X", "OFF 10"])
def test_cpu_preserves_punt_recovery_or_erases_return_fumble(penalty: str) -> None:
    from paydirt.computer_ai import ComputerAI
    _game, outcome = punt_game(True, penalty)
    assert outcome.pending_penalty_decision
    accept_play, _ = ComputerAI().should_accept_penalty(outcome, False, False)
    assert accept_play is penalty.startswith("DEF")


def test_web_touchdown_commentary_does_not_reselect_scorer() -> None:
    from paydirt.play_resolver import PlayResult, ResultType
    description = "Canonical Runner rushed for 1 yards. TOUCHDOWN"
    outcome = PlayOutcome(play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
                          result=PlayResult(ResultType.YARDS, yards=1, raw_result="1"),
                          yards_gained=1, touchdown=True, description=description)
    with patch("paydirt.commentary.Commentary.generate", return_value="WRONG SCORER") as generate:
        for _ in range(2):
            assert ResultFormatter("HOME", "AWAY").format(outcome).commentary == description
    generate.assert_not_called()


@pytest.mark.parametrize("penalty", ["DEF 5", "OFF 10"])
def test_punt_fumble_choice_displays_engine_recovery(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, penalty: str,
) -> None:
    game, outcome = punt_game(True, penalty)
    assert outcome.pending_penalty_decision
    monkeypatch.setattr("builtins.input", lambda *args: "1")
    # The human controls whichever side is offended.
    human_home = penalty.startswith("DEF")
    result = cli.handle_penalty_decision(game, outcome, human_home, human_home)
    output = capsys.readouterr().out
    choice = next(line for line in output.splitlines() if "[1] Accept PLAY result:" in line)
    assert "FUMBLE" in choice and "HOME" in choice
    assert game.state.is_home_possession and not result.pending_penalty_decision
