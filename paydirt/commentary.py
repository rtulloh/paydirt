"""
Colorful commentary system for Paydirt football simulation.
Generates play-by-play descriptions with player names and exciting language.
"""
import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional

from .play_resolver import PlayType, ResultType


@dataclass
class TeamRoster:
    """Key players for a team used in commentary."""
    # Offense
    qb: list[str] = field(default_factory=list)  # Quarterbacks
    rb: list[str] = field(default_factory=list)  # Running backs
    wr: list[str] = field(default_factory=list)  # Wide receivers
    te: list[str] = field(default_factory=list)  # Tight ends
    ol: list[str] = field(default_factory=list)  # Offensive linemen (for run blocking mentions)

    # Defense
    dl: list[str] = field(default_factory=list)  # Defensive linemen
    lb: list[str] = field(default_factory=list)  # Linebackers
    db: list[str] = field(default_factory=list)  # Defensive backs

    # Special Teams
    k: list[str] = field(default_factory=list)   # Kickers
    p: list[str] = field(default_factory=list)   # Punters
    kr: list[str] = field(default_factory=list)  # Kick returners

    def random_qb(self) -> str:
        return random.choice(self.qb) if self.qb else "The quarterback"

    def random_rb(self) -> str:
        return random.choice(self.rb) if self.rb else "The running back"

    def random_wr(self) -> str:
        return random.choice(self.wr) if self.wr else "The receiver"

    def random_te(self) -> str:
        return random.choice(self.te) if self.te else "The tight end"

    def random_dl(self) -> str:
        return random.choice(self.dl) if self.dl else "The defensive lineman"

    def random_lb(self) -> str:
        return random.choice(self.lb) if self.lb else "The linebacker"

    def random_db(self) -> str:
        return random.choice(self.db) if self.db else "The defensive back"

    def random_defender(self) -> str:
        """Return a random defensive player."""
        all_defenders = self.dl + self.lb + self.db
        return random.choice(all_defenders) if all_defenders else "The defender"


def load_roster_from_file(team_dir: str) -> Optional[TeamRoster]:
    """Load roster from a JSON file in the team directory."""
    roster_path = os.path.join(team_dir, "roster.json")
    if os.path.exists(roster_path):
        try:
            with open(roster_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return TeamRoster(
                qb=data.get("qb", []),
                rb=data.get("rb", []),
                wr=data.get("wr", []),
                te=data.get("te", []),
                ol=data.get("ol", []),
                dl=data.get("dl", []),
                lb=data.get("lb", []),
                db=data.get("db", []),
                k=data.get("k", []),
                p=data.get("p", []),
                kr=data.get("kr", []),
            )
        except (json.JSONDecodeError, IOError):
            pass
    return None


# Cache for loaded rosters
_roster_cache: dict[str, TeamRoster] = {}


def get_roster(team_full_name: str, team_dir: str = None) -> TeamRoster:
    """
    Get roster for a team. Loads from team directory JSON file.
    
    Args:
        team_full_name: Full team name like "1972 Miami Dolphins" (used as cache key if team_dir not provided)
        team_dir: Optional path to team directory containing roster.json
    
    Returns:
        TeamRoster with player names, or empty roster if not found
    """
    cache_key = team_dir or team_full_name
    if cache_key in _roster_cache:
        return _roster_cache[cache_key]

    roster = TeamRoster()
    if team_dir:
        roster = load_roster_from_file(team_dir) or TeamRoster()
    
    _roster_cache[cache_key] = roster
    return roster


# Commentary templates
TOUCHDOWN_CALLS = [
    "TOUCHDOWN! {team}! What a play!",
    "HE'S IN! TOUCHDOWN {team}!",
    "SCORE! {team} finds the end zone!",
    "AND IT'S A TOUCHDOWN! {team} strikes!",
    "SIX POINTS! {team} punches it in!",
    "THEY SCORE! Incredible play by {team}!",
    "TOUCHDOWN! The crowd goes wild!",
    "INTO THE END ZONE! TOUCHDOWN {team}!",
]

RUSHING_TD_CALLS = [
    "{player} powers into the end zone! TOUCHDOWN {team}!",
    "{player} breaks through! TOUCHDOWN!",
    "{player} will NOT be denied! TOUCHDOWN {team}!",
    "{player} punches it in from {yards} yards out! TOUCHDOWN!",
    "A magnificent run by {player}! TOUCHDOWN {team}!",
]

PASSING_TD_CALLS = [
    "{qb} finds {receiver} in the end zone! TOUCHDOWN {team}!",
    "{qb} to {receiver}... TOUCHDOWN!",
    "What a throw by {qb}! {receiver} hauls it in for the score!",
    "{qb} launches it... {receiver} makes the catch! TOUCHDOWN {team}!",
    "A perfect strike from {qb} to {receiver}! TOUCHDOWN!",
]

BIG_RUN_CALLS = [
    "{player} breaks free! {yards} yards!",
    "{player} finds a hole and he's GONE! {yards} yards!",
    "Look at {player} go! A gain of {yards}!",
    "{player} sheds a tackle and picks up {yards} yards!",
    "Great blocking! {player} rumbles for {yards}!",
    "{player} with a burst through the line for {yards} yards!",
]

BIG_PASS_CALLS = [
    "{qb} connects with {receiver} for {yards} yards!",
    "{qb} finds {receiver} wide open! {yards} yard gain!",
    "What a catch by {receiver}! {yards} yards on the play!",
    "{qb} drops back... fires... {receiver} has it for {yards}!",
    "A beautiful throw from {qb} to {receiver}! {yards} yards!",
    "{receiver} makes a spectacular grab! {yards} yard pickup!",
]

SHORT_RUN_GAIN_CALLS = [
    "{player} picks up {yards}.",
    "A gain of {yards} on the play.",
    "{player} grinds out {yards} yards.",
    "{player} fights for {yards}.",
    "Tough running by {player} for {yards}.",
]

SHORT_PASS_GAIN_CALLS = [
    "{receiver} catches it for {yards}.",
    "A gain of {yards} on the reception.",
    "{receiver} makes the catch for {yards} yards.",
    "{receiver} holds on for {yards}.",
    "Nice grab by {receiver} for {yards}.",
]

# Check-down calls when defense limits the gain (parentheses result)
CHECK_DOWN_CALLS = [
    "{qb} had to check down to {checkdown_receiver} - {primary_receiver} was covered. {yards} yards.",
    "Good coverage forces {qb} to dump it off to {checkdown_receiver} for {yards}.",
    "{primary_receiver} blanketed! {qb} finds {checkdown_receiver} underneath for {yards}.",
    "Tight coverage! {qb} checks down to {checkdown_receiver} for a short gain of {yards}.",
    "{qb} looks deep but settles for {checkdown_receiver} for {yards}.",
    "The defense takes away the deep ball. {qb} dumps it to {checkdown_receiver} for {yards}.",
]

NO_GAIN_CALLS = [
    "{player} is stopped at the line.",
    "No gain on the play.",
    "The defense holds! No gain.",
    "{player} goes nowhere.",
    "Stuffed at the line of scrimmage!",
]

LOSS_CALLS = [
    "{player} is dropped for a loss of {yards}!",
    "Loss of {yards} on the play!",
    "{player} is hit in the backfield! Loss of {yards}!",
    "The defense blows this one up! {yards} yard loss!",
]

SACK_CALLS = [
    "SACK! {defender} brings down {qb}!",
    "{defender} gets to {qb}! SACKED for a loss of {yards}!",
    "{qb} is BURIED by {defender}!",
    "HUGE SACK! {defender} was unblocked!",
    "{defender} crashes through and sacks {qb}!",
    "DOWN GOES {qb}! {defender} with the sack!",
    "The pocket collapses! {qb} is sacked by {defender}!",
]

QB_SCRAMBLE_CALLS = [
    "{qb} scrambles out of trouble! {yards} yards!",
    "{qb} escapes the rush and picks up {yards}!",
    "Pressure! {qb} takes off and gains {yards}!",
    "{qb} buys time and scrambles for {yards}!",
    "Nobody open! {qb} tucks it and runs for {yards}!",
    "{qb} avoids the sack and scrambles for {yards}!",
    "Great escape by {qb}! Picks up {yards} on the ground!",
    "{qb} uses his legs! {yards} yard scramble!",
]

QB_SCRAMBLE_TD_CALLS = [
    "{qb} scrambles... TOUCHDOWN!",
    "{qb} escapes and takes it to the house! TOUCHDOWN!",
    "Nobody can catch {qb}! Scrambles for the TOUCHDOWN!",
    "{qb} with the legs! TOUCHDOWN on the scramble!",
]

QB_SCRAMBLE_LOSS_CALLS = [
    "{qb} scrambles but loses {yards}!",
    "{qb} tries to escape but is brought down for a loss of {yards}!",
    "Nowhere to go! {qb} scrambles but loses {yards}!",
]

INTERCEPTION_CALLS = [
    "INTERCEPTED! {defender} picks it off!",
    "PICKED OFF! {defender} jumps the route!",
    "{qb}'s pass is INTERCEPTED by {defender}!",
    "TURNOVER! {defender} with the interception!",
    "What a play by {defender}! INTERCEPTION!",
    "{defender} reads it all the way! PICKED OFF!",
    "BAD DECISION! {defender} comes away with the INT!",
]

FUMBLE_CALLS = [
    "FUMBLE! {team} recovers!",
    "HE LOST IT! {team} falls on the loose ball!",
    "The ball is out! {team} recovers the fumble!",
    "TURNOVER! Fumble recovered by {team}!",
    "A costly fumble! {team} takes over!",
]

INCOMPLETE_CALLS = [
    "Pass incomplete.",
    "The pass falls incomplete.",
    "Intended for {receiver}... incomplete.",
    "{qb}'s pass is batted away. Incomplete.",
    "No one there. Incomplete pass.",
    "The throw is off target. Incomplete.",
    "Dropped! The pass hits the ground.",
]

FIRST_DOWN_CALLS = [
    "First down {team}!",
    "That's a {team} first down!",
    "Moving the chains! First down!",
    "First down and more!",
    "{team} moves the chains!",
    "That's enough for a first down!",
]

PENALTY_OFFENSE_CALLS = [
    "FLAG DOWN! Penalty on the offense.",
    "Yellow flag! Offensive penalty.",
    "Penalty against the offense. {yards} yards.",
    "That'll cost them! {yards} yard penalty on the offense.",
]

PENALTY_DEFENSE_CALLS = [
    "FLAG! Penalty on the defense!",
    "The defense is flagged! {yards} yards!",
    "Defensive penalty! {yards} yards!",
    "Gift from the defense! {yards} yard penalty!",
]

PASS_INTERFERENCE_CALLS = [
    "FLAG! Pass interference on the defense!",
    "PI! The defender grabbed him! Automatic first down!",
    "Pass interference! Big penalty on the defense!",
    "He was all over the receiver! Pass interference!",
]

BREAKAWAY_CALLS = [
    "{player} breaks loose! HE COULD GO ALL THE WAY!",
    "LOOK OUT! {player} has daylight!",
    "{player} is GONE! Nobody's going to catch him!",
    "A HUGE hole! {player} takes off!",
    "{player} makes a man miss and he's got room to run!",
]


class Commentary:
    """Generates colorful play-by-play commentary."""

    def __init__(self, offense_roster: TeamRoster, defense_roster: TeamRoster,
                 offense_name: str, defense_name: str):
        self.off_roster = offense_roster
        self.def_roster = defense_roster
        self.off_name = offense_name
        self.def_name = defense_name

    def generate(self, play_type: PlayType, result_type: ResultType,
                 yards: int, is_first_down: bool = False,
                 is_touchdown: bool = False, is_breakaway: bool = False,
                 is_check_down: bool = False,
                 offense_recovered_fumble: bool = False) -> str:
        """Generate commentary for a play result.
        
        Args:
            play_type: The type of play called
            result_type: The result type (yards, TD, INT, etc.)
            yards: Yards gained/lost
            is_first_down: Whether the play resulted in a first down
            is_touchdown: Whether the play resulted in a touchdown
            is_breakaway: Whether this was a breakaway run
            is_check_down: Whether defense limited the gain (parentheses result)
            offense_recovered_fumble: Whether offense recovered (True) or defense (False) for fumbles
        """
        lines = []

        # Determine if this is a pass or run play
        is_pass = play_type in [
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN, PlayType.TE_SHORT_LONG
        ]

        # Get player names
        # Use starting QB (first in list) for passing plays to avoid backup QBs
        # who might also be listed as RBs (e.g., Joe Washington)
        qb = self.off_roster.qb[0] if self.off_roster.qb else "The quarterback"
        rb = self.off_roster.random_rb()
        wr = self.off_roster.random_wr()
        te = self.off_roster.random_te()
        self.def_roster.random_defender()
        db = self.def_roster.random_db()
        dl = self.def_roster.random_dl()
        lb = self.def_roster.random_lb()

        # Choose receiver based on play type
        if play_type == PlayType.TE_SHORT_LONG:
            receiver = te
        elif play_type == PlayType.SCREEN:
            # Screen pass goes to RB, but make sure it's not the same as QB
            receiver = rb
            if receiver == qb and len(self.off_roster.rb) > 1:
                # Pick a different RB
                for other_rb in self.off_roster.rb:
                    if other_rb != qb:
                        receiver = other_rb
                        break
        else:
            receiver = wr

        # Choose ball carrier for runs
        # QB Sneak means the QB runs the ball
        if play_type == PlayType.QB_SNEAK:
            ball_carrier = qb
        else:
            ball_carrier = rb

        # Generate commentary based on result type
        if result_type == ResultType.TOUCHDOWN:
            if is_pass:
                template = random.choice(PASSING_TD_CALLS)
                lines.append(template.format(
                    qb=qb, receiver=receiver, team=self.off_name, yards=yards
                ))
            else:
                template = random.choice(RUSHING_TD_CALLS)
                lines.append(template.format(
                    player=ball_carrier, team=self.off_name, yards=yards
                ))

        elif result_type == ResultType.INTERCEPTION:
            template = random.choice(INTERCEPTION_CALLS)
            lines.append(template.format(
                qb=qb, defender=db, team=self.def_name
            ))

        elif result_type == ResultType.FUMBLE:
            template = random.choice(FUMBLE_CALLS)
            recovering_team = self.off_name if offense_recovered_fumble else self.def_name
            lines.append(template.format(team=recovering_team))

        elif result_type == ResultType.SACK:
            template = random.choice(SACK_CALLS)
            lines.append(template.format(
                qb=qb, defender=random.choice([dl, lb]), yards=abs(yards)
            ))

        elif result_type == ResultType.QB_SCRAMBLE:
            # QB scramble - escaped pressure and ran
            if is_touchdown:
                template = random.choice(QB_SCRAMBLE_TD_CALLS)
                lines.append(template.format(qb=qb))
            elif yards < 0:
                template = random.choice(QB_SCRAMBLE_LOSS_CALLS)
                lines.append(template.format(qb=qb, yards=abs(yards)))
            else:
                template = random.choice(QB_SCRAMBLE_CALLS)
                lines.append(template.format(qb=qb, yards=yards))

        elif result_type == ResultType.INCOMPLETE:
            template = random.choice(INCOMPLETE_CALLS)
            lines.append(template.format(qb=qb, receiver=receiver))

        elif result_type == ResultType.PENALTY_OFFENSE:
            template = random.choice(PENALTY_OFFENSE_CALLS)
            lines.append(template.format(yards=abs(yards)))

        elif result_type == ResultType.PENALTY_DEFENSE:
            template = random.choice(PENALTY_DEFENSE_CALLS)
            lines.append(template.format(yards=yards))

        elif result_type == ResultType.PASS_INTERFERENCE:
            template = random.choice(PASS_INTERFERENCE_CALLS)
            lines.append(template.format(yards=yards))

        elif result_type == ResultType.BREAKAWAY:
            # Breakaway run - but the B column can still produce negative yardage
            if yards > 0:
                template = random.choice(BREAKAWAY_CALLS)
                lines.append(template.format(player=ball_carrier, yards=yards))
                if is_touchdown:
                    lines.append(random.choice(TOUCHDOWN_CALLS).format(team=self.off_name))
            elif yards == 0:
                template = random.choice(NO_GAIN_CALLS)
                lines.append(template.format(player=ball_carrier))
            else:
                template = random.choice(LOSS_CALLS)
                lines.append(template.format(player=ball_carrier, yards=abs(yards)))

        elif result_type == ResultType.YARDS:
            # Normal yardage play
            if is_touchdown:
                if is_pass:
                    template = random.choice(PASSING_TD_CALLS)
                    lines.append(template.format(
                        qb=qb, receiver=receiver, team=self.off_name, yards=yards
                    ))
                else:
                    template = random.choice(RUSHING_TD_CALLS)
                    lines.append(template.format(
                        player=ball_carrier, team=self.off_name, yards=yards
                    ))
            elif yards >= 15:
                # Big play
                if is_pass:
                    template = random.choice(BIG_PASS_CALLS)
                    lines.append(template.format(
                        qb=qb, receiver=receiver, yards=yards
                    ))
                else:
                    template = random.choice(BIG_RUN_CALLS)
                    lines.append(template.format(player=ball_carrier, yards=yards))
            elif yards > 0:
                # Normal gain
                if is_pass:
                    # Check-down commentary when defense limited the gain
                    if is_check_down and play_type in [PlayType.MEDIUM_PASS, PlayType.LONG_PASS]:
                        # Primary receiver was covered, had to check down to RB or TE
                        checkdown_receiver = random.choice([rb, te])
                        template = random.choice(CHECK_DOWN_CALLS)
                        lines.append(template.format(
                            qb=qb, checkdown_receiver=checkdown_receiver,
                            primary_receiver=wr, yards=yards
                        ))
                    else:
                        template = random.choice(SHORT_PASS_GAIN_CALLS)
                        lines.append(template.format(
                            receiver=receiver, yards=yards
                        ))
                else:
                    template = random.choice(SHORT_RUN_GAIN_CALLS)
                    lines.append(template.format(player=ball_carrier, yards=yards))
            elif yards == 0:
                template = random.choice(NO_GAIN_CALLS)
                lines.append(template.format(player=ball_carrier if not is_pass else receiver))
            else:
                # Loss
                template = random.choice(LOSS_CALLS)
                lines.append(template.format(
                    player=ball_carrier if not is_pass else qb, yards=abs(yards)
                ))

        # Add first down call if applicable (and not a touchdown)
        if is_first_down and not is_touchdown:
            lines.append(random.choice(FIRST_DOWN_CALLS).format(team=self.off_name))

        return " ".join(lines)
