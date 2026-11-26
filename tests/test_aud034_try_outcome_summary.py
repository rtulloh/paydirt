"""AUD-034: the scoring summary must report the try, including a failure.

A missed extra point scores no points, so it correctly creates no scoring-log
entry. The summary still has to say the try failed, otherwise the touchdown row
reads like a point went missing. The same applies to a failed two-point try.

The summary is rendered by the core box-score display, which the CLI, the
auto-game runner and any API consumer share, so a fix here covers all of them.
"""

from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import (
    DefenseType,
    PenaltyChoice,
    PlayResult,
    PlayType,
    ResultType,
)
from paydirt.save_game import load_game, save_game
from tests.game_fixtures import make_sample_game


def score_touchdown(*, home: bool = True) -> PaydirtGameEngine:
    """Produce a real six-point touchdown with the public sample teams."""
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.quarter, game.state.time_remaining = 3, 5.0
    game.state.ball_position, game.state.down, game.state.yards_to_go = 94, 2, 6
    result = PlayResult(ResultType.YARDS, yards=6, description="Synthetic touchdown run")
    with (
        patch(
            "paydirt.game_engine.resolve_play_with_penalties",
            return_value=PenaltyChoice(result),
        ),
        patch("paydirt.game_engine.random.uniform", return_value=5),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.OFF_TACKLE, DefenseType.STANDARD
        )
    assert outcome.touchdown
    return game


def summary(game: PaydirtGameEngine, capsys) -> str:
    """Render the shared box score as one line of text.

    The renderer word-wraps descriptions to the table width, so join the lines
    before asserting on a sentence.
    """
    cli.display_box_score(game, "FINAL STATS")
    # Strip the table borders and indentation, then collapse the line breaks so
    # a wrapped sentence reads as one string.
    lines = [
        line.strip("| ").rstrip()
        for line in capsys.readouterr().out.splitlines()
    ]
    return " ".join(" ".join(lines).split())


def test_missed_extra_point_is_reported_in_the_summary(capsys) -> None:
    game = score_touchdown()
    game.state.possession_team.special_teams.extra_point_no_good = [26]
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "miss")):
        success, _description = game.attempt_extra_point()
    assert success is False

    text = summary(game, capsys)
    assert "Extra point is no good." in text
    # The drive still scored exactly six; the miss must not add points.
    assert game.state.home_score == 6
    assert "Extra point is good." not in text


def test_good_extra_point_still_reads_as_good(capsys) -> None:
    game = score_touchdown()
    game.state.possession_team.special_teams.extra_point_no_good = []
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "good")):
        success, _description = game.attempt_extra_point()
    assert success is True

    text = summary(game, capsys)
    assert "Extra point is good." in text
    assert "Extra point is no good." not in text
    assert game.state.home_score == 7


def test_missed_two_point_try_is_reported_in_the_summary(capsys) -> None:
    game = score_touchdown()
    result = PlayResult(ResultType.YARDS, yards=1, description="Synthetic one-yard run")
    with patch("paydirt.game_engine.resolve_play", return_value=result):
        success, defensive_points, _description = game.attempt_two_point(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD
        )
    assert success is False and defensive_points == 0

    text = summary(game, capsys)
    assert "Two-point conversion is no good." in text
    assert game.state.home_score == 6


def test_good_two_point_try_still_reads_as_good(capsys) -> None:
    game = score_touchdown()
    result = PlayResult(ResultType.YARDS, yards=3, description="Synthetic three-yard run")
    with patch("paydirt.game_engine.resolve_play", return_value=result):
        success, defensive_points, _description = game.attempt_two_point(
            PlayType.LINE_PLUNGE, DefenseType.STANDARD
        )
    assert success is True and defensive_points == 0

    text = summary(game, capsys)
    assert "Two-point conversion is good." in text
    assert game.state.home_score == 8


def test_summary_keeps_the_try_on_the_touchdown_row(capsys) -> None:
    """The miss belongs on the touchdown's row, not as a separate score."""
    game = score_touchdown()
    game.state.possession_team.special_teams.extra_point_no_good = [26]
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "miss")):
        game.attempt_extra_point()

    text = summary(game, capsys)
    assert text.count("Touchdown") == 1
    assert "Extra point is no good." in text
    # A failed try scores nothing, so the log stays a record of points; the
    # outcome rides on the touchdown for the summary.
    assert [(play.play_type, play.points) for play in game.state.scoring_plays] == [
        ("TD", 6)
    ]
    assert game.state.scoring_plays[0].try_result == "no good"


def test_missed_extra_point_survives_save_and_resume(tmp_path, capsys) -> None:
    """A resumed game must still explain the missing point."""
    import json

    game = score_touchdown()
    game.state.possession_team.special_teams.extra_point_no_good = [26]
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "miss")):
        game.attempt_extra_point()

    path = tmp_path / "aud034-missed-pat.json"
    save_game(game, str(path))
    saved = json.loads(path.read_text())
    assert saved["scoring_plays"][0]["try_result"] == "no good"
    assert saved["scoring_plays"][0]["try_kind"] == "PAT"

    resumed, *_ = load_game(str(path))
    text = summary(resumed, capsys)
    assert "Extra point is no good." in text
    assert resumed.state.home_score == 6


def test_legacy_save_without_try_fields_still_loads(tmp_path, capsys) -> None:
    """Version-1 saves written before AUD-034 carry no try fields."""
    import json

    game = score_touchdown()
    path = tmp_path / "aud034-legacy.json"
    save_game(game, str(path))
    data = json.loads(path.read_text())
    for play in data["scoring_plays"]:
        play.pop("try_result", None)
        play.pop("try_kind", None)
    path.write_text(json.dumps(data))

    resumed, *_ = load_game(str(path))
    assert resumed.state.scoring_plays[0].try_result == ""
    assert resumed.state.scoring_plays[0].try_kind == ""
    text = summary(resumed, capsys)
    assert "Touchdown" in text
    assert "no good" not in text
