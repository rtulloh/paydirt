"""
Game engine that uses actual Paydirt team charts.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Optional

from .chart_loader import TeamChart, load_team_chart
from .commentary import get_roster
from .game_state import GameState, PlayOutcome, ScoringPlay, TeamStats
from .overtime_rules import OvertimeFormat, OvertimeRules
from .packaging import get_seasons_path
from .penalty_handler import resolve_pass_interference, resolve_penalty
from .play_events import (
    EventType,
    PlayTransaction,
    create_chart_lookup_event,
    create_fumble_event,
    create_interception_event,
    create_recovery_event,
    create_return_event,
    create_touchdown_event,
)
from .play_resolver import (
    CHART_PLAY_TYPES,
    DefenseType,
    PenaltyChoice,
    PenaltyOption,
    PlayResult,
    PlayType,
    ResultType,
    parse_result_string,
    resolve_field_goal_with_penalties,
    resolve_hail_mary,
    resolve_play,
    resolve_play_with_penalties,
    resolve_qb_sneak,
    roll_chart_dice,
    roll_white_dice,
)
from .season_rules import SeasonRules, load_season_rules, season_rules_to_overtime_rules
from .utils import (
    clamp_ball_position,
    format_down_and_distance,
    format_field_position,
    format_field_position_with_team,
    ordinal,
)

# Re-export for backward compatibility
__all__ = ["GameState", "PaydirtGameEngine", "PlayOutcome", "ScoringPlay", "TeamStats"]


@dataclass
class ReturnChartRoll:
    """Every roll taken on a return chart for one return, and what the final cell meant."""

    rolls: list  # [(dice, cell)], the first entry being the initial return roll
    yards: int = 0
    touchdown: bool = False
    fumble: bool = False
    penalty_yards: int = 0
    returner_foul: bool = False  # OFF: the returning team fouled; DEF: the other team did
    offsetting: bool = False

    @property
    def first_roll(self) -> int:
        return self.rolls[0][0]

    @property
    def first_cell(self) -> str:
        return self.rolls[0][1]

    def trace(self, label: str) -> str:
        parts = [f'{label}:{self.rolls[0][0]}→"{self.rolls[0][1]}"']
        parts += [f'{label} reroll:{dice}→"{cell}"' for dice, cell in self.rolls[1:]]
        return " | ".join(parts)


@dataclass
class ReturnChain:
    """A resolved return and any fumble returns it chained into; nothing applied yet.

    spot is from the possessing team's perspective (100 = touchdown, 0 = own end
    zone). penalties and fumbles_lost are statistics to charge when applied;
    choice is set when the other team recovered a fumble while the returner's
    own foul was live and may keep the recovery or take the penalty.
    """

    first_roll: int
    first_cell: str
    possession_home: bool
    spot: int
    yards: int = 0  # The first segment's chart yards (a TD cell counts to the goal line)
    touchback: bool = False
    offsetting: bool = False
    fumbled: bool = False
    td_wiped: bool = False
    penalties: list = field(default_factory=list)  # (fouling_home, effective_yards)
    fumbles_lost: list = field(default_factory=list)  # team_home per lost fumble
    choice: dict | None = None
    trace: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    live: list = field(default_factory=list)

    @property
    def touchdown(self) -> bool:
        return self.spot >= 100

class PaydirtGameEngine:
    """
    Main game engine using actual Paydirt team charts.
    """

    def __init__(self, home_chart: TeamChart, away_chart: TeamChart):
        """
        Initialize a game between two teams.

        Season rules are loaded from the home team's season directory.
        In cross-season matchups, the home team's era rules apply.

        Args:
            home_chart: Home team's chart
            away_chart: Away team's chart
        """
        from pathlib import Path

        self.state = GameState(home_chart=home_chart, away_chart=away_chart)

        # Load season rules from home team's season directory
        # Derive season dir from team_dir (e.g., "seasons/1972/Dolphins" -> "seasons/1972")
        season_dir = None

        if home_chart.team_dir:
            candidate = Path(home_chart.team_dir).parent
            if candidate.exists() and candidate.is_dir():
                season_dir = candidate

        if season_dir is None:
            # Fallback: try to find season directory using peripheral year
            year = home_chart.peripheral.year
            seasons_root = get_seasons_path()
            candidate = seasons_root / str(year)
            if candidate.exists() and candidate.is_dir():
                season_dir = candidate

        if season_dir is not None:
            self.season_rules: SeasonRules = load_season_rules(season_dir)
        else:
            # Could not determine season directory (e.g., mock charts in tests)
            # Generate fallback rules from peripheral year
            from .season_rules import OvertimeConfig, OvertimeFormat

            year = home_chart.peripheral.year
            if not isinstance(year, int):
                # Mock charts - use safe defaults
                year = 2026
            two_point = year >= 1994
            ot_format = (
                OvertimeFormat.MODIFIED_SUDDEN_DEATH
                if year >= 2010
                else OvertimeFormat.SUDDEN_DEATH
            )
            period_length = 10.0 if year >= 2017 else 15.0
            self.season_rules = SeasonRules(
                season=year,
                two_point_conversion=two_point,
                overtime=OvertimeConfig(
                    enabled=True,
                    format=ot_format.value,
                    period_length_minutes=period_length,
                    max_periods_regular=1,
                    max_periods_playoff=0,
                    can_end_in_tie_regular=True,
                    can_end_in_tie_playoff=False,
                    coin_toss_winner_receives=True,
                ),
            )

        self.play_log: list[PlayOutcome] = []
        # Period in which the most recent scoring-capable action began. Scores that
        # expire a half must not be followed by the scoring team's kickoff, and
        # only the engine can know this once _use_time has advanced the period.
        self._last_play_start_quarter: int = self.state.quarter
        self._conversion_in_progress = False
        self.offensive_call_history: list[dict] = []

    def _record_offensive_call(self, play_type: PlayType) -> None:
        """Remember an executed primary call before its result changes possession.

        Penalty rerolls/decisions are part of this call, not additional calls.
        This engine-owned record is shared by CLI and web; previews never enter.
        """
        if play_type in CHART_PLAY_TYPES:
            self.offensive_call_history.append({
                "is_home": self.state.is_home_possession,
                "down": self.state.down, "distance": self.state.yards_to_go,
                "play": play_type.value,
            })
            del self.offensive_call_history[:-96]

    def restore_offensive_call_history(self, records: object) -> None:
        """Validate optional save metadata without inventing legacy call history."""
        if not isinstance(records, list):
            raise ValueError("Invalid offensive call history: expected a list")  # noqa: TRY004 - Save validation uses ValueError consistently.
        allowed = {play.value for play in CHART_PLAY_TYPES}
        restored = []
        for record in records:
            if (not isinstance(record, dict)
                    or type(record.get("is_home")) is not bool
                    or type(record.get("down")) is not int
                    or not 1 <= record["down"] <= 4
                    or type(record.get("distance")) is not int
                    or record["distance"] < 0
                    or not isinstance(record.get("play"), str)
                    or record["play"] not in allowed):
                raise ValueError("Invalid offensive call history entry")
            restored.append({key: record[key] for key in ("is_home", "down", "distance", "play")})
        self.offensive_call_history = restored[-96:]

    @classmethod
    def from_directories(cls, home_dir: str, away_dir: str) -> PaydirtGameEngine:
        """Create a game by loading team charts from directories."""
        home_chart = load_team_chart(home_dir)
        away_chart = load_team_chart(away_dir)
        return cls(home_chart, away_chart)

    def _apply_half_the_distance(self, position: int, penalty_yards: int) -> int:
        """
        Apply half-the-distance rule for penalties near the goal line.

        Args:
            position: Current field position (1-99)
            penalty_yards: Penalty yards to apply

        Returns:
            Effective penalty yards (may be reduced by half-the-distance rule)
        """
        if position - penalty_yards < 1:
            return max(1, position // 2)
        return penalty_yards

    def _handle_double_foul_penalty(
        self,
        penalty_a_yards: int,
        penalty_a_is_offensive: bool,
        penalty_a_has_auto_fd: bool,
        penalty_b_yards: int,
        penalty_b_is_offensive: bool,
        penalty_b_has_auto_fd: bool,
        landing_spot: int,
        punt_roll: int,
        return_roll: int,
        punt_result: str,
        return_result: str,
    ) -> dict:
        """
        Handle double foul scenarios using NFL Rule 14-5-1 (the "5 vs 15" rule).

        When both teams commit fouls on a special teams play:
        - If one foul is 5 yards and the other is 15 yards (and neither has auto first down):
          Apply only the 15-yard penalty, disregard the 5-yard penalty
        - Otherwise: Penalties offset, replay the down

        Args:
            penalty_a_yards: Yardage of first penalty (from punt/kickoff chart)
            penalty_a_is_offensive: True if first penalty is on offense (kicking team)
            penalty_a_has_auto_fd: True if first penalty has auto first down (X modifier)
            penalty_b_yards: Yardage of second penalty (from return chart)
            penalty_b_is_offensive: True if second penalty is on offense (receiving team)
            penalty_b_has_auto_fd: True if second penalty has auto first down
            landing_spot: Field position where return started (for enforcement spot)
            punt_roll: Dice roll for punt/kickoff chart
            return_roll: Dice roll for return chart
            punt_result: Raw result from punt/kickoff chart
            return_result: Raw result from return chart

        Returns:
            Dict with:
            - 'action': 'apply_15' or 'offset'
            - 'penalty_yards': Yards to apply (15 if action is 'apply_15', else 0)
            - 'is_offensive': True if 15-yard penalty is on offense
            - 'description': Log message with dice rolls
            - 'final_position': Ball position after enforcement (if action is 'apply_15')
        """
        # Check for 5 vs 15 scenario
        penalties = [
            (penalty_a_yards, penalty_a_is_offensive, penalty_a_has_auto_fd, punt_result),
            (penalty_b_yards, penalty_b_is_offensive, penalty_b_has_auto_fd, return_result),
        ]

        yards_list = [p[0] for p in penalties]
        has_auto_fd = any(p[2] for p in penalties)

        # Check if one is 5 and other is 15 (and neither has auto first down)
        is_five_vs_fifteen = (
            5 in yards_list
            and 15 in yards_list
            and yards_list.count(5) == 1
            and yards_list.count(15) == 1
            and not has_auto_fd
        )

        if is_five_vs_fifteen:
            # Find the 15-yard penalty
            fifteen_penalty = next(p for p in penalties if p[0] == 15)
            _, is_offensive, _, _result_str = fifteen_penalty

            # Determine which team committed which foul for logging
            five_penalty = next(p for p in penalties if p[0] == 5)
            _five_yards, five_is_off, _, _five_result = five_penalty

            # Team names for logging
            kicking_team_foul = "OFF" if five_is_off else "DEF"
            receiving_team_foul = "OFF" if is_offensive else "DEF"

            # Calculate enforcement from landing spot
            # The 15-yard penalty is enforced against the team that committed it
            if is_offensive:
                # OFF penalty on receiving team - move ball back
                new_position = landing_spot - 15
            else:
                # DEF penalty on kicking team - this shouldn't happen for 5 vs 15
                # (DEF penalty on kicking team would be unusual)
                new_position = landing_spot + 15

            # Apply half-the-distance if needed
            if new_position < 1:
                new_position = max(1, landing_spot // 2)
            elif new_position > 99:
                new_position = 99

            description = (
                f"P:{punt_roll}\u2192'{punt_result}' | R:{return_roll}\u2192'{return_result}' | "
                f"Penalty: {kicking_team_foul} 5-yard (Kicking Team) and {receiving_team_foul} 15-yard (Return Team). "
                f"Under NFL Rule 14-5-1, the 5-yard penalty is disregarded. "
                f"15 yards enforced from the catch. 1st and 10."
            )

            return {
                "action": "apply_15",
                "penalty_yards": 15,
                "is_offensive": is_offensive,
                "description": description,
                "final_position": new_position,
            }
        else:
            # Penalties offset
            description = (
                f"P:{punt_roll}\u2192'{punt_result}' | R:{return_roll}\u2192'{return_result}' | "
                f"OFFSETTING PENALTIES: {punt_result} and {return_result}. Down replayed."
            )

            return {
                "action": "offset",
                "penalty_yards": 0,
                "is_offensive": False,
                "description": description,
                "final_position": landing_spot,
            }

    def kickoff(self, kicking_home: bool = True, kickoff_spot: int = 35) -> PlayOutcome:
        """
        Perform a kickoff.

        Args:
            kicking_home: True if home team is kicking
            kickoff_spot: Yard line to kick from (default 35, use 20 for safety free kick)
        """
        self._record_play_start()
        self._record_opening_kicker(kicking_home)
        kicking_chart = self.state.home_chart if kicking_home else self.state.away_chart
        receiving_chart = self.state.away_chart if kicking_home else self.state.home_chart

        # Roll for kickoff
        dice_roll, _dice_desc = roll_chart_dice()

        # Get kickoff distance from kicking team's chart
        ko_result = kicking_chart.special_teams.kickoff.get(dice_roll, "")

        parse_result_string(ko_result)

        # Kickoff Return rule: the receiving team rolls its own offensive dice for
        # the return. It is rolled once, and only when the kick can be returned
        # (not out of bounds, not a touchback, not at or beyond the end line).
        return_roll = 0
        ret_result = ""
        ret_parsed = parse_result_string("")

        def returnable(result: str, yards: int) -> bool:
            upper = result.upper()
            if "OB" in upper or "OUT" in upper or "TB" in upper or yards >= 75:
                return False
            return 100 - (kickoff_spot + yards) > -10

        def roll_return() -> None:
            nonlocal return_roll, ret_result, ret_parsed
            if return_roll:
                return
            return_roll, _ = roll_chart_dice()
            ret_result = receiving_chart.special_teams.kickoff_return.get(return_roll, "")
            ret_parsed = parse_result_string(ret_result)

        # Calculate field position - use provided kickoff_spot, adjust for pending penalty
        penalty_desc = ""
        if self.state.pending_kickoff_penalty_yards > 0:
            if self.state.pending_kickoff_penalty_is_offense:
                # Scoring team (now receiving) committed penalty - they kick from further back
                # This means kickoff travels further, disadvantage to receiving team
                kickoff_spot += self.state.pending_kickoff_penalty_yards
                penalty_desc = f" (Kickoff from {kickoff_spot} due to OFF {self.state.pending_kickoff_penalty_yards} penalty)"
            else:
                # Kicking team committed penalty during scoring play - kick from closer
                # Shorter kick, advantage to receiving team
                kickoff_spot -= self.state.pending_kickoff_penalty_yards
                penalty_desc = f" (Kickoff from {kickoff_spot} due to DEF {self.state.pending_kickoff_penalty_yards} penalty)"
            # Clear the pending penalty
            self.state.pending_kickoff_penalty_yards = 0
            self.state.pending_kickoff_penalty_is_offense = False

        # Kickoff consumers use the receiving team as offense in both phases.
        # OFF is a receiving-team foul; DEF is a kicking-team foul.
        kick_rerolls = []
        if "OFF" in ko_result.upper() or "DEF" in ko_result.upper():
            ko_penalty_match = re.search(r"(OFF|DEF)\s*(\d+)(X)?", ko_result.upper())
            if ko_penalty_match:
                ko_penalty_yards = int(ko_penalty_match.group(2))
                ko_is_offensive_penalty = ko_penalty_match.group(1) == "OFF"
                ko_has_auto_first_down = bool(ko_penalty_match.group(3))

                # Re-roll to get actual kickoff yardage - keep rolling until non-penalty
                ko_yards = None
                max_rerolls = 10
                reroll_count = 0

                while ko_yards is None and reroll_count < max_rerolls:
                    reroll_count += 1
                    reroll, _ = roll_chart_dice()
                    reroll_result = kicking_chart.special_teams.kickoff.get(reroll, "65")
                    kick_rerolls.append(f'KO reroll:{reroll}→"{reroll_result}"')
                    if "OFF" in reroll_result.upper() or "DEF" in reroll_result.upper():
                        reroll_is_offensive = "OFF" in reroll_result.upper()
                        if ko_is_offensive_penalty != reroll_is_offensive:
                            # Offsetting penalties - re-kick from original spot
                            return self.kickoff(
                                kicking_home=kicking_home, kickoff_spot=kickoff_spot
                            )
                        else:
                            # Same type - take larger penalty, continue rolling
                            reroll_match = re.search(r"(OFF|DEF)\s*(\d+)(X)?", reroll_result.upper())
                            if reroll_match:
                                reroll_penalty = int(reroll_match.group(2))
                                ko_penalty_yards = max(ko_penalty_yards, reroll_penalty)
                                ko_has_auto_first_down = ko_has_auto_first_down or bool(reroll_match.group(3))
                    elif "OB" in reroll_result.upper() or "OUT" in reroll_result.upper():
                        # Out of bounds on re-roll - use that result
                        ko_yards = 0  # Will be handled as OB below
                        ko_result = reroll_result
                    else:
                        try:
                            ko_yards = int(reroll_result)
                        except ValueError:
                            pass  # Continue rolling

                if ko_yards is None:
                    ko_yards = 65  # Fallback
                if returnable(ko_result, ko_yards):
                    roll_return()

                # Check for double foul BEFORE offering penalty choice
                # If there's also a penalty on the return, use 5 vs 15 rule instead
                return_has_penalty = "OFF" in ret_result.upper() or "DEF" in ret_result.upper()

                if return_has_penalty:
                    # Parse return penalty
                    ret_penalty_match = re.search(r"(OFF|DEF)\s*(\d+)", ret_result.upper())
                    if ret_penalty_match and ((ret_penalty_match.group(1) == "OFF") != ko_is_offensive_penalty):
                        return_penalty_yards = int(ret_penalty_match.group(2))
                        return_is_offensive = ret_penalty_match.group(1) == "OFF"

                        # Calculate landing spot first
                        landing_spot = 100 - (kickoff_spot + ko_yards)

                        # Check for double foul (5 vs 15)
                        double_foul_result = self._handle_double_foul_penalty(
                            penalty_a_yards=ko_penalty_yards,
                            penalty_a_is_offensive=ko_is_offensive_penalty,
                            penalty_a_has_auto_fd=ko_has_auto_first_down,
                            penalty_b_yards=return_penalty_yards,
                            penalty_b_is_offensive=return_is_offensive,
                            penalty_b_has_auto_fd=False,
                            landing_spot=landing_spot,
                            punt_roll=dice_roll,
                            return_roll=return_roll,
                            punt_result=ko_result,
                            return_result=ret_result,
                        )

                        trace = " | ".join(kick_rerolls + [f'RT:{return_roll}→"{ret_result}"'])
                        dice_line = self._kickoff_dice_line(dice_roll, ko_result, trace)
                        if double_foul_result["action"] == "offset":
                            self._use_time(10)
                            outcome = self.kickoff(kicking_home=kicking_home, kickoff_spot=kickoff_spot)
                            outcome.description = f"OFFSETTING PENALTIES on kickoff; re-kick. {dice_line} " + outcome.description
                            outcome.result.description = outcome.description
                            return outcome
                        # Preserve the established opposite-team 5-versus-15
                        # exception: disregard 5; assess 15 from the catch.
                        self.state.is_home_possession = not kicking_home
                        final_position = double_foul_result["final_position"]
                        self.state.ball_position = clamp_ball_position(final_position)
                        self.state.down = 1
                        self.state.yards_to_go = 10
                        fouling_receiver = double_foul_result["is_offensive"]
                        fouling_home = not kicking_home if fouling_receiver else kicking_home
                        stats = self.state.home_stats if fouling_home else self.state.away_stats
                        stats.penalties += 1
                        stats.penalty_yards += abs(final_position - landing_spot)
                        parsed = parse_result_string(ko_result)
                        parsed.dice_roll = dice_roll
                        parsed.kickoff_return_dice = return_roll
                        parsed.kickoff_return_result = ret_result
                        description = (
                            "Under NFL Rule 14-5-1, the 5-yard penalty is disregarded. "
                            f"15 yards enforced from the catch. 1st and 10. {dice_line}"
                        )
                        parsed.description = description
                        outcome = PlayOutcome(
                            play_type=PlayType.KICKOFF, defense_type=DefenseType.STANDARD,
                            result=parsed, yards_gained=0, penalty_applied=True,
                            field_position_before=f"Kickoff from {kickoff_spot}",
                            field_position_after=self.state.field_position_str(), description=description,
                        )
                        self.play_log.append(outcome)
                        self._use_time(random.uniform(5, 15))
                        return outcome

                # Store pending kickoff penalty state for choice
                self._pending_kickoff_penalty_state = {
                    "kicking_home": kicking_home,
                    "kickoff_spot": kickoff_spot,
                    "ko_yards": ko_yards,
                    "ko_result": ko_result,
                    "ret_result": ret_result,
                    "return_roll": return_roll,
                    "ko_penalty_yards": ko_penalty_yards,
                    "ko_is_offensive_penalty": ko_is_offensive_penalty,
                    "dice_roll": dice_roll,
                    "kick_reroll_trace": " | ".join(kick_rerolls),
                    "return_trace": " | ".join(kick_rerolls + [f'RT:{return_roll}→"{ret_result}"' if return_roll else "RT:none"]),
                }

                # Build description and return pending decision
                if ko_is_offensive_penalty:
                    adjusted_spot = kickoff_spot + ko_penalty_yards
                    description = f"PENALTY on kickoff: OFF {ko_penalty_yards} (receiving team foul). Kicking team chooses: accept (re-kick from {adjusted_spot}) OR decline."
                else:
                    adjusted_spot = max(1, kickoff_spot - ko_penalty_yards)
                    description = f"PENALTY on kickoff: DEF {ko_penalty_yards} (kicking team foul). Receiving team chooses: accept (re-kick from {adjusted_spot}) OR decline."
                description += " " + self._kickoff_dice_line(
                    dice_roll, ko_result, self._pending_kickoff_penalty_state["return_trace"],
                )
                # Create penalty choice
                accept_option = PenaltyOption(
                    penalty_type="OFF" if ko_is_offensive_penalty else "DEF",
                    raw_result=ko_result,
                    yards=ko_penalty_yards,
                    description=f"Accept penalty: Re-kick from {adjusted_spot}",
                    auto_first_down=False,
                )
                decline_option = PenaltyOption(
                    penalty_type="OFF" if ko_is_offensive_penalty else "DEF",
                    raw_result="DECLINE",
                    yards=0,
                    description="Decline penalty, take kickoff result",
                    auto_first_down=False,
                )

                penalty_choice = PenaltyChoice(
                    play_result=parse_result_string(ko_result),
                    penalty_options=[accept_option, decline_option],
                    offended_team="defense" if ko_is_offensive_penalty else "offense",
                    offsetting=False,
                    kick_phase="kick",
                )

                outcome = PlayOutcome(
                    play_type=PlayType.KICKOFF,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(ko_result),
                    yards_gained=0,
                    field_position_before=f"Kickoff from {kickoff_spot}",
                    field_position_after="pending",
                    description=description,
                    penalty_choice=penalty_choice,
                    pending_penalty_decision=True,
                )
                return outcome

        try:
            ko_yards = int(ko_result) if ko_result and ko_result.isdigit() else 65
        except ValueError:
            ko_yards = 65

        is_touchback = False
        landing_spot = None
        chain = None
        if "OB" in ko_result or "OUT" in ko_result.upper():
            # Out of bounds - ball at 40
            return_position = 40
        elif "TB" in ko_result.upper() or ko_yards >= 75:
            # Touchback
            return_position = 20  # Touchback at 20
            is_touchback = True
        else:
            # Where the ball lands from the receiver's perspective. Per VI-12-F,
            # <= 0 is in the end zone (0 is the goal line) and a return may be
            # attempted unless the ball is at or beyond the end line (<= -10).
            landing_spot = 100 - (kickoff_spot + ko_yards)
            return_position = 20
            if landing_spot <= -10:
                is_touchback = True
            else:
                roll_return()
                chain = self._resolve_return_chain(
                    not kicking_home, landing_spot,
                    receiving_chart.special_teams.kickoff_return, "RT",
                    first=(return_roll, ret_result),
                    end_rule=lambda yards: self._kickoff_return_spot(landing_spot, yards),
                )
                if chain.offsetting:
                    # Offsetting fouls nullify the kick: ten seconds, then re-kick.
                    self._use_time(10)
                    return self.kickoff(kicking_home=kicking_home, kickoff_spot=kickoff_spot)

        ctx = {
            "kicking_home": kicking_home,
            "kickoff_spot": kickoff_spot,
            "dice_roll": dice_roll,
            "ko_result": ko_result,
            "ko_yards": ko_yards,
            "landing_spot": landing_spot,
            "is_touchback": is_touchback,
            "return_position": return_position,
            "penalty_desc": penalty_desc,
            "declined_kick_penalty": None,
        }
        if chain is not None and chain.choice:
            return self._pending_kickoff_return_fumble(ctx, chain)
        return self._complete_kickoff_return(ctx, chain)

    # ------------------------------------------------------------------
    # Return charts (kickoff, punt, interception, fumble and blocked-kick returns)
    # ------------------------------------------------------------------

    def _roll_return_chart(self, chart: dict, first: tuple | None = None) -> ReturnChartRoll:
        """Roll a return chart until a non-penalty cell.

        OFF/DEF cells reroll; same-type fouls keep the larger yardage and
        opposite fouls offset. The result records every roll consumed.
        """
        roll = ReturnChartRoll(rolls=[])
        if first is None:
            dice, _ = roll_chart_dice()
            first = (dice, chart.get(dice, "0"))
        dice, cell = first
        for _ in range(12):
            cell = "" if cell is None else str(cell)
            roll.rolls.append((dice, cell))
            match = re.search(r"(OFF|DEF)\s*(\d+)", cell.upper())
            if match:
                yards = int(match.group(2))
                returner_foul = match.group(1) == "OFF"
                if roll.penalty_yards and returner_foul != roll.returner_foul:
                    roll.offsetting = True
                    return roll
                roll.penalty_yards = max(roll.penalty_yards, yards)
                roll.returner_foul = returner_foul
                dice, _ = roll_chart_dice()
                cell = chart.get(dice, "0")
                continue
            parsed = parse_result_string(cell)
            if parsed.result_type == ResultType.FUMBLE:
                roll.fumble = True
                roll.yards = parsed.yards
            elif parsed.result_type == ResultType.TOUCHDOWN or "TD" in cell.upper():
                roll.touchdown = True
            else:
                try:
                    roll.yards = int(cell.replace("*", "").replace("†", "").strip())
                except ValueError:
                    roll.yards = 0
            return roll
        return roll

    def _enforce_return_penalty(
        self, end_spot: int, penalty_yards: int, returner_foul: bool
    ) -> tuple[int, int, bool]:
        """Assess a return penalty against the end of the return.

        Spots are from the returning team's perspective (100 = goal line).
        Returns (final_spot, effective_yards, touchdown_wiped). A returner's
        foul is walked back (half the distance near its own goal) and wipes out
        a return touchdown; the other team's foul adds yards (half the distance
        to the goal, never a touchdown) and cannot take a touchdown away.
        """
        if returner_foul:
            base = max(1, min(end_spot, 100))
            effective = self._apply_half_the_distance(base, penalty_yards)
            return max(1, base - effective), effective, end_spot >= 100
        if end_spot >= 100:
            return 100, 0, False
        base = max(1, end_spot)
        distance = 100 - base
        effective = penalty_yards if penalty_yards * 2 <= distance else distance // 2
        return base + effective, effective, False

    def _resolve_return_chain(
        self, returning_home: bool, start: int, chart: dict, label: str,
        first: tuple | None = None, end_rule=None, depth: int = 0,
    ) -> ReturnChain:
        """Resolve a return and anything it chains into, without touching game state.

        A fumble cell is resolved with the returning team's recovery roll;
        17–19 (kept) and 37–39 (lost) give the recovering team a fumble return on
        its own interception-return chart, which may chain further. A penalty in a
        segment that ends in a lost fumble stays live and is settled at the end of
        the chain (see _settle_live_penalties). end_rule(yards) -> (end_spot,
        touchback) lets the first segment apply kickoff end-zone or interception
        touchback rules.
        """
        roll = self._roll_return_chart(chart, first)
        chain = ReturnChain(
            first_roll=roll.first_roll, first_cell=roll.first_cell,
            possession_home=returning_home, spot=start,
        )
        chain.trace.append(roll.trace(label))
        if roll.offsetting:
            chain.offsetting = True
            chain.notes.append("OFFSETTING PENALTIES on the return - the play is nullified")
            return chain

        returner = self.state.home_chart if returning_home else self.state.away_chart
        other = self.state.away_chart if returning_home else self.state.home_chart
        returner_name = returner.peripheral.short_name
        other_name = other.peripheral.short_name
        yards = (100 - start) if roll.touchdown else roll.yards
        chain.yards = yards
        kind = f"{'OFF' if roll.returner_foul else 'DEF'} {roll.penalty_yards}"

        if roll.fumble:
            spot = start + yards
            chain.fumbled = True
            recovery_roll, _ = roll_chart_dice()
            low, high = returner.peripheral.fumble_recovered_range
            recovered = low <= recovery_roll <= high
            chain.trace.append(f'R:{recovery_roll}→"{"recovered" if recovered else "lost"}"')
            if spot >= 110:
                # VI-12-D-ii: relocate a fumble beyond the end line into the end zone.
                depth_yards, depth_desc = roll_white_dice()
                spot = 100 + depth_yards
                chain.trace.append(f"End-zone depth:{depth_desc}")
            if spot <= 0:
                spot_text = f"{returner_name} end zone"
            elif spot >= 100:
                spot_text = f"{other_name} end zone"
            else:
                spot_text = format_field_position_with_team(spot, returner_name, other_name)
            if roll.penalty_yards:
                chain.live.append((
                    returning_home, roll.returner_foul, roll.penalty_yards, spot,
                    len(chain.penalties), len(chain.fumbles_lost),
                ))
            if recovered:
                chain.notes.append(f"FUMBLE on the return at {spot_text}! {returner_name} recovers")
                if spot <= 0:
                    # Kick/interception momentum may make this a touchback rather
                    # than a safety; only the original return has that end rule.
                    chain.touchback = end_rule is not None and end_rule(yards)[1]
                    chain.spot = 20 if chain.touchback else 0
                    chain.notes.append("TOUCHBACK" if chain.touchback else "SAFETY")
                elif spot >= 100:
                    chain.spot = 100
                    chain.notes.append("TOUCHDOWN")
                elif 17 <= recovery_roll <= 19 and depth < 3:
                    self._merge_chain(chain, self._resolve_return_chain(
                        returning_home, spot, returner.special_teams.interception_return, "FR",
                        depth=depth + 1,
                    ))
                else:
                    chain.spot = spot
            else:
                chain.fumbles_lost.append(returning_home)
                chain.notes.append(f"FUMBLE on the return at {spot_text}! {other_name} recovers")
                if spot <= 0:
                    chain.possession_home = not returning_home
                    chain.spot = 100
                    chain.notes.append("TOUCHDOWN")
                elif spot >= 100:
                    chain.possession_home = not returning_home
                    chain.spot = 20
                    chain.touchback = True
                    chain.notes.append("TOUCHBACK")
                elif 37 <= recovery_roll <= 39 and depth < 3:
                    self._merge_chain(chain, self._resolve_return_chain(
                        not returning_home, 100 - spot, other.special_teams.interception_return, "FR",
                        depth=depth + 1,
                    ))
                else:
                    chain.possession_home = not returning_home
                    chain.spot = 100 - spot
        else:
            if end_rule is not None:
                end, chain.touchback = end_rule(yards)
            else:
                end = max(0, min(100, start + yards))
            chain.spot = end
            if roll.penalty_yards:
                final, effective, wiped = self._enforce_return_penalty(
                    end, roll.penalty_yards, roll.returner_foul
                )
                chain.spot = final
                chain.td_wiped = chain.td_wiped or wiped
                chain.penalties.append((returning_home if roll.returner_foul else not returning_home, effective))
                chain.notes.append(
                    f"{kind} on the return assessed" + (", return touchdown nullified" if wiped else "")
                )

        if depth == 0 and not chain.offsetting:
            self._settle_live_penalties(chain)
        return chain

    @staticmethod
    def _merge_chain(chain: ReturnChain, sub: ReturnChain) -> None:
        chain.possession_home = sub.possession_home
        chain.spot = sub.spot
        chain.touchback = sub.touchback
        chain.offsetting = chain.offsetting or sub.offsetting
        chain.td_wiped = chain.td_wiped or sub.td_wiped
        chain.fumbled = chain.fumbled or sub.fumbled
        chain.penalties.extend(sub.penalties)
        chain.fumbles_lost.extend(sub.fumbles_lost)
        chain.live.extend(
            (home, foul, yards, spot, n_pen + len(chain.penalties) - len(sub.penalties),
             n_fum + len(chain.fumbles_lost) - len(sub.fumbles_lost))
            for home, foul, yards, spot, n_pen, n_fum in sub.live
        )
        chain.trace.extend(sub.trace)
        chain.notes.extend(sub.notes)

    def _settle_live_penalties(self, chain: ReturnChain) -> None:
        """Settle penalties whose segment ended in a lost fumble.

        The fouling team ends with the ball: assess from the end of the play.
        The other team ends with the ball after a returner's foul: its choice
        (recorded in chain.choice). After the other team's own foul the
        offended returner always takes the penalty and keeps the ball.
        """
        for returning_home, returner_foul, yards, spot, n_penalties, n_fumbles in chain.live:
            fouling_home = returning_home if returner_foul else not returning_home
            returner_name = (self.state.home_chart if returning_home else self.state.away_chart).peripheral.short_name
            kind = f"{'OFF' if returner_foul else 'DEF'} {yards}"
            if chain.possession_home == returning_home:
                final, effective, wiped = self._enforce_return_penalty(chain.spot, yards, returner_foul)
                chain.spot = final
                chain.td_wiped = chain.td_wiped or wiped
                chain.penalties.append((fouling_home, effective))
                chain.notes.append(
                    f"{kind} on the return assessed from the end of the play"
                    + (", touchdown nullified" if wiped else "")
                )
            elif returner_foul:
                penalty_spot, effective, _ = self._enforce_return_penalty(spot, yards, True)
                chain.choice = {
                    "fouling_home": returning_home,
                    "penalty_spot": penalty_spot,
                    "effective": effective,
                    "yards": yards,
                    "n_penalties": n_penalties,
                    "n_fumbles": n_fumbles,
                }
                other_name = (self.state.away_chart if returning_home else self.state.home_chart).peripheral.short_name
                chain.notes.append(f"{kind} on the return declined by {other_name}; the recovery stands")
            else:
                penalty_spot, effective, _ = self._enforce_return_penalty(spot, yards, False)
                chain.possession_home = returning_home
                chain.spot = penalty_spot
                del chain.fumbles_lost[n_fumbles:]
                del chain.penalties[n_penalties:]
                chain.penalties.append((fouling_home, effective))
                chain.notes.append(f"{kind} on the return taken by {returner_name}; the recovery is declined")
                break

    def _apply_return_chain(self, chain: ReturnChain, accept_choice: bool | None = None) -> bool:
        """Apply a resolved chain: possession, spot, statistics and any touchdown."""
        choice = chain.choice if accept_choice else None
        if choice:
            possession_home = choice["fouling_home"]
            spot = choice["penalty_spot"]
            penalties = chain.penalties[:choice["n_penalties"]] + [(possession_home, choice["effective"])]
            fumbles_lost = chain.fumbles_lost[:choice["n_fumbles"]]
        else:
            possession_home, spot = chain.possession_home, chain.spot
            penalties, fumbles_lost = chain.penalties, chain.fumbles_lost
        self.state.is_home_possession = possession_home
        self.state.ball_position = clamp_ball_position(spot)
        self.state.down = 1
        self.state.yards_to_go = 10
        for home, effective in penalties:
            stats = self.state.home_stats if home else self.state.away_stats
            stats.penalties += 1
            stats.penalty_yards += effective
        for home in fumbles_lost:
            stats = self.state.home_stats if home else self.state.away_stats
            stats.fumbles_lost += 1
            stats.turnovers += 1
        touchdown = spot >= 100
        if touchdown:
            self._score_touchdown()
        elif spot <= 0:
            self._score_safety()
        return touchdown

    def _blocked_kick_return(
        self, start: int, first: tuple, kick_name: str, recovery_roll: int, who: str,
    ) -> tuple[ReturnChain, bool, int, str]:
        """Resolve a blocked-kick or fumbled-snap return from an already rolled chart cell.

        Returns (chain, touchdown, return_yards, description). When
        chain.offsetting is set nothing has been applied; the caller nullifies
        the play with _nullify_kick_play().
        """
        possessor_home = self.state.is_home_possession
        chain = self._resolve_return_chain(
            possessor_home, start, self.state.possession_team.special_teams.interception_return,
            "Ret", first=first,
        )
        if chain.offsetting:
            return chain, False, 0, ""
        touchdown = self._apply_return_chain(chain, accept_choice=False)
        kept = self.state.is_home_possession == possessor_home
        return_yards = (chain.spot - start) if kept else 0
        if touchdown:
            self.state.ball_position = 97
            description = f"{kick_name}! {who} recovers (roll {recovery_roll}), return roll {first[0]} - RETURN TD!"
        else:
            description = (
                f"{kick_name}! {who} recovers (roll {recovery_roll}), return roll {first[0]} "
                f"for {return_yards} yards"
            )
        if chain.notes:
            description += "; " + "; ".join(chain.notes)
        if len(chain.trace) > 1 or "reroll" in chain.trace[0]:
            description += f" ({' | '.join(chain.trace)})"
        return chain, touchdown, return_yards, description

    def _nullify_kick_play(
        self, kicking_home: bool, line_of_scrimmage: int, down_before: int, ytg_before: int,
        chain: ReturnChain, kick_name: str,
    ) -> str:
        """Offsetting fouls on a blocked-kick return: replay the down from the previous spot."""
        self.state.is_home_possession = kicking_home
        self.state.ball_position = clamp_ball_position(line_of_scrimmage)
        self.state.down = down_before
        self.state.yards_to_go = ytg_before
        return (
            f"{kick_name}! OFFSETTING PENALTIES on the return - the play is nullified, "
            f"replay the down ({' | '.join(chain.trace)})"
        )

    @staticmethod
    def _kickoff_return_spot(landing_spot: int, ret_yards: int) -> tuple[int, bool]:
        """Field position after a return from landing_spot (<= 0 is yards deep in the end zone).

        Returns (position, is_touchback); 100 is a return touchdown.
        """
        if landing_spot <= 0:
            yards_deep = -landing_spot
            if ret_yards > yards_deep:
                return min(100, ret_yards - yards_deep), False
            return 20, True
        return max(1, min(100, landing_spot + ret_yards)), False

    @staticmethod
    def _kickoff_dice_line(dice_roll: int, ko_result: str, return_trace: str) -> str:
        return f'(KO:{dice_roll}→"{ko_result}" | {return_trace or "RT:none"})'

    def _complete_kickoff_return(
        self, ctx: dict, chain: ReturnChain | None, accept_choice: bool | None = None,
    ) -> PlayOutcome:
        """Apply a kickoff's return (or lack of one) and describe it."""
        kicking_home = ctx["kicking_home"]
        kickoff_spot = ctx["kickoff_spot"]
        ko_result = ctx["ko_result"]
        ko_yards = ctx["ko_yards"]
        kicker = (self.state.home_chart if kicking_home else self.state.away_chart).peripheral.short_name
        receiver = (self.state.away_chart if kicking_home else self.state.home_chart).peripheral.short_name
        is_touchback = ctx["is_touchback"]
        touchdown = False
        turnover = False
        if chain is None:
            self.state.is_home_possession = not kicking_home
            self.state.ball_position = clamp_ball_position(ctx["return_position"])
            self.state.down = 1
            self.state.yards_to_go = 10
            return_trace = "RT:none"
        else:
            touchdown = self._apply_return_chain(chain, accept_choice)
            turnover = self.state.is_home_possession == kicking_home
            is_touchback = is_touchback or chain.touchback
            return_trace = " | ".join(chain.trace)
        safety = chain is not None and chain.spot <= 0 and not (accept_choice and chain.choice)
        if touchdown and ctx.get("declined_kick_penalty"):
            # A declined kick-chart penalty carries over to the next kickoff.
            yards, is_offense = ctx["declined_kick_penalty"]
            self.state.pending_kickoff_penalty_yards = yards
            self.state.pending_kickoff_penalty_is_offense = is_offense

        kick_type = "Safety free kick" if kickoff_spot == 20 else "Kickoff"
        kick_text = f"{kick_type} {ko_yards} yards"
        spot_text = self.state.field_position_str()
        if "OB" in ko_result or "OUT" in ko_result.upper():
            description = f"{kick_type} out of bounds! Ball at the 40."
        elif is_touchback:
            description = f"{kick_text} into the end zone. Touchback."
        elif accept_choice and chain is not None and chain.choice:
            description = (
                f"{kick_text}. FUMBLE on the return; {kicker} takes the OFF {chain.choice['yards']} "
                f"penalty instead of the recovery. {receiver} ball at {spot_text}."
            )
        elif safety:
            description = f"{kick_text}. {receiver} recovers in its own end zone. SAFETY!"
        elif touchdown and turnover:
            description = f"{kick_text}. {kicker} returns the fumble for a TOUCHDOWN!"
        elif touchdown:
            description = f"{kick_text}, RETURNED FOR A TOUCHDOWN!"
        elif turnover:
            description = f"{kick_text}. {kicker} ball at {spot_text}."
        else:
            description = f"{kick_text}, returned to {spot_text}."
            landing_spot = ctx["landing_spot"]
            if chain is not None and not chain.fumbled and not chain.penalties and landing_spot is not None:
                actual_return = chain.spot - landing_spot if landing_spot > 0 else chain.spot
                if actual_return >= 40:
                    description += " What a return!"
                elif actual_return >= 30:
                    description += " Great return!"
                elif 0 <= actual_return <= 5:
                    description += " Excellent coverage!"
                elif actual_return < 0:
                    description += " Outstanding special teams coverage!"
        if chain is not None and not (accept_choice and chain.choice) and chain.notes:
            description += " " + "; ".join(chain.notes) + "."
        if ctx.get("declined_kick_penalty"):
            description += " (kick-chart penalty declined)"
        full_trace = " | ".join(filter(None, [ctx.get("kick_reroll_trace", ""), return_trace]))
        description += f"{ctx['penalty_desc']} {self._kickoff_dice_line(ctx['dice_roll'], ko_result, full_trace)}"

        result = parse_result_string(chain.first_cell if chain is not None else ko_result)
        result.dice_roll = ctx["dice_roll"]
        if chain is not None:
            result.kickoff_return_dice = chain.first_roll
            result.kickoff_return_result = chain.first_cell
            result.touchdown = touchdown
            if chain.fumbled:
                result.fumble_resolved = True
                result.fumble_recovered = not turnover
        outcome = PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=self.state.ball_position,
            turnover=turnover,
            touchdown=touchdown,
            safety=bool(safety),
            field_position_before=f"Kickoff from {kickoff_spot}",
            field_position_after=self.state.field_position_str(),
            description=description,
            penalty_applied=bool(chain is not None and (chain.penalties or accept_choice)),
        )
        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 15))
        return outcome

    def _pending_kickoff_return_fumble(self, ctx: dict, chain: ReturnChain) -> PlayOutcome:
        """The kicking team recovered a return fumble while a receiving-team foul is live.

        It may keep the recovery (and any fumble return) or take the penalty,
        which leaves the ball with the receiving team. Kickoff decisions use the
        receiving team as "offense", so the kicking team is "defense" here.
        """
        kicking_home = ctx["kicking_home"]
        choice = chain.choice
        kicker = (self.state.home_chart if kicking_home else self.state.away_chart).peripheral.short_name
        receiver = (self.state.away_chart if kicking_home else self.state.home_chart).peripheral.short_name
        self.state.is_home_possession = kicking_home
        kind = f"OFF {choice['yards']}"
        penalty_spot_text = format_field_position_with_team(choice["penalty_spot"], receiver, kicker)
        if chain.touchdown:
            play_preview = f"{kicker} returns the fumble for a TOUCHDOWN"
        else:
            play_preview = f"{kicker} recovers at {format_field_position_with_team(chain.spot, kicker, receiver)}"
        accept_preview = f"1st and 10 at {penalty_spot_text}"
        return_trace = " | ".join(chain.trace)
        full_trace = " | ".join(filter(None, [ctx.get("kick_reroll_trace", ""), return_trace]))
        dice_line = self._kickoff_dice_line(ctx["dice_roll"], ctx["ko_result"], full_trace)

        play_result = parse_result_string(chain.first_cell)
        play_result.dice_roll = ctx["dice_roll"]
        play_result.kickoff_return_dice = chain.first_roll
        play_result.kickoff_return_result = chain.first_cell
        play_result.touchdown = chain.touchdown
        play_result.turnover = True
        option = PenaltyOption(
            penalty_type="OFF",
            raw_result=kind,
            yards=choice["yards"],
            description=f"{kind} on the return ({receiver} keeps the ball)",
            auto_first_down=False,
            result_preview=accept_preview,
        )
        penalty_choice = PenaltyChoice(
            play_result=play_result,
            penalty_options=[option],
            offended_team="defense",
            offsetting=False,
            kick_phase="return_fumble",
            play_result_preview=play_preview,
        )
        self._pending_kickoff_penalty_state = {
            "phase": "return_fumble",
            "ctx": ctx,
            "chain": chain,
            "dice_roll": ctx["dice_roll"],
            "ko_result": ctx["ko_result"],
            "return_trace": return_trace,
        }
        description = (
            f"FUMBLE on the kickoff return with {kind} against {receiver}. {kicker} chooses: "
            f"keep the recovery ({play_preview}) OR take the penalty ({receiver} ball at {penalty_spot_text}). "
            f"{dice_line}"
        )
        return PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=play_result,
            yards_gained=0,
            field_position_before=f"Kickoff from {ctx['kickoff_spot']}",
            field_position_after="pending",
            description=description,
            penalty_choice=penalty_choice,
            pending_penalty_decision=True,
        )

    def onside_kick(self, kicking_home: bool = True) -> PlayOutcome:
        """
        Attempt an onside kickoff per official rules.

        Roll offensive dice:
        - Kicking team recovers if dice total is 13-20 (inclusive)
        - Receiving team recovers on any other total
        - Ball travels 12 yards, no advance or return

        Args:
            kicking_home: True if home team is kicking

        Returns:
            PlayOutcome with recovery result
        """
        self._record_play_start()
        self._record_opening_kicker(kicking_home)
        # Roll offensive dice
        dice_roll, _dice_desc = roll_chart_dice()

        # Kicking team recovers on 13-20
        kicking_team_recovers = 13 <= dice_roll <= 20

        # Ball travels 12 yards from the 35 yard line
        # From kicking team's perspective: 35 + 12 = 47 yard line
        # From receiving team's perspective: 100 - 47 = 53 yard line
        ball_position_from_kicker = 47  # Kicking team's 47

        if kicking_team_recovers:
            # Kicking team gets the ball at their 47
            self.state.is_home_possession = kicking_home
            self.state.ball_position = ball_position_from_kicker
            description = (
                f'ONSIDE KICK RECOVERED by kicking team! (ON:{dice_roll}→"REC") Ball at own 47'
            )
        else:
            # Receiving team gets the ball at their 53 (kicking team's 47)
            self.state.is_home_possession = not kicking_home
            self.state.ball_position = 100 - ball_position_from_kicker  # = 53 from receiver's view
            description = f'Onside kick FAILED! Receiving team recovers. (ON:{dice_roll}→"FAIL") Ball at own 53'

        self.state.down = 1
        self.state.yards_to_go = 10

        outcome = PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=parse_result_string(""),
            yards_gained=12,
            touchdown=False,
            field_position_after=self.state.field_position_str(),
            description=description,
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(3, 8))

        return outcome

    def _record_turnover(self, *, interception: bool) -> None:
        """Count an applied statistical loss before switching possession.

        Args:
            interception: True for an interception, False for a lost fumble.
        """
        stats = self.state.offense_stats
        if interception:
            stats.interceptions_thrown += 1
        else:
            stats.fumbles_lost += 1
        stats.turnovers += 1

    def _handle_interception(
        self,
        result: PlayResult,
        ball_pos_before: int,
        yards: int,
        txn: PlayTransaction | None = None,
    ) -> tuple:
        """
        Centralized interception handling per official rules VI-12-E.

        Args:
            result: The PlayResult to update with interception details
            ball_pos_before: Ball position before the play (from offense's perspective)
            yards: Yards on the interception (can be negative)
            txn: Optional transaction to add events to

        Returns:
            tuple: (turnover, touchdown, safety)
        """
        turnover = True
        touchdown = False
        safety = False

        def_team = self.state.defense_team.peripheral.short_name

        # Calculate raw interception spot from offense's perspective
        raw_int_spot = ball_pos_before + yards

        # Handle end zone interception rules
        # <= 0 = offense's end zone, >= 100 = defense's end zone, 1-99 = field of play
        if raw_int_spot >= 100:
            # INT in defense's end zone = TOUCHBACK
            # Defense intercepts in their own end zone, gets ball at 20
            self._record_turnover(interception=True)
            self.state.switch_possession()
            self.state.ball_position = 20
            result.description = "Interception in end zone - TOUCHBACK"
            result.int_spot = 20  # Ball spotted at 20 after touchback
            result.int_return_yards = 0
            result.int_return_dice = 0
            return (turnover, touchdown, safety)
        elif raw_int_spot <= 0:
            # INT in offense's end zone = TD for defense
            # Defense intercepted in opponent's end zone (where they would score)
            touchdown = True
            self._record_turnover(interception=True)
            self.state.switch_possession()
            self._score_touchdown()
            self.state.ball_position = 97
            result.scoring_team = def_team
            result.description = "Interception in end zone - TOUCHDOWN for defense"
            result.int_spot = 100  # Defense's perspective
            result.int_return_yards = 0
            result.int_return_dice = 0
            return (turnover, touchdown, safety)
        else:
            # Normal field position (1-99) - process with return
            int_spot_from_offense = raw_int_spot

        # Normal interception processing with return
        int_spot_from_defense = 100 - int_spot_from_offense

        # Add interception event to transaction
        if txn:
            txn.add_event(
                create_interception_event(
                    int_spot=int_spot_from_defense, int_yards_downfield=yards, acting_team=def_team
                )
            )

        # Check if interception return was already calculated (e.g., after penalty decision)
        # If so, reuse the existing return instead of re-rolling
        if result.int_return_yards and result.int_return_yards != 0:
            self._record_turnover(interception=True)
            return_yards = result.int_return_yards
            return_dice = result.int_return_dice if result.int_return_dice else 0
            return_td = (result.int_spot + return_yards >= 100) if result.int_spot else False
            int_return_result = str(return_yards) if not return_td else "TD"
            if txn:
                txn.add_event(
                    create_return_event(
                        event_type=EventType.INT_RETURN,
                        return_roll=return_dice,
                        return_desc=f"Reuse:{return_dice}",
                        return_yards=return_yards,
                        chart_result=int_return_result,
                        is_touchdown=(return_td or (int_spot_from_defense + return_yards >= 100)),
                        acting_team=def_team,
                    )
                )
            self.state.switch_possession()
            final_position = int_spot_from_defense + return_yards
            if return_td or final_position >= 100:
                touchdown = True
                result.scoring_team = def_team
                self._score_touchdown()
                self.state.ball_position = 97
                if txn:
                    txn.add_event(create_touchdown_event(acting_team=def_team))
            elif final_position <= 0:
                self.state.ball_position = 20
                result.description = (
                    "INTERCEPTION! Momentum carries defender into end zone - TOUCHBACK at the 20"
                )
            else:
                self.state.ball_position = clamp_ball_position(final_position)
            result.int_return_yards = return_yards
            result.int_return_dice = return_dice
            result.int_spot = int_spot_from_defense
            return (turnover, touchdown, safety)

        # Roll the return on the intercepting team's chart. Penalties reroll and are
        # assessed against the end of the return; fumbles resolve and may chain.
        offense_home = self.state.is_home_possession

        def end_rule(advance: int) -> tuple[int, bool]:
            end = int_spot_from_defense + advance
            if end <= 0:
                # Momentum carries the defender into his own end zone: touchback.
                return 20, True
            return min(100, end), False

        chain = self._resolve_return_chain(
            not offense_home, int_spot_from_defense,
            self.state.defense_team.special_teams.interception_return, "Ret",
            end_rule=end_rule,
        )
        return_trace = " | ".join(chain.trace)
        result.int_return_dice = chain.first_roll
        result.int_spot = int_spot_from_defense
        if chain.offsetting:
            # Offsetting fouls on the return nullify the whole play.
            result.replay_down = True
            result.int_return_yards = 0
            result.description = (
                "INTERCEPTION nullified by OFFSETTING PENALTIES on the return - "
                f"replay the down ({return_trace})"
            )
            result.rule_explanation = result.description
            return (False, False, False)

        self._record_turnover(interception=True)
        touchdown = self._apply_return_chain(chain, accept_choice=False)
        safety = chain.spot <= 0
        turnover = self.state.is_home_possession != offense_home
        plain_return = turnover and not chain.penalties and not chain.fumbled
        return_yards = chain.yards if plain_return else (chain.spot - int_spot_from_defense) if turnover else 0
        if txn:
            txn.add_event(
                create_return_event(
                    event_type=EventType.INT_RETURN,
                    return_roll=chain.first_roll,
                    return_desc=return_trace,
                    return_yards=return_yards,
                    chart_result=chain.first_cell,
                    is_touchdown=touchdown and turnover,
                    acting_team=def_team,
                )
            )
        if touchdown:
            result.scoring_team = self.state.possession_team.peripheral.short_name
            self.state.ball_position = 97
            if txn:
                txn.add_event(create_touchdown_event(acting_team=result.scoring_team))
        elif chain.touchback:
            result.description = (
                "INTERCEPTION! Momentum carries defender into end zone - TOUCHBACK at the 20"
            )
        plain_cell = chain.first_cell.strip().lstrip("-").isdigit() or "TD" in chain.first_cell.upper()
        if chain.notes or len(chain.trace) > 1 or "reroll" in return_trace or not plain_cell:
            extra = ("; ".join(chain.notes) + " " if chain.notes else "") + f"({return_trace})"
            result.description = f"{result.description} | {extra}" if result.description else extra

        # Store return info
        result.int_return_yards = return_yards
        result.int_return_dice = chain.first_roll
        result.int_spot = int_spot_from_defense

        return (turnover, touchdown, safety)

    def _handle_fumble(
        self,
        result: PlayResult,
        ball_pos_before: int,
        yards: int,
        down_before: int,
        ytg_before: int,
        txn: PlayTransaction | None = None,
    ) -> tuple:
        """
        Centralized fumble handling per official rules VI-12-D.

        Args:
            result: The PlayResult to update with fumble details
            ball_pos_before: Ball position before the play (from offense's perspective)
            yards: Yards before the fumble (can be negative)
            down_before: Down before the play
            ytg_before: Yards to go before the play
            txn: Optional transaction to add events to

        Returns:
            tuple: (turnover, touchdown, safety, first_down)
        """
        turnover = False
        touchdown = False
        safety = False
        first_down = False

        off_team = self.state.possession_team.peripheral.short_name
        def_team = self.state.defense_team.peripheral.short_name

        # Calculate raw fumble spot
        raw_fumble_spot = ball_pos_before + yards

        # Add fumble event to transaction
        if txn:
            txn.add_event(
                create_fumble_event(
                    yards_before_fumble=yards, fumble_spot=raw_fumble_spot, acting_team=off_team
                )
            )

        # Check if fumble recovery was already determined (e.g., when accepting play result after penalty)
        # If so, use the stored result instead of re-rolling
        if getattr(result, "fumble_resolved", False):
            recovery_roll = result.fumble_recovery_roll
            recovery_desc = f"Roll {recovery_roll} (pre-determined)"
            fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range
            offense_recovers = result.fumble_recovered
        else:
            # Roll for fumble recovery using offensive dice
            recovery_roll, recovery_desc = roll_chart_dice()

            # Get fumble recovery ranges from the offensive team's chart
            fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range

            # Determine if offense recovers or loses the fumble
            offense_recovers = fumble_rec_range[0] <= recovery_roll <= fumble_rec_range[1]

        # Add recovery event to transaction
        if txn:
            txn.add_event(
                create_recovery_event(
                    recovery_roll=recovery_roll,
                    recovery_desc=recovery_desc,
                    offense_recovers=offense_recovers,
                    recovery_range=fumble_rec_range,
                    acting_team=off_team if offense_recovers else def_team,
                )
            )

        # Handle end zone situations per rule VI-12-D
        if raw_fumble_spot >= 110:
            # VI-12-D-ii: Fumble at/beyond opponent's end line
            end_zone_dist, white_desc = roll_white_dice()
            fumble_spot = 100 + end_zone_dist
            result.description = f"Fumble into end zone ({white_desc} yards deep)"

            if offense_recovers:
                touchdown = True
                self._score_touchdown()
                self.state.ball_position = 97
            else:
                turnover = True
                self._record_turnover(interception=False)
                self.state.switch_possession()
                self.state.ball_position = 20  # Touchback
                result.description = "Fumble recovered by defense in end zone - TOUCHBACK"

        elif raw_fumble_spot >= 100:
            # VI-12-D-i: Fumble within opponent's end zone (100-109)
            fumble_spot = raw_fumble_spot

            if offense_recovers:
                touchdown = True
                self._score_touchdown()
                self.state.ball_position = 97
            else:
                turnover = True
                self._record_turnover(interception=False)
                self.state.switch_possession()
                self.state.ball_position = 20  # Touchback
                result.description = "Fumble recovered by defense in end zone - TOUCHBACK"

        elif raw_fumble_spot <= 0:
            # Fumble in offense's own end zone (behind their goal line)
            fumble_spot = 1
            if offense_recovers:
                # Offense recovers in own end zone = SAFETY
                safety = True
                self._score_safety()
                result.description = "Fumble recovered by offense in own end zone - SAFETY"
            else:
                # Defense recovers in opponent's end zone = TD for defense
                turnover = True
                touchdown = True
                self._record_turnover(interception=False)
                self.state.switch_possession()
                result.scoring_team = def_team
                self._score_touchdown()
                self.state.ball_position = 97
                result.fumble_end_zone_touchdown = True
                result.description = (
                    f"{def_team} recovers the fumble in {off_team}'s end zone. TOUCHDOWN!"
                )
                result.rule_explanation = result.description

        else:
            # Normal field position (1-99)
            fumble_spot = raw_fumble_spot

            if offense_recovers:
                self.state.ball_position = fumble_spot

                # Check for special return on recovery rolls 17, 18, 19
                # Per rules: offense gets INT return from spot of recovery for fumbles recovered
                # with totals 17, 18, or 19. (Auto TD on 19 only applies to blocked kicks, not fumbles)
                if recovery_roll in [17, 18, 19]:
                    offense_home = self.state.is_home_possession
                    chain = self._resolve_return_chain(
                        offense_home, fumble_spot,
                        self.state.possession_team.special_teams.interception_return, "Ret",
                        end_rule=lambda advance: (max(0, min(100, fumble_spot + advance)), False),
                    )
                    return_dice = chain.first_roll
                    int_return_result = chain.first_cell
                    return_desc = " | ".join(chain.trace)
                    result.fumble_return_dice = return_dice
                    if chain.offsetting:
                        # Offsetting fouls on the advance nullify the whole play.
                        result.replay_down = True
                        self.state.ball_position = ball_pos_before
                        result.description = (
                            "FUMBLE nullified by OFFSETTING PENALTIES on the advance - "
                            f"replay the down ({return_desc})"
                        )
                        result.rule_explanation = result.description
                        return (False, False, False, False)
                    touchdown = self._apply_return_chain(chain, accept_choice=False)
                    safety = chain.spot <= 0
                    new_position = chain.spot
                    if touchdown:
                        result.scoring_team = self.state.possession_team.peripheral.short_name
                        self.state.ball_position = 97
                    turnover = self.state.is_home_possession != offense_home
                    if turnover:
                        result.fumble_recovered = False  # Lost on the advance after all.
                    if safety:
                        return_yards = chain.yards  # The chart advance that carried the ball back.
                    else:
                        return_yards = (new_position - fumble_spot) if not turnover else 0
                    result.fumble_return_yards = return_yards
                    # Preserve existing description (e.g., "BAD SNAP") if set, otherwise use fumble description
                    if not result.description or result.description.startswith("FUMBLE!"):
                        spot = format_field_position_with_team(fumble_spot, off_team, def_team)
                        result.description = f"FUMBLE! {yards} yards before fumble - Offense recovers at {spot} ({off_team} ball)"
                    result.description += (
                        f' | Recovery roll {recovery_roll}: offense keeps possession'
                        f' | Return roll {return_dice}: chart "{int_return_result}"'
                        f' ({return_yards} yard advance)'
                    )
                    if chain.notes:
                        result.description += " | " + "; ".join(chain.notes)
                    if "reroll" in return_desc or len(chain.trace) > 1:
                        result.description += f" ({return_desc})"

                    # Add fumble return event to transaction for offense recovery rolls 17-19
                    if txn:
                        txn.add_event(
                            create_return_event(
                                event_type=EventType.FUMBLE_RETURN,
                                return_roll=return_dice,
                                return_desc=return_desc,
                                return_yards=return_yards,
                                chart_result=str(int_return_result),
                                acting_team=off_team,
                            )
                        )
                else:
                    # Normal offense recovery without return
                    # Preserve existing description (e.g., "BAD SNAP") if set, otherwise use fumble description
                    if not result.description or result.description.startswith("FUMBLE!"):
                        spot = format_field_position_with_team(fumble_spot, off_team, def_team)
                        result.description = f"FUMBLE! {yards} yards before fumble - Offense recovers at {spot} ({off_team} ball)"
                    result.description += f" | Recovery: {recovery_roll}"

                # The line to gain is measured from the final recovery/advance spot.
                final_position = self.state.ball_position
                net_yards = yards + result.fumble_return_yards
                if not touchdown and not safety and not turnover:
                    if net_yards >= ytg_before:
                        first_down = True
                        self.state.down = 1
                        self.state.yards_to_go = min(10, 100 - final_position)
                        self.state.offense_stats.first_downs += 1
                    elif down_before == 4:
                        turnover = True
                        self.state.switch_possession()
                        self.state.ball_position = 100 - final_position
                    else:
                        # Return-chain application initializes a new series; an own
                        # recovery short of the sticks must consume the original down.
                        self.state.down = down_before
                        self.state.next_down()
                        self.state.yards_to_go = max(1, ytg_before - net_yards)

                if result.fumble_return_dice:
                    spot = format_field_position_with_team(fumble_spot, off_team, def_team)
                    end_spot = format_field_position_with_team(
                        new_position, off_team, def_team
                    )
                    net_description = (
                        f"net gain {net_yards} yards" if net_yards >= 0
                        else f"net loss {-net_yards} yards"
                    )
                    marker = (
                        " SAFETY!" if safety
                        else " FIRST DOWN!" if first_down
                        else " TURNOVER ON DOWNS!" if turnover else ""
                    )
                    result.rule_explanation = (
                        f"{yards} yards before fumble. "
                        f"Recovery roll {recovery_roll} allows an interception-chart advance. "
                        f"Fumble at {spot}, recovered by {off_team}, "
                        f"advanced {result.fumble_return_yards} yards to {end_spot} "
                        f"({net_description}).{marker}"
                    )
                else:
                    spot = format_field_position_with_team(fumble_spot, off_team, def_team)
                    net_description = (f"net gain {net_yards} yards" if net_yards >= 0
                                       else f"net loss {-net_yards} yards")
                    result.rule_explanation = (
                        f"{yards} yards before fumble. Fumble at {spot}, "
                        f"recovered by {off_team} at the spot ({net_description})."
                    )
            else:
                # Defense recovers - fumble lost
                turnover = True
                fumble_spot_defense = 100 - fumble_spot

                # Check for special return on recovery rolls 37, 38, 39
                if recovery_roll in [37, 38, 39]:
                    offense_home = self.state.is_home_possession
                    chain = self._resolve_return_chain(
                        not offense_home, fumble_spot_defense,
                        self.state.defense_team.special_teams.interception_return, "Ret",
                    )
                    return_dice = chain.first_roll
                    int_return_result = chain.first_cell
                    return_desc = " | ".join(chain.trace)
                    result.fumble_return_dice = return_dice
                    if chain.offsetting:
                        # Offsetting fouls on the return nullify the whole play.
                        result.replay_down = True
                        self.state.ball_position = ball_pos_before
                        result.description = (
                            "FUMBLE nullified by OFFSETTING PENALTIES on the return - "
                            f"replay the down ({return_desc})"
                        )
                        result.rule_explanation = result.description
                        return (False, False, False, False)
                    self._record_turnover(interception=False)
                    touchdown = self._apply_return_chain(chain, accept_choice=False)
                    safety = chain.spot <= 0
                    turnover = self.state.is_home_possession != offense_home
                    if touchdown:
                        result.scoring_team = self.state.possession_team.peripheral.short_name
                        self.state.ball_position = 97
                    return_yards = (chain.spot - fumble_spot_defense) if turnover else 0
                    # Preserve existing description (e.g., "BAD SNAP") if set, otherwise use fumble description
                    if not result.description or result.description.startswith("FUMBLE!"):
                        if touchdown and turnover:
                            result.description = f"FUMBLE! {yards} yards before fumble - Defense recovers at the {fumble_spot} - Returned for a TOUCHDOWN! ({def_team} ball)"
                        else:
                            result.description = f"FUMBLE! {yards} yards before fumble - Defense recovers at the {fumble_spot} - Returned {return_yards} yards ({def_team} ball)"
                    result.description += f" | Recovery: {recovery_roll}→{int_return_result}"
                    if chain.notes:
                        result.description += " | " + "; ".join(chain.notes)
                    if "reroll" in return_desc or len(chain.trace) > 1:
                        result.description += f" ({return_desc})"

                    result.fumble_return_yards = return_yards

                    # Add fumble return event to transaction
                    if txn:
                        txn.add_event(
                            create_return_event(
                                event_type=EventType.FUMBLE_RETURN,
                                return_roll=return_dice,
                                return_desc=return_desc,
                                return_yards=return_yards,
                                chart_result=str(int_return_result),
                                acting_team=def_team,
                            )
                        )
                else:
                    # Normal fumble recovery by defense - no return
                    self._record_turnover(interception=False)
                    self.state.switch_possession()
                    self.state.ball_position = fumble_spot_defense
                    # Preserve existing description (e.g., "BAD SNAP") if set, otherwise use fumble description
                    if not result.description or result.description.startswith("FUMBLE!"):
                        result.description = f"FUMBLE! {yards} yards before fumble - Defense recovers at the {fumble_spot} ({def_team} ball)"
                    result.description += f" | Recovery: {recovery_roll}"

                    # Add fumble return event with 0 yards to transaction
                    if txn:
                        txn.add_event(
                            create_return_event(
                                event_type=EventType.FUMBLE_RETURN,
                                return_roll=0,
                                return_desc="",
                                return_yards=0,
                                chart_result="0",
                                acting_team=def_team,
                            )
                        )

        # Offensive recovery touchdowns count as one scrimmage first down.
        # Defensive recovery scores never count for either offense.
        if touchdown and offense_recovers:
            self.state.offense_stats.first_downs += 1

        # Store recovery info
        result.fumble_recovery_roll = recovery_roll
        result.fumble_spot = min(fumble_spot, 99)
        result.fumble_recovered = offense_recovers
        result.fumble_resolved = True  # Mark as resolved so we don't re-roll on penalty acceptance

        return (turnover, touchdown, safety, first_down)

    @staticmethod
    def _credited_scrimmage_yards(result: PlayResult, yards: int, ball_position: int) -> int:
        """Limit offensive gains to the goal line, preserving raw chart data."""
        if result.result_type == ResultType.TOUCHDOWN:
            return 100 - ball_position
        if result.result_type in (ResultType.YARDS, ResultType.BREAKAWAY, ResultType.QB_SCRAMBLE):
            return min(yards, 100 - ball_position)
        return yards

    @staticmethod
    def _record_scrimmage_yardage(
        stats: TeamStats, play_type: PlayType, result: PlayResult,
        yards: int, ball_position: int,
    ) -> None:
        """Credit signed offensive yardage to the team that snapped the ball.

        Return yardage after a defensive recovery/interception is not offense.
        QB-time identifies a passer fumble: at/behind the line it is a sack,
        beyond the line it is rushing. Other fumbles retain the play category.
        """
        if result.result_type not in (
            ResultType.YARDS, ResultType.BREAKAWAY, ResultType.TOUCHDOWN,
            ResultType.FUMBLE, ResultType.QB_SCRAMBLE, ResultType.SACK,
        ):
            return
        credited_yards = max(-ball_position, min(yards, 100 - ball_position))
        stats.total_yards += credited_yards
        qt_fumble = result.result_type == ResultType.FUMBLE and result.qb_scramble_dice > 0
        is_sack = (
            result.result_type == ResultType.SACK
            or (result.result_type == ResultType.QB_SCRAMBLE and yards < 0)
            or (qt_fumble and result.yards <= 0)
        )
        if is_sack:
            loss = min(max(0, -result.yards), ball_position)
            stats.sacks += 1
            stats.sack_yards += loss
            # Any offensive recovery advance is separate from the sack loss.
            stats.rushing_yards += credited_yards + loss
        elif result.result_type == ResultType.QB_SCRAMBLE or qt_fumble:
            stats.rushing_yards += credited_yards
        elif play_type in (
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS,
            PlayType.SCREEN, PlayType.TE_SHORT_LONG, PlayType.HAIL_MARY,
        ):
            stats.passing_yards += credited_yards
        else:
            stats.rushing_yards += credited_yards

    def run_play(
        self,
        play_type: PlayType,
        defense_type: DefenseType,
        out_of_bounds_designation: bool = False,
        in_bounds_designation: bool = False,
        punt_short_drop: bool = False,
        punt_coffin_corner_yards: int = 0,
        no_huddle: bool = False,
    ) -> PlayOutcome:
        """
        Execute an offensive play.

        Args:
            play_type: The offensive play to run
            defense_type: The defensive formation
            out_of_bounds_designation: If True, guarantees 10-sec play but costs 5 yards
            in_bounds_designation: If True, keeps clock running but costs 5 yards
            punt_short_drop: If True, apply short-drop punt rules
            punt_coffin_corner_yards: Yards to subtract from punt (coffin corner)

        Returns:
            PlayOutcome with full details
        """
        if self.state.game_over and not self._conversion_in_progress:
            raise ValueError("Game is over")
        if not self._conversion_in_progress:
            self._record_play_start()

        # Consume this extension before resolving the play. An accepted defensive
        # penalty can then award a new untimed down; otherwise _use_time ends the period.
        if self.state.time_remaining <= 0 and self.has_untimed_down():
            self.clear_untimed_down()

        # Out of bounds designation cannot be used on punts
        if out_of_bounds_designation and play_type == PlayType.PUNT:
            out_of_bounds_designation = False

        # Handle special teams
        if play_type == PlayType.PUNT:
            return self._handle_punt(
                short_drop=punt_short_drop, coffin_corner_yards=punt_coffin_corner_yards
            )
        elif play_type == PlayType.FIELD_GOAL:
            return self._handle_field_goal()
        elif play_type == PlayType.QB_SNEAK:
            return self._handle_qb_sneak()
        elif play_type == PlayType.HAIL_MARY:
            return self._handle_hail_mary()
        elif play_type == PlayType.SPIKE_BALL:
            return self._handle_spike_ball()
        elif play_type == PlayType.QB_KNEEL:
            return self._handle_qb_kneel()

        field_pos_before = self.state.field_position_str()
        down_before = self.state.down
        ball_pos_before = self.state.ball_position
        offense_stats = self.state.offense_stats

        # Resolve the play using charts
        result = resolve_play(
            self.state.possession_team, self.state.defense_team, play_type, defense_type
        )
        self._record_offensive_call(play_type)

        # Process the result
        yards = result.yards
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False
        turnover_on_downs = False
        defensive_penalty = False

        # Apply Out of Bounds designation penalty (-5 yards)
        # Per rules: 5 yards subtracted AFTER combining offense/defense results
        # NOT subtracted from: penalties, incomplete passes, TD results, or already out of bounds
        if out_of_bounds_designation:
            # Check if penalty should NOT be applied
            skip_oob_penalty = (
                result.result_type
                in [
                    ResultType.PENALTY_OFFENSE,
                    ResultType.PENALTY_DEFENSE,
                    ResultType.PASS_INTERFERENCE,
                    ResultType.INCOMPLETE,
                    ResultType.TOUCHDOWN,
                ]
                or result.touchdown
                or result.out_of_bounds  # Already out of bounds anyway
            )
            if not skip_oob_penalty and yards > 0:
                yards -= 5
                result.description += " (Out of Bounds designation: -5 yards)"

        # Apply In Bounds designation penalty (-5 yards)
        # Per rules: 5 yards subtracted from plays NOT otherwise in bounds
        # NOT subtracted from: penalties, incomplete passes, TD results, or already in bounds
        if in_bounds_designation:
            # Check if penalty should NOT be applied
            skip_ib_penalty = (
                result.result_type
                in [
                    ResultType.PENALTY_OFFENSE,
                    ResultType.PENALTY_DEFENSE,
                    ResultType.PASS_INTERFERENCE,
                    ResultType.INCOMPLETE,
                    ResultType.TOUCHDOWN,
                ]
                or result.touchdown
                or not result.out_of_bounds  # Already in bounds anyway
            )
            if not skip_ib_penalty and yards > 0:
                yards -= 5
                result.description += " (In Bounds designation: -5 yards)"
                result.out_of_bounds = False  # Force in bounds

        yards = self._credited_scrimmage_yards(result, yards, ball_pos_before)

        # Handle different result types
        if result.result_type == ResultType.INTERCEPTION:
            # Use centralized interception handler
            turnover, touchdown, safety = self._handle_interception(
                result, self.state.ball_position, yards
            )
            # INT depth identifies the defensive catch spot; it is never
            # offensive scrimmage yardage in the completed outcome.
            yards = 0

        elif result.result_type == ResultType.FUMBLE:
            # Use centralized fumble handler
            turnover, touchdown, safety, first_down = self._handle_fumble(
                result, self.state.ball_position, yards, down_before, self.state.yards_to_go
            )
            if result.fumble_recovered:
                yards += result.fumble_return_yards
                if touchdown:
                    yards = min(yards, 100 - ball_pos_before)

        elif result.result_type == ResultType.SACK:
            self.state.ball_position += yards  # yards is negative
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            else:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.QB_SCRAMBLE:
            # QB scramble - treat like a run play
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards, qb_scramble=True)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.PENALTY_OFFENSE:
            # Full Feature Method: Roll dice to determine actual penalty yardage
            # Derive play_type string for no-huddle bad snap yardage
            nh_play_type = (
                "punt"
                if play_type == PlayType.PUNT
                else ("field_goal" if play_type == PlayType.FIELD_GOAL else "normal")
            )
            ball_pos_numeric = self.state.ball_position
            penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                result.raw_result,
                ball_pos_numeric,
                yards_gained=0,  # No gain on penalty plays
                is_return=False,
                yards_to_go=self.state.yards_to_go,
                down=self.state.down,
                no_huddle=no_huddle,
                play_type=nh_play_type,
            )

            if penalty_result.is_bad_snap:
                # No-huddle bad snap: convert penalty to fumble
                fumble_yards = -penalty_result.fumble_yards  # Negative = behind LOS
                result.description = penalty_result.description
                turnover, touchdown, safety, first_down = self._handle_fumble(
                    result,
                    self.state.ball_position,
                    fumble_yards,
                    down_before,
                    self.state.yards_to_go,
                )
            else:
                self.state.offense_stats.penalties += 1
                self.state.offense_stats.penalty_yards += abs(new_pos - ball_pos_numeric)
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                # Update result description with penalty details
                result.description = penalty_result.description
                yards = new_pos - ball_pos_numeric  # Actual enforced distance.
                if self.state.ball_position <= 0:
                    safety = True
                    self._score_safety()

        elif result.result_type == ResultType.PENALTY_DEFENSE:
            # Full Feature Method: Roll dice to determine actual penalty yardage
            nh_play_type = (
                "punt"
                if play_type == PlayType.PUNT
                else ("field_goal" if play_type == PlayType.FIELD_GOAL else "normal")
            )
            ball_pos_numeric = self.state.ball_position
            penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                result.raw_result,
                ball_pos_numeric,
                yards_gained=0,  # No gain on penalty plays
                is_return=False,
                yards_to_go=self.state.yards_to_go,
                down=self.state.down,
                no_huddle=no_huddle,
                play_type=nh_play_type,
            )

            if penalty_result.is_false_start:
                # No-huddle false start: DEF penalty flipped to OFF 5
                self.state.offense_stats.penalties += 1
                self.state.offense_stats.penalty_yards += abs(new_pos - ball_pos_numeric)
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                result.description = penalty_result.description
                yards = new_pos - ball_pos_numeric
            else:
                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += abs(new_pos - ball_pos_numeric)
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                first_down = got_first
                # Update result description with penalty details
                result.description = penalty_result.description
                yards = new_pos - ball_pos_numeric

                defensive_penalty = True

        elif result.result_type == ResultType.PASS_INTERFERENCE:
            # PI is special: always automatic first down, can exceed half-distance
            # Per VI-12-E-iv: If PI spot is in/beyond defender's end zone, 1st and Goal at the 1
            ball_pos_numeric = self.state.ball_position
            pi_spot = ball_pos_numeric + yards

            if pi_spot >= 100:
                # PI in or beyond end zone = 1st and Goal at the 1
                new_pos = 99  # 1 yard from goal line
                new_down = 1
                new_ytg = 1
                result.description = "Pass interference in end zone - 1st and Goal at the 1"
            else:
                new_pos, new_down, new_ytg = resolve_pass_interference(yards, ball_pos_numeric)
                result.description = f"Pass interference, {yards} yards - automatic first down"

            self.state.defense_stats.penalties += 1
            yards = new_pos - ball_pos_numeric
            self.state.defense_stats.penalty_yards += yards
            self.state.ball_position = new_pos
            self.state.down = new_down
            self.state.yards_to_go = new_ytg
            first_down = True

            defensive_penalty = True

        elif result.result_type == ResultType.TOUCHDOWN:
            touchdown = True
            self.state.ball_position = 100
            self._score_touchdown(play_type, yards)

        elif result.result_type in [ResultType.YARDS, ResultType.BREAKAWAY]:
            # Normal yardage result
            first_down = self.state.advance_ball(yards)

            # Check for touchdown
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards)
            # Check for safety
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down and not turnover:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.INCOMPLETE:
            # Incomplete pass - no yardage, next down
            turnover_on_downs = self.state.next_down()

        # Resolve possession/scoring first, but credit the original offense.
        self._record_scrimmage_yardage(offense_stats, play_type, result, yards, ball_pos_before)

        if (first_down or (touchdown and not turnover)) and result.result_type != ResultType.FUMBLE:
            self.state.offense_stats.first_downs += 1

        if touchdown and not turnover:
            result.description = f"{self.state.scoring_plays[-1].description} | {result.description}"

        outcome = PlayOutcome(
            play_type=play_type,
            defense_type=defense_type,
            result=result,
            yards_gained=yards,
            turnover=turnover,
            turnover_on_downs=turnover_on_downs or (
                turnover and result.fumble_recovered and not touchdown and not safety
            ),
            touchdown=touchdown,
            safety=safety,
            first_down=first_down,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description,
        )

        self.play_log.append(outcome)

        # Per official rules: play is NOT out of bounds if defense overrules or if fumble
        # Defense overrules when their modifier is used (defense_modifier is set)
        is_out_of_bounds = result.out_of_bounds
        if result.defense_modifier:
            is_out_of_bounds = False  # Defense overruled
        if result.result_type == ResultType.FUMBLE:
            is_out_of_bounds = False  # Fumble negates out of bounds
        if result.result_type == ResultType.SACK:
            is_out_of_bounds = False  # Sacks can't go out of bounds

        # Out of Bounds designation guarantees 10-second play (but not on sacks)
        # This bypasses the in_final_minutes gate in _use_time since the player
        # explicitly paid 5 yards for the clock benefit
        forced_10_sec = False
        if out_of_bounds_designation and result.result_type != ResultType.SACK:
            is_out_of_bounds = True
            forced_10_sec = True

        # In Bounds designation forces clock to keep running
        if in_bounds_designation:
            is_out_of_bounds = False
            forced_10_sec = False

        # No huddle reduces play time from ~35 sec to ~20 sec
        if getattr(result, "replay_down", False):
            play_seconds = 10.0  # A play nullified by offsetting fouls takes ten seconds.
        elif forced_10_sec:
            play_seconds = 10.0
        elif no_huddle:
            play_seconds = random.uniform(15, 25)
        else:
            play_seconds = random.uniform(25, 45)

        self._use_time(
            play_seconds, out_of_bounds=is_out_of_bounds, defensive_penalty=defensive_penalty
        )
        if defensive_penalty:
            result.description = self.check_untimed_down_for_defensive_penalty(result.description)
            outcome.description = result.description

        return outcome

    def run_play_with_penalty_procedure(
        self,
        play_type: PlayType,
        defense_type: DefenseType,
        out_of_bounds_designation: bool = False,
        in_bounds_designation: bool = False,
        punt_short_drop: bool = False,
        punt_coffin_corner_yards: int = 0,
        no_huddle: bool = False,
        call_spike: bool = False,
        call_timeout: bool = False,
    ) -> PlayOutcome:
        """
        Execute an offensive play with full penalty procedure per Paydirt rules.

        PENALTY PROCEDURE:
        i. When a penalty occurs, offense rerolls (defense keeps original)
        ii. Offended team chooses: play result (down counts) OR penalty (down replayed)
        iii. If PI, no rerolls - defensive result cancelled, incomplete pass

        POST-PLAY MODIFIERS:
        - call_spike: If True, apply spike modifier after play (caps play + spike at 20 sec)
        - call_timeout: If True, apply timeout after play (reduces play time to 10 sec)

        Returns:
            PlayOutcome with penalty_choice populated if a penalty occurred.
            If pending_penalty_decision is True, caller must call apply_penalty_decision().
        """
        if self.state.game_over:
            raise ValueError("Game is over")
        self._record_play_start()

        # Special teams don't use penalty procedure
        if play_type in [
            PlayType.PUNT,
            PlayType.FIELD_GOAL,
            PlayType.QB_SNEAK,
            PlayType.HAIL_MARY,
            PlayType.SPIKE_BALL,
            PlayType.QB_KNEEL,
        ]:
            return self.run_play(
                play_type,
                defense_type,
                out_of_bounds_designation,
                in_bounds_designation,
                punt_short_drop=punt_short_drop,
                punt_coffin_corner_yards=punt_coffin_corner_yards,
                no_huddle=no_huddle,
            )

        # The engine, not its callers, owns the lifetime of an untimed down.
        if self.state.time_remaining <= 0 and self.has_untimed_down():
            self.clear_untimed_down()

        # Capture time before play for spike/timeout calculations
        time_before_play = self.state.time_remaining
        quarter_before_play = self.state.quarter
        offense_was_home = self.state.is_home_possession
        two_minute_warning_before = self.state.two_minute_warning_called
        timeouts_before_play = (self.state.home_timeouts, self.state.away_timeouts)
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down
        ball_pos_before = self.state.ball_position
        ytg_before = self.state.yards_to_go

        # Use the new penalty procedure
        penalty_choice = resolve_play_with_penalties(
            self.state.possession_team, self.state.defense_team, play_type, defense_type
        )
        self._record_offensive_call(play_type)

        # Check if there are any penalties to decide on
        has_penalties = len(penalty_choice.penalty_options) > 0

        if has_penalties and not penalty_choice.offsetting:
            # There's a penalty and the offended team gets a choice
            # Return the outcome with pending decision - don't apply game state changes yet
            outcome = PlayOutcome(
                play_type=play_type,
                defense_type=defense_type,
                result=penalty_choice.play_result,
                yards_gained=penalty_choice.play_result.yards,
                turnover=penalty_choice.play_result.turnover,
                touchdown=False,
                projected_touchdown=(
                    penalty_choice.play_result.touchdown
                    or penalty_choice.play_result.result_type == ResultType.TOUCHDOWN
                    or (not penalty_choice.play_result.turnover
                        and penalty_choice.play_result.result_type in (
                            ResultType.YARDS, ResultType.BREAKAWAY, ResultType.QB_SCRAMBLE)
                        and self.state.ball_position + (
                            penalty_choice.play_result.offense_yards
                            if (penalty_choice.play_result.defense_modifier or "").startswith("DEF")
                            else penalty_choice.play_result.yards) >= 100)),
                field_position_before=field_pos_before,
                down_before=down_before,
                description=penalty_choice.play_result.description,
                penalty_choice=penalty_choice,
                pending_penalty_decision=True,
                no_huddle=no_huddle,
            )
            return outcome

        elif penalty_choice.offsetting:
            # Offsetting penalties - replay the down, 10 seconds elapse
            self._use_time(10, defensive_penalty=True)
            description = self.check_untimed_down_for_defensive_penalty(
                "Offsetting penalties - down replayed"
            )
            outcome = PlayOutcome(
                play_type=play_type,
                defense_type=defense_type,
                result=penalty_choice.play_result,
                yards_gained=0,
                field_position_before=field_pos_before,
                field_position_after=field_pos_before,
                down_before=down_before,
                down_after=down_before,
                description=description,
                penalty_choice=penalty_choice,
                pending_penalty_decision=False,
            )
            self.play_log.append(outcome)
            return outcome

        else:
            # No penalties - process normally using existing run_play logic
            # Restore state and call run_play (which will re-roll, but that's acceptable)
            # Actually, we should use the result we already have
            outcome = self._apply_play_result(
                play_type,
                defense_type,
                penalty_choice.play_result,
                field_pos_before,
                down_before,
                ball_pos_before,
                ytg_before,
                out_of_bounds_designation,
                in_bounds_designation,
                no_huddle=no_huddle,
            )

            # Apply post-play modifiers (timeout or spike)
            # Note: Only one modifier should be applied - timeout takes precedence
            if call_timeout and not outcome.touchdown and not outcome.turnover:
                self._apply_requested_timeout(
                    outcome, timeout_is_home=offense_was_home,
                    time_before_play=time_before_play, quarter_before_play=quarter_before_play,
                    offense_was_home=offense_was_home,
                    two_minute_warning_before=two_minute_warning_before,
                    timeouts_before_play=timeouts_before_play,
                )

            elif call_spike and not outcome.touchdown and not outcome.turnover:
                play_seconds = (time_before_play - self.state.time_remaining) * 60
                should_apply, _ = self._should_apply_spike_after_play(outcome, play_seconds)
                if should_apply:
                    self._apply_spike(time_before_play, quarter_before_play)
                    outcome.spike_used = True

            return outcome

    def get_penalty_safety_preview(self, outcome: PlayOutcome) -> str | None:
        """Describe a retained scrimmage loss that would score a safety.

        Args:
            outcome: Pending penalty choice, before applying either option.

        Returns:
            Engine-generated safety text, or None for other play results.
            This query does not change game state, consume dice, or resolve
            fumble recoveries/interception returns as ordinary scrimmage losses.
        """
        if not outcome.pending_penalty_decision or not outcome.penalty_choice:
            return None
        if outcome.play_type in (PlayType.FIELD_GOAL, PlayType.PUNT, PlayType.KICKOFF):
            return None

        result = outcome.penalty_choice.play_result
        yards = result.yards
        result_type = result.result_type
        # Match the retained yardage used by apply_penalty_decision when a
        # defensive penalty's yardage replaced the original offensive result.
        if (result.defense_modifier or "").startswith("DEF") and result.offense_yards != yards:
            yards = result.offense_yards
            result_type = ResultType.YARDS
        if result.turnover or result.touchdown or result_type not in (
            ResultType.YARDS, ResultType.BREAKAWAY, ResultType.QB_SCRAMBLE, ResultType.SACK,
        ):
            return None
        if self.state.ball_position + yards > 0:
            return None

        offense = self.state.possession_team.peripheral.short_name
        defense = self.state.defense_team.peripheral.short_name
        return f"SAFETY! {offense} concedes 2 points to {defense}"

    def apply_penalty_decision(
        self, outcome: PlayOutcome, accept_play: bool, penalty_index: int = 0
    ) -> PlayOutcome:
        """
        Apply the offended team's penalty decision.

        Args:
            outcome: The PlayOutcome with pending_penalty_decision=True
            accept_play: True to accept play result (down counts), False to accept penalty
            penalty_index: If accepting penalty and multiple options, which one (0-indexed)

        Returns:
            Updated PlayOutcome with game state applied
        """
        if not outcome.pending_penalty_decision or not outcome.penalty_choice:
            return outcome

        penalty_choice = outcome.penalty_choice
        field_pos_before = outcome.field_position_before
        down_before = outcome.down_before

        if accept_play:
            # Accept the play result - down counts
            # Use original offense result if defense committed penalty
            play_result = penalty_choice.play_result
            # When defense commits a penalty (DEF X), the priority chart returns penalty yards
            # as final_yards, but offense_yards stores the original offense result.
            # Check if defense_modifier indicates a defensive penalty was committed.
            defense_mod = play_result.defense_modifier or ""
            has_def_penalty = defense_mod.startswith("DEF")
            if has_def_penalty and play_result.offense_yards != play_result.yards:
                # Defense committed penalty - use original offense yards
                # Create a new PlayResult with the correct yardage
                from .play_resolver import ResultType

                original_yards = play_result.offense_yards
                play_result = play_result.__class__(
                    result_type=ResultType.YARDS,
                    yards=original_yards,
                    description=f"Play result stands: {original_yards} yards",
                    turnover=play_result.turnover,
                    touchdown=play_result.touchdown,
                    raw_result=play_result.raw_result,
                    dice_roll=play_result.dice_roll,
                    defense_modifier=play_result.defense_modifier,
                    out_of_bounds=play_result.out_of_bounds,
                    offense_yards=original_yards,
                )

            return self._apply_play_result(
                outcome.play_type,
                outcome.defense_type,
                play_result,
                field_pos_before,
                down_before,
                self.state.ball_position,
                self.state.yards_to_go,
                out_of_bounds_designation=False,
                in_bounds_designation=False,
                no_huddle=outcome.no_huddle,
            )
        else:
            # Accept the penalty - down is replayed
            if penalty_index >= len(penalty_choice.penalty_options):
                penalty_index = 0

            penalty_opt = penalty_choice.penalty_options[penalty_index]

            # Resolve the penalty using penalty_handler
            ball_pos_numeric = self.state.ball_position

            if penalty_opt.penalty_type == "PI":
                # Pass interference - special handling
                pi_spot = ball_pos_numeric + penalty_opt.yards
                if pi_spot >= 100:
                    new_pos = 99
                    new_down = 1
                    new_ytg = 1
                    description = "Pass interference in end zone - 1st and Goal at the 1"
                else:
                    new_pos, new_down, new_ytg = resolve_pass_interference(
                        penalty_opt.yards, ball_pos_numeric
                    )
                    description = (
                        f"Pass interference, {penalty_opt.yards} yards - automatic first down"
                    )

                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += new_pos - ball_pos_numeric
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                first_down = True
                yards = new_pos - ball_pos_numeric
            elif penalty_opt.penalty_type == "OFF":
                # Offensive penalty - defense was offended
                # Use chart yardage if explicitly specified (e.g., "OFF 10")
                penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                    penalty_opt.raw_result,
                    ball_pos_numeric,
                    yards_gained=0,
                    is_return=False,
                    yards_to_go=self.state.yards_to_go,
                    down=self.state.down,
                    chart_yards=penalty_opt.yards,
                    auto_first_down=penalty_opt.auto_first_down,
                )
                self.state.offense_stats.penalties += 1
                self.state.offense_stats.penalty_yards += abs(new_pos - ball_pos_numeric)
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                description = penalty_result.description
                yards = new_pos - ball_pos_numeric
                first_down = False

            elif penalty_opt.penalty_type == "DEF":
                # Defensive penalty - offense was offended
                # Use chart yardage if explicitly specified (e.g., "DEF 15")
                penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                    penalty_opt.raw_result,
                    ball_pos_numeric,
                    yards_gained=0,
                    is_return=False,
                    yards_to_go=self.state.yards_to_go,
                    down=self.state.down,
                    chart_yards=penalty_opt.yards,
                    auto_first_down=penalty_opt.auto_first_down,
                )
                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += abs(new_pos - ball_pos_numeric)
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                first_down = got_first
                description = penalty_result.description
                yards = new_pos - ball_pos_numeric

            else:
                # Unknown penalty type
                description = f"Penalty: {penalty_opt.description}"
                yards = 0
                first_down = False

            if first_down:
                self.state.offense_stats.first_downs += 1

            play_seconds = random.uniform(15, 25) if outcome.no_huddle else random.uniform(25, 45)
            defensive_penalty = penalty_opt.penalty_type in ("DEF", "PI")
            self._use_time(play_seconds, defensive_penalty=defensive_penalty)
            if defensive_penalty:
                description = self.check_untimed_down_for_defensive_penalty(description)

            # Build the final outcome
            final_outcome = PlayOutcome(
                play_type=outcome.play_type,
                defense_type=outcome.defense_type,
                result=outcome.result,
                yards_gained=yards,
                first_down=first_down,
                field_position_before=field_pos_before,
                field_position_after=self.state.field_position_str(),
                down_before=down_before,
                down_after=self.state.down,
                description=description,
                penalty_choice=penalty_choice,
                pending_penalty_decision=False,
                penalty_applied=True,  # Penalty was accepted
            )

            self.play_log.append(final_outcome)

            return final_outcome

    def _apply_play_result(
        self,
        play_type: PlayType,
        defense_type: DefenseType,
        result: PlayResult,
        field_pos_before: str,
        down_before: int,
        ball_pos_before: int,
        ytg_before: int,
        out_of_bounds_designation: bool,
        in_bounds_designation: bool,
        no_huddle: bool = False,
    ) -> PlayOutcome:
        """
        Apply a play result to the game state.

        This is a helper method that applies the result of a play (after penalty decisions)
        to the game state. It handles all result types (yards, turnovers, TDs, etc.)
        """
        offense_stats = self.state.offense_stats
        yards = result.yards
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False
        turnover_on_downs = False

        # Apply Out of Bounds designation penalty (-5 yards)
        # Per rules: 5 yards subtracted AFTER combining offense/defense results
        # NOT subtracted from: penalties, incomplete passes, TD results, or already out of bounds
        if out_of_bounds_designation:
            skip_oob_penalty = (
                result.result_type
                in [
                    ResultType.PENALTY_OFFENSE,
                    ResultType.PENALTY_DEFENSE,
                    ResultType.PASS_INTERFERENCE,
                    ResultType.INCOMPLETE,
                    ResultType.TOUCHDOWN,
                ]
                or result.touchdown
                or result.out_of_bounds
            )
            if not skip_oob_penalty and yards > 0:
                yards = max(0, yards - 5)
                result.description += " (Out of Bounds designation: -5 yards)"

        # Apply In Bounds designation penalty (-5 yards)
        if in_bounds_designation:
            skip_ib_penalty = (
                result.result_type
                in [
                    ResultType.PENALTY_OFFENSE,
                    ResultType.PENALTY_DEFENSE,
                    ResultType.PASS_INTERFERENCE,
                    ResultType.INCOMPLETE,
                    ResultType.TOUCHDOWN,
                ]
                or result.touchdown
                or not result.out_of_bounds
            )
            if not skip_ib_penalty and yards > 0:
                yards = max(0, yards - 5)
                result.description += " (In Bounds designation: -5 yards)"
                result.out_of_bounds = False

        yards = self._credited_scrimmage_yards(result, yards, ball_pos_before)

        # Build transaction for this play
        txn = PlayTransaction()
        off_team = self.state.possession_team.peripheral.short_name

        # Add chart lookup event
        txn.add_event(
            create_chart_lookup_event(
                offense_roll=result.dice_roll,
                offense_desc=f"Roll {result.dice_roll}",
                offense_result=result.raw_result,
                defense_row=result.defense_modifier.split("→")[0]
                if "→" in str(result.defense_modifier)
                else "?",
                defense_result=result.defense_modifier,
                priority=result.result_type.value,
                acting_team=off_team,
            )
        )

        # Handle different result types
        if result.result_type == ResultType.INTERCEPTION:
            # Use centralized interception handler
            turnover, touchdown, safety = self._handle_interception(
                result, ball_pos_before, yards, txn
            )

        elif result.result_type == ResultType.FUMBLE:
            # Use centralized fumble handler
            turnover, touchdown, safety, first_down = self._handle_fumble(
                result, ball_pos_before, yards, down_before, ytg_before, txn
            )
            if result.fumble_recovered:
                yards += result.fumble_return_yards
                if touchdown:
                    yards = min(yards, 100 - ball_pos_before)

        elif result.result_type == ResultType.INCOMPLETE:
            turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.QB_SCRAMBLE:
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards, qb_scramble=True)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.SACK:
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.TOUCHDOWN:
            touchdown = True
            self.state.ball_position = 100
            self._score_touchdown(play_type, yards)

        elif result.result_type in [ResultType.YARDS, ResultType.BREAKAWAY]:
            first_down = self.state.advance_ball(yards)

            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        self._record_scrimmage_yardage(offense_stats, play_type, result, yards, ball_pos_before)

        # A touchdown is a statistical first down even on a goal-to-go play.
        # Fumble first downs are recorded in the centralized handler.
        if (first_down or (touchdown and not turnover)) and result.result_type != ResultType.FUMBLE:
            self.state.offense_stats.first_downs += 1

        # Finalize transaction
        txn.turnover = turnover
        txn.touchdown = touchdown
        txn.safety = safety
        txn.first_down = first_down
        txn.yards_gained = yards
        txn.final_ball_position = self.state.ball_position
        txn.final_down = self.state.down
        txn.final_yards_to_go = self.state.yards_to_go
        txn.possession_team = self.state.possession_team.peripheral.short_name
        txn.is_complete = True

        if touchdown and not turnover:
            result.description = f"{self.state.scoring_plays[-1].description} | {result.description}"

        outcome = PlayOutcome(
            play_type=play_type,
            defense_type=defense_type,
            result=result,
            yards_gained=yards,
            turnover=turnover,
            turnover_on_downs=turnover_on_downs or (
                turnover and result.fumble_recovered and not touchdown and not safety
            ),
            touchdown=touchdown,
            safety=safety,
            first_down=first_down,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description,
            transaction=txn,
        )

        self.play_log.append(outcome)

        is_out_of_bounds = result.out_of_bounds
        if result.defense_modifier:
            is_out_of_bounds = False
        if result.result_type == ResultType.FUMBLE:
            is_out_of_bounds = False
        if result.result_type == ResultType.SACK:
            is_out_of_bounds = False  # Sacks can't go out of bounds

        # Out of Bounds designation guarantees 10-second play (but not on sacks)
        # This bypasses the in_final_minutes gate in _use_time since the player
        # explicitly paid 5 yards for the clock benefit
        forced_10_sec = False
        if out_of_bounds_designation and result.result_type != ResultType.SACK:
            is_out_of_bounds = True
            forced_10_sec = True
        if in_bounds_designation:
            is_out_of_bounds = False
            forced_10_sec = False

        # No huddle reduces play time from ~35 sec to ~20 sec
        if getattr(result, "replay_down", False):
            play_seconds = 10.0  # A play nullified by offsetting fouls takes ten seconds.
        elif forced_10_sec:
            play_seconds = 10.0
        elif no_huddle:
            play_seconds = random.uniform(15, 25)
        else:
            play_seconds = random.uniform(25, 45)

        self._use_time(play_seconds, out_of_bounds=is_out_of_bounds)

        return outcome

    def _handle_qb_sneak(self) -> PlayOutcome:
        """
        Handle a QB Sneak play per official rules.

        QB Sneak is used to gain a single yard. Only the box COLOR matters:
        - Green boxes (positive yardage) = 1 yard gain
        - White/Yellow boxes (zero/small/penalty) = No gain
        - Red boxes (fumble results) = Fumble at line of scrimmage

        The defensive result is automatically "No Change" - defense doesn't participate.
        Defensive dice are never rolled.
        """
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down

        # Roll offensive dice only
        dice_roll, _dice_desc = roll_chart_dice()

        # Resolve using QB Sneak rules (box color only)
        result = resolve_qb_sneak(self.state.possession_team.offense, dice_roll)

        yards = result.yards
        turnover = False
        touchdown = False
        safety = False
        first_down = False
        turnover_on_downs = False

        if result.result_type == ResultType.FUMBLE:
            # Fumble at line of scrimmage - use normal fumble handling
            # Roll for fumble recovery
            recovery_roll, _recovery_desc = roll_chart_dice()
            fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range
            offense_recovers = fumble_rec_range[0] <= recovery_roll <= fumble_rec_range[1]

            result.fumble_recovery_roll = recovery_roll
            result.fumble_spot = self.state.ball_position
            result.fumble_recovered = offense_recovers
            result.fumble_resolved = (
                True  # Mark as resolved so we don't re-roll on penalty acceptance
            )

            if offense_recovers:
                # Offense recovers at LOS - no gain, but get another down
                turnover = False
                turnover_on_downs = self.state.next_down()
                result.description = f"QB Sneak - Fumble RECOVERED at LOS (roll {recovery_roll})"
            else:
                # Defense recovers
                turnover = True
                self._record_turnover(interception=False)
                self.state.switch_possession()  # This already flips ball_position
                result.description = (
                    f"QB Sneak - Fumble LOST! Defense recovers (roll {recovery_roll})"
                )
        else:
            # Normal yardage result (0 or 1 yard)
            first_down = self.state.advance_ball(yards)

            # Check for touchdown
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(PlayType.QB_SNEAK, yards)
            # Check for safety (shouldn't happen on QB sneak but handle anyway)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        # Update stats
        if yards > 0 and not turnover:
            self.state.offense_stats.total_yards += yards
            self.state.offense_stats.rushing_yards += yards

        if first_down or (touchdown and not turnover):
            self.state.offense_stats.first_downs += 1

        outcome = PlayOutcome(
            play_type=PlayType.QB_SNEAK,
            defense_type=DefenseType.STANDARD,  # Defense doesn't participate
            result=result,
            yards_gained=yards,
            first_down=first_down,
            touchdown=touchdown,
            turnover_on_downs=turnover_on_downs,
            turnover=turnover,
            safety=safety,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            description=result.description,
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 25))

        return outcome

    def apply_defensive_timeout(
        self,
        outcome: PlayOutcome,
        *,
        time_before_play: float,
        quarter_before_play: int,
        offense_was_home: bool,
        two_minute_warning_before: bool,
        timeouts_before_play: tuple[int, int] | None = None,
    ) -> bool:
        """Request a timeout for the team defending at the original snap.

        Args:
            outcome: Resolved play, after any penalty decision.
            time_before_play: Minutes remaining before the snap.
            quarter_before_play: Period before the snap.
            offense_was_home: Possession before the snap, for timeout ownership.
            two_minute_warning_before: Whether the warning had already occurred.
            timeouts_before_play: Home/away budgets before a possible halftime reset.

        Returns:
            True if a timeout was charged and the play's clock adjusted.
        """
        return self._apply_requested_timeout(
            outcome, timeout_is_home=not offense_was_home,
            time_before_play=time_before_play, quarter_before_play=quarter_before_play,
            offense_was_home=offense_was_home,
            two_minute_warning_before=two_minute_warning_before,
            timeouts_before_play=timeouts_before_play,
        )

    def _apply_requested_timeout(
        self,
        outcome: PlayOutcome,
        *,
        timeout_is_home: bool,
        time_before_play: float,
        quarter_before_play: int,
        offense_was_home: bool,
        two_minute_warning_before: bool,
        timeouts_before_play: tuple[int, int] | None = None,
    ) -> bool:
        """Charge one team's timeout only when the resolved play can save time."""
        if (
            outcome.pending_penalty_decision
            or outcome.penalty_applied
            or outcome.timeout_used
            or outcome.spike_used
            or outcome.touchdown
            or outcome.safety
            or outcome.turnover
            or self.state.is_home_possession != offense_was_home
            or outcome.play_type in (PlayType.PUNT, PlayType.FIELD_GOAL)
            or (not two_minute_warning_before and self.state.two_minute_warning_called)
            or time_before_play * 60 <= 10
        ):
            return False

        play_seconds = (time_before_play - self.state.time_remaining) * 60
        if self.state.quarter == quarter_before_play and play_seconds <= 10 + 1e-6:
            return False
        should_apply, _ = self._should_apply_timeout_after_play(
            outcome, play_seconds, quarter_before_play
        )
        if not should_apply:
            return False

        # A play may already have crossed halftime and reset the timeout budgets.
        # Restore the old half only if an old-half timeout can actually save it.
        crossed_halftime = quarter_before_play == 2 and self.state.quarter == 3
        if crossed_halftime:
            if timeouts_before_play is None:
                return False
            available = timeouts_before_play[0 if timeout_is_home else 1]
            if available <= 0:
                return False
            self.state.home_timeouts, self.state.away_timeouts = timeouts_before_play
            self.state.two_minute_warning_called = two_minute_warning_before
        if not self.state.use_timeout(timeout_is_home):
            return False
        self._apply_timeout(time_before_play, quarter_before_play)
        outcome.timeout_used = True
        return True

    def _should_apply_timeout_after_play(
        self, outcome, play_seconds: float, quarter_before_play: int
    ) -> tuple[bool, str]:
        """
        Check if timeout modifier should be applied after seeing play result.

        Per Paydirt rules, a timeout is wasteful if:
        - Play was incomplete (clock already stopped)
        - Play went out of bounds (clock already at 10 sec)
        - Play_seconds <= 10 (no time would be saved)

        Args:
            outcome: PlayOutcome from the executed play
            play_seconds: Actual seconds used by the play
            quarter_before_play: Quarter before the play started (to detect quarter changes)

        Returns:
            Tuple of (should_apply, message_if_skipped)
        """
        if outcome.result.result_type == ResultType.INCOMPLETE:
            return False, "[Timeout SKIPPED - play was incomplete, clock already stopped]"

        if outcome.result.out_of_bounds:
            return False, "[Timeout SKIPPED - play went out of bounds, clock already at 10 sec]"

        if quarter_before_play != self.state.quarter:
            return True, ""

        if play_seconds <= 10:
            return False, "[Timeout SKIPPED - no time would be saved]"

        return True, ""

    def _should_apply_spike_after_play(self, outcome, play_seconds: float) -> tuple[bool, str]:
        """
        Check if spike modifier should be applied after seeing play result.

        Per Paydirt rules, a spike is wasteful if:
        - Play was incomplete (clock already stopped)
        - Play_seconds <= 3 (no meaningful time would be saved)

        Args:
            outcome: PlayOutcome from the executed play
            play_seconds: Actual seconds used by the play

        Returns:
            Tuple of (should_apply, message_if_skipped)
        """
        if outcome.result.result_type == ResultType.INCOMPLETE:
            return False, "[Spike SKIPPED - clock already stopped]"

        if play_seconds <= 3:
            return False, "[Spike SKIPPED - no time would be saved]"

        return True, ""

    def _apply_timeout(self, time_before_play: float, quarter_before_play: int):
        """
        Apply timeout clock adjustment after a play.

        With a timeout, the play only uses 10 seconds (0.167 minutes) instead of
        the normal play time. If the quarter advanced during the play, revert it
        since the timeout preserves time.

        Args:
            time_before_play: Time remaining before the play started
            quarter_before_play: Quarter number before the play started
        """
        # Timeout means exactly 10 seconds elapse, not the random play time
        # Reset to time_before_play and use exactly 10 seconds
        timeout_seconds = 0.167  # 10 seconds

        time_after_timeout = time_before_play - timeout_seconds
        # Clamp to 0 if less than 1 second remains
        if time_after_timeout < 0.0167:
            time_after_timeout = 0
        self.state.time_remaining = time_after_timeout

        # If quarter advanced during the play but timeout preserves time, revert quarter
        if self.state.quarter > quarter_before_play and time_after_timeout > 0:
            self.state.quarter = quarter_before_play

        # Reopen regulation only if the adjusted clock actually preserves time.
        if time_after_timeout > 0 and self.state.quarter <= 4:
            self.state.game_over = False

    def _apply_spike(self, time_before_play: float, quarter_before_play: int):
        """
        Apply spike clock adjustment after a play.

        Per Paydirt rules, spike + previous play = 20 seconds total.
        If the play used more than 17 seconds, rewind the clock so the
        play effectively used 17 seconds, then add 3 seconds for the spike.
        Total: 20 seconds maximum.

        This allows the two-minute drill: run a play, spike to stop the clock,
        then kick a field goal - all within 20 seconds.

        Args:
            time_before_play: Time remaining before the play started
            quarter_before_play: Quarter number before the play started
        """
        # Spike + play should total 20 seconds max
        # Play gets 17 seconds, spike gets 3 seconds
        max_spike_combo_seconds = 0.333  # 20 seconds (17 for play + 3 for spike)
        spike_seconds = 0.05  # ~3 seconds for the spike itself

        # Calculate how much time the play actually used
        clock_before_spike = self.state.time_remaining
        play_used_seconds = time_before_play - clock_before_spike

        # If the play used more than 17 seconds, cap it
        play_max_seconds = 0.283  # 17 seconds

        if play_used_seconds > play_max_seconds:
            # Rewind: set time to time_before_play - 20 seconds
            time_after_spike = time_before_play - max_spike_combo_seconds
        else:
            # Play used 17 seconds or less, just add spike time
            time_after_spike = self.state.time_remaining - spike_seconds

        # Clamp to 0 if less than 1 second remains
        if time_after_spike < 0.0167:
            time_after_spike = 0

        self.state.time_remaining = time_after_spike

        # If quarter advanced during the play but spike preserves time, revert quarter
        if self.state.quarter > quarter_before_play and time_after_spike > 0:
            self.state.quarter = quarter_before_play

        # A spike cannot reopen a finished game when its adjusted clock is 0:00.
        if time_after_spike > 0 and self.state.quarter <= 4:
            self.state.game_over = False
        elif time_after_spike == 0 and clock_before_spike > 0:
            # The spike itself can consume the final seconds of a live period.
            # Reuse authoritative period/OT/untimed-down handling, without
            # charging additional time or changing the spike down procedure.
            self._use_time(0)

    def _handle_hail_mary(self) -> PlayOutcome:
        """
        Handle a Hail Mary pass per official rules.

        Available at end of half or overtime. Defense is "blank" (no response).

        Dice Total | Result
        -----------|--------
        10-18      | Complete (25 + T1*10 yards downfield)
        19         | Complete (TD)
        20-23, 26-29 | INT (25 + T1*10 yards downfield)
        24-25      | QT (roll again)
        30-38      | INC
        39         | DEF PI (25 + T1*10 yards downfield)
        """
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down

        # Roll offensive dice only - defense doesn't participate
        dice_roll, _dice_desc = roll_chart_dice()

        # Handle QT (Quick Throw) - keep rolling until we get a non-QT result
        while dice_roll in [24, 25]:
            dice_roll, _dice_desc = roll_chart_dice()

        # Resolve using Hail Mary table
        result = resolve_hail_mary(dice_roll, self.state.ball_position)

        yards = self._credited_scrimmage_yards(result, result.yards, self.state.ball_position)
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False
        turnover_on_downs = False

        if result.result_type == ResultType.TOUCHDOWN:
            touchdown = True
            self._score_touchdown(PlayType.HAIL_MARY, yards)
            self.state.ball_position = 97

        elif result.result_type == ResultType.INTERCEPTION:
            # Use centralized interception handler for consistent end zone handling
            turnover, touchdown, safety = self._handle_interception(
                result, self.state.ball_position, yards
            )

        elif result.result_type == ResultType.PASS_INTERFERENCE:
            # PI - automatic first down at spot of foul
            pi_spot = self.state.ball_position + yards
            if pi_spot >= 100:
                # PI in end zone = 1st and Goal at the 1
                self.state.ball_position = 99
                self.state.yards_to_go = 1
            else:
                self.state.ball_position = pi_spot
                self.state.yards_to_go = min(10, 100 - pi_spot)
            self.state.down = 1
            first_down = True
            self.state.defense_stats.penalties += 1
            self.state.defense_stats.penalty_yards += yards
        elif result.result_type == ResultType.YARDS:
            # Completion for yardage
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(PlayType.HAIL_MARY, yards)
            elif not first_down:
                turnover_on_downs = self.state.next_down()

        elif result.result_type == ResultType.INCOMPLETE:
            # Incomplete - next down
            turnover_on_downs = self.state.next_down()

        # Update passing stats
        if yards > 0 and not turnover and result.result_type != ResultType.PASS_INTERFERENCE:
            self.state.offense_stats.total_yards += yards
            self.state.offense_stats.passing_yards += yards

        if first_down or (touchdown and not turnover):
            self.state.offense_stats.first_downs += 1

        outcome = PlayOutcome(
            play_type=PlayType.HAIL_MARY,
            defense_type=DefenseType.STANDARD,  # Defense doesn't participate
            result=result,
            yards_gained=yards,
            first_down=first_down,
            touchdown=touchdown,
            turnover=turnover,
            safety=safety,
            field_position_before=field_pos_before,
            down_before=down_before,
            down_after=self.state.down,
            turnover_on_downs=turnover_on_downs,
            field_position_after=self.state.field_position_str(),
            description=result.description,
        )

        self.play_log.append(outcome)
        self._use_time(
            random.uniform(5, 15),
            defensive_penalty=result.result_type == ResultType.PASS_INTERFERENCE,
        )

        # Only an accepted defensive foul can extend the period, not a clean
        # Hail Mary completion or incompletion that happens to exhaust the clock.
        if result.result_type == ResultType.PASS_INTERFERENCE:
            result.description = self.check_untimed_down_for_defensive_penalty(result.description)
            outcome.description = result.description

        return outcome

    def _handle_spike_ball(self) -> PlayOutcome:
        """
        Handle a spike ball play per official Paydirt rules.

        Spiking the ball is automatic (no dice rolls or charts used).
        - Results in incomplete pass
        - Wastes a down
        - Combined with previous 40-second play, total time is only 20 seconds
        - Avoids the hazards of the quick huddle (no penalty risks)

        Time savings: Normal play (40 sec) + Spike (0 sec effective) = 20 sec total
        vs No Huddle: Previous play reduced to 20 sec, but penalty risks
        """
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down

        # Create the result - automatic incomplete pass
        result = PlayResult(
            result_type=ResultType.INCOMPLETE,
            yards=0,
            description="QB spikes the ball to stop the clock",
            raw_result="SPIKE",
        )

        # Advance to next down - returns True if turnover on downs
        turnover = self.state.next_down()

        if turnover:
            result.description = "QB spikes the ball - TURNOVER ON DOWNS!"

        outcome = PlayOutcome(
            play_type=PlayType.SPIKE_BALL,
            defense_type=DefenseType.STANDARD,  # Defense doesn't matter
            result=result,
            yards_gained=0,
            turnover=turnover,
            turnover_on_downs=turnover,
            touchdown=False,
            safety=False,
            first_down=False,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description,
        )

        self.play_log.append(outcome)

        # Spike uses minimal time - the time savings come from reducing
        # the PREVIOUS play's time from 40 to 20 seconds
        # The spike itself takes essentially no game time
        self._use_time(0.05)  # ~3 seconds for the spike itself

        return outcome

    def can_kneel_out_game(self) -> bool:
        """Whether safe kneels can exhaust regulation without giving up possession.

        Budget only the downs before fourth down: kneels advance the down before
        consuming time. Account for every available defensive timeout and every
        two-yard loss. A timeout reduces a kneel to about ten seconds, so using
        ten as the lower bound is conservative. Overtime, untimed downs, and
        pending scores are deliberately not treated as victory formations.

        Returns:
            True if a kneel-only plan guarantees the offense keeps its lead.
        """
        state = self.state
        offense_leads = (state.home_score > state.away_score if state.is_home_possession
                         else state.away_score > state.home_score)
        if (state.game_over or state.is_overtime or state.quarter != 4
                or not offense_leads or state.time_remaining <= 0
                or state.untimed_down_pending or not 1 <= state.down <= 3
                or not 0 < state.ball_position < 100):
            return False

        for kneels in range(1, 5 - state.down):
            if state.ball_position <= 2 * kneels:
                break  # A later kneel would concede a safety.
            stopped_plays = min(kneels, state.defense_timeouts)
            seconds_available = 40 * kneels - 30 * stopped_plays
            if state.time_remaining * 60 <= seconds_available + 1e-9:
                return True
        return False

    def _handle_qb_kneel(self) -> PlayOutcome:
        """
        Handle a QB Kneel play per official Paydirt rules.

        QB Kneel is used to run out the clock:
        - Automatic 2-yard loss (no dice rolls or charts used)
        - 40 seconds consumed (unless defense calls timeout)
        - Advances to next down
        """
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down
        offense_stats = self.state.offense_stats
        ball_pos_before = self.state.ball_position

        # Automatic 2-yard loss
        yards = -2

        # Check for safety (if at own 1 or 2 yard line)
        safety = False
        new_position = self.state.ball_position + yards
        if new_position <= 0:
            safety = True
            self._score_safety()
            new_position = 20  # After safety, other team gets ball
        else:
            self.state.ball_position = new_position

        # Create the result
        result = PlayResult(
            result_type=ResultType.YARDS,
            yards=yards,
            description="QB takes a knee - intentional 2-yard loss to run out the clock",
            raw_result="KNEEL",
        )

        if safety:
            result.description = "QB takes a knee in end zone - SAFETY!"

        # Advance to next down (unless safety)
        turnover = False
        if not safety:
            turnover = self.state.next_down()
            if turnover:
                result.description = "QB takes a knee - TURNOVER ON DOWNS!"

        self._record_scrimmage_yardage(offense_stats, PlayType.QB_KNEEL, result, yards, ball_pos_before)

        outcome = PlayOutcome(
            play_type=PlayType.QB_KNEEL,
            defense_type=DefenseType.STANDARD,  # Defense doesn't matter
            result=result,
            yards_gained=yards,
            turnover=turnover,
            turnover_on_downs=turnover,
            touchdown=False,
            safety=safety,
            first_down=False,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description,
        )

        self.play_log.append(outcome)

        # QB Kneel uses full 40 seconds (unless defense calls timeout)
        self._use_time(40)  # 40 seconds

        return outcome

    def _punt_keep_result_preview(self, receiving_position: int) -> str:
        """Describe a kept punt result from the receiving team's perspective."""
        receiving_team = self.state.defense_team.peripheral.short_name
        kicking_team = self.state.possession_team.peripheral.short_name
        if receiving_position >= 100:
            return f"{receiving_team} TOUCHDOWN!"
        field_position = format_field_position_with_team(
            clamp_ball_position(receiving_position), receiving_team, kicking_team
        )
        return f"{receiving_team} 1st and 10 at {field_position}"

    def _handle_punt(
        self, short_drop: bool = False, coffin_corner_yards: int = 0, punt_from: int | None = None
    ) -> PlayOutcome:
        """
        Handle a punt play per official Paydirt rules.

        Advanced Punt Options (per advanced rules):
        - Short-Drop Punts: If LOS is inside 5-yard line, defenders get Free All-Out Kick Rush,
          all * and † are deleted, minus yardage returns become 0
        - Coffin-Corner Punts: Can subtract yardage from punt before dice roll.
          If 15+ yards subtracted, punt is automatic out of bounds (no return)

        Args:
            short_drop: If True, apply short-drop punt rules
            coffin_corner_yards: Yards to subtract from punt distance (0 = no coffin corner)
            punt_from: Override field position to punt from (for safety free kick punt)
        """
        field_pos_before = punt_from if punt_from is not None else self.state.ball_position
        down_before = self.state.down
        ytg_before = self.state.yards_to_go
        punting_team = self.state.possession_team
        receiving_team = self.state.defense_team

        # Check for short-drop punt (inside own 5-yard line)
        is_short_drop = short_drop and field_pos_before <= 5

        # Check for coffin corner (automatic OOB if 15+ yards subtracted)
        is_coffin_corner = coffin_corner_yards >= 15

        # Roll for punt distance
        punt_roll, _punt_dice_desc = roll_chart_dice()
        punt_result = punting_team.special_teams.punt.get(punt_roll, "40")

        # Check for special markers
        is_downed = "†" in punt_result or "+" in punt_result  # † = downed/out of bounds
        is_fair_catch = "*" in punt_result  # * = fair catch
        is_blocked = "BK" in punt_result.upper()
        is_penalty = "OFF" in punt_result.upper() or "DEF" in punt_result.upper()

        # Short-drop punt: delete all * and † markers
        if is_short_drop:
            punt_result = punt_result.replace("†", "").replace("*", "").replace("+", "")
            is_downed = False
            is_fair_catch = False

        # Parse punt distance (strip markers)
        punt_clean = punt_result.replace("†", "").replace("*", "").replace("+", "").strip()

        # Handle blocked punt per official rules:
        # - Move ball forward/backward the yards shown
        # - Roll offensive dice for recovery (same as fumble)
        # - Defense gets INT return for blocked kicks lost (rolls 19, 39 = auto TD)
        # - Offense gets INT return for blocked kicks recovered at/behind LOS with rolls 17, 18, 19
        safety = False
        if is_blocked:
            # Extract blocked punt yardage (e.g., "BK -12" means -12 yards)
            try:
                block_yards = int(punt_clean.replace("BK", "").strip())
            except ValueError:
                block_yards = -10

            block_spot = self.state.ball_position + block_yards
            kicking_home = self.state.is_home_possession
            nullified = False

            if block_spot <= 0:
                # Safety - ball went out of own end zone
                self._score_safety()
                description = "BLOCKED PUNT! Safety!"
                turnover = False
                touchdown = False
                safety = True
            else:
                # Roll for recovery using offensive dice (kicking team)
                recovery_roll, _recovery_desc = roll_chart_dice()
                fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range
                kicking_team_recovers = fumble_rec_range[0] <= recovery_roll <= fumble_rec_range[1]

                turnover = not kicking_team_recovers
                touchdown = False

                if kicking_team_recovers:
                    # Kicking team recovers at block_spot
                    # On 4th down, must reach first down marker or it's turnover on downs
                    first_down_marker = field_pos_before + ytg_before
                    final_spot = block_spot  # May be updated by return

                    # Check for return on rolls 17, 18, 19 (only if at/behind LOS)
                    if recovery_roll in [17, 18, 19] and block_spot <= field_pos_before:
                        return_dice, return_desc = roll_chart_dice()
                        int_return_result = (
                            self.state.possession_team.special_teams.interception_return.get(
                                return_dice, "0"
                            )
                        )

                        if recovery_roll == 19:
                            # Automatic TD
                            return_yards = 100 - block_spot
                            final_spot = 100
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}) - RETURN TD!"
                        else:
                            chain, touchdown, return_yards, description = self._blocked_kick_return(
                                block_spot, (return_dice, int_return_result), "BLOCKED PUNT",
                                recovery_roll, "Kicking team",
                            )
                            safety = not chain.offsetting and chain.spot <= 0
                            if chain.offsetting:
                                nullified = True
                                description = self._nullify_kick_play(
                                    kicking_home, field_pos_before, down_before, ytg_before, chain, "BLOCKED PUNT",
                                )
                            elif self.state.is_home_possession != kicking_home:
                                turnover = True  # Lost again on the return
                            else:
                                final_spot = chain.spot
                    else:
                        self.state.ball_position = block_spot
                        description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                    # On 4th down, check if kicking team reached first down marker
                    # If not, it's turnover on downs (unless TD scored)
                    if nullified or turnover or safety:
                        pass
                    elif down_before == 4 and not touchdown and final_spot < first_down_marker:
                        turnover = True
                        self.state.switch_possession()
                        self.state.ball_position = 100 - final_spot
                        self.state.down = 1
                        self.state.yards_to_go = min(10, 100 - self.state.ball_position)
                        description += " - TURNOVER ON DOWNS!"
                    elif not touchdown:
                        # Kicking team keeps ball with new set of downs
                        self.state.down = 1
                        self.state.yards_to_go = min(10, 100 - self.state.ball_position)
                else:
                    # Defense recovers - blocked kick lost
                    block_spot_defense = 100 - block_spot
                    self.state.switch_possession()

                    # Check for return on rolls 37, 38, 39
                    if recovery_roll in [37, 38, 39]:
                        return_dice, return_desc = roll_chart_dice()
                        int_return_result = (
                            self.state.possession_team.special_teams.interception_return.get(
                                return_dice, "0"
                            )
                        )

                        if recovery_roll == 39:
                            # Automatic TD
                            return_yards = 100 - block_spot_defense
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}) - RETURN TD!"
                        else:
                            chain, touchdown, return_yards, description = self._blocked_kick_return(
                                block_spot_defense, (return_dice, int_return_result), "BLOCKED PUNT",
                                recovery_roll, "Defense",
                            )
                            safety = not chain.offsetting and chain.spot <= 0
                            if chain.offsetting:
                                nullified = True
                                turnover = False
                                description = self._nullify_kick_play(
                                    kicking_home, field_pos_before, down_before, ytg_before, chain, "BLOCKED PUNT",
                                )
                            elif self.state.is_home_possession == kicking_home:
                                turnover = False  # Fumbled back to the kicking team
                    else:
                        self.state.ball_position = block_spot_defense
                        description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

            parsed_result = parse_result_string(punt_result)
            parsed_result.dice_roll = punt_roll
            parsed_result.replay_down = nullified

            outcome = PlayOutcome(
                play_type=PlayType.PUNT,
                defense_type=DefenseType.STANDARD,
                result=parsed_result,
                yards_gained=block_yards,
                turnover=turnover,
                touchdown=touchdown,
                safety=safety,
                field_position_before=field_pos_before,
                field_position_after=self.state.field_position_str(),
                description=description,
            )
            self.play_log.append(outcome)
            self._use_time(10 if nullified else random.uniform(3, 6))
            return outcome

        # Handle penalty on punt (before the ball is kicked)
        punt_penalty_yards = 0
        is_punt_offensive_penalty = False
        punt_penalty_auto_first_down = False
        if is_penalty:
            # Parse penalty yardage from result like "OFF 15", "DEF 10", or "DEF 5X"
            # X modifier means automatic first down
            penalty_match = re.search(r"(OFF|DEF)\s*(\d+)(X)?", punt_result.upper())
            if penalty_match:
                punt_penalty_yards = int(penalty_match.group(2))
                is_punt_offensive_penalty = penalty_match.group(1) == "OFF"
                punt_penalty_auto_first_down = penalty_match.group(3) == "X"

            # Re-roll to get actual punt yardage - keep rolling until we get a non-penalty result
            punt_yards = None
            max_rerolls = 10  # Safety limit to prevent infinite loops
            reroll_count = 0

            while punt_yards is None and reroll_count < max_rerolls:
                reroll_count += 1
                reroll, _reroll_desc = roll_chart_dice()
                reroll_result = punting_team.special_teams.punt.get(reroll, "40")

                # Check if re-roll is also a penalty
                if "OFF" in reroll_result.upper() or "DEF" in reroll_result.upper():
                    reroll_is_offensive = "OFF" in reroll_result.upper()
                    if is_punt_offensive_penalty != reroll_is_offensive:
                        # Offsetting penalties (OFF + DEF) - replay the down
                        description = f"OFFSETTING PENALTIES: {punt_result} and {reroll_result}. Down replayed."

                        outcome = PlayOutcome(
                            play_type=PlayType.PUNT,
                            defense_type=DefenseType.STANDARD,
                            result=parse_result_string(punt_result),
                            yards_gained=0,
                            field_position_before=field_pos_before,
                            field_position_after=self.state.field_position_str(),
                            description=description,
                        )
                        self.play_log.append(outcome)
                        return outcome
                    else:
                        # Same type penalties - take larger penalty and re-roll again
                        reroll_match = re.search(r"(OFF|DEF)\s*(\d+)(X)?", reroll_result.upper())
                        if reroll_match:
                            reroll_penalty = int(reroll_match.group(2))
                            punt_penalty_yards = max(punt_penalty_yards, reroll_penalty)
                            # Check for X modifier on re-roll too
                            if reroll_match.group(3) == "X":
                                punt_penalty_auto_first_down = True
                        # Continue loop to get actual yardage
                else:
                    # Re-roll gave actual punt yardage
                    try:
                        punt_yards = int(reroll_result.replace("*", "").replace("†", "").strip())
                    except ValueError:
                        # Non-numeric, non-penalty result (e.g., blocked kick) - continue rolling
                        pass

            # If we exhausted re-rolls without getting yardage, use chart average
            if punt_yards is None:
                punt_yards = 40  # Fallback only if chart has no valid yardage entries

            description = f"Penalty on punt - {punt_result}"

            original_punt_yards = punt_yards
        else:
            # Parse punt yardage
            try:
                punt_yards = int(punt_clean)
            except ValueError:
                punt_yards = 40  # Default

            # Apply coffin corner yardage subtraction (before moving ball downfield)
            # Per rules: yardage is subtracted from the Special Team Chart result
            # but not from penalties, blocked kicks, or fumbled snap results
            if coffin_corner_yards > 0:
                original_punt_yards = punt_yards
                punt_yards = max(0, punt_yards - coffin_corner_yards)
                description = f"[CC: {original_punt_yards}-{coffin_corner_yards}={punt_yards}] "
            else:
                description = ""
                original_punt_yards = punt_yards

        # Calculate where punt lands (from punting team's perspective)
        # Ball position is yards from own goal, punt travels toward opponent's goal
        landing_spot = self.state.ball_position + punt_yards

        # Check for touchback
        if landing_spot >= 100:
            # Handle penalty on touchback - can't return early, need to offer choice
            if punt_penalty_yards > 0 and is_punt_offensive_penalty:
                # OFF penalty - receiving team gets choice: replay from LOS-penalty OR keep touchback + yards
                # Touchback is at the 20 (receiving team's perspective)
                receiving_position = 20
                final_position = 20

                # Calculate options
                # Replay: ball moves back from original LOS (not touchback position)
                replay_pos = self.state.ball_position - punt_penalty_yards
                replay_pos = max(replay_pos, 1)

                # Keep result: touchback + penalty yards = 20 + 5 = 25
                keep_position = 20 + punt_penalty_yards

                replay_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"OFF {punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=f"Replay punt from {format_field_position(replay_pos)}",
                    auto_first_down=False,
                )

                keep_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"KEEP+{punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=f"Keep touchback + {punt_penalty_yards} yards → {format_field_position(keep_position)}",
                    auto_first_down=True,  # Receiving team starts a new possession
                    result_preview=self._punt_keep_result_preview(keep_position),
                )

                penalty_choice = PenaltyChoice(
                    play_result=parse_result_string(punt_result),
                    penalty_options=[replay_option, keep_option],
                    offended_team="defense",  # Receiving team is offended
                    offsetting=False,
                )

                self._pending_punt_state = {
                    "field_pos_before": field_pos_before,
                    "down_before": down_before,
                    "ytg_before": ytg_before,
                    "punt_yards": punt_yards,
                    "punt_result": punt_result,
                    "punt_roll": punt_roll,
                    "receiving_position": receiving_position,
                    "return_roll": 0,
                    "return_yards": 0,
                    "return_desc": "touchback",
                    "final_position": final_position,
                    "would_be_td": False,
                    "punt_penalty_yards": punt_penalty_yards,
                    "is_offensive_penalty": True,
                    "short_drop": short_drop,
                    "coffin_corner_yards": coffin_corner_yards,
                    "is_fair_catch": False,
                    "punt_from": punt_from,
                }

                description = f"Punt {punt_yards} yards into the end zone - Touchback at the 20. PENALTY: OFF {punt_penalty_yards} on kicking team. Receiving team chooses: replay punt OR keep result + yardage."

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(punt_result),
                    yards_gained=punt_yards,
                    touchdown=False,
                    field_position_before=field_pos_before,
                    field_position_after="pending",
                    description=description,
                    penalty_choice=penalty_choice,
                    pending_penalty_decision=True,
                )
                return outcome
            else:
                # No penalty - regular touchback
                self.state.switch_possession()
                self.state.ball_position = 20  # Touchback at 20
                description = (
                    f"{description}Punt {punt_yards} yards into the end zone - Touchback at the 20"
                )

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(punt_result),
                    yards_gained=punt_yards,
                    field_position_before=field_pos_before,
                    field_position_after=self.state.field_position_str(),
                    description=description,
                )
                outcome.result.dice_roll = punt_roll
                self.play_log.append(outcome)
                self._use_time(random.uniform(5, 10))
                return outcome

        # Convert landing spot to receiving team's perspective
        # If punt lands at punting team's 70, that's receiving team's 30
        receiving_position = 100 - landing_spot

        # Check if punt can be returned
        return_yards = 0
        return_desc = ""

        # Coffin corner: 15+ yards subtracted = automatic out of bounds (no return)
        # Per rules: "If 15 yards or more is subtracted from a punt, the punt is automatically
        # out of bounds (unless otherwise specified in advance by the punting team),
        # and there can be no return, fair catch, or roll yardage."
        if is_coffin_corner:
            # Handle penalty on OOB - can't return early, need to offer choice
            if punt_penalty_yards > 0 and is_punt_offensive_penalty:
                # OFF penalty - receiving team gets choice: replay from LOS-penalty OR keep OOB spot + yards
                receiving_position = clamp_ball_position(100 - landing_spot)
                final_position = receiving_position

                # Calculate options
                replay_pos = self.state.ball_position - punt_penalty_yards
                replay_pos = max(replay_pos, 1)

                keep_position = receiving_position + punt_penalty_yards

                replay_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"OFF {punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=f"Replay punt from {format_field_position(replay_pos)}",
                    auto_first_down=False,
                )

                keep_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"KEEP+{punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=f"Keep result + {punt_penalty_yards} yards → {format_field_position(keep_position)}",
                    auto_first_down=True,  # Receiving team starts a new possession
                    result_preview=self._punt_keep_result_preview(keep_position),
                )

                penalty_choice = PenaltyChoice(
                    play_result=parse_result_string(punt_result),
                    penalty_options=[replay_option, keep_option],
                    offended_team="defense",
                    offsetting=False,
                )

                self._pending_punt_state = {
                    "field_pos_before": field_pos_before,
                    "down_before": down_before,
                    "ytg_before": ytg_before,
                    "punt_yards": punt_yards,
                    "punt_result": punt_result,
                    "punt_roll": punt_roll,
                    "receiving_position": receiving_position,
                    "return_roll": 0,
                    "return_yards": 0,
                    "return_desc": return_desc,
                    "final_position": final_position,
                    "would_be_td": False,
                    "punt_penalty_yards": punt_penalty_yards,
                    "is_offensive_penalty": True,
                    "short_drop": short_drop,
                    "coffin_corner_yards": coffin_corner_yards,
                    "is_fair_catch": False,
                    "punt_from": punt_from,
                }

                full_description = f"Punt {punt_yards} yards ({coffin_corner_yards} yards subtracted) - out of bounds at {format_field_position(receiving_position)}. PENALTY: OFF {punt_penalty_yards} on kicking team. Receiving team chooses: replay punt OR keep result + yardage."

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(punt_result),
                    yards_gained=punt_yards,
                    touchdown=False,
                    field_position_before=field_pos_before,
                    field_position_after="pending",
                    description=full_description,
                    penalty_choice=penalty_choice,
                    pending_penalty_decision=True,
                )
                return outcome
            else:
                # No penalty - regular coffin corner
                return_desc = "coffin corner - out of bounds"
                self.state.switch_possession()
                self.state.ball_position = receiving_position
                self.state.down = 1
                self.state.yards_to_go = 10

                full_description = f"Punt {punt_yards} yards ({coffin_corner_yards} yards subtracted) - out of bounds at {self.state.field_position_str()}"
                if description:
                    full_description = description + " - " + full_description

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(punt_result),
                    yards_gained=punt_yards,
                    field_position_before=field_pos_before,
                    field_position_after=self.state.field_position_str(),
                    description=full_description,
                )
                outcome.result.dice_roll = punt_roll
                self.play_log.append(outcome)
                self._use_time(random.uniform(5, 10))
                return outcome

        # Track return penalty separately for TD negation logic
        return_penalty_yards = 0
        return_penalty_is_offensive = False
        return_roll = 0  # Initialize for all code paths
        return_fumbled = False
        return_chain = None

        if is_downed:
            # Ball downed or out of bounds - no return
            return_desc = "downed"
        elif is_fair_catch:
            # Fair catch - no return
            return_desc = "fair catch"
        else:
            # The receiving team owns the return chart and any recovery roll.
            return_chart = receiving_team.special_teams.punt_return
            end_rule = None
            if is_short_drop:
                end_rule = lambda yards: (min(100, receiving_position + max(0, yards)), False)
            return_chain = self._resolve_return_chain(
                not self.state.is_home_possession, receiving_position, return_chart, "Ret", end_rule=end_rule,
            )
            if is_short_drop and not return_chain.fumbled:
                return_chain.yards = max(0, return_chain.yards)
            return_roll, return_result = return_chain.first_roll, return_chain.first_cell
            return_yards = return_chain.yards
            return_fumbled = return_chain.fumbled
            return_desc = f"returned {return_yards} yards"
            if return_chain.offsetting:
                self._use_time(10)
                outcome = self._handle_punt(
                    short_drop=short_drop, coffin_corner_yards=coffin_corner_yards, punt_from=punt_from,
                )
                outcome.description = (
                    f"OFFSETTING PENALTIES on the punt return; re-kick "
                    f"(P:{punt_roll}→{punt_result} | {' | '.join(return_chain.trace)}). "
                    + outcome.description
                )
                return outcome
            if not punt_penalty_yards:
                return self._finish_punt_return_chain(
                    return_chain, punt_result, punt_roll, punt_yards, field_pos_before,
                    prefix="Safety free kick punt" if punt_from == 20 else "Punt",
                    lead=description, shanked=not short_drop and coffin_corner_yards == 0 and punt_yards < 20,
                )
            if return_chain.penalties:
                fouling_home, return_penalty_yards = return_chain.penalties[0]
                return_penalty_is_offensive = fouling_home != self.state.is_home_possession

        # Final position is receiving position plus return yards (before penalty)
        final_position = receiving_position + return_yards
        if return_chain is not None:
            final_position = (return_chain.spot if return_chain.possession_home != self.state.is_home_possession
                              else 100 - return_chain.spot)

        # Check for return touchdown first (before applying penalties)
        touchdown = False
        would_be_td = final_position >= 100

        # Check for double foul (both punt chart and return chart have penalties)
        if punt_penalty_yards > 0 and return_penalty_yards > 0:
            # Use NFL Rule 14-5-1 to determine outcome
            double_foul_result = self._handle_double_foul_penalty(
                penalty_a_yards=punt_penalty_yards,
                penalty_a_is_offensive=is_punt_offensive_penalty,
                penalty_a_has_auto_fd=punt_penalty_auto_first_down,
                penalty_b_yards=return_penalty_yards,
                penalty_b_is_offensive=return_penalty_is_offensive,
                penalty_b_has_auto_fd=False,  # Return penalties don't have X modifier
                landing_spot=landing_spot,
                punt_roll=punt_roll,
                return_roll=return_roll,
                punt_result=punt_result,
                return_result=return_result,
            )

            if double_foul_result["action"] == "offset":
                # Penalties offset - replay the punt
                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parse_result_string(punt_result),
                    yards_gained=0,
                    field_position_before=field_pos_before,
                    field_position_after=self.state.field_position_str(),
                    description=double_foul_result["description"],
                )
                self.play_log.append(outcome)
                return outcome
            else:
                # Apply 15-yard penalty only - receiving team keeps possession
                self.state.switch_possession()
                self.state.ball_position = clamp_ball_position(double_foul_result["final_position"])
                self.state.down = 1
                self.state.yards_to_go = 10

                parsed_result = parse_result_string(punt_result)
                parsed_result.dice_roll = punt_roll
                parsed_result.punt_return_dice = return_roll
                parsed_result.punt_return_result = return_result

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parsed_result,
                    yards_gained=punt_yards,
                    touchdown=False,
                    field_position_before=field_pos_before,
                    field_position_after=self.state.field_position_str(),
                    description=double_foul_result["description"],
                )
                self.play_log.append(outcome)
                self._use_time(random.uniform(5, 12))
                return outcome

        # Check for penalty on punt chart that requires a choice
        # Chart penalties use scrimmage play perspective (punting team = offense, receiving team = defense)
        # OFF penalty = punting team foul → receiving team gets choice
        # DEF penalty = receiving team foul → punting team gets choice (X modifier = auto first down)
        # NOTE: Do NOT switch possession yet - wait for penalty decision
        if punt_penalty_yards > 0 and return_penalty_yards == 0:
            if is_punt_offensive_penalty:
                # OFF penalty - kicking team committed foul, receiving team gets choice
                # Options: (1) Replay punt from LOS - penalty yards, or (2) Keep result + yardage

                # Calculate replay position (ball moves back for kicking team)
                replay_pos = self.state.ball_position - punt_penalty_yards
                replay_pos = max(replay_pos, 1)

                # Calculate keep result position (add penalty yards to final position)
                keep_position, _, _ = self._enforce_return_penalty(final_position, punt_penalty_yards, False)
                keep_td = keep_position >= 100

                replay_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"OFF {punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=f"Replay punt from {format_field_position(replay_pos)}",
                    auto_first_down=False,
                )

                keep_desc = f"Keep return + {punt_penalty_yards} yards → {format_field_position(keep_position) if not keep_td else 'TOUCHDOWN'}"
                keep_option = PenaltyOption(
                    penalty_type="OFF",
                    raw_result=f"KEEP+{punt_penalty_yards}",
                    yards=punt_penalty_yards,
                    description=keep_desc,
                    auto_first_down=True,  # Receiving team starts a new possession
                    result_preview=self._punt_keep_result_preview(keep_position),
                )

                penalty_choice = PenaltyChoice(
                    play_result=parse_result_string(punt_result),
                    penalty_options=([replay_option] if return_chain is not None
                                     and return_chain.possession_home == self.state.is_home_possession
                                     else [replay_option, keep_option]),
                    offended_team="defense",  # Receiving team is offended
                    offsetting=False,
                )

                self._pending_punt_state = {
                    "field_pos_before": field_pos_before,
                    "down_before": down_before,
                    "ytg_before": ytg_before,
                    "punt_yards": punt_yards,
                    "punt_result": punt_result,
                    "punt_roll": punt_roll,
                    "receiving_position": receiving_position,
                    "return_roll": return_roll,
                    "return_yards": return_yards,
                    "return_result": return_result,
                    "return_desc": return_desc,
                    "final_position": final_position,
                    "would_be_td": would_be_td,
                    "punt_penalty_yards": punt_penalty_yards,
                    "is_offensive_penalty": True,
                    "short_drop": short_drop,
                    "coffin_corner_yards": coffin_corner_yards,
                    "is_fair_catch": is_fair_catch,
                    "punt_from": punt_from,
                    "return_fumbled": return_fumbled,
                    "return_chain": return_chain,
                }

                parsed_result = parse_result_string(punt_result)
                parsed_result.dice_roll = punt_roll
                if return_chain is not None:
                    parsed_result = self._punt_return_chain_result(return_chain, punt_result, punt_roll)
                    penalty_choice.play_result = parsed_result
                if return_fumbled:
                    description = (f"Punt {punt_yards} yards. " + "; ".join(return_chain.notes)
                                   + f". PENALTY: OFF {punt_penalty_yards}. Receiving team may replay or decline.")
                else:
                    description = f"Punt {punt_yards} yards, returned {return_yards} yards. PENALTY: OFF {punt_penalty_yards} on kicking team. Receiving team chooses: replay punt OR keep result + yardage."

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parsed_result,
                    yards_gained=punt_yards,
                    touchdown=False,
                    field_position_before=field_pos_before,
                    field_position_after="pending",
                    description=description,
                    penalty_choice=penalty_choice,
                    pending_penalty_decision=True,
                )
                return outcome
            else:
                # DEF penalty - receiving team committed foul, kicking team gets choice
                # Calculate accept penalty position (ball moves forward for kicking team)
                accept_pos = self.state.ball_position + punt_penalty_yards
                accept_pos = min(accept_pos, 99)

                # Check if accepting would give a first down
                # X modifier (e.g., DEF 5X) means automatic first down regardless of ytg
                # For DEF penalty on a PUNT, it's typically a pre-snap penalty (encroachment/offsides),
                # so the offense just gets 5 yards and replays the down - not a new set of downs
                would_get_first_down = (
                    punt_penalty_auto_first_down or punt_penalty_yards >= ytg_before
                )

                if would_get_first_down:
                    if punt_penalty_auto_first_down:
                        accept_desc = f"Accept penalty: 1st down at {format_field_position(accept_pos)} (auto first down)"
                    else:
                        accept_desc = (
                            f"Accept penalty: 1st down at {format_field_position(accept_pos)}"
                        )
                else:
                    new_ytg = ytg_before - punt_penalty_yards
                    accept_desc = (
                        f"Accept penalty: 4th and {new_ytg} at {format_field_position(accept_pos)}"
                    )

                accept_option = PenaltyOption(
                    penalty_type="DEF",
                    raw_result=f"DEF {punt_penalty_yards}{'X' if punt_penalty_auto_first_down else ''}",
                    yards=punt_penalty_yards,
                    description=accept_desc,
                    auto_first_down=would_get_first_down,
                )

                decline_option = PenaltyOption(
                    penalty_type="DEF",
                    raw_result="DECLINE",
                    yards=0,
                    description="Decline penalty, take punt result",
                    auto_first_down=False,
                )

                penalty_choice = PenaltyChoice(
                    play_result=parse_result_string(punt_result),
                    penalty_options=[accept_option, decline_option],
                    offended_team="offense",  # Kicking team is offended
                    offsetting=False,
                )

                self._pending_punt_state = {
                    "field_pos_before": field_pos_before,
                    "down_before": down_before,
                    "ytg_before": ytg_before,
                    "punt_yards": punt_yards,
                    "punt_result": punt_result,
                    "punt_roll": punt_roll,
                    "receiving_position": receiving_position,
                    "return_roll": return_roll,
                    "return_yards": return_yards,
                    "return_result": return_result,
                    "return_desc": return_desc,
                    "final_position": final_position,
                    "would_be_td": would_be_td,
                    "punt_penalty_yards": punt_penalty_yards,
                    "is_offensive_penalty": False,
                    "punt_penalty_auto_first_down": punt_penalty_auto_first_down,
                    "short_drop": short_drop,
                    "coffin_corner_yards": coffin_corner_yards,
                    "is_fair_catch": is_fair_catch,
                    "punt_from": punt_from,
                    "return_fumbled": return_fumbled,
                    "return_chain": return_chain,
                }

                parsed_result = parse_result_string(punt_result)
                parsed_result.dice_roll = punt_roll
                if return_chain is not None:
                    parsed_result = self._punt_return_chain_result(return_chain, punt_result, punt_roll)
                    penalty_choice.play_result = parsed_result
                penalty_suffix = "X" if punt_penalty_auto_first_down else ""
                description = f"Punt {punt_yards} yards. PENALTY: DEF {punt_penalty_yards}{penalty_suffix} on receiving team. Kicking team chooses: accept OR decline."
                if return_fumbled:
                    description += " " + "; ".join(return_chain.notes)

                outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=parsed_result,
                    yards_gained=punt_yards,
                    touchdown=False,
                    field_position_before=field_pos_before,
                    field_position_after="pending",
                    description=description,
                    penalty_choice=penalty_choice,
                    pending_penalty_decision=True,
                )
                return outcome

        # Only downed/fair-caught punts without a kick-chart choice remain here.
        self.state.switch_possession()

        self.state.ball_position = clamp_ball_position(final_position)
        self.state.down = 1
        self.state.yards_to_go = 10

        # Add punt commentary for exceptional punts
        punt_commentary = ""
        # Check for shank: normal punt under 20 yards (not short-drop or coffin-corner)
        if not short_drop and coffin_corner_yards == 0 and punt_yards < 20 and not touchdown:
            punt_commentary = " Shanked!"
        # Check if receiving team is pinned inside their 20 (ball_position is from their perspective now)
        elif self.state.ball_position <= 20 and not touchdown:
            if self.state.ball_position <= 10:
                punt_commentary = " Pinned deep!"
            else:
                punt_commentary = " Pinned inside the 20!"
        # Check for extra long punt (50+ yards) that isn't a touchback
        elif punt_yards >= 55 and not touchdown:
            punt_commentary = " What a boot!"
        elif punt_yards >= 50 and not touchdown:
            punt_commentary = " Great hang time!"

        # Build description
        penalty_desc = ""
        if return_penalty_yards > 0:
            penalty_team = "OFF" if return_penalty_is_offensive else "DEF"
            direction = "enforced" if return_penalty_is_offensive else "added"
            penalty_desc = f" ({penalty_team} {return_penalty_yards} {direction} on return)"
        elif punt_penalty_yards > 0:
            if is_punt_offensive_penalty:
                penalty_desc = f" (OFF {punt_penalty_yards} - offense penalized)"
            else:
                penalty_desc = f" (DEF {punt_penalty_yards} added)"

        # Check if there's a pending penalty for the kickoff (from TD + penalty scenario)
        if self.state.pending_kickoff_penalty_yards > 0:
            if self.state.pending_kickoff_penalty_is_offense:
                penalty_desc = f" (PENALTY on return - will apply to kickoff: OFF {self.state.pending_kickoff_penalty_yards})"
            else:
                penalty_desc = f" (PENALTY on return - will apply to kickoff: DEF {self.state.pending_kickoff_penalty_yards} added)"

        # Use "Safety free kick punt" for punts from own 20 (after safety)
        punt_type = "Safety free kick punt" if punt_from == 20 else "Punt"

        if return_desc:
            if "fair catch" in return_desc or "downed" in return_desc:
                description = f"{description}{punt_type} {punt_yards} yards, {return_desc} at {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"
            elif touchdown:
                description = (
                    f"{description}{punt_type} {punt_yards} yards, {return_desc} - TOUCHDOWN!"
                )
            else:
                description = f"{description}{punt_type} {punt_yards} yards, {return_desc} to {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"
        else:
            description = f"{description}{punt_type} {punt_yards} yards to {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"

        parsed_result = parse_result_string(punt_result)
        parsed_result.dice_roll = punt_roll
        parsed_result.raw_result = f"{punt_yards}{'*' if is_fair_catch else ''}"
        # Preserve the return-chart fact for UI traces, even when it is a fumble or penalty.
        parsed_result.punt_return_dice = return_roll if return_roll else 0
        parsed_result.punt_return_result = return_result if return_roll else ""

        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=parsed_result,
            yards_gained=punt_yards,
            touchdown=touchdown,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            description=description,
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 12))

        return outcome

    def _punt_return_chain_result(self, chain: ReturnChain, punt_result: str, punt_roll: int) -> PlayResult:
        """Project return facts without applying possession, scores, or statistics."""
        result = parse_result_string(punt_result)
        result.dice_roll = punt_roll
        result.punt_return_dice = chain.first_roll
        result.punt_return_result = chain.first_cell
        if chain.fumbled:
            result.result_type = ResultType.FUMBLE
            result.fumble_resolved = True
            result.fumble_recovered = chain.possession_home == self.state.is_home_possession
        result.description = "; ".join(chain.notes) + f" ({' | '.join(chain.trace)})"
        return result

    def _finish_punt_return_chain(
        self, chain: ReturnChain, punt_result: str, punt_roll: int, punt_yards: int,
        field_pos_before: int, prefix: str = "Punt", lead: str = "", shanked: bool = False,
    ) -> PlayOutcome:
        """Apply a punt return exactly once, after any kick-chart decision."""
        result = self._punt_return_chain_result(chain, punt_result, punt_roll)
        if punt_result.strip().isdigit():
            result.raw_result = str(punt_yards)
        touchdown = self._apply_return_chain(chain, accept_choice=False)
        safety = chain.spot <= 0
        description = f"{lead}{prefix} {punt_yards} yards, returned {chain.yards} yards to {self.state.field_position_str()}."
        if not chain.fumbled and not chain.penalties and not touchdown and not safety:
            if chain.yards >= 30:
                description += " What a return!"
            elif chain.yards >= 20:
                description += " Great return!"
            elif chain.yards == 0:
                description += " Excellent coverage!"
            elif chain.yards < 0:
                description += " Outstanding special teams coverage!"
            if shanked:
                description += " Shanked!"
            elif self.state.ball_position <= 10:
                description += " Pinned deep!"
            elif self.state.ball_position <= 20:
                description += " Pinned inside the 20!"
            elif punt_yards >= 55:
                description += " What a boot!"
            elif punt_yards >= 50:
                description += " Great hang time!"
        if chain.penalties:
            description += " Penalty on return."
        if touchdown:
            description += " TOUCHDOWN!"
        elif safety:
            description += " SAFETY!"
        elif chain.touchback:
            description += " TOUCHBACK."
        if chain.notes:
            description += " " + "; ".join(chain.notes)
        description += f" (P:{punt_roll}→{punt_result} | {' | '.join(chain.trace)})"
        result.description = description
        result.touchdown = touchdown
        outcome = PlayOutcome(
            play_type=PlayType.PUNT, defense_type=DefenseType.STANDARD, result=result,
            yards_gained=punt_yards, touchdown=touchdown, safety=safety,
            penalty_applied=bool(chain.penalties), field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(), description=description,
        )
        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 12))
        return outcome

    def apply_punt_penalty_decision(
        self, outcome: PlayOutcome, accept_penalty: bool, penalty_index: int = 0
    ) -> PlayOutcome:
        """
        Apply the punt penalty decision.

        Roles: Kicking team = OFFENSE, Receiving team = DEFENSE

        OFF penalty (kicking team foul) - receiving team chooses:
        - penalty_index=0: Replay punt from LOS - penalty yards (kicking team pushed back)
        - penalty_index=1: Keep return result + penalty yards added to final position

        DEF penalty (receiving team foul) - kicking team chooses:
        - accept_penalty=True: Accept penalty (1st down if auto, else replay from LOS + penalty)
        - accept_penalty=False: Decline penalty, take punt result as-is

        Args:
            outcome: The PlayOutcome with pending_penalty_decision=True
            accept_penalty: True to accept/enforce penalty, False to decline/keep result
            penalty_index: Which penalty option was selected (0=first, 1=second, etc.)

        Returns:
            Updated PlayOutcome with game state applied
        """
        if not outcome.pending_penalty_decision or not hasattr(self, "_pending_punt_state"):
            return outcome

        state = self._pending_punt_state
        penalty_yards = state["punt_penalty_yards"]
        is_offensive_penalty = state.get("is_offensive_penalty", False)

        chain = state.get("return_chain")
        if chain is not None and not accept_penalty:
            del self._pending_punt_state
            return self._finish_punt_return_chain(
                chain, state["punt_result"], state["punt_roll"], state["punt_yards"], state["field_pos_before"],
                prefix=("Receiving team" if is_offensive_penalty else "Kicking team") + " declines penalty. Punt",
            )

        if is_offensive_penalty and accept_penalty:
            # OFF penalty - kicking team committed foul, receiving team decides
            # Check if the selected option is "keep return" (contains "KEEP" in raw_result)
            keep_return = False
            if (outcome.penalty_choice and outcome.penalty_choice.penalty_options) and (penalty_index < len(outcome.penalty_choice.penalty_options)):
                selected_option = outcome.penalty_choice.penalty_options[penalty_index]
                keep_return = "KEEP" in selected_option.raw_result

            if keep_return:
                if chain is not None:
                    chain.spot, effective, _ = self._enforce_return_penalty(chain.spot, penalty_yards, False)
                    chain.penalties.append((self.state.is_home_possession, effective))
                    chain.notes.append(f"Receiving team keeps result + {effective} yards (OFF {penalty_yards})")
                    del self._pending_punt_state
                    return self._finish_punt_return_chain(
                        chain, state["punt_result"], state["punt_roll"], state["punt_yards"], state["field_pos_before"],
                    )
                # No-return punts (fair catch, downed, or touchback) keep their stored result.
                final_position, effective, _ = self._enforce_return_penalty(state["final_position"], penalty_yards, False)

                touchdown = False
                if final_position >= 100:
                    touchdown = True
                    final_position = 100

                self.state.switch_possession()
                self.state.ball_position = clamp_ball_position(final_position)
                self.state.down = 1
                self.state.yards_to_go = 10

                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += effective

                if touchdown:
                    self._score_touchdown()

                del self._pending_punt_state

                punt_yards = state["punt_yards"]
                return_yards = state["return_yards"]

                if touchdown:
                    description = f"Receiving team keeps result + {penalty_yards} yards: TOUCHDOWN!"
                else:
                    description = f"Receiving team keeps result + {penalty_yards} yards to {self.state.field_position_str()}."

                new_outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=outcome.result,
                    yards_gained=punt_yards,
                    touchdown=touchdown,
                    field_position_before=state["field_pos_before"],
                    field_position_after=self.state.field_position_str(),
                    description=description,
                    penalty_applied=True,
                )

                self.play_log.append(new_outcome)
                self._use_time(random.uniform(25, 45))

                return new_outcome
            else:
                # Option 1: Replay punt from LOS - penalty yards (kicking team pushed back)
                # User selected "Replay punt from X" or default when penalty_index=0
                original_pos = self.state.ball_position
                new_pos = original_pos - penalty_yards
                new_pos = max(new_pos, 1)

                self.state.ball_position = new_pos
                self.state.down = 4  # Still 4th down, replay the punt
                self.state.yards_to_go = state["ytg_before"] + original_pos - new_pos
                self.state.offense_stats.penalties += 1
                self.state.offense_stats.penalty_yards += original_pos - new_pos

                del self._pending_punt_state

                description = f"Receiving team accepts penalty: OFF {penalty_yards}. Punt replayed from {self.state.field_position_str()}."

                new_outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=outcome.result,
                    yards_gained=0,
                    touchdown=False,
                    field_position_before=state["field_pos_before"],
                    field_position_after=self.state.field_position_str(),
                    description=description,
                    penalty_applied=True,
                )

                self.play_log.append(new_outcome)
                self._use_time(random.uniform(25, 45))

                return new_outcome
        else:
            # Enforce a receiving-team penalty, or decline either penalty.
            if accept_penalty:
                # Accept penalty - ball moves forward for kicking team
                original_pos = self.state.ball_position
                new_pos = original_pos + penalty_yards
                new_pos = min(new_pos, 99)

                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += new_pos - original_pos
                self.state.ball_position = new_pos

                # Check if penalty yards give a first down
                # X modifier means automatic first down regardless of ytg
                ytg_before = state.get("ytg_before", 10)
                auto_first_down = state.get("punt_penalty_auto_first_down", False)
                got_first_down = auto_first_down or penalty_yards >= ytg_before

                penalty_suffix = "X" if auto_first_down else ""
                if got_first_down:
                    self.state.down = 1
                    self.state.yards_to_go = min(10, 100 - new_pos)
                    description = f"Kicking team accepts penalty: DEF {penalty_yards}{penalty_suffix}. 1st down at {self.state.field_position_str()}."
                else:
                    # Still 4th down, but with reduced yards to go
                    self.state.down = 4
                    self.state.yards_to_go = ytg_before - penalty_yards
                    description = f"Kicking team accepts penalty: DEF {penalty_yards}. 4th and {self.state.yards_to_go} at {self.state.field_position_str()}."

                del self._pending_punt_state

                new_outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=outcome.result,
                    yards_gained=penalty_yards,
                    touchdown=False,
                    first_down=got_first_down,
                    field_position_before=state["field_pos_before"],
                    field_position_after=self.state.field_position_str(),
                    description=description,
                    penalty_applied=True,
                )

                self.play_log.append(new_outcome)
                self._use_time(random.uniform(25, 45))

                return new_outcome
            else:
                # A declined penalty preserves the punt/return without penalty yardage.
                deciding_team = "Receiving team" if is_offensive_penalty else "Kicking team"
                final_position = state["final_position"]

                touchdown = False
                if final_position >= 100:
                    touchdown = True
                    final_position = 100

                self.state.switch_possession()
                self.state.ball_position = clamp_ball_position(final_position)
                self.state.down = 1
                self.state.yards_to_go = 10

                if touchdown:
                    self._score_touchdown()

                del self._pending_punt_state

                punt_yards = state["punt_yards"]
                return_yards = state["return_yards"]

                if touchdown:
                    description = f"{deciding_team} declines penalty. Punt {punt_yards} yards, returned for TOUCHDOWN!"
                else:
                    description = f"{deciding_team} declines penalty. Punt {punt_yards} yards, returned {return_yards} yards to {self.state.field_position_str()}."

                new_outcome = PlayOutcome(
                    play_type=PlayType.PUNT,
                    defense_type=DefenseType.STANDARD,
                    result=outcome.result,
                    yards_gained=punt_yards,
                    touchdown=touchdown,
                    field_position_before=state["field_pos_before"],
                    field_position_after=self.state.field_position_str(),
                    description=description,
                    penalty_applied=False,
                )

                self.play_log.append(new_outcome)
                self._use_time(random.uniform(25, 45))

                return new_outcome

    def apply_kickoff_penalty_decision(
        self, outcome: PlayOutcome, accept_penalty: bool
    ) -> PlayOutcome:
        """
        Apply the offended team's decision for a kickoff penalty.

        A kick-chart penalty is re-kicked (accepted) or played as rolled
        (declined). A return-chart penalty is enforced from the return
        (accepted) or the return stands (declined).

        Args:
            outcome: The PlayOutcome with pending_penalty_decision=True from kickoff
            accept_penalty: True to accept the penalty, False to decline it

        Returns:
            Updated PlayOutcome with game state applied
        """
        if not hasattr(self, "_pending_kickoff_penalty_state"):
            return outcome

        state = self._pending_kickoff_penalty_state
        del self._pending_kickoff_penalty_state
        if state.get("phase") == "return_fumble":
            return self._complete_kickoff_return(state["ctx"], state["chain"], accept_choice=accept_penalty)

        kicking_home = state["kicking_home"]
        kickoff_spot = state["kickoff_spot"]
        ko_penalty_yards = state["ko_penalty_yards"]
        ko_is_offensive_penalty = state["ko_is_offensive_penalty"]

        if accept_penalty:
            # Accept penalty - re-kick from adjusted spot
            if ko_is_offensive_penalty:
                # OFF penalty (receiving team foul) - kick from further
                new_kickoff_spot = kickoff_spot + ko_penalty_yards
            else:
                # DEF penalty (kicking team foul) - kick from closer
                new_kickoff_spot = max(1, kickoff_spot - ko_penalty_yards)

            fouling_home = not kicking_home if ko_is_offensive_penalty else kicking_home
            stats = self.state.home_stats if fouling_home else self.state.away_stats
            stats.penalties += 1
            stats.penalty_yards += abs(new_kickoff_spot - kickoff_spot)
            outcome = self.kickoff(kicking_home=kicking_home, kickoff_spot=new_kickoff_spot)
            dice_line = self._kickoff_dice_line(state["dice_roll"], state["ko_result"], state["return_trace"])
            outcome.description = f"Kick-chart penalty accepted; re-kick. {dice_line} " + outcome.description
            outcome.result.description = outcome.description
            outcome.penalty_applied = True
            return outcome
        else:
            # Decline the kick-chart penalty: play the kick as rolled, with the
            # receiving team's return roll already taken for that kick.
            ko_yards = state["ko_yards"]
            ko_result = state["ko_result"]
            ret_result = state["ret_result"]
            return_roll = state["return_roll"]
            dice_roll = state.get("dice_roll", 0)
            receiving_chart = self.state.away_chart if kicking_home else self.state.home_chart

            is_touchback = False
            landing_spot = None
            chain = None
            return_position = 20
            if "OB" in ko_result.upper() or "OUT" in ko_result.upper():
                return_position = 40
            elif ko_yards >= 75:
                is_touchback = True
            else:
                landing_spot = 100 - (kickoff_spot + ko_yards)
                if landing_spot <= -10:
                    is_touchback = True
                else:
                    chain = self._resolve_return_chain(
                        not kicking_home, landing_spot,
                        receiving_chart.special_teams.kickoff_return, "RT",
                        first=(return_roll, ret_result),
                        end_rule=lambda yards: self._kickoff_return_spot(landing_spot, yards),
                    )
                    if chain.offsetting:
                        self._use_time(10)
                        outcome = self.kickoff(kicking_home=kicking_home, kickoff_spot=kickoff_spot)
                        full_trace = " | ".join(filter(None, [state.get("kick_reroll_trace", ""), *chain.trace]))
                        dice_line = self._kickoff_dice_line(dice_roll, ko_result, full_trace)
                        outcome.description = f"OFFSETTING PENALTIES on kickoff return; re-kick. {dice_line} " + outcome.description
                        outcome.result.description = outcome.description
                        return outcome
            ctx = {
                "kicking_home": kicking_home,
                "kickoff_spot": kickoff_spot,
                "dice_roll": dice_roll,
                "ko_result": ko_result,
                "ko_yards": ko_yards,
                "landing_spot": landing_spot,
                "is_touchback": is_touchback,
                "return_position": return_position,
                "penalty_desc": "",
                "declined_kick_penalty": (ko_penalty_yards, ko_is_offensive_penalty),
                "kick_reroll_trace": state.get("kick_reroll_trace", ""),
            }
            if chain is not None and chain.choice:
                return self._pending_kickoff_return_fumble(ctx, chain)
            return self._complete_kickoff_return(ctx, chain)

    def _evaluate_field_goal_result(
        self,
        fg_result: str,
        distance_to_goal: int,
        statistical_distance: int,
        spot_of_hold: int,
        field_pos_before: str,
        down_before: int,
        dice_roll: int,
    ) -> PlayOutcome:
        """
        Evaluate a field goal result WITHOUT applying state changes.
        Used when there's a penalty and we need to show the FG outcome for the choice.

        Returns a PlayOutcome describing what would happen if the play result is accepted.
        """
        # For FG, don't use parse_result_string - it treats "12" as 12 yards gained
        # Instead, create a proper PlayResult for field goal (yards=0 to avoid "Gain of" display)
        parsed = PlayResult(
            result_type=ResultType.YARDS,
            yards=0,
            description="",
            raw_result=fg_result,
            dice_roll=dice_roll,
        )

        success = False
        blocked = False
        description = ""

        if "BK" in fg_result.upper():
            blocked = True
            description = f"BLOCKED FG! (from {statistical_distance} yards)"
        elif re.match(r"^F\s*[+-]", fg_result, re.IGNORECASE):
            # Fumble on FG attempt
            description = "FUMBLED SNAP on FG attempt!"
        elif fg_result:
            try:
                chart_yards = int(fg_result.strip())
                success = chart_yards >= distance_to_goal
                if success:
                    description = f"Field goal GOOD! ({statistical_distance} yards)"
                else:
                    description = f"Field goal NO GOOD! ({statistical_distance} yards, kick only reached {chart_yards})"
            except ValueError:
                success = False
                description = f"Field goal NO GOOD from {statistical_distance} yards"
        else:
            success = False
            description = f"Field goal NO GOOD from {statistical_distance} yards"

        return PlayOutcome(
            play_type=PlayType.FIELD_GOAL,
            defense_type=DefenseType.STANDARD,
            result=parsed,
            yards_gained=0,
            touchdown=False,
            field_goal_made=success and not blocked,
            field_position_before=field_pos_before,
            down_before=down_before,
            description=description,
        )

    def apply_fg_penalty_decision(
        self, outcome: PlayOutcome, accept_play: bool, penalty_index: int = 0
    ) -> PlayOutcome:
        """
        Apply the offended team's penalty decision for a field goal attempt.

        Args:
            outcome: The PlayOutcome with pending_penalty_decision=True from _handle_field_goal
            accept_play: True to accept the FG result, False to accept a penalty
            penalty_index: Which penalty to accept (if multiple)

        Returns:
            Updated PlayOutcome with the decision applied
        """
        if not outcome.pending_penalty_decision:
            return outcome

        penalty_choice = outcome.penalty_choice

        # Retrieve stored FG-specific state
        distance_to_goal = getattr(outcome, "_fg_distance_to_goal", 100 - self.state.ball_position)
        statistical_distance = getattr(outcome, "_fg_statistical_distance", distance_to_goal + 17)
        spot_of_hold = getattr(outcome, "_fg_spot_of_hold", self.state.ball_position - 7)
        ball_pos_before = getattr(outcome, "_fg_ball_pos_before", self.state.ball_position)
        ytg_before = getattr(outcome, "_fg_ytg_before", self.state.yards_to_go)

        if accept_play:
            # Accept the FG result - apply the full FG logic
            fg_result = outcome.result.raw_result

            success = False
            blocked = False
            description = outcome.description

            if "BK" in fg_result.upper():
                # Handle blocked kick (simplified - full logic is complex)
                blocked = True
                # For simplicity, treat as turnover at spot of hold
                defense_at_spot = 100 - max(1, spot_of_hold)
                self.state.switch_possession()
                self.state.ball_position = max(20, defense_at_spot)
                self.state.down = 1
                self.state.yards_to_go = 10
                description = f"BLOCKED FG! Defense takes over at {self.state.field_position_str()}"

            elif re.match(r"^F\s*[+-]", fg_result, re.IGNORECASE):
                # Fumble on FG attempt
                self.state.ball_position = max(1, spot_of_hold)
                self.state.switch_possession()
                self.state.down = 1
                self.state.yards_to_go = 10
                description = f"FUMBLED SNAP! Defense recovers at {self.state.field_position_str()}"

            elif fg_result:
                try:
                    chart_yards = int(fg_result.strip())
                    success = chart_yards >= distance_to_goal
                    if success:
                        self._score_field_goal()
                        description = f"Field goal GOOD! ({statistical_distance} yards)"
                    else:
                        # Missed FG - defense gets ball
                        defense_at_20 = 20
                        defense_at_spot = 100 - max(1, spot_of_hold)
                        self.state.switch_possession()
                        if defense_at_spot > defense_at_20:
                            self.state.ball_position = defense_at_spot
                        else:
                            self.state.ball_position = defense_at_20
                        self.state.down = 1
                        self.state.yards_to_go = 10
                        description = f"Field goal NO GOOD! Defense takes over at {self.state.field_position_str()}"
                except ValueError:
                    success = False
                    self.state.switch_possession()
                    self.state.ball_position = 20
                    self.state.down = 1
                    self.state.yards_to_go = 10
                    description = f"Field goal NO GOOD from {statistical_distance} yards"

            outcome.field_goal_made = success and not blocked
            outcome.field_position_after = self.state.field_position_str()
            outcome.description = description + " (play result accepted)"
            outcome.pending_penalty_decision = False

        else:
            # Accept the penalty - rekick from new spot
            if penalty_index >= len(penalty_choice.penalty_options):
                penalty_index = 0

            penalty = penalty_choice.penalty_options[penalty_index]
            penalty_result, new_position, new_down, new_ytg, first_down = resolve_penalty(
                penalty.raw_result,
                ball_pos_before,
                yards_to_go=ytg_before,
                down=outcome.down_before,
                chart_yards=penalty.yards,
                auto_first_down=penalty.auto_first_down,
            )
            self.state.ball_position = new_position
            self.state.down = new_down
            self.state.yards_to_go = min(new_ytg, 100 - new_position)
            enforced_yards = abs(new_position - ball_pos_before)
            stats = (
                self.state.offense_stats if penalty.penalty_type == "OFF"
                else self.state.defense_stats
            )
            stats.penalties += 1
            stats.penalty_yards += enforced_yards
            if first_down:
                self.state.offense_stats.first_downs += 1

            # The kick was discarded: report only the enforced penalty, even if
            # the provisional kick would have scored or turned the ball over.
            outcome.penalty_applied = True
            outcome.field_goal_made = False
            outcome.touchdown = False
            outcome.safety = False
            outcome.turnover = False
            outcome.first_down = first_down
            outcome.yards_gained = new_position - ball_pos_before
            outcome.down_after = new_down
            down_distance = format_down_and_distance(
                new_down, self.state.yards_to_go, 100 - new_position
            )
            action = "first down" if first_down else "down replayed"
            description = (
                f"{penalty_result.description} - {action}; "
                f"{down_distance} at {self.state.field_position_str()}"
            )

            # Preserve the existing FG rekick procedure at the end of a half.
            if (penalty.penalty_type == 'OFF') and (self.state.time_remaining <= 0.5):
                self.state.untimed_down_pending = True
                description += " (HALF EXTENDED - UNTIMED DOWN)"

            outcome.field_position_after = self.state.field_position_str()
            outcome.description = description
            outcome.pending_penalty_decision = False

        self.play_log.append(outcome)

        # Only advance time if there's no untimed down pending
        # (if untimed_down_pending is True, the half extends and clock stays at 0)
        if not self.state.untimed_down_pending:
            seconds = random.uniform(5, 10) if accept_play else random.uniform(25, 45)
            self._use_time(seconds)

        return outcome

    def _record_play_start(self) -> None:
        """Remember the period a scoring-capable action starts in (engine-owned)."""
        self._last_play_start_quarter = self.state.quarter

    def should_kickoff_after_score(self, scoring_quarter: int | None = None) -> bool:
        """Whether a score is followed by a kickoff before any half/OT transition.

        Args:
            scoring_quarter: Period in which the scoring play began. Defaults to
                the period recorded when the most recent action started.

        Returns:
            False after game end or when the scoring play exhausted a half or
            overtime period. Quarter-one/three scores still require a kickoff.
        """
        if scoring_quarter is None:
            scoring_quarter = self._last_play_start_quarter
        if self.state.game_over:
            return False
        if scoring_quarter == 2 or scoring_quarter >= 4:
            return self.state.quarter == scoring_quarter and self.state.time_remaining > 0
        return True

    def _handle_field_goal(self) -> PlayOutcome:
        """
        Handle a field goal attempt per official Paydirt rules with full penalty handling.

        1. Roll offensive dice, consult Field Goal column on kicking team's Special Team Chart
        2. If penalty, reroll until non-penalty result (like normal plays)
        3. If yardage shown EQUALS or EXCEEDS distance from LOS to goal line, FG is GOOD
        4. On miss, defense gets ball at their 20 OR spot of hold (7 yards back) - whichever
           is to their advantage
        5. If penalties occurred, offended team gets to choose between play result and penalty

        NOTE: Chart yardages are distance from LOS to goal line, NOT the statistical length
        (which is 17 yards greater: 10 yards end zone + 7 yards to spot of hold)
        """
        field_pos_before = self.state.field_position_str()
        down_before = self.state.down
        ball_pos_before = self.state.ball_position
        ytg_before = self.state.yards_to_go

        # Distance from line of scrimmage to opponent's goal line
        # ball_position is yards from own goal, so distance to opponent's goal = 100 - ball_position
        distance_to_goal = 100 - self.state.ball_position

        # Statistical FG distance (for display) = distance + 17 (end zone + snap)
        statistical_distance = distance_to_goal + 17

        # Spot of hold is 7 yards behind line of scrimmage
        spot_of_hold = self.state.ball_position - 7

        # Roll for field goal result with full penalty procedure
        fg_roll_result = resolve_field_goal_with_penalties(self.state.possession_team.special_teams)

        dice_roll = fg_roll_result.dice_roll
        # dice_desc available but not currently used in this method
        fg_result = fg_roll_result.raw_result

        parsed = parse_result_string(fg_result)
        parsed.dice_roll = dice_roll  # Store dice roll for display

        # Handle offsetting penalties - replay the down (rekick)
        if fg_roll_result.offsetting:
            self._use_time(10)
            # Create a PenaltyChoice for the outcome
            penalty_choice = PenaltyChoice(
                play_result=parsed,
                penalty_options=fg_roll_result.penalty_options,
                offended_team="",
                offsetting=True,
                is_pass_interference=False,
                original_defense_result="",
                reroll_log=fg_roll_result.reroll_log,
            )
            outcome = PlayOutcome(
                play_type=PlayType.FIELD_GOAL,
                defense_type=DefenseType.STANDARD,
                result=parsed,
                yards_gained=0,
                field_position_before=field_pos_before,
                field_position_after=field_pos_before,
                down_before=down_before,
                down_after=down_before,
                description="Offsetting penalties on FG attempt - rekick",
                penalty_choice=penalty_choice,
                pending_penalty_decision=False,
            )
            self.play_log.append(outcome)
            return outcome

        # Handle non-offsetting penalties - offended team gets a choice
        if fg_roll_result.penalty_options and not fg_roll_result.offsetting:
            # We need to evaluate what the FG result would be, then let offended team choose
            # Build the FG outcome first (without applying state changes)
            fg_outcome = self._evaluate_field_goal_result(
                fg_result,
                distance_to_goal,
                statistical_distance,
                spot_of_hold,
                field_pos_before,
                down_before,
                dice_roll,
            )

            # Create a PenaltyChoice for the outcome
            penalty_choice = PenaltyChoice(
                play_result=fg_outcome.result,
                penalty_options=fg_roll_result.penalty_options,
                offended_team=fg_roll_result.offended_team,
                offsetting=False,
                is_pass_interference=False,
                original_defense_result="",
                reroll_log=fg_roll_result.reroll_log,
            )

            # Store state for later application
            fg_outcome.penalty_choice = penalty_choice
            fg_outcome.pending_penalty_decision = True
            fg_outcome.field_position_before = field_pos_before
            fg_outcome.down_before = down_before

            # Store additional FG-specific info for apply_fg_penalty_decision
            fg_outcome._fg_distance_to_goal = distance_to_goal
            fg_outcome._fg_statistical_distance = statistical_distance
            fg_outcome._fg_spot_of_hold = spot_of_hold
            fg_outcome._fg_ball_pos_before = ball_pos_before
            fg_outcome._fg_ytg_before = ytg_before

            return fg_outcome

        # Determine success based on result
        success = False
        blocked = False
        touchdown = False
        safety = False
        is_penalty = False
        is_fumble = False
        description = ""

        # Check for blocked kick per official rules:
        # - Move ball forward/backward the yards shown from spot of hold
        # - Roll offensive dice for recovery (same as fumble)
        # - Defense gets INT return for blocked kicks lost (rolls 19, 39 = auto TD)
        # - Offense gets INT return for blocked kicks recovered at/behind LOS with rolls 17, 18, 19
        fg_kicking_home = self.state.is_home_possession
        fg_down_before = self.state.down
        fg_ytg_before = self.state.yards_to_go
        nullified = False
        if "BK" in fg_result.upper():
            blocked = True
            success = False
            touchdown = False

            # Extract block yardage if present (e.g., "BK -8")
            try:
                block_yards = int(fg_result.upper().replace("BK", "").strip())
            except ValueError:
                block_yards = -7

            # Ball goes back from spot of hold
            block_spot = spot_of_hold + block_yards

            # Roll for recovery using offensive dice (kicking team)
            recovery_roll, _recovery_desc = roll_chart_dice()
            fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range
            kicking_team_recovers = fumble_rec_range[0] <= recovery_roll <= fumble_rec_range[1]

            if block_spot <= 0:
                # Ball in end zone - outcome depends on who recovers
                if kicking_team_recovers:
                    # Kicking team recovers in their own end zone = Safety
                    self._score_safety()
                    description = "BLOCKED FG! Kicking team recovers in end zone - Safety!"
                else:
                    # Defense recovers in kicking team's end zone = Touchback for defense
                    self.state.switch_possession()
                    self.state.ball_position = 20
                    self.state.down = 1
                    self.state.yards_to_go = 10
                    description = "BLOCKED FG! Defense recovers in end zone - Touchback"
            elif kicking_team_recovers:
                # Kicking team recovers
                line_of_scrimmage = spot_of_hold + 7  # Original ball position
                line_to_gain = line_of_scrimmage + self.state.yards_to_go
                final_position = block_spot

                # Check for return on rolls 17, 18, 19 (only if at/behind LOS)
                if recovery_roll in [17, 18, 19] and block_spot <= line_of_scrimmage:
                    return_dice, _return_desc = roll_chart_dice()
                    int_return_result = (
                        self.state.possession_team.special_teams.interception_return.get(
                            return_dice, "0"
                        )
                    )

                    if recovery_roll == 19:
                        # Automatic TD
                        _return_yards = 100 - block_spot
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97
                        description = (
                            f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}) - RETURN TD!"
                        )
                    else:
                        chain, touchdown, _return_yards, description = self._blocked_kick_return(
                            block_spot, (return_dice, int_return_result), "BLOCKED FG",
                            recovery_roll, "Kicking team",
                        )
                        safety = not chain.offsetting and chain.spot <= 0
                        if chain.offsetting:
                            nullified = True
                            description = self._nullify_kick_play(
                                fg_kicking_home, line_of_scrimmage, fg_down_before, fg_ytg_before, chain, "BLOCKED FG",
                            )
                        elif self.state.is_home_possession == fg_kicking_home:
                            final_position = chain.spot
                else:
                    self.state.ball_position = block_spot
                    description = f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                # Check if kicking team reached line to gain or scored
                if nullified or safety or self.state.is_home_possession != fg_kicking_home:
                    pass  # Nullified, or lost again on the return: nothing more to settle.
                elif not touchdown and final_position < line_to_gain:
                    # Only turnover on downs if it was 4th down
                    if self.state.down == 4:
                        defense_position = 100 - final_position
                        self.state.switch_possession()
                        self.state.ball_position = defense_position
                        description += " - TURNOVER ON DOWNS!"
                        # Reset down and distance for new possession
                        self.state.down = 1
                        self.state.yards_to_go = 10
                    else:
                        # Not 4th down - kicking team keeps ball, advance to next down
                        # Calculate yards lost from original LOS
                        yards_lost = line_of_scrimmage - final_position
                        self.state.down += 1
                        self.state.yards_to_go = max(1, self.state.yards_to_go + yards_lost)
                else:
                    # Reached line to gain or scored - reset downs
                    self.state.down = 1
                    self.state.yards_to_go = 10
            else:
                # Defense recovers - blocked kick lost (turnover)
                block_spot_defense = 100 - block_spot
                self.state.switch_possession()

                # Check for return on rolls 37, 38, 39
                if recovery_roll in [37, 38, 39]:
                    return_dice, _return_desc = roll_chart_dice()
                    int_return_result = (
                        self.state.possession_team.special_teams.interception_return.get(
                            return_dice, "0"
                        )
                    )

                    if recovery_roll == 39:
                        # Automatic TD
                        _return_yards = 100 - block_spot_defense
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97
                        description = (
                            f"BLOCKED FG! Defense recovers (roll {recovery_roll}) - RETURN TD!"
                        )
                    else:
                        chain, touchdown, _return_yards, description = self._blocked_kick_return(
                            block_spot_defense, (return_dice, int_return_result), "BLOCKED FG",
                            recovery_roll, "Defense",
                        )
                        safety = not chain.offsetting and chain.spot <= 0
                        if chain.offsetting:
                            nullified = True
                            description = self._nullify_kick_play(
                                fg_kicking_home, spot_of_hold + 7, fg_down_before, fg_ytg_before, chain, "BLOCKED FG",
                            )
                else:
                    self.state.ball_position = block_spot_defense
                    description = f"BLOCKED FG! Defense recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                # Reset down and distance for defense (new possession)
                if not nullified:
                    self.state.down = 1
                    self.state.yards_to_go = 10

        # Check for fumble on hold/snap (F followed by space/+/- and number, e.g., "F - 5", "F + 3")
        elif re.match(r"^F\s*([+-])\s*(\d+)", fg_result, re.IGNORECASE):
            success = False
            is_fumble = True

            # Parse the yards from fumble result (e.g., "F - 7" -> -7 yards)
            fumble_yards = 0
            match = re.match(r"^F\s*([+-])\s*(\d+)", fg_result, re.IGNORECASE)
            if match:
                sign = match.group(1)
                yards = int(match.group(2))
                fumble_yards = -yards if sign == "-" else yards

            # Fumble - defense recovers at spot of hold minus/plus the fumble yards
            # Calculate recovery spot from kicking team's perspective
            # spot_of_hold is from kicking team's perspective (ball_position - 7)
            # recovery_spot is where the ball ends up after fumble, from kicking team's perspective
            recovery_spot = max(
                1, spot_of_hold + fumble_yards
            )  # Add fumble yards (can be negative)

            # Convert recovery_spot from kicking team's perspective to defense's perspective
            # Before switch: recovery_spot is from kicking team's perspective (e.g., 59 = opponent's 41)
            # After switch: we need position from defense's perspective = 100 - recovery_spot
            fumble_spot_defense = 100 - recovery_spot

            # Switch possession (this flips ball_position from kicking team's to defense's perspective)
            self.state.switch_possession()

            # Check for return on recovery roll (like blocked FGs - rolls 37, 38, 39)
            recovery_roll, _recovery_desc = roll_chart_dice()
            touchdown = False

            if recovery_roll in [37, 38, 39]:
                return_dice, _return_desc = roll_chart_dice()
                int_return_result = (
                    self.state.possession_team.special_teams.interception_return.get(
                        return_dice, "0"
                    )
                )

                if recovery_roll == 39:
                    # Automatic TD
                    _return_yards = 100 - fumble_spot_defense
                    touchdown = True
                    self._score_touchdown()
                    self.state.ball_position = 97
                    description = f"FUMBLED SNAP! Defense recovers (roll {recovery_roll}) - RETURN TD! ({statistical_distance} yards)"
                else:
                    chain, touchdown, _return_yards, description = self._blocked_kick_return(
                        fumble_spot_defense, (return_dice, int_return_result), "FUMBLED SNAP",
                        recovery_roll, "Defense",
                    )
                    safety = not chain.offsetting and chain.spot <= 0
                    if chain.offsetting:
                        nullified = True
                        description = self._nullify_kick_play(
                            fg_kicking_home, spot_of_hold + 7, fg_down_before, fg_ytg_before, chain, "FUMBLED SNAP",
                        )
                    else:
                        description += f" ({statistical_distance} yards)"
            else:
                # No return - defense takes over at fumble spot
                self.state.ball_position = fumble_spot_defense
                description = f"FUMBLED SNAP! Defense recovers at {self.state.field_position_str()} ({statistical_distance} yards)"

            # Reset down and distance for defense (new possession)
            if not nullified:
                self.state.down = 1
                self.state.yards_to_go = 10

        # Normal field goal result - number indicates max distance kick can reach
        elif fg_result:
            try:
                # Parse the yardage from the chart
                chart_yards = int(fg_result.strip())
                # If chart yardage >= distance to goal, kick is GOOD
                success = chart_yards >= distance_to_goal
                if success:
                    description = f"Field goal GOOD! ({statistical_distance} yards, needed {distance_to_goal})"
                else:
                    description = f"Field goal NO GOOD! ({statistical_distance} yards, kick only reached {chart_yards})"
            except ValueError:
                # Unknown result, default to miss
                success = False
                description = f"Field goal NO GOOD from {statistical_distance} yards"
        else:
            # Empty result = miss
            success = False
            description = f"Field goal NO GOOD from {statistical_distance} yards"

        # Handle successful field goal
        if success and not blocked:
            self._score_field_goal()

        # Handle missed field goal (not blocked, not penalty, not fumble)
        elif not success and not blocked and not is_penalty and not is_fumble:
            # Defense gets ball at their 20 OR spot of hold, whichever is to their advantage
            # From defense perspective after switch: position = yards from their own goal
            # Lower position = closer to their own goal (bad), higher = further from goal (good)
            # But wait - after switch_possession, ball_position flips, so we need to think carefully
            #
            # Before switch: spot_of_hold is from kicking team's perspective
            # After switch: defense_at_spot = 100 - spot_of_hold (from defense's perspective)
            # Defense wants ball FURTHER from their own goal = LOWER position number after switch
            # Their 20 = position 20 after switch
            # Spot of hold after switch = 100 - spot_of_hold
            #
            # Example: kick from own 15, spot_of_hold = 8
            #   defense_at_spot = 100 - 8 = 92 (defense at their own 8 - very bad!)
            #   defense_at_20 = 20 (defense at their own 20 - better)
            #   Defense chooses 20 (lower number = further from their goal)

            defense_at_20 = 20
            defense_at_spot = 100 - max(1, spot_of_hold)

            self.state.switch_possession()

            # Defense wants ball further from their own goal (higher position number)
            # Position = yards from own goal, so higher = better field position
            if defense_at_spot > defense_at_20:
                # Spot of hold is better for defense (further from their goal)
                self.state.ball_position = defense_at_spot
            else:
                # 20 yard line is better for defense
                self.state.ball_position = defense_at_20

            self.state.down = 1
            self.state.yards_to_go = 10

        parsed.replay_down = nullified
        outcome = PlayOutcome(
            play_type=PlayType.FIELD_GOAL,
            defense_type=DefenseType.STANDARD,
            result=parsed,
            yards_gained=0,
            touchdown=touchdown,
            safety=safety,
            field_goal_made=success and not blocked,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            description=description,
        )

        self.play_log.append(outcome)
        self._use_time(10 if nullified else random.uniform(5, 10))

        return outcome

    def attempt_extra_point(self) -> tuple[bool, str]:
        """
        Attempt an extra point (1-point conversion by kick) per official rules.

        Roll offensive dice and refer to the # ON DICE column of the Special Team Chart.
        If the dice total is in a WHITE box, the point is GOOD.
        If the dice total is in a RED box, the point is NO GOOD.

        Returns: (success, description)
        """
        dice_roll, _dice_desc = roll_chart_dice()

        # Check if this roll is in the "no good" range (RED boxes)
        no_good_rolls = self.state.possession_team.special_teams.extra_point_no_good

        success = dice_roll not in no_good_rolls

        if success:
            if self.state.is_home_possession:
                team = self.state.home_chart.peripheral.short_name
                self.state.home_score += 1
                is_home = True
            else:
                team = self.state.away_chart.peripheral.short_name
                self.state.away_score += 1
                is_home = False
            self._log_score(team, is_home, "PAT", "Extra point", 1)
            description = f"Extra point GOOD! (Roll: {dice_roll})"
        else:
            description = f"Extra point NO GOOD! (Roll: {dice_roll})"

        self._recompute_game_over_after_try()
        return success, description

    def _recompute_game_over_after_try(self) -> None:
        """A last-second touchdown leaves regulation provisionally over or tied.

        Only the completed try determines the final result or the need for OT.
        """
        if (self.state.quarter == 4 and self.state.time_remaining <= 0
                and not self.state.is_overtime and not self.has_untimed_down()):
            self.state.game_over = (
                self.state.home_score != self.state.away_score
                or not self.season_rules.overtime.enabled
            )

    def attempt_two_point(
        self, play_type: PlayType, defense_type: DefenseType = None
    ) -> tuple[bool, int, str]:
        """
        Attempt a two-point conversion per official rules.

        Ball is placed on the 2-yard line and a play is called.
        If the result places the ball at or beyond the defensive Goal Line, the try is GOOD.
        If the defense returns a turnover to or beyond their opponent's Goal Line,
        the two points are awarded to the defensive team.

        Returns: (success, points_for_defense, description)
        """
        # Save current state
        original_position = self.state.ball_position
        original_down = self.state.down
        original_ytg = self.state.yards_to_go

        # Set up for 2-point conversion from the 2-yard line
        # Position 98 = 2 yards from opponent's goal line
        self.state.ball_position = 98
        self.state.down = 1
        self.state.yards_to_go = 2

        # Use default defense if not specified
        if defense_type is None:
            defense_type = DefenseType.STANDARD

        # Run the play using the normal play resolution
        # The try is untimed and belongs to the touchdown's period; a regulation
        # try is still played after the clock has expired (the game-over flag is
        # recomputed below, as attempt_extra_point does).
        start_quarter = self._last_play_start_quarter
        self._conversion_in_progress = True
        try:
            outcome = self.run_play(play_type, defense_type)
        finally:
            self._conversion_in_progress = False
            self._last_play_start_quarter = start_quarter

        # Check for turnover returned for defensive 2 points
        # Check if defense returned it all the way (defensive TD on conversion = 2 pts)
        if (outcome.turnover) and (outcome.touchdown):
            if self.state.is_home_possession:
                # Offense is home, so defense is away
                team = self.state.away_chart.peripheral.short_name
                self.state.away_score += 2
                is_home = False
            else:
                # Defense is home team
                team = self.state.home_chart.peripheral.short_name
                self.state.home_score += 2
                is_home = True
            self._log_score(team, is_home, "Def 2PT", "Defensive 2-point return", 2)
            description = "TURNOVER! Defense returns for 2 points!"
            # Restore state
            self.state.ball_position = original_position
            self.state.down = original_down
            self.state.yards_to_go = original_ytg
            return False, 2, description

        yards_gained = outcome.yards_gained if outcome.yards_gained else 0

        # For 2-point conversion, we check if the play result would put ball in end zone
        success = False
        if outcome.touchdown or not outcome.turnover and yards_gained >= 2:
            success = True

        if success:
            if self.state.is_home_possession:
                team = self.state.home_chart.peripheral.short_name
                self.state.home_score += 2
                is_home = True
            else:
                team = self.state.away_chart.peripheral.short_name
                self.state.away_score += 2
                is_home = False
            self._log_score(team, is_home, "2PT", "Two-point conversion", 2)
            description = f"Two-point conversion GOOD! ({play_type.value} for {yards_gained} yards)"
        else:
            if outcome.turnover:
                description = "Two-point conversion NO GOOD - Turnover!"
            else:
                description = (
                    f"Two-point conversion NO GOOD! ({play_type.value} for {yards_gained} yards)"
                )

        # Restore state (conversion attempt doesn't affect normal game state)
        self.state.ball_position = original_position
        self.state.down = original_down
        self.state.yards_to_go = original_ytg
        self._recompute_game_over_after_try()

        return success, 0, description

    def _log_score(
        self, team: str, is_home_team: bool, play_type: str, description: str, points: int
    ):
        """Log a scoring play."""
        quarter = self.state.quarter
        if play_type in ("PAT", "2PT", "Def 2PT") and self.state.scoring_plays:
            touchdown = self.state.scoring_plays[-1]
            if touchdown.play_type == "TD":
                # A try belongs to the TD period even after the play advances it.
                # The live quarter/time must remain untouched for subsequent flow.
                quarter = touchdown.quarter
        self.state.scoring_plays.append(
            ScoringPlay(
                quarter=quarter,
                time_remaining=self.state.time_remaining,
                team=team,
                is_home_team=is_home_team,
                play_type=play_type,
                description=description,
                points=points,
            )
        )

    def _score_touchdown(
        self, play_type: PlayType = None, yards: int = 0, *, qb_scramble: bool = False,
    ) -> None:
        """Record a touchdown with player names from roster."""
        if self.state.is_home_possession:
            team = self.state.home_chart.peripheral.short_name
            chart = self.state.home_chart
            self.state.home_score += 6
            is_home = True
        else:
            team = self.state.away_chart.peripheral.short_name
            chart = self.state.away_chart
            self.state.away_score += 6
            is_home = False

        # Generate description with player names
        description = self._generate_td_description(chart, play_type, yards)
        if qb_scramble:
            # Preserve the existing scoring-name RNG draw above: narrative repair
            # must not change the dice stream of later plays. Only the QB runs.
            roster = get_roster(chart.peripheral.team_name, chart.team_dir)
            qb = roster.qb[0] if roster.qb else "The quarterback"
            description = f"{qb} scrambled for {yards} yards. TOUCHDOWN"
        self._log_score(team, is_home, "TD", description, 6)

        # Check if this TD ends overtime (sudden death)
        if self.state.is_overtime:
            self.check_overtime_score(scored=True, was_touchdown=True, scoring_team_is_home=is_home)

    def setup_for_pat(self):
        """
        Set up game state for PAT/2-point conversion attempt after a touchdown.

        Ball is placed at the 2-yard line (position 98) for the conversion attempt.
        Possession remains with the scoring team.
        """
        self.state.ball_position = 98  # 2 yards from goal line
        self.state.down = 1
        self.state.yards_to_go = 2

    def setup_for_kickoff(self, from_safety: bool = False):
        """
        Set up game state for a kickoff.

        Args:
            from_safety: If True, kickoff is from the 20 (safety free kick).
                        If False, kickoff is from the 35 (normal kickoff).

        After a score, possession should be switched to the kicking team
        before calling this method, OR this method should be called and
        then kickoff() called with the appropriate kicking_home parameter.
        """
        if from_safety:
            self.state.ball_position = 20  # Safety free kick from own 20
        else:
            self.state.ball_position = 35  # Normal kickoff from 35
        self.state.down = 1
        self.state.yards_to_go = 10

    def _record_opening_kicker(self, kicking_home: bool) -> None:
        """Remember who kicked to open the game; later kicks never overwrite it."""
        if self.state.opening_kicking_home is None:
            self.state.opening_kicking_home = kicking_home

    def halftime_pending(self) -> bool:
        """Whether the first half has ended and the second-half kickoff is still owed.

        True from the moment a second-quarter action (play, kick, try, or penalty
        decision) advances the period until the second-half kickoff starts.
        """
        return (
            not self.state.is_overtime
            and self.state.quarter == 3
            and self._last_play_start_quarter == 2
            and not self.has_untimed_down()
        )

    def second_half_kicking_home(self) -> bool:
        """The opening receiver kicks off to start the second half.

        Legacy saves without an opening-kick record fall back to the previous
        approximation (the team without the ball kicks).
        """
        if self.state.opening_kicking_home is not None:
            return not self.state.opening_kicking_home
        return not self.state.is_home_possession

    def prepare_second_half_kickoff(self) -> None:
        """Give the ball to the second-half kicker at the normal kickoff spot."""
        self.state.is_home_possession = self.second_half_kicking_home()
        self.setup_for_kickoff()

    def _generate_td_description(self, chart: TeamChart, play_type: PlayType, yards: int) -> str:
        """Generate a touchdown description with player names."""
        # Get roster for this team
        roster = get_roster(chart.peripheral.team_name, chart.team_dir)

        if play_type is None:
            return "Touchdown"

        # Get starting QB (first in list)
        qb = roster.qb[0] if roster.qb else "The quarterback"

        # Passing touchdowns
        if play_type in [
            PlayType.SHORT_PASS,
            PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS,
            PlayType.SCREEN,
            PlayType.TE_SHORT_LONG,
        ]:
            if play_type == PlayType.SCREEN:
                receiver = roster.random_rb()
            elif play_type == PlayType.TE_SHORT_LONG:
                receiver = roster.random_te()
            else:
                receiver = roster.random_wr()
            return f"{qb} pass complete to {receiver} for {yards} yards. TOUCHDOWN"

        # Running touchdowns
        elif play_type in [
            PlayType.LINE_PLUNGE,
            PlayType.OFF_TACKLE,
            PlayType.END_RUN,
            PlayType.DRAW,
        ]:
            rb = roster.random_rb()
            return f"{rb} rushed for {yards} yards. TOUCHDOWN"

        # QB Sneak
        elif play_type == PlayType.QB_SNEAK:
            return f"{qb} QB sneak for {yards} yard. TOUCHDOWN"

        # Hail Mary
        elif play_type == PlayType.HAIL_MARY:
            receiver = roster.random_wr()
            return f"{qb} Hail Mary pass complete to {receiver}. TOUCHDOWN"

        # Default
        return f"{yards} yard touchdown" if yards else "Touchdown"

    def _score_field_goal(self, distance: int = 0):
        """Record a field goal with kicker name."""
        if self.state.is_home_possession:
            team = self.state.home_chart.peripheral.short_name
            chart = self.state.home_chart
            self.state.home_score += 3
            is_home = True
        else:
            team = self.state.away_chart.peripheral.short_name
            chart = self.state.away_chart
            self.state.away_score += 3
            is_home = False

        # Get kicker name from roster
        roster = get_roster(chart.peripheral.team_name, chart.team_dir)
        kicker = roster.k[0] if roster.k else "Kicker"

        desc = (
            f"{kicker} {distance} yard field goal is good"
            if distance > 0
            else f"{kicker} field goal is good"
        )
        self._log_score(team, is_home, "FG", desc, 3)

        # Check if this FG ends overtime (sudden death - any score wins)
        if self.state.is_overtime:
            self.check_overtime_score(
                scored=True, was_touchdown=False, scoring_team_is_home=is_home
            )

    def _score_safety(self):
        """
        Record a safety (2 points for defense).

        Per official rules: Safety scores 2 points for defense.
        The victims of the safety are awarded a free kick (kickoff or punt)
        from their own 20 yard line. The actual kick is handled separately
        via safety_free_kick() method.
        """
        # Defense scores on safety
        if self.state.is_home_possession:
            team = self.state.away_chart.peripheral.short_name
            self.state.away_score += 2
            is_home = False
        else:
            team = self.state.home_chart.peripheral.short_name
            self.state.home_score += 2
            is_home = True
        self._log_score(team, is_home, "Safety", "Safety", 2)

        # After safety, team that was scored on kicks from their 20
        # Note: possession does NOT switch here - the team that gave up the safety
        # will kick, so they keep possession temporarily for the free kick
        self.state.ball_position = 20

        # Check if this safety ends overtime (sudden death)
        if self.state.is_overtime:
            self.check_overtime_score(
                scored=True, was_touchdown=False, scoring_team_is_home=is_home
            )

    def safety_free_kick(self, use_punt: bool = False) -> PlayOutcome:
        """
        Execute the free kick after a safety per official rules.

        The team that gave up the safety may choose:
        - Kickoff from their own 20 (default)
        - Punt from their own 20

        Args:
            use_punt: If True, punt instead of kickoff

        Returns:
            PlayOutcome with the result of the free kick
        """
        self._record_play_start()
        kicking_home = self.state.is_home_possession

        if use_punt:
            # Free kick punt from own 20
            return self._handle_safety_punt(kicking_home)
        else:
            # Free kick kickoff from own 20 (instead of normal 35)
            return self._handle_safety_kickoff(kicking_home)

    def _handle_safety_kickoff(self, kicking_home: bool) -> PlayOutcome:
        """Handle kickoff after safety (from own 20 instead of 35)."""
        # Use the standard kickoff method with kickoff_spot=20
        return self.kickoff(kicking_home=kicking_home, kickoff_spot=20)

    def _handle_safety_punt(self, kicking_home: bool) -> PlayOutcome:
        """Handle punt after safety (from own 20)."""
        # Use the standard punt method with punt_from=20
        return self._handle_punt(punt_from=20)

    def _handle_end_zone_return(
        self, yards_deep_in_end_zone: int, return_yards: int, elect_touchback: bool = False
    ) -> tuple[int, bool]:
        """
        Handle return from end zone per official rules VI-12-F.

        When a team gains possession in their own end zone:
        i. They may either: (a) Elect an automatic touchback, or (b) Attempt a return.
           If a return is attempted, the end zone yardage must be counted in the return;
           if the ball is not advanced across the goal line, a touchback results.
        ii. Returns may not be attempted from on or behind the end line.

        Args:
            yards_deep_in_end_zone: How deep in end zone (0 = goal line, 9 = 1 yard from end line)
            return_yards: Yards gained on return attempt
            elect_touchback: If True, automatically take touchback

        Returns:
            Tuple of (final_field_position, is_touchback)
        """
        # Cannot return from on/behind end line (10+ yards deep)
        if yards_deep_in_end_zone >= 10:
            return 20, True  # Automatic touchback

        if elect_touchback:
            return 20, True

        # Attempt return - must count end zone yardage
        # Must advance MORE than yards_deep to cross goal line onto field
        if return_yards > yards_deep_in_end_zone:
            # Made it out of end zone - field position is return yards minus end zone yards
            field_position = return_yards - yards_deep_in_end_zone
            return field_position, False
        else:
            # Didn't make it past goal line - touchback
            return 20, True

    def _use_time(
        self, seconds: float, out_of_bounds: bool = False, *, defensive_penalty: bool = False,
    ) -> bool:
        """
        Use game clock time.

        Per official rules for asterisk (*) and dagger (†):
        - These indicate the play ended out of bounds
        - Normal timing applies EXCEPT in the last 2 minutes of 1st half
          and last 5 minutes of 2nd half, where only 10 seconds elapse
        - The play is NOT out of bounds if defense overrules or if play results in fumble

        Per official rules for 2-minute warning:
        - If a play begins with more than 2 minutes remaining in a half,
          there must be at least 2 minutes remaining when the following play begins
        - This is an official's timeout at the 2-minute warning

        Args:
            seconds: Normal time to use for the play
            out_of_bounds: True if play ended out of bounds (asterisk/dagger marker)
            defensive_penalty: Hold the period at expiry so the caller can award
                an untimed down for an accepted defensive or offsetting foul.

        Returns:
            True if 2-minute warning was triggered
        """
        two_minute_warning = False
        time_before = self.state.time_remaining

        # Check if we're in final minutes where out-of-bounds timing applies
        in_final_minutes = False
        if self.state.quarter == 2 and self.state.time_remaining <= 2.0:
            # Last 2 minutes of first half
            in_final_minutes = True
        elif self.state.quarter == 4 and self.state.time_remaining <= 5.0:
            # Last 5 minutes of second half
            in_final_minutes = True

        # Apply out-of-bounds timing if applicable
        if out_of_bounds and in_final_minutes:
            # Only 10 seconds elapse on out-of-bounds plays in final minutes
            seconds = 10.0

        minutes = seconds / 60.0
        self.state.time_remaining -= minutes

        # Check for 2-minute warning (only in Q2 and Q4)
        # 2-minute warning - clock stops at 2:00
        if (self.state.quarter == 2 or self.state.quarter == 4) and ((time_before > 2.0 and self.state.time_remaining < 2.0) and (not self.state.two_minute_warning_called)):
            self.state.time_remaining = 2.0
            self.state.two_minute_warning_called = True
            two_minute_warning = True

        # Clamp sub-second residuals to 0 to prevent phantom plays at "0:00"
        # (e.g., 0.003 minutes displays as 0:00 but doesn't trigger quarter end)
        if 0 < self.state.time_remaining < 0.0167:  # Less than 1 second
            self.state.time_remaining = 0

        if self.state.time_remaining <= 0:
            self.state.time_remaining = 0
            # Hold the period until an accepted defensive foul can award its extension.
            # This is checked after actual timing, not from an estimated snap-time threshold.
            if self.state.untimed_down_pending or defensive_penalty:
                # Keep time at 0, don't advance quarter - untimed down must be played
                pass
            elif self.state.quarter < 4:
                self.state.quarter += 1
                self.state.time_remaining = 15.0
                # Reset 2-minute warning for new half
                if self.state.quarter == 3:
                    self.state.reset_timeouts_for_half()
            elif self.state.is_overtime:
                # End of overtime period
                self._check_overtime_end()
            else:
                # End of Q4 - check for overtime or game over
                if (self.state.home_score != self.state.away_score
                        or not self.season_rules.overtime.enabled):
                    self.state.game_over = True
                # If tied, overtime will be started by the game loop

        return two_minute_warning

    def get_score_str(self) -> str:
        """Get formatted score string."""
        away_name = self.state.away_chart.short_name
        home_name = self.state.home_chart.short_name
        return f"{away_name} {self.state.away_score} - {home_name} {self.state.home_score}"

    def get_period_scores(self) -> list[dict]:
        """Return regulation and overtime scoring, including scoreless periods.

        Returns:
            Period labels, names, and each team's points from the scoring log.
        """
        last_period = max(4, self.state.quarter)
        if self.state.is_overtime:
            last_period = max(last_period, 4 + self.state.ot_period)
        for play in self.state.scoring_plays:
            last_period = max(last_period, play.quarter)
        quarter_names = {1: "1st Quarter", 2: "2nd Quarter", 3: "3rd Quarter", 4: "4th Quarter"}
        periods = []
        for quarter in range(1, last_period + 1):
            periods.append({
                "quarter": quarter,
                "label": f"{quarter}Q" if quarter <= 4 else "OT" if quarter == 5 else f"OT{quarter - 4}",
                "name": quarter_names.get(quarter, f"Overtime {quarter - 4}"),
                "home": 0,
                "away": 0,
            })
        for play in self.state.scoring_plays:
            team = "home" if play.is_home_team else "away"
            periods[play.quarter - 1][team] += play.points
        return periods

    def get_play_narrative(self, outcome: PlayOutcome) -> str:
        """Return authoritative action text without repeated resolution evidence.

        Raw resolution evidence remains on the outcome/result for technical traces.
        This query never resolves a play, changes state, or draws randomness.
        """
        if outcome.play_type == PlayType.QB_KNEEL:
            return re.sub(r" - (?:SAFETY|TURNOVER ON DOWNS)!$", "", outcome.description)
        if (outcome.touchdown and not outcome.turnover
                and outcome.result.result_type != ResultType.FUMBLE):
            narrative = outcome.description.partition(" | ")[0]
            if narrative.strip(".! ").upper() == "TOUCHDOWN":
                return "TOUCHDOWN!"
            if not re.search(r"\bTOUCHDOWN\b", narrative, flags=re.IGNORECASE):
                narrative += " TOUCHDOWN!"
            return narrative.strip()
        return outcome.description

    def get_status(self) -> dict:
        """Get current game status."""
        quarter_str = self.state.quarter
        if self.state.is_overtime:
            quarter_str = f"OT{self.state.ot_period}"
        distance_to_goal = 100 - self.state.ball_position
        down_description = format_down_and_distance(self.state.down, self.state.yards_to_go)
        if 0 < distance_to_goal <= self.state.yards_to_go:
            down_description = f"{ordinal(self.state.down)} & Goal"
        return {
            "quarter": quarter_str,
            "time": f"{int(self.state.time_remaining)}:{int((self.state.time_remaining % 1) * 60):02d}",
            "score": self.get_score_str(),
            "possession": self.state.possession_team.short_name,
            "field_position": self.state.field_position_str(),
            "down": self.state.down,
            "yards_to_go": self.state.yards_to_go,
            "down_description": down_description,
            "game_over": self.state.game_over,
            "is_overtime": self.state.is_overtime,
        }

    def can_attempt_conversion_after_touchdown(self) -> bool:
        """Allow the regulation try even after time expires, but not after OT wins."""
        return not (self.state.is_overtime and self.state.game_over)

    def can_kickoff_after_play(self, quarter_before: int | None = None) -> bool:
        """Whether a scoring play may be followed by a kick in the current period.

        Half-ending scores wait for the second-half kickoff. Expired regulation,
        untimed downs, and game-ending overtime scores never trigger a new kick.
        Quarter-one/three transitions still allow the scoring team to kick.
        `quarter_before` defaults to the engine-recorded start period of the
        most recent action.
        """
        if quarter_before is None:
            quarter_before = self._last_play_start_quarter
        return (
            not self.state.game_over
            and self.state.time_remaining > 0
            and not self.has_untimed_down()
            and not (quarter_before == 2 and self.state.quarter == 3)
        )

    def needs_overtime(self) -> bool:
        """Check if the game needs to go to overtime (tied at end of Q4)."""
        return (
            self.state.quarter == 4
            and self.state.time_remaining <= 0
            and self.state.home_score == self.state.away_score
            and not self.state.game_over
            and not self.state.is_overtime
            and not self.has_untimed_down()
            and self.season_rules.overtime.enabled
        )

    def start_overtime(self, coin_toss_winner_is_home: bool | None = None) -> str:
        """
        Start overtime period.

        Args:
            coin_toss_winner_is_home: True if home team wins coin toss, False if away.
                                     If None, randomly determined (away team calls).

        Returns:
            Description of the overtime start
        """
        # Get overtime rules for this season
        rules = self.get_overtime_rules()

        # Coin toss - visiting team calls
        if coin_toss_winner_is_home is None:
            # Random coin toss - 50/50
            coin_toss_winner_is_home = random.random() < 0.5

        self.state.ot_coin_toss_winner_is_home = coin_toss_winner_is_home

        # Start overtime
        self.state.is_overtime = True
        self.state.ot_period = 1
        self.state.quarter = 5  # OT is "quarter 5"
        self.state.time_remaining = rules.period_length_minutes
        self.state.two_minute_warning_called = False

        # Reset OT tracking
        self.state.ot_first_possession_complete = False
        self.state.ot_first_possession_scored = False
        self.state.ot_first_possession_was_td = False

        # Winner receives (per 1983 rules and most eras)
        self.state.is_home_possession = coin_toss_winner_is_home

        # Reset timeouts - each team gets 3 for OT
        self.state.home_timeouts = 3
        self.state.away_timeouts = 3

        # Set up for kickoff
        self.state.ball_position = 35  # Kickoff from 35
        self.state.down = 1
        self.state.yards_to_go = 10

        winner_name = (
            self.state.home_chart.short_name
            if coin_toss_winner_is_home
            else self.state.away_chart.short_name
        )
        return f"OVERTIME! {winner_name} wins the coin toss and will receive."

    def _check_overtime_end(self):
        """Check if overtime period has ended and handle accordingly."""
        rules = self.get_overtime_rules()

        if self.state.home_score != self.state.away_score:
            # Someone scored - game over
            self.state.game_over = True
            return

        # Still tied at end of OT period
        max_periods = rules.get_max_periods(self.state.is_playoff)

        # Reached max OT periods
        # Regular season can end in tie
        if (max_periods > 0 and self.state.ot_period >= max_periods) and (rules.can_end_in_tie_regular and (not self.state.is_playoff)):
            self.state.game_over = True
            return

        # Start another OT period (playoffs continue until someone wins)
        self.state.ot_period += 1
        self.state.quarter = 4 + self.state.ot_period
        self.state.time_remaining = rules.period_length_minutes
        self.state.two_minute_warning_called = False
        self.state.ot_first_possession_complete = False
        self.state.ot_first_possession_scored = False
        self.state.ot_first_possession_was_td = False

        # Alternate possession for new OT period
        self.state.is_home_possession = not self.state.ot_coin_toss_winner_is_home

    def check_overtime_score(
        self, scored: bool, was_touchdown: bool, scoring_team_is_home: bool
    ) -> bool:
        """
        Check if a score in overtime ends the game.

        Args:
            scored: Whether a score occurred
            was_touchdown: Whether the score was a touchdown
            scoring_team_is_home: Whether the home team scored

        Returns:
            True if game is over, False if it continues
        """
        if not self.state.is_overtime or not scored:
            return False

        rules = self.get_overtime_rules()

        if rules.format == OvertimeFormat.SUDDEN_DEATH:
            # Any score wins in sudden death
            self.state.game_over = True
            return True

        elif rules.format == OvertimeFormat.MODIFIED_SUDDEN_DEATH:
            # First possession TD wins
            if not self.state.ot_first_possession_complete:
                self.state.ot_first_possession_scored = True
                self.state.ot_first_possession_was_td = was_touchdown

                if was_touchdown:
                    # TD on first possession wins
                    self.state.game_over = True
                    return True
                else:
                    # FG on first possession - other team gets a chance
                    self.state.ot_first_possession_complete = True
                    return False
            else:
                # After first possession, any score wins
                self.state.game_over = True
                return True

        return False

    def get_overtime_rules(self) -> OvertimeRules:
        """Get the overtime rules for this game's season."""
        return season_rules_to_overtime_rules(self.season_rules)

    def get_season_rules(self) -> dict:
        """
        Get season rules as a dictionary for API/UI consumption.

        Returns:
            Dict with season rule configuration
        """
        return self.season_rules.to_dict()

    def has_untimed_down(self) -> bool:
        """
        Check if an untimed down is pending.

        Per NFL rules: No quarter may end on an accepted defensive penalty.
        An extra play is run with the clock stopped at 0:00 remaining.

        Returns:
            True if an untimed down must be played
        """
        return self.state.untimed_down_pending

    def check_untimed_down_for_defensive_penalty(self, result_description: str) -> str:
        """
        Check if an untimed down should be applied for a defensive penalty.

        Per NFL Rule 4, Section 8, Article 2: A period must be extended for one
        untimed down if there is a defensive foul on a play in which time expires,
        regardless of whether that foul results in a new set of downs.

        Per NFL Rule 16 (Overtime Procedures): All rules that apply to the end of
        the fourth quarter regarding timing and extension of a period also apply to
        the end of an overtime period. This prevents a defender from, for example,
        tackling a receiver during a Hail Mary to force a tie as time expires.

        Args:
            result_description: The current result description to potentially append to

        Returns:
            Updated result description (with "(Untimed down)" appended if applicable)
        """
        if self.state.untimed_down_pending:
            return result_description

        # Call after consuming play time; low time alone is not an extension.
        if self.state.time_remaining <= 0:
            self.state.untimed_down_pending = True
            return result_description + " (Untimed down)"

        return result_description

    def clear_untimed_down(self):
        """Clear the untimed down flag after the extra play is run."""
        self.state.untimed_down_pending = False
