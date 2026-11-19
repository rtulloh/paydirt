"""Extended statistics from synthetic engine outcomes."""

from unittest.mock import patch

import pytest

from paydirt.play_resolver import DefenseType, PlayResult, PlayType, ResultType
from tests.game_fixtures import make_sample_game


@pytest.fixture
def game():
    g = make_sample_game("Home", "Away")
    g.state.is_home_possession = True
    g.state.ball_position = 40
    g.state.down = 3
    g.state.yards_to_go = 5
    return g


def counters(g, home=True):
    value = getattr(
        g.state.home_stats if home else g.state.away_stats, "_extended_team_stats", None
    )
    assert isinstance(value, dict), "new engines must track authoritative extended counters"
    return value


def apply(g, result, play=PlayType.SHORT_PASS):
    return g._apply_play_result(
        play,
        DefenseType.STANDARD,
        result,
        g.state.field_position_str(),
        g.state.down,
        g.state.ball_position,
        g.state.yards_to_go,
        False,
        False,
    )


@pytest.mark.parametrize(
    "play,yards,category",
    [(PlayType.SHORT_PASS, 12, "passing"), (PlayType.LINE_PLUNGE, 7, "rushing")],
)
def test_retained_first_down_and_longest(game, play, yards, category):
    apply(game, PlayResult(ResultType.YARDS, yards, "synthetic"), play)
    c = counters(game)
    assert c["third_down_attempts"] == 1
    assert c["third_down_conversions"] == 1
    assert c["first_downs_" + category] == 1
    assert c["longest_pass" if category == "passing" else "longest_rush"] == yards


def test_incompletion_is_failed_third_down(game):
    apply(game, PlayResult(ResultType.INCOMPLETE, 0, "synthetic"))
    assert counters(game)["third_down_attempts"] == 1
    assert counters(game)["third_down_conversions"] == 0


def test_punt_faircatch_is_not_return_or_fourth_attempt(game):
    game.state.down = 4
    game.state.home_chart.special_teams.punt[35] = "45*"
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(35, "synthetic")):
        game._handle_punt()
    c = counters(game)
    r = counters(game, False)
    assert c["punts"] == 1 and c["punt_yards"] == 45 and c["longest_punt"] == 45
    assert c["punt_fair_catches"] == 1 and c["punts_inside_20"] == 1
    assert r["punt_return_fair_catches"] == 1 and r["punt_returns"] == 0
    assert c["fourth_down_attempts"] == 0


def test_extra_point_credits_original_team(game):
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(35, "synthetic")):
        made, _ = game.attempt_extra_point()
    assert counters(game)["extra_points_attempted"] == 1
    assert counters(game)["extra_points_made"] == int(made)
    assert counters(game, False)["extra_points_attempted"] == 0


@pytest.mark.parametrize(
    "kind,yards,qt,rush",
    [
        (ResultType.YARDS, 8, 0, False),
        (ResultType.QB_SCRAMBLE, 8, 25, True),
        (ResultType.SACK, -5, 0, None),
        (ResultType.FUMBLE, 8, 0, False),
    ],
)
def test_scrimmage_classification(game, kind, yards, qt, rush):
    result = PlayResult(kind, yards, "synthetic", qb_scramble_dice=qt)
    if kind == ResultType.FUMBLE:
        result.fumble_resolved = True
        result.fumble_recovered = False
        result.fumble_recovery_roll = 39
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "synthetic")):
        apply(game, result)
    c = counters(game)
    assert c["third_down_attempts"] == 1
    if rush is not None:
        assert c["longest_rush" if rush else "longest_reception"] == yards
    if kind == ResultType.FUMBLE:
        assert c["receiving_fumbles"] == 1 and c["receiving_fumbles_lost"] == 1


@pytest.mark.parametrize("cell,ball,expected", [("70", 40, 60), ("45", 20, 45)])
def test_punt_distance_capped_at_goal_line(game, cell, ball, expected):
    game.state.ball_position = ball
    game.state.home_chart.special_teams.punt[35] = cell
    game.state.away_chart.special_teams.punt_return[36] = "7"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(35, "P"), (36, "R")]):
        game._handle_punt()
    c = counters(game)
    r = counters(game, False)
    assert c["punt_yards"] == expected
    if ball + int(cell) >= 100:
        assert c["punt_touchbacks"] == 1 and r["punt_returns"] == 0
    else:
        assert (
            c["punts_returned"] == 1
            and c["punt_return_yards_allowed"] == 7
            and r["punt_return_yards"] == 7
        )


def test_kickoff_return_uses_actual_segment(game):
    game.state.home_chart.special_teams.kickoff[35] = "50"
    game.state.away_chart.special_teams.kickoff_return[36] = "12"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(35, "K"), (36, "R")]):
        game.kickoff(kicking_home=True)
    c = counters(game, False)
    assert (
        c["kickoff_returns"] == 1
        and c["kickoff_return_yards"] == 12
        and c["longest_kickoff_return"] == 12
    )


def test_long_field_goal_uses_statistical_distance(game):
    from tests.test_field_goal import create_fg_result

    game.state.ball_position = 70
    with patch(
        "paydirt.game_engine.resolve_field_goal_with_penalties",
        return_value=create_fg_result(35, "40", 40),
    ):
        game._handle_field_goal()
    assert counters(game)["longest_field_goal"] == 47


def test_legacy_extended_coverage_stays_unknown(game):
    game.state.home_stats._extended_team_stats = None
    apply(game, PlayResult(ResultType.YARDS, 12, "synthetic"))
    assert game.state.home_stats._extended_team_stats is None


@pytest.mark.parametrize("accept_play", [False, True])
@pytest.mark.parametrize("play", [PlayType.SHORT_PASS, PlayType.LINE_PLUNGE])
def test_pending_foul_commit_once_and_repeated_choice_is_inert(game, accept_play, play):
    from paydirt.play_resolver import PenaltyChoice, PenaltyOption

    choice = PenaltyChoice(
        PlayResult(ResultType.YARDS, 12, "synthetic"),
        [PenaltyOption("DEF", "DEF 5X", 5, "synthetic", auto_first_down=True)],
        offended_team="offense",
    )
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice):
        pending = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    assert not any(counters(game).values())
    # A pending presentation may already be retained in a caller's play log.
    game.play_log.append(pending)
    final = game.apply_penalty_decision(pending, accept_play=accept_play)
    c = counters(game).copy()
    if accept_play:
        assert c["third_down_attempts"] == 1 and c["third_down_conversions"] == 1
        assert (
            c["first_downs_passing" if play == PlayType.SHORT_PASS else "first_downs_rushing"] == 1
        )
    else:
        assert c["third_down_attempts"] == 0 and c["first_downs_penalty"] == 1
    game.apply_penalty_decision(final, accept_play=accept_play)
    assert counters(game) == c


@pytest.mark.parametrize("down,prefix", [(2, "third"), (3, "fourth")])
def test_automatic_spike_records_its_own_failed_down(game, down, prefix):
    from paydirt.play_resolver import PenaltyChoice

    game.state.down = down
    game.state.yards_to_go = 10
    game.state.quarter = 4
    game.state.time_remaining = 1
    game.state.two_minute_warning_called = True
    with (
        patch(
            "paydirt.game_engine.resolve_play_with_penalties",
            return_value=PenaltyChoice(PlayResult(ResultType.YARDS, 4, "synthetic")),
        ),
        patch("paydirt.game_engine.random.uniform", return_value=40),
    ):
        outcome = game.run_play_with_penalty_procedure(
            PlayType.SHORT_PASS, DefenseType.STANDARD, call_spike=True
        )
    assert outcome.spike_used
    assert counters(game)[prefix + "_down_attempts"] == 1
    assert counters(game)[prefix + "_down_conversions"] == 0


def test_return_chain_first_segment_does_not_credit_later_fumble_returns(game):
    from paydirt.game_engine import ReturnChain

    game._team_stats_context = {
        "home": True,
        "ball": 40,
        "down": 4,
        "first_downs": 0,
        "punt": {"home": True, "ball": 40, "distance": 40},
    }
    chain = ReturnChain(
        first_roll=35, first_cell="F 7", possession_home=True, spot=30, yards=7, fumbled=True
    )
    # Resolve actual core punt chain, including the final other-team recovery.
    with patch.object(game, "_apply_return_chain", return_value=False):
        outcome = game._finish_punt_return_chain(chain, "40", 35, 40, 40)
    from paydirt.team_stats import _commit

    _commit(game, game._team_stats_context, outcome)
    assert (
        counters(game, False)["punt_return_yards"] == 7
        and counters(game, False)["punt_return_touchdowns"] == 0
    )


def test_pending_capture_context_has_closed_semantic_schema():
    from paydirt.team_stats import validate_team_stats_context

    valid = {
        "home": True,
        "ball": 40,
        "down": 3,
        "first_downs": 0,
        "passing_yards": 0,
        "rushing_yards": 0,
        "pending": True,
    }
    assert validate_team_stats_context({}) == {}
    assert validate_team_stats_context(valid) == valid
    assert (
        validate_team_stats_context({**valid, "penalty_first_downs": 1})["penalty_first_downs"] == 1
    )
    for invalid in [
        [],
        {"home": True},
        {**valid, "ball": 101},
        {**valid, "unknown": 1},
        {
            **valid,
            "punt": {"home": True, "ball": 40, "blocked": False, "distance": 40, "foreign": True},
        },
    ]:
        with pytest.raises(ValueError):
            validate_team_stats_context(invalid)


def test_punt_inside_twenty_uses_return_end_before_later_enforcement(game):
    from paydirt.game_engine import PlayOutcome
    from paydirt.team_stats import _commit

    context = {
        "home": True,
        "ball": 40,
        "down": 4,
        "first_downs": 0,
        "punt": {"home": True, "ball": 40, "blocked": False, "distance": 45},
        "return": {"home": False, "yards": 7, "touchdown": False, "cancelled": False},
    }
    game.state.is_home_possession = False
    game.state.ball_position = 10  # later enforcement; initial return ended at22
    outcome = PlayOutcome(
        play_type=PlayType.PUNT,
        defense_type=DefenseType.STANDARD,
        result=PlayResult(ResultType.YARDS, 45, "synthetic"),
    )
    _commit(game, context, outcome)
    assert counters(game)["punts_inside_20"] == 0


@pytest.mark.parametrize("cell,punts,blocked", [("BK -8", 1, 1), ("F -5", 0, 0)])
def test_blocked_punt_is_team_attempt_but_no_punting_or_return_yards(game, cell, punts, blocked):
    game.state.home_chart.special_teams.punt[35] = cell
    game.state.home_chart.special_teams.fumble_recovery_range = (10, 18)
    game.state.away_chart.special_teams.interception_return[35] = "0"
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(35, "P")):
        game._handle_punt()
    c = counters(game)
    assert c["punts"] == punts and c["punts_blocked"] == blocked
    assert c["punt_yards"] == 0 and c["punt_return_yards_allowed"] == 0
    assert counters(game, False)["punt_returns"] == 0


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.SHORT_PASS])
def test_goal_line_caps_longest_play_and_records_only_rushing_touchdown(game, play):
    game.state.ball_position = 95
    apply(game, PlayResult(ResultType.YARDS, 12, "synthetic"), play)
    c = counters(game)
    assert c["longest_rush" if play == PlayType.LINE_PLUNGE else "longest_reception"] == 5
    assert c["rushing_touchdowns"] == int(play == PlayType.LINE_PLUNGE)


@pytest.mark.parametrize("kickoff", [False, True])
def test_first_return_touchdown_has_actual_goal_line_yards(game, kickoff):
    if kickoff:
        game.state.home_chart.special_teams.kickoff[35] = "50"
        game.state.away_chart.special_teams.kickoff_return[36] = "TD"
    else:
        game.state.home_chart.special_teams.punt[35] = "40"
        game.state.away_chart.special_teams.punt_return[36] = "TD"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(35, "K"), (36, "R")]):
        outcome = game.kickoff(kicking_home=True) if kickoff else game._handle_punt()
    assert outcome.touchdown
    c = counters(game, False)
    prefix = "kickoff" if kickoff else "punt"
    assert c[prefix + "_return_touchdowns"] == 1
    assert c[prefix + "_return_yards"] == (85 if kickoff else 80)
    assert c["longest_" + prefix + "_return"] == (85 if kickoff else 80)


def test_receiver_fumble_recovery_advance_first_down_is_rushing(game):
    game.state.home_chart.peripheral.fumble_recovered_range = (10, 32)
    game.state.home_chart.special_teams.interception_return[13] = "10"
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(19, "R"), (13, "A")]):
        outcome = apply(game, PlayResult(ResultType.FUMBLE, 3, "synthetic"))
    assert outcome.first_down and game.state.home_stats.first_downs == 1
    c = counters(game)
    assert c["first_downs_rushing"] == 1 and c["first_downs_passing"] == 0
    assert c["longest_reception"] == 3


def test_coffin_corner_cancels_chart_fair_catch_stat(game):
    game.state.home_chart.special_teams.punt[35] = "45*"
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(35, "P")):
        game._handle_punt(coffin_corner_yards=15)
    assert counters(game)["punts"] == 1
    assert counters(game)["punt_fair_catches"] == 0
    assert counters(game, False)["punt_return_fair_catches"] == 0


def test_unblocked_backward_punt_keeps_signed_distance(game):
    game.state.home_chart.special_teams.punt[35] = "-5*"
    with patch("paydirt.game_engine.roll_chart_dice", return_value=(35, "P")):
        game._handle_punt()
    assert counters(game)["punt_yards"] == -5
    assert counters(game)["longest_punt"] == 0


@pytest.mark.parametrize("accept", [False, True])
@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_pending_punt_foul_only_counts_retained_kick(game, accept, foul):
    game.state.home_chart.special_teams.punt = {10: foul, 11: "40*"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "F"), (11, "K")]):
        pending = game.run_play_with_penalty_procedure(PlayType.PUNT, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    assert counters(game)["punts"] == 0
    final = game.apply_punt_penalty_decision(pending, accept)
    assert counters(game)["punts"] == int(not accept)
    assert counters(game)["punt_yards"] == (0 if accept else 40)
    before = counters(game).copy()
    game.apply_punt_penalty_decision(final, accept)
    assert counters(game) == before


@pytest.mark.parametrize("accept_play", [False, True])
def test_pending_field_goal_records_longest_only_after_retained_choice(game, accept_play):
    game.state.ball_position = 70
    game.state.home_chart.special_teams.field_goal.update({22: "DEF 5", 21: "40"})
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(22, "F"), (21, "K")]):
        pending = game.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    assert counters(game)["longest_field_goal"] == 0
    final = game.apply_fg_penalty_decision(pending, accept_play=accept_play)
    assert counters(game)["longest_field_goal"] == (47 if accept_play else 0)
    before = counters(game).copy()
    game.apply_fg_penalty_decision(final, accept_play=accept_play)
    assert counters(game) == before


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {"punts": True},
        {"punts": -1},
        {"foreign": 1},
        {"punts": 1, "punts_blocked": 2},
        {"rushing_fumbles": 0, "rushing_fumbles_lost": 1},
        {"extra_points_attempted": 0, "extra_points_made": 1},
    ],
)
def test_extended_counter_schema_rejects_invalid_values(bad):
    from paydirt.team_stats import validate_extended_team_stats

    if bad is None:
        assert validate_extended_team_stats(bad) is None
    else:
        with pytest.raises(ValueError):
            validate_extended_team_stats(bad)


@pytest.mark.parametrize(
    "patch_value",
    [
        {"pending": 1},
        {"penalty_first_downs": 2},
        {"yards_to_go": 0},
        {"spikes": [{"home": True, "down": 5}]},
        {"return": {"home": True, "yards": 111, "touchdown": False, "cancelled": False}},
        {"punt": {"home": True, "ball": 101, "blocked": False, "distance": 40}},
    ],
)
def test_capture_context_rejects_malformed_optional_facts(patch_value):
    from paydirt.team_stats import validate_team_stats_context

    valid = {
        "home": True,
        "ball": 40,
        "down": 3,
        "first_downs": 0,
        "passing_yards": 0,
        "rushing_yards": 0,
    }
    with pytest.raises(ValueError):
        validate_team_stats_context({**valid, **patch_value})


@pytest.mark.parametrize("play", [PlayType.LINE_PLUNGE, PlayType.PUNT])
def test_own_recovery_short_of_sticks_automatic_foul_is_penalty_first_down(play):
    from tests.test_fumble_return_penalty_first_down import advance_game, run_advance

    game = advance_game(True, 2, {11: "DEF 5X", 12: "0"})
    outcome = run_advance(game, play, [17, 11, 12])
    assert outcome.first_down and game.state.home_stats.first_downs == 1
    assert counters(game)["first_downs_penalty"] == 1
    assert counters(game)["first_downs_rushing"] == 0


def test_accepted_field_goal_foul_first_down_is_penalty(game):
    game.state.ball_position = 60
    game.state.yards_to_go = 2
    game.state.down = 4
    game.state.home_chart.special_teams.field_goal.update({22: "DEF 5", 21: "30"})
    with patch("paydirt.play_resolver.roll_chart_dice", side_effect=[(22, "F"), (21, "K")]):
        pending = game.run_play_with_penalty_procedure(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    game.apply_fg_penalty_decision(pending, accept_play=False)
    assert game.state.home_stats.first_downs == 1
    assert counters(game)["first_downs_penalty"] == 1
