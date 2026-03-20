"""
Result Formatter for Paydirt Web UI.

Pure presentation layer - takes PlayOutcome and returns UI-ready formatted result.
No game logic here - purely formatting for display purposes.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .play_resolver import ResultType
from .game_state import PlayOutcome
from .commentary import Commentary, TeamRoster


@dataclass
class FormattedPlayResult:
    """UI-ready formatted play result."""

    headline: str
    commentary: str = ""

    yards: int = 0
    is_gain: bool = False

    big_play_factor: int = 0
    big_play_type: str = "normal"

    is_stuffed: bool = False
    is_big_play: bool = False
    is_explosive: bool = False
    is_turnover: bool = False
    is_interception: bool = False
    is_fumble: bool = False
    is_touchdown: bool = False
    is_first_down: bool = False
    is_safety: bool = False
    is_sack: bool = False
    is_breakaway: bool = False
    is_return: bool = False
    is_coffin_corner: bool = False

    pending_penalty: bool = False
    penalty_description: str = ""
    penalty_options: List[Dict[str, Any]] = field(default_factory=list)
    penalty_offended_team: str = ""


class ResultFormatter:
    """
    Formats PlayOutcome for Web UI consumption.

    Takes resolved play data from the game engine and returns UI-ready format.
    Does NOT contain game logic - purely presentation.
    """

    def __init__(self, offense_team: str, defense_team: str,
                 offense_roster: Optional[Dict] = None,
                 defense_roster: Optional[Dict] = None):
        self.offense_team = offense_team
        self.defense_team = defense_team
        self.offense_roster = offense_roster or {}
        self.defense_roster = defense_roster or {}

    def format(self, outcome: PlayOutcome) -> FormattedPlayResult:
        """Main formatting method - converts PlayOutcome to UI-ready format."""

        result = outcome.result
        yards = outcome.yards_gained

        headline = self._get_headline(outcome, result)
        commentary = self._get_commentary(outcome, result)
        big_play_factor, big_play_type = self._get_big_play_info(outcome, result)
        flags = self._get_flags(outcome, result, yards)
        penalty_info = self._get_penalty_info(outcome)

        if penalty_info['pending']:
            headline = f"PENALTY: {penalty_info['description']}"

        return FormattedPlayResult(
            headline=headline,
            commentary=commentary,
            yards=yards,
            is_gain=yards > 0,
            big_play_factor=big_play_factor,
            big_play_type=big_play_type,
            pending_penalty=penalty_info['pending'],
            penalty_description=penalty_info['description'],
            penalty_options=penalty_info['options'],
            penalty_offended_team=penalty_info['offended_team'],
            **flags
        )

    def _get_headline(self, outcome: PlayOutcome, result) -> str:
        """Generate main display headline."""
        if outcome.pending_penalty_decision:
            return "PENALTY ON THE PLAY!"
        
        if outcome.touchdown:
            return "TOUCHDOWN!"

        if outcome.turnover:
            if "INT" in str(result.result_type):
                return "INTERCEPTED!"
            return "FUMBLE!"

        if outcome.safety:
            return "SAFETY!"

        yards = outcome.yards_gained

        if result.result_type == ResultType.SACK:
            return f"SACKED for {abs(yards)}!"

        if result.result_type == ResultType.BREAKAWAY:
            if yards <= 0:
                return f"Stuffed ({yards})"
            return f"BREAKAWAY! +{yards}"

        if result.result_type == ResultType.INCOMPLETE:
            return "Incomplete"

        if result.result_type == ResultType.PENALTY_OFFENSE:
            return f"OFFENSIVE PENALTY ({abs(yards)} yds)"

        if result.result_type == ResultType.PENALTY_DEFENSE:
            return f"DEFENSIVE PENALTY! +{yards} yds"

        if result.result_type == ResultType.PASS_INTERFERENCE:
            return f"PASS INTERFERENCE! +{yards} yds"

        if yards > 0:
            return f"Gain of {yards}"
        elif yards < 0:
            return f"Loss of {abs(yards)}"
        return "No gain"

    def _get_commentary(self, outcome: PlayOutcome, result) -> str:
        """Generate colorful commentary from commentary.py system."""
        off_roster = TeamRoster(
            qb=self.offense_roster.get('qb', []),
            rb=self.offense_roster.get('rb', []),
            wr=self.offense_roster.get('wr', []),
            te=self.offense_roster.get('te', []),
            ol=self.offense_roster.get('ol', []),
            dl=self.defense_roster.get('dl', []),
            lb=self.defense_roster.get('lb', []),
            db=self.defense_roster.get('db', []),
            k=self.defense_roster.get('k', []),
            p=self.defense_roster.get('p', []),
            kr=self.defense_roster.get('kr', []),
        )
        def_roster = TeamRoster(
            qb=self.defense_roster.get('qb', []),
            rb=self.defense_roster.get('rb', []),
            wr=self.defense_roster.get('wr', []),
            te=self.defense_roster.get('te', []),
            ol=self.defense_roster.get('ol', []),
            dl=self.defense_roster.get('dl', []),
            lb=self.defense_roster.get('lb', []),
            db=self.defense_roster.get('db', []),
            k=self.defense_roster.get('k', []),
            p=self.defense_roster.get('p', []),
            kr=self.defense_roster.get('kr', []),
        )

        comm = Commentary(off_roster, def_roster,
                          self.offense_team, self.defense_team)

        is_breakaway = (result.result_type == ResultType.BREAKAWAY)

        return comm.generate(
            play_type=outcome.play_type,
            result_type=result.result_type,
            yards=outcome.yards_gained,
            is_first_down=outcome.first_down,
            is_touchdown=outcome.touchdown,
            is_breakaway=is_breakaway,
            is_check_down=False
        )

    def _get_big_play_info(self, outcome: PlayOutcome, result) -> tuple:
        """
        Categorize play for big_play_factor and big_play_type.

        Factor levels:
        0 (normal): Routine play
        1 (notable): First down, 5+ yards, tackle for loss
        2 (exciting): Breakaway, sack, 10+ yards
        3 (critical): TD, turnover, safety
        """
        yards = outcome.yards_gained

        if outcome.touchdown:
            return 3, "touchdown"
        if outcome.turnover:
            if "INT" in str(result.result_type):
                return 3, "interception"
            return 3, "fumble"
        if outcome.safety:
            return 3, "safety"

        if result.result_type == ResultType.SACK:
            return 2, "sack"
        
        if result.result_type == ResultType.PASS_INTERFERENCE:
            return 2, "pass_interference"
        if result.result_type == ResultType.BREAKAWAY:
            if yards <= 0:
                return 2, "stuff"
            if yards >= 20:
                return 2, "explosive"
            return 2, "breakaway"
        if yards >= 20:
            return 2, "explosive"
        if yards >= 10:
            return 2, "big_play"

        if outcome.first_down:
            return 1, "first_down"
        if yards >= 5:
            return 1, "positive"
        if yards < 0:
            return 1, "tackle_for_loss"

        return 0, "normal"

    def _get_flags(self, outcome: PlayOutcome, result, yards: int) -> dict:
        """Generate semantic flags for UI."""
        return {
            'is_stuffed': yards <= 0 and result.result_type != ResultType.INCOMPLETE,
            'is_big_play': yards >= 10,
            'is_explosive': yards >= 20,
            'is_turnover': outcome.turnover,
            'is_interception': "INT" in str(result.result_type),
            'is_fumble': result.result_type == ResultType.FUMBLE,
            'is_touchdown': outcome.touchdown,
            'is_first_down': outcome.first_down,
            'is_safety': outcome.safety,
            'is_sack': result.result_type == ResultType.SACK,
            'is_breakaway': result.result_type == ResultType.BREAKAWAY,
        }

    def _get_penalty_info(self, outcome: PlayOutcome) -> dict:
        """Extract penalty information if applicable."""
        if not outcome.penalty_choice or not outcome.penalty_choice.penalty_options:
            return {
                'pending': False,
                'description': '',
                'options': [],
                'offended_team': '',
                'play_result': None,
                'play_result_description': '',
                'offsetting': False,
                'is_pass_interference': False,
            }

        pc = outcome.penalty_choice
        
        # Filter penalties based on who is offended (matching CLI logic)
        # If offense is offended: show only DEF or PI penalties
        # If defense is offended: show only OFF penalties
        offended_is_offense = pc.offended_team == "offense"
        if offended_is_offense:
            filtered_options = [opt for opt in pc.penalty_options
                               if opt.penalty_type in ["DEF", "PI"]]
        else:
            filtered_options = [opt for opt in pc.penalty_options
                               if opt.penalty_type == "OFF"]

        options = []
        for opt in filtered_options:
            options.append({
                'type': opt.penalty_type,
                'raw_result': opt.raw_result,
                'description': opt.description,
                'yards': opt.yards,
                'auto_first_down': getattr(opt, 'auto_first_down', False),
                'is_pass_interference': getattr(opt, 'is_pass_interference', False)
            })

        # Get play result description for display
        play_result = pc.play_result
        play_result_desc = ""
        if play_result:
            if hasattr(play_result, 'description') and play_result.description:
                play_result_desc = play_result.description
            elif hasattr(play_result, 'raw_result') and play_result.raw_result:
                play_result_desc = f"{play_result.raw_result} ({play_result.yards} yards)" if hasattr(play_result, 'yards') else play_result.raw_result

        return {
            'pending': outcome.pending_penalty_decision,
            'description': pc.penalty_options[0].description if pc.penalty_options else '',
            'options': options,
            'offended_team': pc.offended_team,
            'play_result': {
                'yards': play_result.yards if play_result and hasattr(play_result, 'yards') else 0,
                'turnover': play_result.turnover if play_result and hasattr(play_result, 'turnover') else False,
                'touchdown': play_result.touchdown if play_result and hasattr(play_result, 'touchdown') else False,
            },
            'play_result_description': play_result_desc,
            'offsetting': pc.offsetting,
            'is_pass_interference': pc.is_pass_interference,
        }


def format_play_result(outcome: PlayOutcome,
                      offense_team: str,
                      defense_team: str,
                      offense_roster: Optional[Dict] = None,
                      defense_roster: Optional[Dict] = None) -> FormattedPlayResult:
    """
    Convenience function to format a play result.

    Args:
        outcome: PlayOutcome from game engine
        offense_team: Name of offense team
        defense_team: Name of defense team
        offense_roster: Optional roster dict for commentary
        defense_roster: Optional roster dict for commentary

    Returns:
        FormattedPlayResult ready for UI consumption
    """
    formatter = ResultFormatter(offense_team, defense_team,
                                  offense_roster, defense_roster)
    return formatter.format(outcome)
