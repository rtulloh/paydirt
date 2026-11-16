"""Saved scores resume their owed procedure without adding points again."""

from __future__ import annotations

import json
from unittest.mock import ANY, Mock, patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


class StopBeforeNextSnap(Exception):
    """Stop the resumed CLI loop after its scoring follow-up."""


def scored_game(result: PlayResult, *, home: bool):
    """Produce a real engine score and return both the game and its outcome."""
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.quarter, game.state.time_remaining = 3, 5.0
    game.state.two_minute_warning_called = True
    if result.result_type == ResultType.SACK:
        game.state.ball_position, game.state.down, game.state.yards_to_go = 3, 2, 8
    else:
        game.state.ball_position, game.state.down, game.state.yards_to_go = 94, 2, 6
    with (
        patch(
            "paydirt.game_engine.resolve_play_with_penalties",
            return_value=PenaltyChoice(result),
        ),
        patch("paydirt.game_engine.random.uniform", return_value=30),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.OFF_TACKLE, DefenseType.STANDARD
        )
    assert outcome.touchdown is not outcome.safety
    return game, outcome


def resume_patches(monkeypatch, game, *, away: bool, home: bool, pending: str | None) -> None:
    """Drive resume through the loaded state and stop before the next snap."""
    monkeypatch.setattr(cli, "load_game", lambda _: (game, away, home, pending))
    monkeypatch.setattr(
        cli, "create_computer_ai",
        lambda *args, **kwargs: Mock(use_analysis=False),
    )
    monkeypatch.setattr(cli, "get_save_info", lambda _: {
        "saved_at": "synthetic", "away_team": "AWAY", "home_team": "HOME",
        "away_score": game.state.away_score, "home_score": game.state.home_score,
        "quarter": game.state.quarter, "time_remaining": game.state.time_remaining * 60,
    })
    monkeypatch.setattr(cli, "get_kickoff_choice", lambda *args: False)
    monkeypatch.setattr(cli, "clear_screen", lambda: None)
    monkeypatch.setattr(cli, "display_box_score", lambda *args: None)
    monkeypatch.setattr(cli, "display_game_status", Mock(side_effect=StopBeforeNextSnap))
    monkeypatch.setattr("builtins.input", lambda prompt="": "")


@pytest.mark.parametrize("home", [False, True], ids=["away-scorer", "home-scorer"])
def test_real_touchdown_save_load_resume_does_not_double_score(tmp_path, monkeypatch, home):
    """The loader must preserve an already-scored real TD and resume only its try."""
    game, outcome = scored_game(PlayResult(ResultType.YARDS, yards=9), home=home)
    score_before = (game.state.home_score, game.state.away_score)
    scoring_before = [(p.team, p.play_type, p.points) for p in game.state.scoring_plays]
    assert score_before[0 if home else 1] == 6
    assert scoring_before == [(game.state.possession_team.peripheral.short_name, "TD", 6)]
    assert game.pending_post_score_action() == "try"

    path = tmp_path / "real-touchdown.json"
    save_game(game, str(path), human_is_away=not home, human_is_home=home)
    loaded, away, is_home, pending = load_game(str(path))
    assert (away, is_home, pending) == (not home, home, "try")
    assert (loaded.state.home_score, loaded.state.away_score) == score_before
    assert [(p.team, p.play_type, p.points) for p in loaded.state.scoring_plays] == scoring_before

    kicks = Mock(return_value=PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
        description="Synthetic kickoff",
    ))
    loaded.state.possession_team.special_teams.extra_point_no_good = []
    loaded.kickoff = kicks
    loaded.onside_kick = kicks
    attempts = Mock(wraps=loaded.attempt_extra_point)
    loaded.attempt_extra_point = attempts
    resume_patches(monkeypatch, loaded, away=away, home=is_home, pending=pending)

    with pytest.raises(StopBeforeNextSnap):
        cli.resume_game(str(path), compact=True)

    attempts.assert_called_once_with()
    kicks.assert_called_once_with(kicking_home=home)
    assert (loaded.state.home_score, loaded.state.away_score) == (
        score_before[0] + (1 if home else 0), score_before[1] + (0 if home else 1)
    )
    assert [p.play_type for p in loaded.state.scoring_plays] == ["TD", "PAT"]


@pytest.mark.parametrize("home", [False, True], ids=["away-scorer", "home-scorer"])
def test_missed_try_resumes_without_repeating_or_inventing_a_score(tmp_path, monkeypatch, home):
    """A failed try is not a scoring entry; field position must not create one."""
    game, _ = scored_game(PlayResult(ResultType.YARDS, yards=9), home=home)
    game.state.possession_team.special_teams.extra_point_no_good = [26]
    path = tmp_path / "missed-try.json"
    save_game(game, str(path), human_is_away=not home, human_is_home=home)
    loaded, away, is_home, pending = load_game(str(path))
    assert pending == "try"
    score_before = (loaded.state.home_score, loaded.state.away_score)
    loaded.state.possession_team.special_teams.extra_point_no_good = [26]

    loaded.setup_for_pat()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "miss")):
        success, _ = loaded.attempt_extra_point()
    assert success is False
    assert (loaded.state.home_score, loaded.state.away_score) == score_before
    assert loaded.pending_post_score_action() == "kickoff"
    assert [p.play_type for p in loaded.state.scoring_plays] == ["TD"]


def test_field_goal_save_resume_takes_the_owed_kickoff(tmp_path, monkeypatch):
    """A score with its try already resolved resumes by kicking off once."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 3, 5.0
    game.state.ball_position = 70
    game.state.possession_team.special_teams.field_goal = dict.fromkeys(range(10, 40), "40")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "FG")):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.field_goal_made and game.pending_post_score_action() == "kickoff"
    score_before = (game.state.home_score, game.state.away_score)

    path = tmp_path / "field-goal.json"
    save_game(game, str(path), human_is_away=False, human_is_home=True)
    loaded, away, is_home, pending = load_game(str(path))
    assert pending == "kickoff"
    assert (loaded.state.home_score, loaded.state.away_score) == score_before
    kick = Mock(return_value=PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
        description="Synthetic kickoff",
    ))
    loaded.kickoff = kick
    loaded.onside_kick = kick
    resume_patches(monkeypatch, loaded, away=away, home=is_home, pending=pending)

    with pytest.raises(StopBeforeNextSnap):
        cli.resume_game(str(path), compact=True)

    kick.assert_called_once_with(kicking_home=True)
    assert (loaded.state.home_score, loaded.state.away_score) == score_before


def test_real_safety_save_load_resume_runs_only_the_free_kick(tmp_path, monkeypatch):
    """An already-scored safety must resume its free kick without +2 again."""
    game, outcome = scored_game(
        PlayResult(ResultType.SACK, yards=-8, raw_result="-8"), home=False
    )
    assert outcome.safety
    score_before = (game.state.home_score, game.state.away_score)
    assert score_before == (2, 0)
    assert [(p.play_type, p.points) for p in game.state.scoring_plays] == [("Safety", 2)]
    assert game.pending_post_score_action() == "safety_free_kick"

    path = tmp_path / "real-safety.json"
    save_game(game, str(path), human_is_away=False, human_is_home=True)
    loaded, away, is_home, pending = load_game(str(path))
    assert (away, is_home, pending) == (False, True, "safety_free_kick")
    assert (loaded.state.home_score, loaded.state.away_score) == score_before

    free_kick = Mock(return_value=PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
        description="Synthetic safety free kick",
    ))
    resume_patches(monkeypatch, loaded, away=away, home=is_home, pending=pending)
    monkeypatch.setattr(cli, "handle_safety_free_kick", free_kick)

    with pytest.raises(StopBeforeNextSnap):
        cli.resume_game(str(path), compact=True)

    free_kick.assert_called_once_with(loaded, False, True, ANY)
    assert (loaded.state.home_score, loaded.state.away_score) == score_before
    assert [(p.play_type, p.points) for p in loaded.state.scoring_plays] == [("Safety", 2)]


def test_resumed_kickoff_return_touchdown_still_runs_the_try(tmp_path, monkeypatch):
    """A score during the resumed kick must not skip its owed conversion."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 3, 5.0
    game.state.ball_position = 70
    game.state.possession_team.special_teams.field_goal = dict.fromkeys(range(10, 40), "40")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "FG")):
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert outcome.field_goal_made and game.pending_post_score_action() == "kickoff"

    path = tmp_path / "kickoff-return.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    loaded, away, is_home, pending = load_game(str(path))
    assert pending == "kickoff"
    score_before = (loaded.state.home_score, loaded.state.away_score)
    assert score_before == (3, 0)

    ordinary_return = PlayOutcome(
        PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.YARDS),
        description="Synthetic kickoff",
    )
    returns = [ordinary_return]
    attempts = Mock(wraps=loaded.attempt_extra_point)

    def kickoff(kicking_home: bool = True) -> PlayOutcome:
        # A real return switches possession before the engine scores it.
        loaded.state.is_home_possession = not kicking_home
        if not returns:
            result = ordinary_return
        else:
            returns.pop(0)
            loaded._score_touchdown(PlayType.KICKOFF, 95)
            result = PlayOutcome(
                PlayType.KICKOFF, DefenseType.STANDARD, PlayResult(ResultType.TOUCHDOWN),
                touchdown=True, description="Synthetic kickoff return touchdown",
            )
        return result

    kicks = Mock(side_effect=kickoff)
    loaded.kickoff = kicks
    loaded.onside_kick = kicks
    loaded.state.away_chart.special_teams.extra_point_no_good = []
    loaded.state.home_chart.special_teams.extra_point_no_good = []
    loaded.attempt_extra_point = attempts
    resume_patches(monkeypatch, loaded, away=away, home=is_home, pending=pending)

    with pytest.raises(StopBeforeNextSnap):
        cli.resume_game(str(path), compact=True)

    assert [call.kwargs for call in kicks.call_args_list] == [
        {"kicking_home": True}, {"kicking_home": False},
    ]
    attempts.assert_called_once_with()
    assert [play.play_type for play in loaded.state.scoring_plays] == ["FG", "TD", "PAT"]
    assert (loaded.state.home_score, loaded.state.away_score) == (3, 7)


def test_end_zone_position_without_a_score_record_is_rejected(tmp_path):
    """A corrupt legacy save cannot be repaired by inventing six points."""
    game = make_sample_game()
    game.state.ball_position = 100
    game.state.is_home_possession = True
    path = tmp_path / "corrupt.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    data = json.loads(path.read_text())
    data.pop("pending_post_score_action")
    path.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="end-zone field position"):
        load_game(str(path))


def test_own_end_zone_position_without_a_safety_record_is_rejected(tmp_path):
    """A zero-position save cannot silently start a scrimmage snap on the goal line."""
    game = make_sample_game()
    game.state.ball_position = 0
    path = tmp_path / "corrupt-safety.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    data = json.loads(path.read_text())
    data.pop("pending_post_score_action")
    path.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="own-end-zone field position"):
        load_game(str(path))


def test_legacy_end_zone_touchdown_derives_only_the_try(tmp_path):
    """Old saves may lack the marker; the scoring record proves points exist."""
    game, _ = scored_game(PlayResult(ResultType.YARDS, yards=9), home=True)
    path = tmp_path / "legacy-td.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    data = json.loads(path.read_text())
    data.pop("pending_post_score_action")
    path.write_text(json.dumps(data))

    loaded, _, _, pending = load_game(str(path))
    assert pending == "try"
    assert (loaded.state.home_score, loaded.state.away_score) == (6, 0)
    assert [(play.play_type, play.points) for play in loaded.state.scoring_plays] == [("TD", 6)]


def test_completed_overtime_touchdown_reload_owes_no_conversion(tmp_path):
    """A game-ending OT TD still leaves the ball past the goal line; no try is owed."""
    game = make_sample_game()
    game.state.is_overtime = True
    game.state.is_home_possession = True
    game.state.home_score = game.state.away_score = 14
    game.state.ball_position, game.state.down, game.state.yards_to_go = 94, 2, 6
    with (
        patch(
            "paydirt.game_engine.resolve_play_with_penalties",
            return_value=PenaltyChoice(PlayResult(ResultType.YARDS, yards=9)),
        ),
        patch("paydirt.game_engine.random.uniform", return_value=30),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.OFF_TACKLE, DefenseType.STANDARD
        )
    assert outcome.touchdown and game.state.game_over
    assert game.pending_post_score_action() is None
    assert game.state.ball_position >= 100

    path = tmp_path / "overtime-td.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    loaded, _, _, pending = load_game(str(path))
    assert pending is None
    assert loaded.pending_post_score_action() is None
    assert [play.play_type for play in loaded.state.scoring_plays] == ["TD"]


def test_kickoff_setup_keeps_the_owed_kickoff_marker(tmp_path):
    """Preparing a kick must not erase the engine's record that it is owed."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 1, 5.0
    game.state.ball_position = 70
    game.state.possession_team.special_teams.field_goal = dict.fromkeys(range(10, 40), "40")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "FG")):
        game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert game.pending_post_score_action() == "kickoff"

    game.setup_for_kickoff()
    assert game.pending_post_score_action() == "kickoff"

    path = tmp_path / "prepared-kickoff.json"
    save_game(game, str(path), human_is_away=True, human_is_home=False)
    loaded, _, _, pending = load_game(str(path))
    assert pending == "kickoff"
    assert loaded.pending_post_score_action() == "kickoff"


def test_kick_execution_consumes_the_owed_kickoff_marker():
    """Only the kick itself clears the owed kickoff, not the setup before it."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.quarter, game.state.time_remaining = 1, 5.0
    game.state.ball_position = 70
    game.state.possession_team.special_teams.field_goal = dict.fromkeys(range(10, 40), "40")
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "FG")):
        game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert game.pending_post_score_action() == "kickoff"

    game.setup_for_kickoff()
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "kick")):
        game.kickoff(kicking_home=True)
    assert game.pending_post_score_action() is None


def test_stale_try_marker_on_completed_overtime_game_runs_no_conversion(monkeypatch):
    """Resume must not honor a try marker the engine says is ineligible."""
    game = make_sample_game()
    game.state.is_overtime = True
    game.state.is_home_possession = True
    game.state.home_score, game.state.away_score = 20, 14
    game.state.ball_position, game.state.down, game.state.yards_to_go = 94, 2, 6
    with (
        patch(
            "paydirt.game_engine.resolve_play_with_penalties",
            return_value=PenaltyChoice(PlayResult(ResultType.YARDS, yards=9)),
        ),
        patch("paydirt.game_engine.random.uniform", return_value=30),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.OFF_TACKLE, DefenseType.STANDARD
        )
    assert outcome.touchdown and game.state.game_over
    assert not game.can_attempt_conversion_after_touchdown()

    attempts = Mock(wraps=game.attempt_extra_point)
    game.attempt_extra_point = attempts
    score_before = (game.state.home_score, game.state.away_score)
    resume_patches(monkeypatch, game, away=True, home=False, pending="try")

    # A completed game returns before the loop's first status display.
    cli.resume_game("synthetic.json", compact=True)

    attempts.assert_not_called()
    assert (game.state.home_score, game.state.away_score) == score_before
    assert [play.play_type for play in game.state.scoring_plays] == ["TD"]


def test_resaved_pending_safety_keeps_its_free_kick(tmp_path):
    """Reload/reconcile/save must preserve the owed safety free kick."""
    game, outcome = scored_game(
        PlayResult(ResultType.SACK, yards=-8, raw_result="-8"), home=False
    )
    assert outcome.safety and game.pending_post_score_action() == "safety_free_kick"

    first = tmp_path / "safety-first.json"
    save_game(game, str(first), human_is_away=False, human_is_home=True)
    loaded, _, _, pending = load_game(str(first))
    assert pending == "safety_free_kick"

    second = tmp_path / "safety-second.json"
    save_game(loaded, str(second), human_is_away=False, human_is_home=True)
    reloaded, _, _, repending = load_game(str(second))
    assert repending == "safety_free_kick"
    assert reloaded.state.ball_position == 20
    assert reloaded.state.home_score + reloaded.state.away_score == 2
