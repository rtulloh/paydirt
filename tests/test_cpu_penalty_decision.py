"""Regression tests for CPU penalty eligibility and original option indices."""

from unittest.mock import patch

import pytest

from paydirt.chart_loader import (
    DefenseChart, OffenseChart, PeripheralData, SpecialTeamsChart, TeamChart,
)
from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine, PlayOutcome
from paydirt.interactive_game import handle_penalty_decision
from paydirt.play_resolver import (
    DefenseType, PenaltyChoice, PenaltyOption, PlayResult, PlayType, ResultType,
)


PLAY_TYPES = [
    PlayType.LINE_PLUNGE, PlayType.FIELD_GOAL, PlayType.PUNT, PlayType.KICKOFF,
]
APPLY_METHODS = {
    PlayType.LINE_PLUNGE: "apply_penalty_decision",
    PlayType.FIELD_GOAL: "apply_fg_penalty_decision",
    PlayType.PUNT: "apply_punt_penalty_decision",
    PlayType.KICKOFF: "apply_kickoff_penalty_decision",
}


@pytest.fixture
def game() -> PaydirtGameEngine:
    """Create a real engine without depending on installed team charts."""
    charts = [
        TeamChart(
            peripheral=PeripheralData(
                year=1983, team_name=name, team_nickname=name,
                power_rating=50, short_name=name,
            ),
            offense=OffenseChart(),
            defense=DefenseChart(),
            special_teams=SpecialTeamsChart(interception_return={10: "0"}),
            team_dir="",
        )
        for name in ("HOME", "AWAY")
    ]
    engine = PaydirtGameEngine(*charts)
    engine.state.is_home_possession = True
    engine.state.ball_position = 50
    return engine


@pytest.fixture(params=["empty_offense", "wrong_offense", "empty_defense", "wrong_defense"])
def no_eligible_outcome(request: pytest.FixtureRequest) -> PlayOutcome:
    """Exercise both empty options and options against the offended team."""
    offended_team = request.param.split("_")[1]
    offense_offended = offended_team == "offense"
    result = PlayResult(
        result_type=ResultType.INTERCEPTION if offense_offended else ResultType.YARDS,
        yards=0 if offense_offended else 10,
        turnover=offense_offended,
        description="Interception" if offense_offended else "Gain of 10",
    )
    options = []
    if request.param.startswith("wrong"):
        penalty_type = "OFF" if offense_offended else "DEF"
        options.append(PenaltyOption(penalty_type, f"{penalty_type} 10", 10, "Wrong-side penalty"))
    return PlayOutcome(
        play_type=PlayType.LINE_PLUNGE,
        defense_type=DefenseType.STANDARD,
        result=result,
        penalty_choice=PenaltyChoice(
            play_result=result, penalty_options=options, offended_team=offended_team,
        ),
        pending_penalty_decision=True,
        down_before=1,
    )


class TestCPUPenaltyDecision:
    """Test shared AI decisions and CLI dispatch, not copied decision logic."""

    @pytest.mark.parametrize("play_type", PLAY_TYPES)
    def test_ai_accepts_play_without_eligible_penalty(
        self, no_eligible_outcome: PlayOutcome, play_type: PlayType,
    ) -> None:
        no_eligible_outcome.play_type = play_type
        is_human_offense = no_eligible_outcome.penalty_choice.offended_team == "defense"

        decision = ComputerAI().should_accept_penalty(
            no_eligible_outcome, is_human_offense, human_is_home=True,
        )

        assert decision == (True, None)

    @pytest.mark.parametrize("play_type", PLAY_TYPES)
    def test_cli_dispatches_play_without_eligible_penalty(
        self, game: PaydirtGameEngine, no_eligible_outcome: PlayOutcome,
        play_type: PlayType, capsys: pytest.CaptureFixture[str],
    ) -> None:
        no_eligible_outcome.play_type = play_type
        is_human_offense = no_eligible_outcome.penalty_choice.offended_team == "defense"
        kwargs = (
            {"accept_penalty": False}
            if play_type in (PlayType.PUNT, PlayType.KICKOFF)
            else {"accept_play": True}
        )

        with patch.object(game, APPLY_METHODS[play_type], return_value=no_eligible_outcome) as apply:
            final = handle_penalty_decision(
                game, no_eligible_outcome, is_human_offense, human_is_home=True,
            )

        apply.assert_called_once_with(no_eligible_outcome, **kwargs)
        assert final is no_eligible_outcome
        assert "accepts play result" in capsys.readouterr().out

    def test_no_eligible_penalty_applies_real_play_result(
        self, game: PaydirtGameEngine, no_eligible_outcome: PlayOutcome,
    ) -> None:
        offense_offended = no_eligible_outcome.penalty_choice.offended_team == "offense"
        with patch("paydirt.game_engine.roll_chart_dice", return_value=(10, "Return roll")):
            final = handle_penalty_decision(
                game, no_eligible_outcome, not offense_offended, human_is_home=True,
            )

        assert not final.pending_penalty_decision
        assert not final.penalty_applied
        assert final.turnover is offense_offended
        assert game.state.is_home_possession is not offense_offended
        assert game.state.ball_position == (50 if offense_offended else 60)
        assert game.state.home_stats.penalties == 0
        assert game.state.away_stats.penalties == 0

    @pytest.mark.parametrize("play_type", PLAY_TYPES)
    def test_ai_and_cli_use_original_penalty_index(
        self, game: PaydirtGameEngine, play_type: PlayType,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        options = [
            PenaltyOption("OFF", "OFF 10", 10, "Ineligible offensive penalty"),
            PenaltyOption("DEF", "DEF 5", 5, "Defensive penalty"),
            PenaltyOption("PI", "PI 10", 10, "Pass interference", auto_first_down=True),
        ]
        result = PlayResult(ResultType.YARDS, yards=0)
        outcome = PlayOutcome(
            play_type=play_type, defense_type=DefenseType.STANDARD, result=result,
            penalty_choice=PenaltyChoice(
                play_result=result, penalty_options=options, offended_team="offense",
            ),
            pending_penalty_decision=True,
        )
        # Scrimmage AI prefers automatic first down; special teams pick the first eligible option.
        expected_index = 2 if play_type == PlayType.LINE_PLUNGE else 1
        assert ComputerAI().should_accept_penalty(outcome, False, True) == (False, expected_index)

        kwargs = {"accept_play": False, "penalty_index": expected_index}
        if play_type == PlayType.PUNT:
            kwargs = {"accept_penalty": True, "penalty_index": expected_index}
        elif play_type == PlayType.KICKOFF:
            kwargs = {"accept_penalty": True}
        with patch.object(game, APPLY_METHODS[play_type], return_value=outcome) as apply:
            final = handle_penalty_decision(game, outcome, False, human_is_home=True)

        apply.assert_called_once_with(outcome, **kwargs)
        assert final is outcome
        assert f"accepts penalty: {options[expected_index].description}" in capsys.readouterr().out

    @pytest.mark.parametrize("offended_team", ["offense", "defense"])
    def test_turnover_and_defensive_decisions_use_original_index(
        self, offended_team: str,
    ) -> None:
        offense_offended = offended_team == "offense"
        eligible_type = "DEF" if offense_offended else "OFF"
        ineligible_type = "OFF" if offense_offended else "DEF"
        options = [
            PenaltyOption(ineligible_type, f"{ineligible_type} 5", 5, "Ineligible penalty"),
            PenaltyOption(eligible_type, f"{eligible_type} 10", 10, "Eligible penalty"),
        ]
        result = PlayResult(
            ResultType.INTERCEPTION if offense_offended else ResultType.YARDS,
            yards=10, turnover=offense_offended,
        )
        outcome = PlayOutcome(
            play_type=PlayType.LINE_PLUNGE, defense_type=DefenseType.STANDARD,
            result=result, penalty_choice=PenaltyChoice(
                play_result=result, penalty_options=options, offended_team=offended_team,
            ),
        )

        assert ComputerAI().should_accept_penalty(
            outcome, not offense_offended, human_is_home=True,
        ) == (False, 1)
