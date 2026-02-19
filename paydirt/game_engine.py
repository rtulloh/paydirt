"""
Game engine that uses actual Paydirt team charts.
"""
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from .chart_loader import TeamChart, load_team_chart
from .utils import format_field_position, clamp_ball_position
from .play_resolver import (
    PlayType, DefenseType, PlayResult, ResultType,
    resolve_play, roll_chart_dice,
    parse_result_string, roll_white_dice, resolve_qb_sneak, resolve_hail_mary,
    resolve_play_with_penalties, PenaltyChoice, resolve_field_goal_with_penalties
)
from .penalty_handler import (
    resolve_penalty, resolve_pass_interference
)
from .commentary import get_roster
from .overtime_rules import get_overtime_rules, OvertimeRules, OvertimeFormat
from .play_events import (
    PlayTransaction, EventType,
    create_chart_lookup_event, create_fumble_event, create_recovery_event,
    create_interception_event, create_return_event, create_touchdown_event
)


@dataclass
class ScoringPlay:
    """Record of a scoring play."""
    quarter: int
    time_remaining: float
    team: str  # Team short name
    is_home_team: bool  # True if home team scored, False if away team
    play_type: str  # "TD", "FG", "PAT", "2PT", "Safety", "Def TD", "Def 2PT"
    description: str
    points: int

@dataclass
class TeamStats:
    """Game statistics for a team."""
    first_downs: int = 0
    total_yards: int = 0
    rushing_yards: int = 0
    passing_yards: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    sacks: int = 0
    sack_yards: int = 0
    interceptions_thrown: int = 0
    fumbles_lost: int = 0


@dataclass
class GameState:
    """Current state of the game."""
    home_chart: TeamChart
    away_chart: TeamChart
    home_score: int = 0
    away_score: int = 0
    quarter: int = 1
    time_remaining: float = 15.0  # minutes in quarter
    is_home_possession: bool = False  # Away receives opening kickoff
    ball_position: int = 20  # Yard line (0=own goal, 100=opponent's goal)
    down: int = 1
    yards_to_go: int = 10
    game_over: bool = False
    home_stats: TeamStats = field(default_factory=TeamStats)
    away_stats: TeamStats = field(default_factory=TeamStats)
    # Timeouts: 3 per half for each team
    home_timeouts: int = 3
    away_timeouts: int = 3
    # 2-minute warning tracking
    two_minute_warning_called: bool = False
    # Scoring log
    scoring_plays: list = field(default_factory=list)
    # Overtime tracking
    is_overtime: bool = False
    ot_period: int = 0  # Current OT period (1, 2, etc.)
    ot_first_possession_complete: bool = False
    ot_first_possession_scored: bool = False
    ot_first_possession_was_td: bool = False
    ot_coin_toss_winner_is_home: bool = False  # Who won the OT coin toss
    is_playoff: bool = False  # Is this a playoff game?
    # Untimed down tracking (defensive penalty at 0:00)
    untimed_down_pending: bool = False  # True if an untimed down must be played
    # Pending penalty to apply to next kickoff (e.g., when TD scored on return with penalty)
    pending_kickoff_penalty_yards: int = 0
    pending_kickoff_penalty_is_offense: bool = False  # True = offense committed penalty, False = defense

    @property
    def possession_team(self) -> TeamChart:
        return self.home_chart if self.is_home_possession else self.away_chart

    @property
    def defense_team(self) -> TeamChart:
        return self.away_chart if self.is_home_possession else self.home_chart

    @property
    def offense_stats(self) -> TeamStats:
        return self.home_stats if self.is_home_possession else self.away_stats

    @property
    def defense_stats(self) -> TeamStats:
        return self.away_stats if self.is_home_possession else self.home_stats

    def field_position_str(self) -> str:
        """Get human-readable field position."""
        return format_field_position(self.ball_position)

    def switch_possession(self):
        """Switch possession between teams."""
        self.is_home_possession = not self.is_home_possession
        self.ball_position = 100 - self.ball_position
        self.down = 1
        self.yards_to_go = 10

    @property
    def offense_timeouts(self) -> int:
        """Get timeouts remaining for offense."""
        return self.home_timeouts if self.is_home_possession else self.away_timeouts

    @property
    def defense_timeouts(self) -> int:
        """Get timeouts remaining for defense."""
        return self.away_timeouts if self.is_home_possession else self.home_timeouts

    def use_timeout(self, is_home: bool) -> bool:
        """
        Use a timeout for the specified team.
        Returns True if timeout was available and used, False otherwise.
        """
        if is_home:
            if self.home_timeouts > 0:
                self.home_timeouts -= 1
                return True
        else:
            if self.away_timeouts > 0:
                self.away_timeouts -= 1
                return True
        return False

    def reset_timeouts_for_half(self):
        """Reset timeouts to 3 for each team at start of second half."""
        self.home_timeouts = 3
        self.away_timeouts = 3
        self.two_minute_warning_called = False

    def advance_ball(self, yards: int) -> bool:
        """
        Advance the ball. Returns True if first down achieved.
        """
        self.ball_position += yards

        # Clamp to valid range
        if self.ball_position > 100:
            self.ball_position = 100
        elif self.ball_position < 0:
            self.ball_position = 0

        self.yards_to_go -= yards

        if self.yards_to_go <= 0:
            self.down = 1
            self.yards_to_go = min(10, 100 - self.ball_position)
            return True

        return False

    def next_down(self):
        """Advance to next down. Returns True if turnover on downs."""
        self.down += 1
        if self.down > 4:
            self.switch_possession()
            return True
        return False


@dataclass
class PlayOutcome:
    """Complete outcome of a play for the game."""
    play_type: PlayType
    defense_type: DefenseType
    result: PlayResult
    yards_gained: int = 0
    turnover: bool = False
    touchdown: bool = False
    safety: bool = False
    first_down: bool = False
    field_goal_made: bool = False
    field_position_before: str = ""
    field_position_after: str = ""
    down_before: int = 1
    down_after: int = 1
    description: str = ""
    # Penalty choice information - when a penalty occurs, offended team gets a choice
    penalty_choice: Optional[PenaltyChoice] = None
    # Whether this outcome requires a penalty decision from the user
    pending_penalty_decision: bool = False
    # Whether a penalty was accepted (vs play result)
    penalty_applied: bool = False
    # Transaction-based event chain (new architecture)
    transaction: Optional[PlayTransaction] = None


class PaydirtGameEngine:
    """
    Main game engine using actual Paydirt team charts.
    """

    def __init__(self, home_chart: TeamChart, away_chart: TeamChart):
        """
        Initialize a game between two teams.
        
        Args:
            home_chart: Home team's chart
            away_chart: Away team's chart
        """
        self.state = GameState(home_chart=home_chart, away_chart=away_chart)
        self.play_log: list[PlayOutcome] = []

    @classmethod
    def from_directories(cls, home_dir: str, away_dir: str) -> "PaydirtGameEngine":
        """Create a game by loading team charts from directories."""
        home_chart = load_team_chart(home_dir)
        away_chart = load_team_chart(away_dir)
        return cls(home_chart, away_chart)

    def kickoff(self, kicking_home: bool = True) -> PlayOutcome:
        """
        Perform a kickoff.
        
        Args:
            kicking_home: True if home team is kicking
        """
        kicking_chart = self.state.home_chart if kicking_home else self.state.away_chart
        receiving_chart = self.state.away_chart if kicking_home else self.state.home_chart

        # Roll for kickoff
        dice_roll, dice_desc = roll_chart_dice()

        # Get kickoff distance from kicking team's chart
        ko_result = kicking_chart.special_teams.kickoff.get(dice_roll, "")

        # Get return yardage from receiving team's chart
        ret_result = receiving_chart.special_teams.kickoff_return.get(dice_roll, "")

        # Parse results
        parse_result_string(ko_result)
        ret_parsed = parse_result_string(ret_result)

        # Calculate field position
        # Kickoff normally from 35, but adjust for pending penalty from previous scoring play
        kickoff_spot = 35
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

        try:
            ko_yards = int(ko_result) if ko_result and ko_result.isdigit() else 65
        except ValueError:
            ko_yards = 65

        is_touchback = False

        # Handle special kickoff results
        if "OB" in ko_result or "OUT" in ko_result.upper():
            # Out of bounds - ball at 40
            return_position = 40
        elif "TB" in ko_result.upper() or ko_yards >= 75:
            # Touchback
            return_position = 20  # Touchback at 20
            is_touchback = True
        else:
            # Normal return
            landing_spot = 100 - (kickoff_spot + ko_yards)  # Where ball lands from receiver's perspective

            # Per VI-12-F: Handle end zone returns
            # landing_spot <= 0 means ball is in or beyond the end zone
            # landing_spot = 0 is the goal line (part of end zone)
            # landing_spot < 0 is deeper in end zone (negative = yards deep)
            if landing_spot <= 0:
                # Ball in end zone - can elect touchback or attempt return
                # Per rule VI-12-F-ii: Returns cannot be attempted from on/behind end line
                # End line is 10 yards deep in end zone (landing_spot <= -10)
                if landing_spot <= -10:
                    # At or behind end line - automatic touchback, no return allowed
                    return_position = 20
                    is_touchback = True
                else:
                    # In end zone but not at end line - can attempt return
                    # Convert landing_spot to yards deep in end zone (0 = goal line, -5 = 5 yards deep)
                    yards_deep = abs(landing_spot)  # 0 = at goal line, 5 = 5 yards deep
                    try:
                        ret_yards = int(ret_result) if ret_result else 20
                    except ValueError:
                        if ret_parsed.result_type == ResultType.FUMBLE:
                            ret_yards = ret_parsed.yards
                        elif ret_parsed.result_type == ResultType.TOUCHDOWN:
                            ret_yards = 100
                        else:
                            ret_yards = 20

                    # End zone yardage counts in return
                    # Must advance past goal line (yards_deep yards) to get on field
                    if ret_yards > yards_deep:
                        # Made it out of end zone
                        return_position = ret_yards - yards_deep  # Field position
                        is_touchback = False
                    else:
                        # Didn't make it out - touchback
                        return_position = 20
                        is_touchback = True
            else:
                # Normal field return - parse return yardage first
                try:
                    ret_yards = int(ret_result) if ret_result else 20
                except ValueError:
                    if ret_parsed.result_type == ResultType.FUMBLE:
                        ret_yards = ret_parsed.yards
                    elif ret_parsed.result_type == ResultType.TOUCHDOWN:
                        ret_yards = 100
                    else:
                        ret_yards = 20

                # Check for penalty on return
                ko_penalty_yards = 0
                ko_is_offensive_penalty = False
                if "OFF" in ret_result.upper() or "DEF" in ret_result.upper():
                    # Penalty on kickoff return
                    penalty_match = re.search(r'(OFF|DEF)\s*(\d+)', ret_result.upper())
                    if penalty_match:
                        ko_penalty_yards = int(penalty_match.group(2))
                        ko_is_offensive_penalty = penalty_match.group(1) == "OFF"
                        # Use default return yardage when penalty occurs
                        ret_yards = 20

                # Calculate return position: landing spot + return yards
                return_position = landing_spot + ret_yards

                # Apply penalty on top of return
                if ko_penalty_yards > 0:
                    if ko_is_offensive_penalty:
                        # OFF penalty - subtract from return position with half-the-distance
                        effective_penalty = ko_penalty_yards
                        if return_position - effective_penalty < 1:
                            effective_penalty = max(1, return_position // 2)
                        return_position -= effective_penalty
                    else:
                        # DEF penalty - add yards to return position
                        return_position += ko_penalty_yards

                if return_position > 100:
                    return_position = 100  # Touchdown
                if return_position < 1:
                    return_position = 1  # Minimum field position

        # Set game state
        self.state.is_home_possession = not kicking_home
        self.state.ball_position = clamp_ball_position(return_position)
        self.state.down = 1
        self.state.yards_to_go = 10

        # Check for return touchdown
        touchdown = return_position >= 100
        if touchdown:
            self._score_touchdown()

        # Build description based on result
        # Add commentary for exceptional returns
        return_commentary = ""
        actual_return = 0
        if not is_touchback and "OB" not in ko_result and "OUT" not in ko_result.upper():
            # Calculate actual return yards (from landing spot to final position)
            actual_return = return_position - landing_spot if landing_spot > 0 else return_position
            if actual_return >= 40:
                return_commentary = " What a return!"
            elif actual_return >= 30:
                return_commentary = " Great return!"
            elif actual_return <= 5 and actual_return >= 0:
                return_commentary = " Excellent coverage!"
            elif actual_return < 0:
                return_commentary = " Outstanding special teams coverage!"

        dice_line = f"(KO:{dice_roll}→\"{ko_yards}\" | RT:{dice_roll}→\"{actual_return}\")"

        if touchdown:
            description = f"Kickoff {ko_yards} yards, RETURNED FOR A TOUCHDOWN!{penalty_desc} {dice_line}"
        elif is_touchback:
            description = f"Kickoff {ko_yards} yards into the end zone. Touchback.{penalty_desc} {dice_line}"
        elif "OB" in ko_result or "OUT" in ko_result.upper():
            description = f"Kickoff out of bounds! Ball at the 40.{penalty_desc} {dice_line}"
        else:
            description = f"Kickoff {ko_yards} yards, returned to {self.state.field_position_str()}.{return_commentary}{penalty_desc} {dice_line}"

        outcome = PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=ret_parsed,
            yards_gained=return_position,
            touchdown=touchdown,
            field_position_after=self.state.field_position_str(),
            description=description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 15))

        return outcome

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
        # Roll offensive dice
        dice_roll, dice_desc = roll_chart_dice()

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
            description = f"ONSIDE KICK RECOVERED by kicking team! (ON:{dice_roll}→\"REC\") Ball at own 47"
        else:
            # Receiving team gets the ball at their 53 (kicking team's 47)
            self.state.is_home_possession = not kicking_home
            self.state.ball_position = 100 - ball_position_from_kicker  # = 53 from receiver's view
            description = f"Onside kick FAILED! Receiving team recovers. (ON:{dice_roll}→\"FAIL\") Ball at own 53"

        self.state.down = 1
        self.state.yards_to_go = 10

        outcome = PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=parse_result_string(""),
            yards_gained=12,
            touchdown=False,
            field_position_after=self.state.field_position_str(),
            description=description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(3, 8))

        return outcome

    def _handle_interception(self, result: PlayResult, ball_pos_before: int, yards: int,
                              txn: Optional[PlayTransaction] = None) -> tuple:
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

        self.state.offense_stats.interceptions_thrown += 1
        def_team = self.state.defense_team.peripheral.short_name

        # Calculate raw interception spot from offense's perspective
        raw_int_spot = ball_pos_before + yards

        # Handle end zone interception rules
        # <= 0 = offense's end zone, >= 100 = defense's end zone, 1-99 = field of play
        if raw_int_spot >= 100:
            # INT in defense's end zone = TOUCHBACK
            # Defense intercepts in their own end zone, gets ball at 20
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
            self.state.switch_possession()
            self._score_touchdown()
            self.state.ball_position = 97
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
            txn.add_event(create_interception_event(
                int_spot=int_spot_from_defense,
                int_yards_downfield=yards,
                acting_team=def_team
            ))

        # Roll for interception return using defense's special teams chart
        return_dice, return_desc = roll_chart_dice()
        int_return_result = self.state.defense_team.special_teams.interception_return.get(return_dice, "0")

        # Parse return result
        return_yards = 0
        return_td = False
        try:
            if "TD" in int_return_result.upper():
                return_td = True
                return_yards = 100 - int_spot_from_defense
            elif int_return_result.lstrip('-').isdigit():
                return_yards = int(int_return_result)
            else:
                match = re.search(r'(-?\d+)', int_return_result)
                if match:
                    return_yards = int(match.group(1))
        except (ValueError, AttributeError):
            return_yards = 0

        # Add return event to transaction
        if txn:
            txn.add_event(create_return_event(
                event_type=EventType.INT_RETURN,
                return_roll=return_dice,
                return_desc=return_desc,
                return_yards=return_yards,
                chart_result=int_return_result,
                is_touchdown=(return_td or (int_spot_from_defense + return_yards >= 100)),
                acting_team=def_team
            ))

        # Switch possession and set ball position
        self.state.switch_possession()
        final_position = int_spot_from_defense + return_yards

        # Check for return touchdown BEFORE capping position
        if return_td or final_position >= 100:
            touchdown = True
            self._score_touchdown()
            self.state.ball_position = 97
            if txn:
                txn.add_event(create_touchdown_event(acting_team=def_team))
        elif final_position <= 0:
            # INT return into own end zone = TOUCHBACK at 20
            # Per NFL momentum rule, impetus from the pass means touchback, not safety
            self.state.ball_position = 20
            result.description = "INTERCEPTION! Momentum carries defender into end zone - TOUCHBACK at the 20"
        else:
            # Normal field position
            final_position = clamp_ball_position(final_position)
            self.state.ball_position = final_position

        # Store return info
        result.int_return_yards = return_yards
        result.int_return_dice = return_dice
        result.int_spot = int_spot_from_defense

        return (turnover, touchdown, safety)

    def _handle_fumble(self, result: PlayResult, ball_pos_before: int, yards: int,
                       down_before: int, ytg_before: int,
                       txn: Optional[PlayTransaction] = None) -> tuple:
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
            txn.add_event(create_fumble_event(
                yards_before_fumble=yards,
                fumble_spot=raw_fumble_spot,
                acting_team=off_team
            ))

        # Check if fumble recovery was already determined (e.g., when accepting play result after penalty)
        # If so, use the stored result instead of re-rolling
        if getattr(result, 'fumble_resolved', False):
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
            txn.add_event(create_recovery_event(
                recovery_roll=recovery_roll,
                recovery_desc=recovery_desc,
                offense_recovers=offense_recovers,
                recovery_range=fumble_rec_range,
                acting_team=off_team if offense_recovers else def_team
            ))

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
                self.state.offense_stats.fumbles_lost += 1
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
                self.state.offense_stats.fumbles_lost += 1
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
                self.state.offense_stats.fumbles_lost += 1
                self.state.switch_possession()
                self._score_touchdown()
                self.state.ball_position = 97
                result.description = "Fumble recovered by defense in end zone - TOUCHDOWN"

        else:
            # Normal field position (1-99)
            fumble_spot = raw_fumble_spot

            if offense_recovers:
                self.state.ball_position = fumble_spot

                # Check for special return on recovery rolls 17, 18, 19
                # Per rules: offense gets INT return from spot of recovery for fumbles recovered
                # with totals 17, 18, or 19. (Auto TD on 19 only applies to blocked kicks, not fumbles)
                if recovery_roll in [17, 18, 19]:
                    return_dice, return_desc = roll_chart_dice()
                    int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                    return_yards = self._parse_return_yards(int_return_result, fumble_spot)
                    new_position = fumble_spot + return_yards
                    new_position = clamp_ball_position(new_position)
                    self.state.ball_position = new_position

                    if new_position >= 100 or "TD" in str(int_return_result).upper():
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97

                    result.fumble_return_yards = return_yards
                    result.fumble_return_dice = return_dice

                # Check down/distance after recovery
                yards_gained_to_spot = fumble_spot - ball_pos_before

                if down_before == 4:
                    if yards_gained_to_spot < ytg_before:
                        # Turnover on downs even though offense recovered
                        turnover = True
                        self.state.switch_possession()
                        self.state.ball_position = 100 - fumble_spot
                    else:
                        first_down = True
                        self.state.down = 1
                        self.state.yards_to_go = 10
                        self.state.offense_stats.first_downs += 1
                else:
                    if yards_gained_to_spot >= ytg_before:
                        first_down = True
                        self.state.down = 1
                        self.state.yards_to_go = 10
                        self.state.offense_stats.first_downs += 1
                    else:
                        self.state.next_down()
                        self.state.yards_to_go = max(1, ytg_before - yards_gained_to_spot)
            else:
                # Defense recovers - fumble lost
                turnover = True
                self.state.offense_stats.fumbles_lost += 1
                fumble_spot_defense = 100 - fumble_spot

                # Check for special return on recovery rolls 37, 38, 39
                if recovery_roll in [37, 38, 39]:
                    self.state.switch_possession()

                    return_dice, return_desc = roll_chart_dice()
                    int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                    if recovery_roll == 39:
                        return_yards = 100 - fumble_spot_defense
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97
                    else:
                        return_yards = self._parse_return_yards(int_return_result, fumble_spot_defense)
                        new_position = fumble_spot_defense + return_yards
                        new_position = clamp_ball_position(new_position)
                        self.state.ball_position = new_position

                        if new_position >= 100 or "TD" in str(int_return_result).upper():
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97

                    result.fumble_return_yards = return_yards
                    result.fumble_return_dice = return_dice

                    # Add fumble return event to transaction
                    if txn:
                        txn.add_event(create_return_event(
                            event_type=EventType.FUMBLE_RETURN,
                            return_roll=return_dice,
                            return_desc=return_desc,
                            return_yards=return_yards,
                            chart_result=str(int_return_result),
                            acting_team=def_team
                        ))
                else:
                    # Normal fumble recovery by defense - no return
                    self.state.switch_possession()
                    self.state.ball_position = fumble_spot_defense

                    # Add fumble return event with 0 yards to transaction
                    if txn:
                        txn.add_event(create_return_event(
                            event_type=EventType.FUMBLE_RETURN,
                            return_roll=0,
                            return_desc="",
                            return_yards=0,
                            chart_result="0",
                            acting_team=def_team
                        ))

        # Store recovery info
        result.fumble_recovery_roll = recovery_roll
        result.fumble_spot = fumble_spot if fumble_spot <= 99 else 99
        result.fumble_recovered = offense_recovers
        result.fumble_resolved = True  # Mark as resolved so we don't re-roll on penalty acceptance

        return (turnover, touchdown, safety, first_down)

    def run_play(self, play_type: PlayType, defense_type: DefenseType,
                 out_of_bounds_designation: bool = False,
                 in_bounds_designation: bool = False,
                 punt_short_drop: bool = False,
                 punt_coffin_corner_yards: int = 0) -> PlayOutcome:
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
        if self.state.game_over:
            raise ValueError("Game is over")

        # Out of bounds designation cannot be used on punts
        if out_of_bounds_designation and play_type == PlayType.PUNT:
            out_of_bounds_designation = False

        # Handle special teams
        if play_type == PlayType.PUNT:
            return self._handle_punt(short_drop=punt_short_drop, coffin_corner_yards=punt_coffin_corner_yards)
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

        # Resolve the play using charts
        result = resolve_play(
            self.state.possession_team,
            self.state.defense_team,
            play_type,
            defense_type
        )

        # Determine if this is a running or passing play
        is_pass = play_type in [
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN, PlayType.TE_SHORT_LONG
        ]

        # Process the result
        yards = result.yards
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False

        # Apply Out of Bounds designation penalty (-5 yards)
        # Per rules: 5 yards subtracted AFTER combining offense/defense results
        # NOT subtracted from: penalties, incomplete passes, TD results, or already out of bounds
        if out_of_bounds_designation:
            # Check if penalty should NOT be applied
            skip_oob_penalty = (
                result.result_type in [ResultType.PENALTY_OFFENSE, ResultType.PENALTY_DEFENSE,
                                       ResultType.PASS_INTERFERENCE, ResultType.INCOMPLETE,
                                       ResultType.TOUCHDOWN] or
                result.touchdown or
                result.out_of_bounds  # Already out of bounds anyway
            )
            if not skip_oob_penalty and yards > 0:
                yards = max(0, yards - 5)  # Subtract 5 yards, minimum 0
                result.description += " (Out of Bounds designation: -5 yards)"

        # Apply In Bounds designation penalty (-5 yards)
        # Per rules: 5 yards subtracted from plays NOT otherwise in bounds
        # NOT subtracted from: penalties, incomplete passes, TD results, or already in bounds
        if in_bounds_designation:
            # Check if penalty should NOT be applied
            skip_ib_penalty = (
                result.result_type in [ResultType.PENALTY_OFFENSE, ResultType.PENALTY_DEFENSE,
                                       ResultType.PASS_INTERFERENCE, ResultType.INCOMPLETE,
                                       ResultType.TOUCHDOWN] or
                result.touchdown or
                not result.out_of_bounds  # Already in bounds anyway
            )
            if not skip_ib_penalty and yards > 0:
                yards = max(0, yards - 5)  # Subtract 5 yards, minimum 0
                result.description += " (In Bounds designation: -5 yards)"
                result.out_of_bounds = False  # Force in bounds

        # Handle different result types
        if result.result_type == ResultType.INTERCEPTION:
            # Use centralized interception handler
            turnover, touchdown, safety = self._handle_interception(
                result, self.state.ball_position, yards
            )

        elif result.result_type == ResultType.FUMBLE:
            # Use centralized fumble handler
            turnover, touchdown, safety, first_down = self._handle_fumble(
                result, self.state.ball_position, yards, down_before, self.state.yards_to_go
            )

        elif result.result_type == ResultType.SACK:
            self.state.offense_stats.sacks += 1
            self.state.offense_stats.sack_yards += abs(yards)
            self.state.ball_position += yards  # yards is negative
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            else:
                self.state.next_down()

        elif result.result_type == ResultType.QB_SCRAMBLE:
            # QB scramble - treat like a run play
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                self.state.next_down()

        elif result.result_type == ResultType.PENALTY_OFFENSE:
            # Full Feature Method: Roll dice to determine actual penalty yardage
            ball_pos_numeric = self.state.ball_position
            penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                result.raw_result,
                ball_pos_numeric,
                yards_gained=0,  # No gain on penalty plays
                is_return=False,
                yards_to_go=self.state.yards_to_go,
                down=self.state.down
            )
            self.state.offense_stats.penalties += 1
            self.state.offense_stats.penalty_yards += penalty_result.yards
            self.state.ball_position = new_pos
            self.state.down = new_down
            self.state.yards_to_go = new_ytg
            # Update result description with penalty details
            result.description = penalty_result.description
            yards = -penalty_result.yards  # For outcome reporting
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()

        elif result.result_type == ResultType.PENALTY_DEFENSE:
            # Full Feature Method: Roll dice to determine actual penalty yardage
            ball_pos_numeric = self.state.ball_position
            penalty_result, new_pos, new_down, new_ytg, got_first = resolve_penalty(
                result.raw_result,
                ball_pos_numeric,
                yards_gained=0,  # No gain on penalty plays
                is_return=False,
                yards_to_go=self.state.yards_to_go,
                down=self.state.down
            )
            self.state.defense_stats.penalties += 1
            self.state.defense_stats.penalty_yards += penalty_result.yards
            self.state.ball_position = new_pos
            self.state.down = new_down
            self.state.yards_to_go = new_ytg
            first_down = got_first
            # Update result description with penalty details
            result.description = penalty_result.description
            yards = penalty_result.yards  # For outcome reporting

            # Check for untimed down rule: defensive penalty at 0:00 means extra play
            if self.state.time_remaining <= 0 and not self.state.is_overtime:
                self.state.untimed_down_pending = True
                result.description += " (Untimed down)"

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
                new_pos, new_down, new_ytg = resolve_pass_interference(
                    yards, ball_pos_numeric
                )
                result.description = f"Pass interference, {yards} yards - automatic first down"

            self.state.defense_stats.penalties += 1
            self.state.defense_stats.penalty_yards += yards
            self.state.ball_position = new_pos
            self.state.down = new_down
            self.state.yards_to_go = new_ytg
            first_down = True

            # Check for untimed down rule: PI (defensive penalty) at 0:00 means extra play
            if self.state.time_remaining <= 0 and not self.state.is_overtime:
                self.state.untimed_down_pending = True
                result.description += " (Untimed down)"

        elif result.result_type == ResultType.TOUCHDOWN:
            touchdown = True
            # For direct TD results, yards is the distance to the end zone
            td_yards = 100 - self.state.ball_position if yards == 0 else yards
            self.state.ball_position = 100
            self._score_touchdown(play_type, td_yards)

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
                self.state.next_down()

        elif result.result_type == ResultType.INCOMPLETE:
            # Incomplete pass - no yardage, next down
            self.state.next_down()

        # Update stats
        if yards > 0 and not turnover:
            self.state.offense_stats.total_yards += yards
            if is_pass:
                self.state.offense_stats.passing_yards += yards
            else:
                self.state.offense_stats.rushing_yards += yards

        if first_down:
            self.state.offense_stats.first_downs += 1

        if turnover:
            self.state.offense_stats.turnovers += 1

        outcome = PlayOutcome(
            play_type=play_type,
            defense_type=defense_type,
            result=result,
            yards_gained=yards,
            turnover=turnover,
            touchdown=touchdown,
            safety=safety,
            first_down=first_down,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description
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
        if out_of_bounds_designation and result.result_type != ResultType.SACK:
            is_out_of_bounds = True

        # In Bounds designation forces clock to keep running
        if in_bounds_designation:
            is_out_of_bounds = False

        self._use_time(random.uniform(5, 40), out_of_bounds=is_out_of_bounds)

        return outcome

    def run_play_with_penalty_procedure(self, play_type: PlayType, defense_type: DefenseType,
                                         out_of_bounds_designation: bool = False,
                                         in_bounds_designation: bool = False,
                                         punt_short_drop: bool = False,
                                         punt_coffin_corner_yards: int = 0) -> PlayOutcome:
        """
        Execute an offensive play with full penalty procedure per Paydirt rules.
        
        PENALTY PROCEDURE:
        i. When a penalty occurs, offense rerolls (defense keeps original)
        ii. Offended team chooses: play result (down counts) OR penalty (down replayed)
        iii. If PI, no rerolls - defensive result cancelled, incomplete pass
        
        Returns:
            PlayOutcome with penalty_choice populated if a penalty occurred.
            If pending_penalty_decision is True, caller must call apply_penalty_decision().
        """
        if self.state.game_over:
            raise ValueError("Game is over")

        # Special teams don't use penalty procedure
        if play_type in [PlayType.PUNT, PlayType.FIELD_GOAL, PlayType.QB_SNEAK,
                         PlayType.HAIL_MARY, PlayType.SPIKE_BALL, PlayType.QB_KNEEL]:
            return self.run_play(play_type, defense_type, out_of_bounds_designation, in_bounds_designation,
                                 punt_short_drop=punt_short_drop, punt_coffin_corner_yards=punt_coffin_corner_yards)

        field_pos_before = self.state.field_position_str()
        down_before = self.state.down
        ball_pos_before = self.state.ball_position
        ytg_before = self.state.yards_to_go

        # Use the new penalty procedure
        penalty_choice = resolve_play_with_penalties(
            self.state.possession_team,
            self.state.defense_team,
            play_type,
            defense_type
        )

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
                touchdown=penalty_choice.play_result.touchdown,
                field_position_before=field_pos_before,
                down_before=down_before,
                description=penalty_choice.play_result.description,
                penalty_choice=penalty_choice,
                pending_penalty_decision=True
            )
            return outcome

        elif penalty_choice.offsetting:
            # Offsetting penalties - replay the down, 10 seconds elapse
            self._use_time(10)
            outcome = PlayOutcome(
                play_type=play_type,
                defense_type=defense_type,
                result=penalty_choice.play_result,
                yards_gained=0,
                field_position_before=field_pos_before,
                field_position_after=field_pos_before,
                down_before=down_before,
                down_after=down_before,
                description="Offsetting penalties - down replayed",
                penalty_choice=penalty_choice,
                pending_penalty_decision=False
            )
            self.play_log.append(outcome)
            return outcome

        else:
            # No penalties - process normally using existing run_play logic
            # Restore state and call run_play (which will re-roll, but that's acceptable)
            # Actually, we should use the result we already have
            return self._apply_play_result(
                play_type, defense_type, penalty_choice.play_result,
                field_pos_before, down_before, ball_pos_before, ytg_before,
                out_of_bounds_designation, in_bounds_designation
            )

    def apply_penalty_decision(self, outcome: PlayOutcome, accept_play: bool,
                                penalty_index: int = 0) -> PlayOutcome:
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
            # Apply the play result to game state
            return self._apply_play_result(
                outcome.play_type, outcome.defense_type, penalty_choice.play_result,
                field_pos_before, down_before, self.state.ball_position, self.state.yards_to_go,
                out_of_bounds_designation=False, in_bounds_designation=False
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
                    description = f"Pass interference, {penalty_opt.yards} yards - automatic first down"

                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += penalty_opt.yards
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                first_down = True
                yards = penalty_opt.yards

                # Check for untimed down rule: PI (defensive penalty) at 0:00 means extra play
                if self.state.time_remaining <= 0 and not self.state.is_overtime:
                    self.state.untimed_down_pending = True
                    description += " (Untimed down)"

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
                    auto_first_down=penalty_opt.auto_first_down
                )
                self.state.offense_stats.penalties += 1
                self.state.offense_stats.penalty_yards += penalty_result.yards
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                description = penalty_result.description
                yards = -penalty_result.yards
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
                    auto_first_down=penalty_opt.auto_first_down
                )
                self.state.defense_stats.penalties += 1
                self.state.defense_stats.penalty_yards += penalty_result.yards
                self.state.ball_position = new_pos
                self.state.down = new_down
                self.state.yards_to_go = new_ytg
                first_down = got_first
                description = penalty_result.description
                yards = penalty_result.yards

                # Check for untimed down rule: defensive penalty at 0:00 means extra play
                if self.state.time_remaining <= 0 and not self.state.is_overtime:
                    self.state.untimed_down_pending = True
                    description += " (Untimed down)"
            else:
                # Unknown penalty type
                description = f"Penalty: {penalty_opt.description}"
                yards = 0
                first_down = False

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
                penalty_applied=True  # Penalty was accepted
            )

            self.play_log.append(final_outcome)
            self._use_time(random.uniform(5, 40))

            return final_outcome

    def _apply_play_result(self, play_type: PlayType, defense_type: DefenseType,
                           result: PlayResult, field_pos_before: str, down_before: int,
                           ball_pos_before: int, ytg_before: int,
                           out_of_bounds_designation: bool, in_bounds_designation: bool) -> PlayOutcome:
        """
        Apply a play result to the game state.
        
        This is a helper method that applies the result of a play (after penalty decisions)
        to the game state. It handles all result types (yards, turnovers, TDs, etc.)
        """
        yards = result.yards
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False

        # Build transaction for this play
        txn = PlayTransaction()
        off_team = self.state.possession_team.peripheral.short_name

        # Add chart lookup event
        txn.add_event(create_chart_lookup_event(
            offense_roll=result.dice_roll,
            offense_desc=f"Roll {result.dice_roll}",
            offense_result=result.raw_result,
            defense_row=result.defense_modifier.split('→')[0] if '→' in str(result.defense_modifier) else "?",
            defense_result=result.defense_modifier,
            priority=result.result_type.value,
            acting_team=off_team
        ))

        # Determine if this is a passing play
        is_pass = play_type in [
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN, PlayType.TE_SHORT_LONG
        ]

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

        elif result.result_type == ResultType.INCOMPLETE:
            self.state.next_down()

        elif result.result_type == ResultType.QB_SCRAMBLE:
            if yards < 0:
                self.state.offense_stats.sacks += 1
                self.state.offense_stats.sack_yards += abs(yards)
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                self.state.next_down()

        elif result.result_type == ResultType.SACK:
            self.state.offense_stats.sacks += 1
            self.state.offense_stats.sack_yards += abs(yards)
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif not first_down:
                self.state.next_down()

        elif result.result_type == ResultType.TOUCHDOWN:
            touchdown = True
            # For direct TD results, yards is the distance to the end zone
            td_yards = 100 - self.state.ball_position if yards == 0 else yards
            self.state.ball_position = 100
            self._score_touchdown(play_type, td_yards)

        elif result.result_type in [ResultType.YARDS, ResultType.BREAKAWAY]:
            if is_pass:
                self.state.offense_stats.passing_yards += yards
            else:
                self.state.offense_stats.rushing_yards += yards
            self.state.offense_stats.total_yards += yards

            first_down = self.state.advance_ball(yards)

            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(play_type, yards)
            elif self.state.ball_position <= 0:
                safety = True
                self._score_safety()
            elif first_down:
                self.state.offense_stats.first_downs += 1
            elif not first_down:
                self.state.next_down()

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

        outcome = PlayOutcome(
            play_type=play_type,
            defense_type=defense_type,
            result=result,
            yards_gained=yards,
            turnover=turnover,
            touchdown=touchdown,
            safety=safety,
            first_down=first_down,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description,
            transaction=txn
        )

        self.play_log.append(outcome)

        is_out_of_bounds = result.out_of_bounds
        if result.defense_modifier:
            is_out_of_bounds = False
        if result.result_type == ResultType.FUMBLE:
            is_out_of_bounds = False
        if result.result_type == ResultType.SACK:
            is_out_of_bounds = False  # Sacks can't go out of bounds
        if out_of_bounds_designation and result.result_type != ResultType.SACK:
            is_out_of_bounds = True
        if in_bounds_designation:
            is_out_of_bounds = False

        self._use_time(random.uniform(5, 40), out_of_bounds=is_out_of_bounds)

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

        # Roll offensive dice only
        dice_roll, dice_desc = roll_chart_dice()

        # Resolve using QB Sneak rules (box color only)
        result = resolve_qb_sneak(self.state.possession_team.offense, dice_roll)

        yards = result.yards
        turnover = False
        touchdown = False
        safety = False
        first_down = False

        if result.result_type == ResultType.FUMBLE:
            # Fumble at line of scrimmage - use normal fumble handling
            # Roll for fumble recovery
            recovery_roll, recovery_desc = roll_chart_dice()
            fumble_rec_range = self.state.possession_team.peripheral.fumble_recovered_range
            offense_recovers = fumble_rec_range[0] <= recovery_roll <= fumble_rec_range[1]

            result.fumble_recovery_roll = recovery_roll
            result.fumble_spot = self.state.ball_position
            result.fumble_recovered = offense_recovers
            result.fumble_resolved = True  # Mark as resolved so we don't re-roll on penalty acceptance

            if offense_recovers:
                # Offense recovers at LOS - no gain
                turnover = False
                result.description = f"QB Sneak - Fumble RECOVERED at LOS (roll {recovery_roll})"
            else:
                # Defense recovers
                turnover = True
                self.state.offense_stats.fumbles_lost += 1
                self.state.switch_possession()  # This already flips ball_position
                result.description = f"QB Sneak - Fumble LOST! Defense recovers (roll {recovery_roll})"
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
                self.state.next_down()

        # Update stats
        if yards > 0 and not turnover:
            self.state.offense_stats.total_yards += yards
            self.state.offense_stats.rushing_yards += yards

        outcome = PlayOutcome(
            play_type=PlayType.QB_SNEAK,
            defense_type=DefenseType.STANDARD,  # Defense doesn't participate
            result=result,
            yards_gained=yards,
            first_down=first_down,
            touchdown=touchdown,
            turnover=turnover,
            safety=safety,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            description=result.description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 25))

        return outcome

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

        # Roll offensive dice only - defense doesn't participate
        dice_roll, dice_desc = roll_chart_dice()

        # Handle QT (Quick Throw) - keep rolling until we get a non-QT result
        while dice_roll in [24, 25]:
            dice_roll, dice_desc = roll_chart_dice()

        # Resolve using Hail Mary table
        result = resolve_hail_mary(dice_roll, self.state.ball_position)

        yards = result.yards
        turnover = result.turnover
        touchdown = result.touchdown
        safety = False
        first_down = False

        if result.result_type == ResultType.TOUCHDOWN:
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
            
            # Check for untimed down rule: defensive penalty at 0:00 means extra play
            if self.state.time_remaining <= 0 and not self.state.is_overtime:
                self.state.untimed_down_pending = True
                result.description += " (Untimed down)"

        elif result.result_type == ResultType.YARDS:
            # Completion for yardage
            first_down = self.state.advance_ball(yards)
            if self.state.ball_position >= 100:
                touchdown = True
                self._score_touchdown(PlayType.HAIL_MARY, yards)
            elif not first_down:
                self.state.next_down()

        elif result.result_type == ResultType.INCOMPLETE:
            # Incomplete - next down
            self.state.next_down()

        # Update passing stats
        if yards > 0 and not turnover:
            self.state.offense_stats.total_yards += yards
            self.state.offense_stats.passing_yards += yards

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
            field_position_after=self.state.field_position_str(),
            description=result.description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 15))  # End of half play

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
            raw_result="SPIKE"
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
            touchdown=False,
            safety=False,
            first_down=False,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description
        )

        self.play_log.append(outcome)

        # Spike uses minimal time - the time savings come from reducing
        # the PREVIOUS play's time from 40 to 20 seconds
        # The spike itself takes essentially no game time
        self._use_time(0.05)  # ~3 seconds for the spike itself

        return outcome

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
            description="QB takes a knee - running out the clock",
            raw_result="KNEEL"
        )

        if safety:
            result.description = "QB takes a knee in end zone - SAFETY!"

        # Advance to next down (unless safety)
        turnover = False
        if not safety:
            turnover = self.state.next_down()
            if turnover:
                result.description = "QB takes a knee - TURNOVER ON DOWNS!"

        outcome = PlayOutcome(
            play_type=PlayType.QB_KNEEL,
            defense_type=DefenseType.STANDARD,  # Defense doesn't matter
            result=result,
            yards_gained=yards,
            turnover=turnover,
            touchdown=False,
            safety=safety,
            first_down=False,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            down_before=down_before,
            down_after=self.state.down,
            description=result.description
        )

        self.play_log.append(outcome)

        # QB Kneel uses full 40 seconds (unless defense calls timeout)
        self._use_time(40)  # 40 seconds

        return outcome

    def _handle_punt(self, short_drop: bool = False, coffin_corner_yards: int = 0) -> PlayOutcome:
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
        """
        field_pos_before = self.state.ball_position
        down_before = self.state.down
        ytg_before = self.state.yards_to_go
        punting_team = self.state.possession_team
        receiving_team = self.state.defense_team

        # Check for short-drop punt (inside own 5-yard line)
        is_short_drop = short_drop and field_pos_before <= 5

        # Check for coffin corner (automatic OOB if 15+ yards subtracted)
        is_coffin_corner = coffin_corner_yards >= 15

        # Roll for punt distance
        punt_roll, punt_dice_desc = roll_chart_dice()
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

            if block_spot <= 0:
                # Safety - ball went out of own end zone
                self._score_safety()
                description = "BLOCKED PUNT! Safety!"
                turnover = False
                touchdown = False
                safety = True
            else:
                # Roll for recovery using offensive dice (kicking team)
                recovery_roll, recovery_desc = roll_chart_dice()
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
                        int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                        if recovery_roll == 19:
                            # Automatic TD
                            return_yards = 100 - block_spot
                            final_spot = 100
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}) - RETURN TD!"
                        else:
                            return_yards = self._parse_return_yards(int_return_result, block_spot)
                            new_position = block_spot + return_yards
                            new_position = clamp_ball_position(new_position)
                            final_spot = new_position
                            self.state.ball_position = new_position

                            if new_position >= 100:
                                touchdown = True
                                self._score_touchdown()
                                self.state.ball_position = 97
                                description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}), return roll {return_dice} - RETURN TD!"
                            else:
                                description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}), return roll {return_dice} for {return_yards} yards"
                    else:
                        self.state.ball_position = block_spot
                        description = f"BLOCKED PUNT! Kicking team recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                    # On 4th down, check if kicking team reached first down marker
                    # If not, it's turnover on downs (unless TD scored)
                    if down_before == 4 and not touchdown and final_spot < first_down_marker:
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
                        int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                        if recovery_roll == 39:
                            # Automatic TD
                            return_yards = 100 - block_spot_defense
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}) - RETURN TD!"
                        else:
                            return_yards = self._parse_return_yards(int_return_result, block_spot_defense)
                            new_position = block_spot_defense + return_yards
                            new_position = clamp_ball_position(new_position)
                            self.state.ball_position = new_position

                            if new_position >= 100:
                                touchdown = True
                                self._score_touchdown()
                                self.state.ball_position = 97
                                description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}), return roll {return_dice} - RETURN TD!"
                            else:
                                description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}), return roll {return_dice} for {return_yards} yards"
                    else:
                        self.state.ball_position = block_spot_defense
                        description = f"BLOCKED PUNT! Defense recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

            parsed_result = parse_result_string(punt_result)
            parsed_result.dice_roll = punt_roll
            
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
                description=description
            )
            self.play_log.append(outcome)
            self._use_time(random.uniform(3, 6))
            return outcome

        # Handle penalty on punt (before the ball is kicked)
        punt_penalty_yards = 0
        is_punt_offensive_penalty = False
        if is_penalty:
            # Parse penalty yardage from result like "OFF 15" or "DEF 10"
            penalty_match = re.search(r'(OFF|DEF)\s*(\d+)', punt_result.upper())
            if penalty_match:
                punt_penalty_yards = int(penalty_match.group(2))
                is_punt_offensive_penalty = penalty_match.group(1) == "OFF"
            # Use default punt yardage
            punt_yards = 35
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
            self.state.switch_possession()
            self.state.ball_position = 20  # Touchback at 20
            description = f"{description}Punt {punt_yards} yards into the end zone - Touchback at the 20"

            outcome = PlayOutcome(
                play_type=PlayType.PUNT,
                defense_type=DefenseType.STANDARD,
                result=parse_result_string(punt_result),
                yards_gained=punt_yards,
                field_position_before=field_pos_before,
                field_position_after=self.state.field_position_str(),
                description=description
            )
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
            return_desc = "coffin corner - out of bounds"
            self.state.ball_position = receiving_position
            self.state.switch_possession()
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
                description=full_description
            )
            self.play_log.append(outcome)
            self._use_time(random.uniform(5, 10))
            return outcome

        if is_downed:
            # Ball downed or out of bounds - no return
            return_desc = "downed"
        elif is_fair_catch:
            # Fair catch - no return
            return_desc = "fair catch"
        else:
            # Punt can be returned - roll on receiving team's punt return chart
            return_roll, return_dice_desc = roll_chart_dice()
            return_result = receiving_team.special_teams.punt_return.get(return_roll, "0")

            # Parse return result
            if return_result:
                # Check for penalty on return first (before fumble check since DEF contains F)
                if "OFF" in return_result.upper() or "DEF" in return_result.upper():
                    return_desc = f"Penalty on return: {return_result}"
                    # Parse penalty yardage from result like "OFF 15" or "DEF 10"
                    penalty_match = re.search(r'(OFF|DEF)\s*(\d+)', return_result.upper())
                    if penalty_match:
                        penalty_yards = int(penalty_match.group(2))
                        is_offensive_penalty = penalty_match.group(1) == "OFF"
                        # Offensive penalty on return: receiving team penalized, ball moves back
                        # Defensive penalty on return: kicking team penalized, ball moves forward
                        if is_offensive_penalty:
                            # Apply half-the-distance rule from receiving position
                            if receiving_position - penalty_yards < 1:
                                penalty_yards = max(1, receiving_position // 2)
                            return_yards = -penalty_yards  # Move ball back
                        else:
                            return_yards = penalty_yards  # Move ball forward
                    else:
                        return_yards = 0
                # Check for fumble on return
                elif "F" in return_result.upper():
                    # Fumble on return - punting team recovers
                    return_desc = "FUMBLE on the return!"
                    # Punting team gets ball at landing spot
                    self.state.ball_position = landing_spot
                    # Don't switch possession - punting team recovers
                    # Reset to 1st and 10 since kicking team gets fresh possession
                    self.state.down = 1
                    self.state.yards_to_go = 10

                    outcome = PlayOutcome(
                        play_type=PlayType.PUNT,
                        defense_type=DefenseType.STANDARD,
                        result=parse_result_string(punt_result),
                        yards_gained=punt_yards,
                        turnover=False,  # Punting team recovers - no turnover
                        field_position_before=field_pos_before,
                        field_position_after=self.state.field_position_str(),
                        description=f"{description}Punt {punt_yards} yards, {return_desc} Recovered at {self.state.field_position_str()}"
                    )
                    self.play_log.append(outcome)
                    self._use_time(random.uniform(5, 12))
                    return outcome
                else:
                    # Normal return yardage
                    try:
                        return_yards = int(return_result.replace("*", "").replace("†", "").strip())
                    except ValueError:
                        return_yards = 0

                    # Short-drop punt: minus yardage returns become 0 yard returns
                    # Per rules: "all minus yardage returns are zero yard returns"
                    if is_short_drop and return_yards < 0:
                        return_yards = 0

                    # Add commentary for exceptional returns
                    if return_yards >= 30:
                        return_desc = f"returned {return_yards} yards. What a return!"
                    elif return_yards >= 20:
                        return_desc = f"returned {return_yards} yards. Great return!"
                    elif return_yards > 0:
                        return_desc = f"returned {return_yards} yards"
                    elif return_yards == 0:
                        return_desc = "no return. Excellent coverage!"
                    else:
                        return_desc = f"tackled for a loss of {abs(return_yards)} yards! Outstanding special teams coverage!"

        # Switch possession and set ball position
        self.state.switch_possession()

        # Final position is receiving position plus return yards (before penalty)
        final_position = receiving_position + return_yards

        # Check for return touchdown first (before applying penalties)
        touchdown = False
        would_be_td = final_position >= 100

        if punt_penalty_yards > 0:
            if is_punt_offensive_penalty:
                # OFF penalty on receiving team
                if would_be_td:
                    # TD negated - penalty applied from CATCH POINT, not final position
                    # Half-the-distance rule: if penalty exceeds half distance to goal, use half
                    effective_penalty = punt_penalty_yards
                    if receiving_position - effective_penalty < 1:
                        effective_penalty = max(1, receiving_position // 2)
                    final_position = receiving_position - effective_penalty
                    touchdown = False
                else:
                    # No TD - apply penalty to final position with half-the-distance
                    effective_penalty = punt_penalty_yards
                    if final_position - effective_penalty < 1:
                        effective_penalty = max(1, final_position // 2)
                    final_position -= effective_penalty
            else:
                # DEF penalty on kicking team
                if would_be_td:
                    # TD stands, penalty applied to kickoff spot
                    touchdown = True
                    final_position = 100
                    self.state.pending_kickoff_penalty_yards = punt_penalty_yards
                    self.state.pending_kickoff_penalty_is_offense = False
                    punt_penalty_yards = 0  # Clear for description
                    self._score_touchdown()
                else:
                    # No TD - add yards to receiving team (no half-distance needed, moves toward opponent)
                    final_position += punt_penalty_yards
                    if final_position >= 100:
                        # DEF penalty pushes into end zone = TD
                        touchdown = True
                        final_position = 100
                        self._score_touchdown()
        elif would_be_td:
            # No penalty - normal TD
            touchdown = True
            final_position = 100
            self._score_touchdown()

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
        if punt_penalty_yards > 0:
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
        
        if return_desc:
            if "fair catch" in return_desc or "downed" in return_desc:
                description = f"{description}Punt {punt_yards} yards, {return_desc} at {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"
            elif touchdown:
                description = f"{description}Punt {punt_yards} yards, {return_desc} - TOUCHDOWN!"
            else:
                description = f"{description}Punt {punt_yards} yards, {return_desc} to {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"
        else:
            description = f"{description}Punt {punt_yards} yards to {self.state.field_position_str()}{penalty_desc}.{punt_commentary}"

        parsed_result = parse_result_string(punt_result)
        parsed_result.dice_roll = punt_roll
        parsed_result.raw_result = f"{punt_yards}{'*' if is_fair_catch else ''}"

        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=parsed_result,
            yards_gained=punt_yards,
            touchdown=touchdown,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            description=description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 12))

        return outcome

    def _evaluate_field_goal_result(self, fg_result: str, distance_to_goal: int,
                                     statistical_distance: int, spot_of_hold: int,
                                     field_pos_before: str, down_before: int,
                                     dice_roll: int) -> PlayOutcome:
        """
        Evaluate a field goal result WITHOUT applying state changes.
        Used when there's a penalty and we need to show the FG outcome for the choice.
        
        Returns a PlayOutcome describing what would happen if the play result is accepted.
        """
        parsed = parse_result_string(fg_result)
        parsed.dice_roll = dice_roll
        
        success = False
        blocked = False
        description = ""
        
        if "BK" in fg_result.upper():
            blocked = True
            description = f"BLOCKED FG! (from {statistical_distance} yards)"
        elif re.match(r'^F\s*[+-]', fg_result, re.IGNORECASE):
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
            description=description
        )

    def apply_fg_penalty_decision(self, outcome: PlayOutcome, accept_play: bool,
                                   penalty_index: int = 0) -> PlayOutcome:
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
        distance_to_goal = getattr(outcome, '_fg_distance_to_goal', 100 - self.state.ball_position)
        statistical_distance = getattr(outcome, '_fg_statistical_distance', distance_to_goal + 17)
        spot_of_hold = getattr(outcome, '_fg_spot_of_hold', self.state.ball_position - 7)
        ball_pos_before = getattr(outcome, '_fg_ball_pos_before', self.state.ball_position)
        # ytg_before retrieved but not currently used - kept for potential future use
        _ = getattr(outcome, '_fg_ytg_before', self.state.yards_to_go)
        
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
                
            elif re.match(r'^F\s*[+-]', fg_result, re.IGNORECASE):
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
            penalty_yards = penalty.yards
            
            if penalty.penalty_type == "OFF":
                # Offensive penalty - move back, rekick
                new_position = max(1, ball_pos_before - penalty_yards)
                self.state.ball_position = new_position
                description = f"Offensive penalty ({penalty_yards} yards) - rekick from {self.state.field_position_str()}"
            else:
                # Defensive penalty - move forward, rekick (or auto first down)
                new_position = min(99, ball_pos_before + penalty_yards)
                self.state.ball_position = new_position
                if penalty.auto_first_down:
                    # Auto first down - offense keeps ball with new set of downs
                    self.state.down = 1
                    self.state.yards_to_go = max(1, 100 - new_position)
                    description = f"Defensive penalty ({penalty_yards} yards + auto 1st down) - 1st down at {self.state.field_position_str()}"
                else:
                    description = f"Defensive penalty ({penalty_yards} yards) - rekick from {self.state.field_position_str()}"
            
            outcome.field_goal_made = False
            outcome.field_position_after = self.state.field_position_str()
            outcome.description = description
            outcome.pending_penalty_decision = False
        
        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 10))
        
        return outcome

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
                reroll_log=fg_roll_result.reroll_log
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
                pending_penalty_decision=False
            )
            self.play_log.append(outcome)
            return outcome

        # Handle non-offsetting penalties - offended team gets a choice
        if fg_roll_result.penalty_options and not fg_roll_result.offsetting:
            # We need to evaluate what the FG result would be, then let offended team choose
            # Build the FG outcome first (without applying state changes)
            fg_outcome = self._evaluate_field_goal_result(
                fg_result, distance_to_goal, statistical_distance, spot_of_hold,
                field_pos_before, down_before, dice_roll
            )
            
            # Create a PenaltyChoice for the outcome
            penalty_choice = PenaltyChoice(
                play_result=fg_outcome.result,
                penalty_options=fg_roll_result.penalty_options,
                offended_team=fg_roll_result.offended_team,
                offsetting=False,
                is_pass_interference=False,
                original_defense_result="",
                reroll_log=fg_roll_result.reroll_log
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
        is_penalty = False
        is_fumble = False
        description = ""

        # Check for blocked kick per official rules:
        # - Move ball forward/backward the yards shown from spot of hold
        # - Roll offensive dice for recovery (same as fumble)
        # - Defense gets INT return for blocked kicks lost (rolls 19, 39 = auto TD)
        # - Offense gets INT return for blocked kicks recovered at/behind LOS with rolls 17, 18, 19
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
            recovery_roll, recovery_desc = roll_chart_dice()
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
                    return_dice, return_desc = roll_chart_dice()
                    int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                    if recovery_roll == 19:
                        # Automatic TD
                        return_yards = 100 - block_spot
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97
                        description = f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}) - RETURN TD!"
                    else:
                        return_yards = self._parse_return_yards(int_return_result, block_spot)
                        final_position = block_spot + return_yards
                        final_position = clamp_ball_position(final_position)
                        self.state.ball_position = final_position

                        if final_position >= 100:
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}), return roll {return_dice} - RETURN TD!"
                        else:
                            description = f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}), return roll {return_dice} for {return_yards} yards"
                else:
                    self.state.ball_position = block_spot
                    description = f"BLOCKED FG! Kicking team recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                # Check if kicking team reached line to gain or scored
                if not touchdown and final_position < line_to_gain:
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
                    return_dice, return_desc = roll_chart_dice()
                    int_return_result = self.state.possession_team.special_teams.interception_return.get(return_dice, "0")

                    if recovery_roll == 39:
                        # Automatic TD
                        return_yards = 100 - block_spot_defense
                        touchdown = True
                        self._score_touchdown()
                        self.state.ball_position = 97
                        description = f"BLOCKED FG! Defense recovers (roll {recovery_roll}) - RETURN TD!"
                    else:
                        return_yards = self._parse_return_yards(int_return_result, block_spot_defense)
                        new_position = block_spot_defense + return_yards
                        new_position = clamp_ball_position(new_position)
                        self.state.ball_position = new_position

                        if new_position >= 100:
                            touchdown = True
                            self._score_touchdown()
                            self.state.ball_position = 97
                            description = f"BLOCKED FG! Defense recovers (roll {recovery_roll}), return roll {return_dice} - RETURN TD!"
                        else:
                            description = f"BLOCKED FG! Defense recovers (roll {recovery_roll}), return roll {return_dice} for {return_yards} yards"
                else:
                    self.state.ball_position = block_spot_defense
                    description = f"BLOCKED FG! Defense recovers (roll {recovery_roll}) at {self.state.field_position_str()}"

                # Reset down and distance for defense (new possession)
                self.state.down = 1
                self.state.yards_to_go = 10

        # Check for fumble on hold/snap (F followed by space/+/- and number, e.g., "F - 5", "F + 3")
        elif re.match(r'^F\s*[+-]', fg_result, re.IGNORECASE):
            success = False
            is_fumble = True
            # Fumble - defense recovers at spot of hold
            # Set ball position first (from kicking team's perspective), then switch
            self.state.ball_position = max(1, spot_of_hold)
            self.state.switch_possession()  # This flips ball_position to defense's perspective
            description = f"FUMBLED SNAP! Recovered at {self.state.field_position_str()}"

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

        outcome = PlayOutcome(
            play_type=PlayType.FIELD_GOAL,
            defense_type=DefenseType.STANDARD,
            result=parsed,
            yards_gained=0,
            touchdown=touchdown,
            field_goal_made=success and not blocked,
            field_position_before=field_pos_before,
            field_position_after=self.state.field_position_str(),
            description=description
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 10))

        return outcome

    def attempt_extra_point(self) -> tuple[bool, str]:
        """
        Attempt an extra point (1-point conversion by kick) per official rules.
        
        Roll offensive dice and refer to the # ON DICE column of the Special Team Chart.
        If the dice total is in a WHITE box, the point is GOOD.
        If the dice total is in a RED box, the point is NO GOOD.
        
        Returns: (success, description)
        """
        dice_roll, dice_desc = roll_chart_dice()

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

        return success, description

    def attempt_two_point(self, play_type: PlayType, defense_type: DefenseType = None) -> tuple[bool, int, str]:
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
        outcome = self.run_play(play_type, defense_type)

        # Check for turnover returned for defensive 2 points
        if outcome.turnover:
            # Check if defense returned it all the way (defensive TD on conversion = 2 pts)
            if outcome.touchdown:
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
        if outcome.touchdown:
            success = True
        elif not outcome.turnover and yards_gained >= 2:
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
                description = f"Two-point conversion NO GOOD! ({play_type.value} for {yards_gained} yards)"

        # Restore state (conversion attempt doesn't affect normal game state)
        self.state.ball_position = original_position
        self.state.down = original_down
        self.state.yards_to_go = original_ytg

        return success, 0, description

    def _log_score(self, team: str, is_home_team: bool, play_type: str, description: str, points: int):
        """Log a scoring play."""
        self.state.scoring_plays.append(ScoringPlay(
            quarter=self.state.quarter,
            time_remaining=self.state.time_remaining,
            team=team,
            is_home_team=is_home_team,
            play_type=play_type,
            description=description,
            points=points
        ))

    def _score_touchdown(self, play_type: PlayType = None, yards: int = 0):
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
        self._log_score(team, is_home, "TD", description, 6)

        # Check if this TD ends overtime (sudden death)
        if self.state.is_overtime:
            self.check_overtime_score(scored=True, was_touchdown=True, scoring_team_is_home=is_home)

    def _generate_td_description(self, chart: TeamChart, play_type: PlayType, yards: int) -> str:
        """Generate a touchdown description with player names."""
        # Get roster for this team
        roster = get_roster(chart.peripheral.team_name, chart.team_dir)


        if play_type is None:
            return "Touchdown"

        # Get starting QB (first in list)
        qb = roster.qb[0] if roster.qb else "The quarterback"

        # Passing touchdowns
        if play_type in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS,
                         PlayType.SCREEN, PlayType.TE_SHORT_LONG]:
            if play_type == PlayType.SCREEN:
                receiver = roster.random_rb()
            elif play_type == PlayType.TE_SHORT_LONG:
                receiver = roster.random_te()
            else:
                receiver = roster.random_wr()
            return f"{qb} pass complete to {receiver} for {yards} yards. TOUCHDOWN"

        # Running touchdowns
        elif play_type in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN, PlayType.DRAW]:
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

        desc = f"{kicker} {distance} yard field goal is good" if distance > 0 else f"{kicker} field goal is good"
        self._log_score(team, is_home, "FG", desc, 3)

        # Check if this FG ends overtime (sudden death - any score wins)
        if self.state.is_overtime:
            self.check_overtime_score(scored=True, was_touchdown=False, scoring_team_is_home=is_home)

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
            self.check_overtime_score(scored=True, was_touchdown=False, scoring_team_is_home=is_home)

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
        kicking_home = self.state.is_home_possession

        if use_punt:
            # Free kick punt from own 20
            return self._handle_safety_punt(kicking_home)
        else:
            # Free kick kickoff from own 20 (instead of normal 35)
            return self._handle_safety_kickoff(kicking_home)

    def _handle_safety_kickoff(self, kicking_home: bool) -> PlayOutcome:
        """Handle kickoff after safety (from own 20 instead of 35)."""
        kicking_chart = self.state.home_chart if kicking_home else self.state.away_chart
        receiving_chart = self.state.away_chart if kicking_home else self.state.home_chart

        # Roll for kickoff
        dice_roll, dice_desc = roll_chart_dice()
        ko_result = kicking_chart.special_teams.kickoff.get(dice_roll, "50")
        ret_result = receiving_chart.special_teams.kickoff_return.get(dice_roll, "20")

        parse_result_string(ko_result)
        ret_parsed = parse_result_string(ret_result)

        try:
            ko_yards = int(ko_result) if ko_result and ko_result.isdigit() else 50
        except ValueError:
            ko_yards = 50

        # Handle special kickoff results
        if "OB" in ko_result or "OUT" in ko_result.upper():
            # Out of bounds - ball at 40 from kicking team's perspective
            # From own 20, that's receiving team's 40
            return_position = 40
        elif "TB" in ko_result.upper() or ko_yards >= 80:
            # Touchback (kick from 20 + 80 yards = end zone)
            return_position = 20
        else:
            # Normal return - kick from own 20
            landing_spot = 100 - (20 + ko_yards)  # From receiver's perspective

            # Per VI-12-F: Handle end zone returns
            # landing_spot <= 0 means ball is in or beyond the end zone
            if landing_spot <= 0:
                # Ball in end zone
                if landing_spot <= -10:
                    # At or behind end line - automatic touchback
                    return_position = 20
                else:
                    # In end zone but not at end line - can attempt return
                    yards_deep = abs(landing_spot)
                    try:
                        ret_yards = int(ret_result) if ret_result else 20
                    except ValueError:
                        ret_yards = 20
                    if ret_yards > yards_deep:
                        return_position = ret_yards - yards_deep
                    else:
                        return_position = 20
            else:
                # Normal field return
                try:
                    ret_yards = int(ret_result) if ret_result else 20
                except ValueError:
                    ret_yards = 20
                return_position = landing_spot + ret_yards
                if return_position > 100:
                    return_position = 100

        # Switch possession to receiving team
        self.state.is_home_possession = not kicking_home
        self.state.ball_position = return_position
        self.state.down = 1
        self.state.yards_to_go = 10

        touchdown = return_position >= 100
        if touchdown:
            self._score_touchdown()

        outcome = PlayOutcome(
            play_type=PlayType.KICKOFF,
            defense_type=DefenseType.STANDARD,
            result=ret_parsed,
            yards_gained=return_position,
            touchdown=touchdown,
            field_position_after=self.state.field_position_str(),
            description=f"Safety free kick {ko_yards} yards, returned to {self.state.field_position_str()}"
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 15))

        return outcome

    def _handle_safety_punt(self, kicking_home: bool) -> PlayOutcome:
        """Handle punt after safety (from own 20)."""
        kicking_chart = self.state.home_chart if kicking_home else self.state.away_chart
        receiving_chart = self.state.away_chart if kicking_home else self.state.home_chart

        # Roll for punt
        punt_roll, punt_desc = roll_chart_dice()
        punt_result = kicking_chart.special_teams.punt.get(punt_roll, "40")

        # Check for special markers
        is_downed = "†" in punt_result or "+" in punt_result
        is_fair_catch = "*" in punt_result

        # Parse punt distance
        punt_clean = punt_result.replace("†", "").replace("*", "").replace("+", "").strip()
        try:
            punt_yards = int(punt_clean) if punt_clean.isdigit() else 40
        except ValueError:
            punt_yards = 40

        # Calculate landing spot from receiver's perspective
        # Punt from own 20
        landing_spot_from_kicker = 20 + punt_yards
        landing_spot = 100 - landing_spot_from_kicker

        return_yards = 0

        # Per VI-12-F: Handle end zone returns
        # landing_spot <= 0 means ball is in or beyond the end zone
        if landing_spot <= 0:
            # Ball in end zone
            if landing_spot <= -10:
                # At or behind end line - automatic touchback
                return_position = 20
            elif is_downed or is_fair_catch:
                # Downed or fair catch in end zone = touchback
                return_position = 20
            else:
                # Attempt return from end zone
                yards_deep = abs(landing_spot)
                ret_roll, ret_desc = roll_chart_dice()
                ret_result = receiving_chart.special_teams.punt_return.get(ret_roll, "5")
                try:
                    return_yards = int(ret_result.replace("*", "").replace("†", "").strip())
                except ValueError:
                    return_yards = 5
                if return_yards > yards_deep:
                    return_position = return_yards - yards_deep
                else:
                    return_position = 20
        else:
            # Normal field position
            if is_downed or is_fair_catch:
                return_position = landing_spot
            else:
                ret_roll, ret_desc = roll_chart_dice()
                ret_result = receiving_chart.special_teams.punt_return.get(ret_roll, "5")
                try:
                    return_yards = int(ret_result.replace("*", "").replace("†", "").strip())
                except ValueError:
                    return_yards = 5
                return_position = landing_spot + return_yards
                if return_position > 100:
                    return_position = 100

        # Switch possession
        self.state.is_home_possession = not kicking_home
        self.state.ball_position = return_position
        self.state.down = 1
        self.state.yards_to_go = 10

        touchdown = return_position >= 100
        if touchdown:
            self._score_touchdown()

        parsed_result = parse_result_string(punt_result)
        parsed_result.dice_roll = punt_roll
        parsed_result.raw_result = f"{punt_yards}{'*' if is_fair_catch else ''}"

        outcome = PlayOutcome(
            play_type=PlayType.PUNT,
            defense_type=DefenseType.STANDARD,
            result=parsed_result,
            yards_gained=return_yards,
            touchdown=touchdown,
            field_position_after=self.state.field_position_str(),
            description=f"Safety free kick punt {punt_yards} yards to {self.state.field_position_str()}"
        )

        self.play_log.append(outcome)
        self._use_time(random.uniform(5, 12))

        return outcome

    def _handle_end_zone_return(self, yards_deep_in_end_zone: int, return_yards: int,
                                 elect_touchback: bool = False) -> tuple[int, bool]:
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

    def _parse_return_yards(self, return_result: str, current_position: int) -> int:
        """
        Parse return yards from a special teams chart result.
        
        Args:
            return_result: The result string from the chart (e.g., "20", "TD", "-5")
            current_position: Current ball position for TD calculation
        
        Returns:
            Number of return yards
        """
        if not return_result:
            return 0

        return_result = str(return_result).strip()

        # Handle TD result
        if "TD" in return_result.upper():
            return 100 - current_position

        # Try to extract numeric value
        try:
            if return_result.lstrip('-').isdigit():
                return int(return_result)
            else:
                # Try to extract number from result
                match = re.search(r'(-?\d+)', return_result)
                if match:
                    return int(match.group(1))
        except (ValueError, AttributeError):
            pass

        return 0

    def _use_time(self, seconds: float, out_of_bounds: bool = False) -> bool:
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
        if (self.state.quarter == 2 or self.state.quarter == 4):
            if time_before > 2.0 and self.state.time_remaining < 2.0:
                if not self.state.two_minute_warning_called:
                    # 2-minute warning - clock stops at 2:00
                    self.state.time_remaining = 2.0
                    self.state.two_minute_warning_called = True
                    two_minute_warning = True

        if self.state.time_remaining <= 0:
            self.state.time_remaining = 0
            # Don't advance quarter if untimed down is pending (defensive penalty at 0:00)
            # Per NFL rules: No quarter may end on an accepted defensive penalty
            if self.state.untimed_down_pending:
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
                if self.state.home_score != self.state.away_score:
                    self.state.game_over = True
                # If tied, overtime will be started by the game loop

        return two_minute_warning

    def get_score_str(self) -> str:
        """Get formatted score string."""
        away_name = self.state.away_chart.short_name
        home_name = self.state.home_chart.short_name
        return f"{away_name} {self.state.away_score} - {home_name} {self.state.home_score}"

    def get_status(self) -> dict:
        """Get current game status."""
        quarter_str = self.state.quarter
        if self.state.is_overtime:
            quarter_str = f"OT{self.state.ot_period}"
        return {
            "quarter": quarter_str,
            "time": f"{int(self.state.time_remaining)}:{int((self.state.time_remaining % 1) * 60):02d}",
            "score": self.get_score_str(),
            "possession": self.state.possession_team.short_name,
            "field_position": self.state.field_position_str(),
            "down": self.state.down,
            "yards_to_go": self.state.yards_to_go,
            "game_over": self.state.game_over,
            "is_overtime": self.state.is_overtime,
        }

    def needs_overtime(self) -> bool:
        """Check if the game needs to go to overtime (tied at end of Q4)."""
        return (self.state.quarter == 4 and
                self.state.time_remaining <= 0 and
                self.state.home_score == self.state.away_score and
                not self.state.game_over and
                not self.state.is_overtime)

    def start_overtime(self, coin_toss_winner_is_home: bool = None) -> str:
        """
        Start overtime period.
        
        Args:
            coin_toss_winner_is_home: True if home team wins coin toss, False if away.
                                     If None, randomly determined (away team calls).
        
        Returns:
            Description of the overtime start
        """
        # Get overtime rules for this season
        year = self.state.home_chart.peripheral.year
        rules = get_overtime_rules(year)

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

        winner_name = self.state.home_chart.short_name if coin_toss_winner_is_home else self.state.away_chart.short_name
        return f"OVERTIME! {winner_name} wins the coin toss and will receive."

    def _check_overtime_end(self):
        """Check if overtime period has ended and handle accordingly."""
        year = self.state.home_chart.peripheral.year
        rules = get_overtime_rules(year)

        if self.state.home_score != self.state.away_score:
            # Someone scored - game over
            self.state.game_over = True
            return

        # Still tied at end of OT period
        max_periods = rules.get_max_periods(self.state.is_playoff)

        if max_periods > 0 and self.state.ot_period >= max_periods:
            # Reached max OT periods
            if rules.can_end_in_tie_regular and not self.state.is_playoff:
                # Regular season can end in tie
                self.state.game_over = True
                return

        # Start another OT period (playoffs continue until someone wins)
        self.state.ot_period += 1
        self.state.time_remaining = rules.period_length_minutes
        self.state.two_minute_warning_called = False
        self.state.ot_first_possession_complete = False
        self.state.ot_first_possession_scored = False
        self.state.ot_first_possession_was_td = False

        # Alternate possession for new OT period
        self.state.is_home_possession = not self.state.ot_coin_toss_winner_is_home

    def check_overtime_score(self, scored: bool, was_touchdown: bool, scoring_team_is_home: bool) -> bool:
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

        year = self.state.home_chart.peripheral.year
        rules = get_overtime_rules(year)

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
        year = self.state.home_chart.peripheral.year
        return get_overtime_rules(year)

    def has_untimed_down(self) -> bool:
        """
        Check if an untimed down is pending.
        
        Per NFL rules: No quarter may end on an accepted defensive penalty.
        An extra play is run with the clock stopped at 0:00 remaining.
        
        Returns:
            True if an untimed down must be played
        """
        return self.state.untimed_down_pending

    def clear_untimed_down(self):
        """Clear the untimed down flag after the extra play is run."""
        self.state.untimed_down_pending = False
