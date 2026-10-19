"""Semantic audit regressions: expected decisions and actions, not just totals."""

from copy import deepcopy
import random
from unittest.mock import patch

import pytest

from paydirt.computer_ai import ComputerAI
from paydirt.game_state import PlayOutcome
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)
from paydirt import interactive_game as cli
from paydirt.result_formatter import ResultFormatter
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("offended_offense", [False, True])
@pytest.mark.parametrize("defensive_score", [False, True])
@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("play", [PlayType.SHORT_PASS, PlayType.PUNT, PlayType.KICKOFF, PlayType.FIELD_GOAL])
def test_cpu_keeps_only_its_own_touchdown(
    offended_offense: bool, defensive_score: bool, home: bool, play: PlayType,
) -> None:
    option = PenaltyOption("DEF" if offended_offense else "OFF",
                           "DEF 5" if offended_offense else "OFF 10",
                           5 if offended_offense else 10, "Eligible penalty")
    result = PlayResult(ResultType.INTERCEPTION if defensive_score else ResultType.TOUCHDOWN,
                        touchdown=True, turnover=defensive_score)
    pending = PlayOutcome(play_type=play, defense_type=DefenseType.STANDARD,
                          result=result, touchdown=True, turnover=defensive_score,
                          pending_penalty_decision=True, penalty_choice=PenaltyChoice(
                              result, penalty_options=[option],
                              offended_team="offense" if offended_offense else "defense"))
    before = deepcopy(pending)
    accept, index = ComputerAI().should_accept_penalty(pending, not offended_offense, home)
    assert accept is (offended_offense != defensive_score)
    assert index == 0
    assert pending == before


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("result_type", [ResultType.TOUCHDOWN, ResultType.YARDS, ResultType.QB_SCRAMBLE])
@pytest.mark.parametrize("cpu_offense", [False, True])
def test_cpu_scoring_choice_has_real_engine_consequences(
    home: bool, result_type: ResultType, cpu_offense: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 94
    game.state.down, game.state.yards_to_go = 2, 6
    result = PlayResult(result_type, yards=9, raw_result="TD" if result_type == ResultType.TOUCHDOWN else "9",
                        touchdown=result_type == ResultType.TOUCHDOWN, description="Synthetic result")
    option = PenaltyOption("DEF" if cpu_offense else "OFF",
                           "DEF 5" if cpu_offense else "OFF 10",
                           5 if cpu_offense else 10, "Eligible penalty")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
            result, penalty_options=[option], offended_team="offense" if cpu_offense else "defense")) as resolve:
        pending = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    assert game.state.home_score == game.state.away_score == 0
    assert not game.state.scoring_plays
    assert pending.touchdown is False  # No score recorded while the choice is pending.
    assert pending.projected_touchdown  # Includes a non-TD chart gain crossing the goal line.
    decision, index = ComputerAI().should_accept_penalty(pending, not cpu_offense, home)
    assert decision is cpu_offense
    with patch("paydirt.game_engine.resolve_play_with_penalties") as reroll:
        outcome = game.apply_penalty_decision(pending, decision, index)
    resolve.assert_called_once()
    reroll.assert_not_called()
    assert game.state.is_home_possession is home
    if cpu_offense:
        assert outcome.touchdown and not outcome.penalty_applied
        assert game.state.offense_stats.penalties == game.state.defense_stats.penalties == 0
        assert (game.state.home_score, game.state.away_score) == ((6, 0) if home else (0, 6))
        assert len(game.state.scoring_plays) == 1
    else:
        assert not outcome.touchdown and outcome.penalty_applied
        assert game.state.home_score == game.state.away_score == 0
        assert not game.state.scoring_plays
        assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (84, 2, 16)
        assert (game.state.offense_stats.penalties, game.state.offense_stats.penalty_yards) == (1, 10)
        assert game.state.offense_stats.total_yards == 0


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
@pytest.mark.parametrize("cross_boundary", [False, True])
@pytest.mark.parametrize("good", [False, True])
def test_try_points_stay_with_touchdown_period(
    home: bool, quarter: int, cross_boundary: bool, good: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 94
    game.state.quarter = quarter
    game.state.time_remaining = 24 / 60 if cross_boundary else 2
    result = PlayResult(ResultType.YARDS, yards=9, raw_result="9", description="Synthetic score")
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
          patch("paydirt.game_engine.random.uniform", return_value=35)):
        outcome = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    assert outcome.touchdown
    live = (game.state.quarter, game.state.time_remaining, game.state.is_home_possession)
    game.state.possession_team.special_teams.extra_point_no_good = [] if good else [26]
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Synthetic try")):
        success, _ = game.attempt_extra_point()
    assert success is good
    assert (game.state.quarter, game.state.time_remaining, game.state.is_home_possession) == live
    assert all(score.quarter == quarter for score in game.state.scoring_plays)
    periods = game.get_period_scores()
    assert periods[quarter - 1]["home" if home else "away"] == 6 + int(good)
    assert sum(p["home"] + p["away"] for p in periods) == 6 + int(good)
    assert len(game.state.scoring_plays) == 1 + int(good)


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure", "declined-penalty"])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full", "formatter"])
def test_qb_time_touchdown_is_rushing_in_every_narrative(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, flow: str, view: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 82
    result = PlayResult(ResultType.QB_SCRAMBLE, yards=18, raw_result="QT",
                        description="QB scrambled for 18 yards", qb_scramble_dice=26, qb_scramble_yards=18)
    options = [PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty")] if flow == "declined-penalty" else []
    with (patch("paydirt.game_engine.resolve_play", return_value=result),
          patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result, penalty_options=options))):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(PlayType.TE_SHORT_LONG, DefenseType.STANDARD)
        if options:
            outcome = game.apply_penalty_decision(outcome, accept_play=True)
    assert outcome.touchdown and outcome.yards_gained == 18
    assert game.state.offense_stats.rushing_yards == 18
    assert game.state.offense_stats.passing_yards == 0
    assert "scrambl" in game.state.scoring_plays[-1].description.lower()
    assert "pass complete" not in outcome.description.lower()
    if view == "legacy-compact":
        outcome.transaction = None
    before, rng = deepcopy(game.state), random.getstate()
    if view == "formatter":
        text = ResultFormatter("OFF", "DEF").format(outcome).commentary
    else:
        monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
        cli.display_play_result(game, outcome, PlayType.TE_SHORT_LONG, DefenseType.STANDARD, game.state.home_chart, home)
        text = capsys.readouterr().out
    assert "scrambl" in text.lower() and "18" in text
    assert "pass complete" not in text.lower()
    assert game.state == before and random.getstate() == rng


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
def test_pending_conversion_survives_save_resume(tmp_path, home: bool, quarter: int) -> None:
    from paydirt.save_game import load_game, save_game

    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position, game.state.quarter, game.state.time_remaining = 94, quarter, 0.4
    result = PlayResult(ResultType.YARDS, yards=9)
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)),
          patch("paydirt.game_engine.random.uniform", return_value=35)):
        game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    path = str(tmp_path / "pending.json")
    save_game(game, filepath=path, human_is_away=not home, human_is_home=home)
    loaded, _, _, pending = load_game(path)
    assert pending == "touchdown"
    live = loaded.state.quarter, loaded.state.time_remaining
    loaded.state.possession_team.special_teams.extra_point_no_good = []
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
        assert loaded.attempt_extra_point()[0]
    assert (loaded.state.quarter, loaded.state.time_remaining) == live
    assert [score.quarter for score in loaded.state.scoring_plays] == [quarter, quarter]
    assert loaded.state.home_score + loaded.state.away_score == 7
    # The CLI completes the scoring sequence before allowing another save.
    loaded.setup_for_kickoff()
    save_game(loaded, filepath=path, human_is_away=not home, human_is_home=home)
    reloaded, _, _, pending = load_game(path)
    assert pending is None
    assert reloaded.state.home_score + reloaded.state.away_score == 7
    assert [score.quarter for score in reloaded.state.scoring_plays] == [quarter, quarter]


@pytest.mark.parametrize("play", [PlayType.SHORT_PASS, PlayType.TE_SHORT_LONG, PlayType.SCREEN])
def test_scramble_description_preserves_core_receiver_selection_rng(play: PlayType) -> None:
    game = make_sample_game()
    initial = random.getstate()
    try:
        game._generate_td_description(game.state.home_chart, play, 18)
        expected = random.getstate()
        random.setstate(initial)
        game._score_touchdown(play, 18, qb_scramble=True)
        assert random.getstate() == expected
        assert "scrambled" in game.state.scoring_plays[-1].description
    finally:
        random.setstate(initial)


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, 5])
def test_untimed_touchdown_try_uses_its_scoring_period(quarter: int) -> None:
    game = make_sample_game()
    game.state.quarter, game.state.time_remaining = quarter, 0
    game.state.untimed_down_pending = True
    game.state.is_overtime = quarter == 5
    game.state.ot_period = int(quarter == 5)
    game.state.ball_position = 94
    result = PlayResult(ResultType.YARDS, yards=9)
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)):
        assert game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD).touchdown
    live = game.state.quarter, game.state.time_remaining
    if game.can_attempt_conversion_after_touchdown():
        game.state.possession_team.special_teams.extra_point_no_good = []
        with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Try")):
            game.attempt_extra_point()
        assert [score.quarter for score in game.state.scoring_plays] == [quarter, quarter]
    else:
        assert quarter == 5  # Sudden-death TD ends OT without a try.
        assert [score.quarter for score in game.state.scoring_plays] == [quarter]
    assert (game.state.quarter, game.state.time_remaining) == live
    assert game.can_kickoff_after_play(quarter) is (quarter in (1, 3))


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("defensive", [False, True])
def test_two_point_period_attribution_without_reinterpreting_conversion_mechanics(quarter: int, defensive: bool) -> None:
    game = make_sample_game()
    game.season_rules.two_point_conversion = True
    game.state.is_home_possession = True
    game.state.quarter = quarter
    game._score_touchdown(PlayType.OFF_TACKLE, 9)
    game.state.quarter = quarter + 1
    live = game.state.quarter, game.state.time_remaining
    result = PlayResult(ResultType.INTERCEPTION if defensive else ResultType.YARDS, yards=2)
    resolved = PlayOutcome(play_type=PlayType.SHORT_PASS, defense_type=DefenseType.STANDARD,
                           result=result, yards_gained=2, turnover=defensive, touchdown=defensive)
    # This tests try logging, not the independent full-play conversion resolver.
    with patch.object(game, "run_play", return_value=resolved):
        success, defense_points, _ = game.attempt_two_point(PlayType.SHORT_PASS)
    assert success is not defensive
    assert defense_points == (2 if defensive else 0)
    assert [score.quarter for score in game.state.scoring_plays] == [quarter, quarter]
    assert game.state.scoring_plays[-1].is_home_team is not defensive
    assert (game.state.quarter, game.state.time_remaining) == live


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("cell", ["TD", "9", "B", "QT"])
def test_pending_penalty_outcome_projects_but_does_not_record_a_touchdown(home: bool, cell: str) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 94
    offense = game.state.possession_team.offense
    offense.off_tackle.update({26: "OFF 10", 27: cell})
    offense.breakaway[26] = "40"
    offense.qb_time[26] = "15"
    game.state.defense_team.defense.modifiers = {}
    rolls = [(26, "foul"), (27, "reroll"), (26, "secondary")]
    with (patch("paydirt.play_resolver.roll_chart_dice", side_effect=rolls),
          patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls)):
        pending = game.run_play_with_penalty_procedure(PlayType.OFF_TACKLE, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    assert pending.touchdown is False  # Nothing has been recorded yet.
    assert pending.projected_touchdown is True
    assert game.state.ball_position == 94 and not game.state.scoring_plays
    accept, index = ComputerAI().should_accept_penalty(pending, is_human_offense=True, human_is_home=home)
    assert (accept, index) == (False, 0)  # Defense erases the provisional score.
