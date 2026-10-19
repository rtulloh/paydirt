"""Public-team regressions for player-facing announcements, status, and kneels."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from paydirt import interactive_game as cli
from paydirt.play_resolver import DefenseType, PenaltyChoice, PlayResult, PlayType, ResultType
from paydirt.result_formatter import ResultFormatter
from paydirt.utils import format_field_position_with_team
from tests.game_fixtures import make_sample_game


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("flow", ["direct", "procedure"])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
@pytest.mark.parametrize("play,result_type,raw", [
    (PlayType.SHORT_PASS, ResultType.YARDS, "15"),
    (PlayType.OFF_TACKLE, ResultType.YARDS, "15"),
    (PlayType.LONG_PASS, ResultType.TOUCHDOWN, "TD"),
    (PlayType.OFF_TACKLE, ResultType.BREAKAWAY, "B"),
])
def test_touchdown_announced_once_with_authoritative_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, flow: str, view: str, play: PlayType, result_type: ResultType, raw: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 94
    game.state.down, game.state.yards_to_go = 2, 6
    result = PlayResult(result_type, yards=15, raw_result=raw, dice_roll=26,
                        description="Add: 15 + 0 = 15 [Off: B2+W1+W5=26, Def: R1+G0=1]")
    choice = PenaltyChoice(result)
    with (patch("paydirt.game_engine.resolve_play", return_value=result),
          patch("paydirt.game_engine.resolve_play_with_penalties", return_value=choice)):
        run = game.run_play if flow == "direct" else game.run_play_with_penalty_procedure
        outcome = run(play, DefenseType.STANDARD)
    if view == "legacy-compact":
        outcome.transaction = None
    assert outcome.touchdown and not outcome.turnover
    assert outcome.yards_gained == 6
    assert (game.state.home_score, game.state.away_score) == ((6, 0) if home else (0, 6))
    canonical_detail = game.state.scoring_plays[-1].description.removesuffix(" TOUCHDOWN")
    before = deepcopy(game.state)
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    with patch("paydirt.commentary.Commentary.generate", return_value="WRONG PLAYER") as generate:
        cli.display_play_result(game, outcome, play, DefenseType.STANDARD,
                                game.state.home_chart, home)
    output = capsys.readouterr().out
    generate.assert_not_called()
    assert output.upper().count("TOUCHDOWN") == 1
    assert canonical_detail in output
    assert "WRONG PLAYER" not in output
    assert game.state == before
    assert raw in output  # Raw chart evidence remains available.


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
def test_first_down_has_one_announcement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool, view: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    result = PlayResult(ResultType.YARDS, yards=12, raw_result="12", description="Gain 12")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    if view == "legacy-compact":
        outcome.transaction = None
    assert outcome.first_down and not outcome.touchdown
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    with patch("paydirt.commentary.random.choice", side_effect=lambda options: options[0]):
        cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.STANDARD,
                                game.state.home_chart, home)
    output = capsys.readouterr().out
    assert output.upper().count("FIRST DOWN") == 1
    assert "12" in output


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("position,distance,expected", [(94, 6, "Goal"), (85, 15, "Goal"), (94, 2, "2"), (40, 10, "10")])
def test_status_has_one_engine_owned_location(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    home: bool, compact: bool, position: int, distance: int, expected: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = position
    game.state.yards_to_go = distance
    spot = format_field_position_with_team(position, game.state.possession_team.peripheral.short_name,
                                           game.state.defense_team.peripheral.short_name)
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_game_status(game, game.state.home_chart, home)
    output = capsys.readouterr().out
    assert output.count(spot) == 1
    assert game.get_status()["down_description"] == f"1st & {expected}"
    if compact:
        assert f"1st & {expected} @ {spot}" in output
        assert output.count(" @ ") == 1
    else:
        assert f"Down: 1st and {expected}" in output


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "full", "formatter"])
def test_kneel_uses_engine_intent_and_loss(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool, view: str,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 30
    game.state.quarter, game.state.time_remaining = 4, 1
    with patch("paydirt.game_engine.roll_chart_dice") as dice:
        outcome = game.run_play(PlayType.QB_KNEEL, DefenseType.STANDARD)
    dice.assert_not_called()
    assert outcome.yards_gained == -2 and not outcome.turnover and not outcome.safety
    assert game.state.ball_position == 28 and game.state.down == 2
    assert game.state.time_remaining == pytest.approx(1 / 3)
    before = deepcopy(game.state)
    with patch("paydirt.commentary.Commentary.generate", return_value="Defense blows this up!") as generate:
        if view == "formatter":
            output = ResultFormatter("OFF", "DEF").format(outcome).commentary
        else:
            monkeypatch.setattr(cli, "COMPACT_MODE", view == "compact")
            cli.display_play_result(game, outcome, PlayType.QB_KNEEL, DefenseType.STANDARD,
                                    game.state.home_chart, home)
            output = capsys.readouterr().out
    generate.assert_not_called()
    assert outcome.description in output
    assert "takes a knee" in output
    assert "2-yard loss" in outcome.description
    assert "blows" not in output
    assert game.state == before


@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full", "formatter"])
@pytest.mark.parametrize("result_type,yards", [(ResultType.YARDS, 12), (ResultType.YARDS, -2),
                                               (ResultType.YARDS, 0), (ResultType.INCOMPLETE, 0)])
def test_rendering_does_not_advance_gameplay_rng_or_mutate_outcome(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    view: str, result_type: ResultType, yards: int,
) -> None:
    import random

    game = make_sample_game()
    result = PlayResult(result_type, yards=yards, raw_result=str(yards), description="Synthetic play")
    with patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(result)):
        outcome = game.run_play_with_penalty_procedure(PlayType.SHORT_PASS, DefenseType.STANDARD)
    if view == "legacy-compact":
        outcome.transaction = None
    state_before, outcome_before = deepcopy(game.state), deepcopy(outcome)
    rng_before = random.getstate()
    try:
        if view == "formatter":
            ResultFormatter("OFF", "DEF").format(outcome)
        else:
            monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
            cli.display_play_result(game, outcome, PlayType.SHORT_PASS, DefenseType.STANDARD,
                                    game.state.home_chart, True)
        assert random.getstate() == rng_before
        assert game.state == state_before
        assert outcome == outcome_before
    finally:
        random.setstate(rng_before)
    capsys.readouterr()


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full"])
@pytest.mark.parametrize("kind", ["safety", "kneel-safety", "kneel-downs", "scramble-td", "interception-td", "penalty-first"])
def test_edge_announcements_use_one_player_facing_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool, view: str, kind: str,
) -> None:
    from paydirt.play_resolver import PenaltyOption

    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 2 if "safety" in kind else 94 if kind == "scramble-td" else 30
    play = PlayType.QB_KNEEL if kind.startswith("kneel") else PlayType.SHORT_PASS
    if kind == "kneel-downs":
        game.state.down = 4
    result_type = {"scramble-td": ResultType.QB_SCRAMBLE, "interception-td": ResultType.INTERCEPTION}.get(kind, ResultType.YARDS)
    result = PlayResult(result_type, yards=15 if kind == "scramble-td" else -3 if kind == "safety" else 0,
                        raw_result="QT" if kind == "scramble-td" else "INT 0" if kind == "interception-td" else "0",
                        description="Synthetic result", dice_roll=26)
    options = [PenaltyOption("DEF", "DEF 15", 15, "Defensive penalty, 15 yards", auto_first_down=True)] if kind == "penalty-first" else []
    game.state.defense_team.special_teams.interception_return[11] = "TD"
    with (patch("paydirt.game_engine.resolve_play_with_penalties", return_value=PenaltyChoice(
            result, penalty_options=options, offended_team="offense")),
          patch("paydirt.game_engine.roll_chart_dice", return_value=(11, "synthetic return"))):
        outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
        if kind == "penalty-first":
            outcome = game.apply_penalty_decision(outcome, accept_play=False, penalty_index=0)
    if view == "legacy-compact":
        outcome.transaction = None
    if kind == "interception-td":
        assert outcome.result.scoring_team == game.state.scoring_plays[-1].team
    before, result_before = deepcopy(game.state), deepcopy(outcome)
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    cli.display_play_result(game, outcome, play, DefenseType.STANDARD, game.state.home_chart, home)
    output = capsys.readouterr().out
    # Technical chart/priority evidence is not a second player-facing announcement.
    narrative = "\n".join(line for line in output.splitlines() if line.startswith(("►", "  >>", "  →", "  ***")))
    if "safety" in kind:
        assert outcome.safety and not outcome.touchdown
        assert (game.state.home_score, game.state.away_score) == ((0, 2) if home else (2, 0))
        assert narrative.upper().count("SAFETY") == 1
    elif kind.endswith("td"):
        assert outcome.touchdown and not outcome.safety
        if "TOUCHDOWN" in narrative.upper():
            assert narrative.upper().count("TOUCHDOWN") == 1
        else:
            assert narrative.upper().count("PICK SIX") == 1
    elif kind == "kneel-downs":
        assert outcome.turnover_on_downs and not outcome.touchdown and not outcome.safety
        assert narrative.upper().count("TURNOVER ON DOWNS") == 1
        assert "takes a knee" in output
    else:
        assert outcome.first_down and outcome.penalty_applied
        assert narrative.upper().count("FIRST DOWN") == 1
    assert game.state == before
    assert outcome == result_before


def test_core_roster_selection_preserves_seeded_engine_contract() -> None:
    """Isolating rendering must not change core scoring-name RNG consumption."""
    import random
    from paydirt.commentary import TeamRoster

    before = random.getstate()
    try:
        random.seed(8306)
        expected_rng = random.Random(8306)
        roster = TeamRoster(rb=["Runner A", "Runner B"], wr=["Receiver A", "Receiver B"])
        assert roster.random_rb() == expected_rng.choice(roster.rb)
        assert roster.random_wr() == expected_rng.choice(roster.wr)
        assert random.getstate() == expected_rng.getstate()
    finally:
        random.setstate(before)


@pytest.mark.parametrize("seed", [8306, 42])
@pytest.mark.parametrize("view", ["compact", "legacy-compact", "full", "formatter"])
@pytest.mark.parametrize("render_count", [1, 2])
def test_seeded_real_drive_is_independent_of_render_frequency(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    seed: int, view: str, render_count: int,
) -> None:
    import random

    def drive(render: bool) -> tuple[list, object]:
        random.seed(seed)
        game = make_sample_game()
        results = []
        for play in [PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS] * 4:
            home = game.state.is_home_possession
            outcome = game.run_play_with_penalty_procedure(play, DefenseType.STANDARD)
            if outcome.pending_penalty_decision:
                outcome = game.apply_penalty_decision(outcome, accept_play=True)
            if render:
                if view == "legacy-compact":
                    outcome.transaction = None
                for _ in range(render_count):
                    if view == "formatter":
                        ResultFormatter("OFF", "DEF").format(outcome)
                    else:
                        cli.display_play_result(game, outcome, play, DefenseType.STANDARD,
                                                game.state.home_chart, home)
            results.append((outcome.result.raw_result, outcome.result.dice_roll,
                            outcome.yards_gained, outcome.touchdown, outcome.turnover,
                            outcome.safety, outcome.first_down, deepcopy(game.get_status())))
            if outcome.touchdown or outcome.safety or game.state.game_over:
                break
        return results, random.getstate()

    before = random.getstate()
    monkeypatch.setattr(cli, "COMPACT_MODE", view != "full")
    try:
        assert drive(False) == drive(True)
    finally:
        random.setstate(before)
    capsys.readouterr()


@pytest.mark.parametrize("home", [False, True])
@pytest.mark.parametrize("compact", [False, True])
def test_made_field_goal_has_one_success_announcement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, home: bool, compact: bool,
) -> None:
    game = make_sample_game()
    game.state.is_home_possession = home
    game.state.ball_position = 70
    game.state.down = 4
    game.state.possession_team.special_teams.field_goal[20] = "60"
    with patch("paydirt.play_resolver.roll_chart_dice", return_value=(20, "synthetic kick")) as dice:
        outcome = game.run_play(PlayType.FIELD_GOAL, DefenseType.STANDARD)
    dice.assert_called_once()
    assert outcome.field_goal_made and not outcome.touchdown
    assert (game.state.home_score, game.state.away_score) == ((3, 0) if home else (0, 3))
    monkeypatch.setattr(cli, "COMPACT_MODE", compact)
    cli.display_play_result(game, outcome, PlayType.FIELD_GOAL, DefenseType.STANDARD,
                            game.state.home_chart, home)
    output = capsys.readouterr().out
    assert output.upper().count("GOOD") == 1
    assert "60" in output
