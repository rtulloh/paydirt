"""RULE-034: a retained fumble's recovery is known before accept/penalty is offered.

A punt-chart foul forces a reroll. When that reroll is a snap fumble, the old
engine stored the raw cell and asked the offended team to choose while recovery
was still unresolved, so the choice was a gamble on a die the procedure already
requires. Scrimmage fumbles already resolve recovery first; this suite pins the
same contract for the punt snap-fumble and blocked-punt paths.

All cells are synthetic and the games use the public 2026 sample teams.
"""

from unittest.mock import patch

import pytest

from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType, ResultType
from tests.game_fixtures import make_sample_game

# THE-ATW 2026 sample-team abbreviations are display-only labels here.
RECOVERY_RANGE = (10, 31)


def pending_punt_foul(
    cell: str, *, foul: str = "OFF 5", down: int = 4, position: int = 22,
    distance: int = 4, rolls: list[int],
) -> tuple[PaydirtGameEngine, object]:
    """Punt-chart foul on the first roll, then ``cell`` on the offense reroll."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = position, down, distance
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: foul, 11: cell, 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    scripted = [(total, f"Roll {total}") for total in rolls]
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=scripted):
        return game, game.run_play(PlayType.PUNT, DefenseType.STANDARD)


@pytest.mark.parametrize("recovery", [20, 35])
def test_snap_fumble_recovery_is_resolved_before_the_choice(recovery: int) -> None:
    """The recovery roll is consumed and recorded while the choice is still pending."""
    _, pending = pending_punt_foul("F - 10", rolls=[10, 11, recovery])
    assert pending.pending_penalty_decision
    facts = pending.pending_fumble_facts
    assert facts is not None, "a pending snap fumble must carry resolved recovery facts"
    assert facts.recovery_roll == recovery
    assert facts.offense_recovers is (recovery == 20)
    assert pending.result.fumble_resolved
    assert pending.result.fumble_recovery_roll == recovery


@pytest.mark.parametrize(
    ("recovery", "down", "expected_possession_home", "expected_spot", "expected_down"),
    [
        # Offense recovers at its own 22-10=12: 2nd & 4 stays live, 4th down loses.
        (20, 2, True, 12, 3),
        (20, 4, False, 88, 1),
        # Defense recovers the ball spotted on HOME's 12, which is 88 yards
        # from the new possessor's own goal.
        (35, 2, False, 88, 1),
        (35, 4, False, 88, 1),
    ],
)
def test_decline_preview_matches_the_applied_result(
    recovery: int, down: int, expected_possession_home: bool, expected_spot: int,
    expected_down: int,
) -> None:
    """The displayed keep-the-play outcome equals what declining actually does."""
    game, pending = pending_punt_foul("F - 10", down=down, rolls=[10, 11, recovery])
    preview = pending.penalty_choice.play_result_preview
    assert "recovery pending" not in preview.lower(), preview
    assert "HOME" in preview, preview
    with patch("paydirt.game_engine.roll_chart_dice") as rerolled, \
         patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=False)
    rerolled.assert_not_called()
    assert game.state.is_home_possession is expected_possession_home
    assert game.state.ball_position == expected_spot
    assert game.state.down == expected_down
    assert outcome.result.punt_snap_fumble


def test_recovery_roll_is_consumed_once_across_choice_and_decline() -> None:
    """Pending resolution and decline share one roll; nothing is re-rolled."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 22, 2, 4
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    with patch(
        "paydirt.game_engine.roll_chart_dice",
        side_effect=[(10, "Foul"), (11, "Snap"), (20, "Recovery")],
    ) as rolls:
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert rolls.call_count == 3, "foul, reroll, and recovery are all required before the choice"
    with patch("paydirt.game_engine.roll_chart_dice") as after:
        game.apply_punt_penalty_decision(pending, accept_penalty=False)
    after.assert_not_called()


@pytest.mark.parametrize("foul", ["OFF 5", "DEF 5"])
def test_accepting_the_foul_discards_the_resolved_fumble(foul: str) -> None:
    """Enforcement is unchanged: no recovery statistics and no awarded points."""
    game, pending = pending_punt_foul("F - 10", foul=foul, rolls=[10, 11, 20])
    assert pending.pending_fumble_facts is not None
    before = (game.state.home_score, game.state.away_score)
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=True)
    assert (game.state.home_score, game.state.away_score) == before
    assert outcome.penalty_applied
    assert not outcome.result.punt_snap_fumble
    assert not outcome.turnover
    assert game.state.home_stats.fumbles_lost == game.state.away_stats.fumbles_lost == 0
    assert game.state.home_stats.penalties + game.state.away_stats.penalties == 1


def test_deep_snap_fumble_previews_the_safety() -> None:
    """A snap fumble behind the own goal line displays a safety, not a guess."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 5, 4, 2
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (20, "Recovery"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    preview = pending.penalty_choice.play_result_preview
    assert "safety" in preview.lower(), preview
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        game.apply_punt_penalty_decision(pending, accept_penalty=False)
    assert game.state.away_score == 2


def test_choice_does_not_change_live_state_or_commit_statistics() -> None:
    """Resolving the recovery early must not apply the play before the choice."""
    game, pending = pending_punt_foul("F - 10", rolls=[10, 11, 20])
    assert (game.state.ball_position, game.state.down, game.state.yards_to_go) == (22, 4, 4)
    assert game.state.is_home_possession
    assert game.state.home_stats.turnovers == 0
    assert game.state.home_stats.fumbles_lost == 0
    assert not game.play_log
    assert game.state.time_remaining == 10
    assert pending.pending_fumble_facts is not None


def test_pending_resolution_leaves_the_dice_stream_and_ledger_untouched() -> None:
    """Resolving recovery early must not consume or disturb anything live."""
    import random

    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 22, 2, 4
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    random.seed(8306)
    before_stats = (game.state.home_stats, game.state.away_stats)
    before_scoring = list(game.state.scoring_plays)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (20, "Recovery"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    # The projection ran on a copy: the live ledger is untouched.
    assert list(game.state.scoring_plays) == before_scoring
    assert (game.state.home_stats, game.state.away_stats) == before_stats
    assert game.state.untimed_down_pending is False
    # The stream continues from just after the recovery roll.
    first_draw = random.random()
    random.seed(8306)
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (20, "Recovery"),
    ]):
        game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert random.random() == first_draw
    assert pending.pending_fumble_facts is not None


def test_blocked_punt_preview_does_not_claim_a_pending_fumble() -> None:
    """A blocked kick has a kick-recovery roll, not a fumble recovery."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 4, 8
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "BK - 8", 12: "40"}
    game.state.home_chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[(10, "Foul"), (11, "Block")]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    assert pending.pending_penalty_decision
    assert pending.pending_fumble_facts is None
    preview = pending.penalty_choice.play_result_preview
    assert "blocked punt" in preview.lower()
    assert "recovery is rolled when the play is kept" in preview.lower()


def test_choice_preview_helper_does_not_disturb_the_pending_recovery() -> None:
    """The display-only preview path must not resolve or apply the fumble."""
    game, pending = pending_punt_foul("F - 10", rolls=[10, 11, 20])
    facts = pending.pending_fumble_facts
    preview = game.get_penalty_choice_preview(pending)
    assert preview is not None
    assert preview.play_result_preview == pending.penalty_choice.play_result_preview
    assert pending.pending_fumble_facts is facts
    assert (game.state.ball_position, game.state.down) == (22, 4)
    assert game.state.is_home_possession


def test_touchdown_preview_names_the_recovering_team() -> None:
    """A recovery in the opponent's end zone previews a touchdown, not a spot."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 96, 2, 2
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F + 5", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (20, "Recovery"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    facts = pending.pending_fumble_facts
    assert facts is not None
    assert facts.touchdown
    assert facts.home_score == 6
    assert "TOUCHDOWN" in pending.penalty_choice.play_result_preview
    # Nothing is awarded while the choice is pending.
    assert game.state.home_score == game.state.away_score == 0
    assert not game.state.scoring_plays
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        game.apply_punt_penalty_decision(pending, accept_penalty=False)
    assert game.state.home_score == 6


def test_offsetting_return_fouls_replay_the_down_on_decline() -> None:
    """A chained offsetting foul nullifies the play, exactly as before the change."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 40, 2, 5
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
        chart.special_teams.interception_return = {14: "DEF 15", 15: "OFF 15"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (17, "Recovery"), (14, "P14"), (15, "P15"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    before = (game.state.home_stats, game.state.away_stats)
    with patch("paydirt.game_engine.roll_chart_dice") as rolls:
        outcome = game.apply_punt_penalty_decision(pending, accept_penalty=False)
    rolls.assert_not_called()
    assert outcome.result.replay_down
    assert game.state.is_home_possession
    assert (game.state.ball_position, game.state.down) == (40, 2)
    assert (game.state.home_stats, game.state.away_stats) == before
    assert not outcome.touchdown and not outcome.turnover and not outcome.safety


def test_own_end_zone_recovery_previews_the_safety() -> None:
    """An own-end-zone recovery is a safety; the offer must say so."""
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 3, 2, 2
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=[
        (10, "Foul"), (11, "Snap"), (20, "Recovery"),
    ]):
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
    facts = pending.pending_fumble_facts
    assert facts is not None and facts.safety
    assert facts.away_score == 2
    preview = pending.penalty_choice.play_result_preview
    assert "SAFETY" in preview
    with patch("paydirt.game_engine.random.uniform", return_value=8):
        game.apply_punt_penalty_decision(pending, accept_penalty=False)
    assert game.state.away_score == 2


def test_fourth_down_own_recovery_previews_the_turnover() -> None:
    """A 4th-down own recovery short of the marker previews turnover on downs."""
    _, pending = pending_punt_foul("F - 10", down=4, rolls=[10, 11, 20])
    facts = pending.pending_fumble_facts
    assert facts is not None
    assert facts.turnover_on_downs
    assert "on downs" in pending.penalty_choice.play_result_preview


@pytest.mark.parametrize("recovery", [17, 18, 19, 37, 38, 39])
def test_chained_return_decline_matches_the_preview(recovery: int) -> None:
    """A recovery that triggers a chained return must not re-roll on decline.

    Recovery rolls 17-19 give the offense an interception-chart advance and
    37-39 give the defense one. The preview already consumed that return, so
    declining has to apply the same return rather than roll a new one.
    """
    game = make_sample_game()
    game.state.is_home_possession = True
    game.state.ball_position, game.state.down, game.state.yards_to_go = 22, 4, 4
    game.state.quarter, game.state.time_remaining = 2, 10
    game.state.home_chart.special_teams.punt = {10: "OFF 5", 11: "F - 10", 12: "40"}
    for chart in (game.state.home_chart, game.state.away_chart):
        chart.peripheral.fumble_recovered_range = RECOVERY_RANGE
        chart.special_teams.punt_return = {20: "0"}
        # Distinct cells so a shifted stream shows up as a different spot.
        chart.special_teams.interception_return = {17: "12", 25: "0"}

    rolls = [(10, "Foul"), (11, "Snap"), (recovery, "Recovery"), (17, "Return")]
    with patch("paydirt.game_engine.roll_chart_dice", side_effect=rolls) as scripted:
        pending = game.run_play(PlayType.PUNT, DefenseType.STANDARD)
        preview = pending.pending_fumble_facts.preview
        applied = game.apply_punt_penalty_decision(pending, accept_penalty=False)

    assert scripted.call_count == len(rolls), "the preview's return roll must be reused"
    # The preview and the applied play are worded from different viewpoints, so
    # compare the outcome they describe rather than the prose.
    assert "recovery pending" not in preview.lower(), preview
    facts = pending.pending_fumble_facts
    assert game.state.is_home_possession is facts.possession_home
    assert game.state.ball_position == facts.ball_position
    assert game.state.down == facts.down
    assert game.state.home_score == facts.home_score
    assert game.state.away_score == facts.away_score
    assert applied.touchdown is facts.touchdown
    assert applied.safety is facts.safety
