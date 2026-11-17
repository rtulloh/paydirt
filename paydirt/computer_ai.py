"""
Computer AI for Paydirt play calling.
Makes intelligent decisions based on:
- Down and distance
- Field position
- Time remaining
- Score differential
- Game situation (2-minute drill, goal line, etc.)
- Team chart analysis (Phase 1)
- Opponent tendencies (Phase 2)
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from math import ceil, exp
from typing import Optional

from .ai_analysis import OffenseAnalyzer, OpponentModel, TeamAnalyzer
from .chart_loader import OffenseChart
from .game_engine import PaydirtGameEngine
from .game_state import PenaltySituation
from .offense_strategy import OffensiveStrategy
from .play_resolver import CHART_PLAY_TYPES, DefenseType, PlayType, ResultType, is_passing_play
from .season_rules import AIBehavior

# Field-goal coaching bands. The make probability itself always comes from the
# kicking team's chart (engine-owned); these are decision thresholds, not odds.
FG_EASY_PROBABILITY = 0.70
FG_KICK_PROBABILITY = 0.35
FG_LONG_PROBABILITY = 0.15
FG_LAST_SECONDS_PROBABILITY = 0.10
FOURTH_DOWN_NO_HUDDLE_SECONDS = 25.0
FOURTH_DOWN_NEXT_SNAP_SECONDS = 5.0


@dataclass(frozen=True)
class CoachingPrecision:
    """Bounded decision imprecision for lower coaching difficulties.

    Difficulty is not only aggression: Easy and Medium should also be less
    reliable on marginal calls. ``fg_optimism`` is a systematic misjudgement of
    the kicking chart, and ``band_confusion`` is a chance to misread a call
    that sits within ``band_margin`` of a decision threshold. Neither changes
    dice odds, play legality, or an endgame rule.
    """

    name: str = "precise"
    fg_optimism: float = 0.0
    band_confusion: float = 0.0
    band_margin: float = 0.06


HARD_PRECISION = CoachingPrecision(name="hard")
MEDIUM_PRECISION = CoachingPrecision(name="medium", fg_optimism=0.02, band_confusion=0.12)
EASY_PRECISION = CoachingPrecision(name="easy", fg_optimism=0.05, band_confusion=0.30)
FG_BAND_EDGES = (FG_LONG_PROBABILITY, FG_KICK_PROBABILITY, FG_EASY_PROBABILITY)


def _uncharted_field_goal_probability(statistical_distance: int) -> float:
    """Legacy-shaped estimate for charts that carry no field-goal data.

    Mock or partial charts cannot be evaluated by the engine. Real charts never
    reach this fallback, so a coaching call always reflects an actual attempt.
    """
    if statistical_distance <= 35:
        return 0.85
    if statistical_distance <= 47:
        return 0.60
    if statistical_distance <= 55:
        return 0.35
    return 0.05


def _defensive_situation_rank(situation: PenaltySituation) -> tuple[int, int, int]:
    """Rank an offense situation as the defense values it; higher is better.

    Field position comes first: an offense farther from the defense's goal is
    the defense's clearest gain, including a half-distance enforcement that
    only moves the ball a few yards. Remaining attempts then break near ties,
    and a longer distance to convert ranks last. This is a coaching ordering,
    not an expected-points estimate.
    """
    return (100 - situation.ball_position, situation.down, situation.yards_to_go)


def _foul_hands_offense_a_kneel_out(
    game: PaydirtGameEngine, outcome, best_index: int | None,
) -> bool:
    """Whether enforcing an offensive foul lets the offense kneel out the game.

    The position comparison in :meth:`ComputerAI.should_accept_penalty` ranks
    field position, down and distance only. Late in regulation a trailing
    defense must regain possession, and replaying the down can leave the offense
    on second or third down with enough clock to kneel. Declining keeps the play
    result and its down, which in that shape prevents the kneel-out. The engine
    projects each choice, including the clock it charges, and supplies the
    kneel-out rule; the AI reads those projections without copying or mutating
    the live state.

    Args:
        game: Live engine; only read.
        outcome: Pending penalty outcome.
        best_index: Penalty option the position comparison chose, if any.

    Returns:
        True only when the defense trails, enforcement allows a kneel-out and
        declining the play does not.
    """
    if best_index is None:
        return False
    state = game.state
    offense_leads = (
        state.home_score > state.away_score if state.is_home_possession
        else state.away_score > state.home_score
    )
    if not offense_leads or state.is_overtime or state.quarter != 4:
        return False
    enforced = game._project_scrimmage_penalty_situation(outcome, False, best_index)
    retained = game._project_scrimmage_penalty_situation(outcome, True)
    if enforced is None or retained is None or not 1 <= enforced.down <= 3:
        return False
    if enforced.touchdown or enforced.turnover or enforced.game_over or enforced.untimed_down:
        return False
    return (
        game.can_kneel_out_penalty_situation(enforced)
        and not game.can_kneel_out_penalty_situation(retained)
    )


def _field_goal_foul_costs_a_won_game(
    game: PaydirtGameEngine, outcome, penalty_index: int,
) -> bool:
    """Whether enforcing a field-goal foul trades a won game for a live down.

    A made kick can end the game with the defense ahead. Enforcing the foul
    instead replays the down, and the offense is free to attempt a
    game-winning touchdown rather than re-kick. The engine projects both
    resolutions, including their scores, clock, period and game-over state; this
    guard only asks whether the retained kick wins and the enforced foul does
    not. It never changes live state.

    Args:
        game: Live engine; only read.
        outcome: Pending field-goal penalty outcome.
        penalty_index: Enforcement option the position logic chose.

    Returns:
        True only when keeping the kick ends the game with the defense ahead and
        enforcement leaves the game unfinished.
    """
    if game is None:
        return False
    state = game.state
    defense_is_home = not state.is_home_possession
    retained = game.project_field_goal_penalty_choice(outcome, True)
    enforced = game.project_field_goal_penalty_choice(outcome, False, penalty_index)
    if retained is None or enforced is None:
        return False
    retained_wins = (
        retained.game_over
        and not retained.untimed_down
        and retained.points_for(defense_is_home) > retained.points_against(defense_is_home)
    )
    enforced_wins = (
        enforced.game_over
        and not enforced.untimed_down
        and enforced.points_for(defense_is_home) > enforced.points_against(defense_is_home)
    )
    return retained_wins and not enforced_wins


class ComputerAI:
    """
    Intelligent computer opponent for Paydirt.

    Play calling philosophy:
    - Balanced attack on early downs
    - Situational awareness for 3rd/4th down
    - Clock management in late-game situations
    - Aggressive when trailing, conservative when leading
    - Uses chart analysis and opponent modeling in hard mode
    """

    def __init__(
        self,
        aggression: float = 0.5,
        use_analysis: bool = False,
        ai_behavior: AIBehavior | None = None,
        precision: CoachingPrecision | None = None,
    ):
        """
        Initialize AI with aggression level.

        Args:
            aggression: 0.0 = very conservative, 1.0 = very aggressive
            use_analysis: If True, use chart analysis and opponent modeling
            ai_behavior: Era-specific AI behavior settings (pace-of-play, strategic
                decisions). Defaults to conservative era settings if not provided.
            precision: Difficulty imprecision profile. None (the balanced auto
                baseline and direct constructions) keeps every call exact.
        """
        self.aggression = aggression
        self.use_analysis = use_analysis
        self.ai_behavior = ai_behavior if ai_behavior is not None else AIBehavior()
        self.precision = precision
        self.last_mode = None  # Track current mode for logging

        # For opponent modeling (shared across offense and defense)
        self.opponent_model = OpponentModel() if use_analysis else None
        self.team_analyzer = None  # Set when we know our team
        self._defense_rng: random.Random | None = None  # Lazy, separate from engine dice.
        self._offense_rng: random.Random | None = None
        self._decision_rng: random.Random | None = None  # Coaching noise, never dice.
        self.offense_strategy: OffensiveStrategy | None = None
        self.use_team_strength = False  # Explicit Medium capability, enabled by the factory.
        self._run_bias = 0.0

    def set_team(self, team_chart):
        """Set the AI's team for chart analysis."""
        if self.use_analysis:
            self.team_analyzer = TeamAnalyzer(team_chart)
            self.offense_strategy = OffensiveStrategy(team_chart.offense)
        self._run_bias = (OffenseAnalyzer(team_chart.offense).early_down_run_bias()
                          if self.use_team_strength else 0.0)

    def select_offense(self, game: PaydirtGameEngine) -> PlayType:
        """
        Select an offensive play based on game situation.

        Decision factors:
        1. Down and distance
        2. Field position
        3. Time remaining
        4. Score differential
        5. Quarter
        6. Team chart analysis (if use_analysis=True)
        """
        play_type, _, _, _, _, _ = self.select_offense_with_clock_management(game)
        return play_type

    def select_two_point_offense(self, game: PaydirtGameEngine) -> PlayType:
        """Choose a scoring play for an untimed try, never a clock-management call."""
        situation = game.get_two_point_situation()
        legal = situation["legal_plays"]
        weights = {play: 1.0 for play in legal}
        if self.use_analysis or self.use_team_strength:
            strategy = OffensiveStrategy(game.state.possession_team.offense)
            scores = strategy.conversion_scores(situation["yards_to_go"], situation["points"])
            if scores:
                best = max(scores.values())
                weights = {
                    play: exp((score - best) / OffensiveStrategy.TEMPERATURE)
                    for play, score in scores.items()
                    if play in legal and best - score <= OffensiveStrategy.COMPETITIVE_GAP
                }
        if self._offense_rng is None:
            self._offense_rng = random.Random(f"paydirt-offense:{random.getstate()!r}")
        self.last_mode = "Two-Point Try"
        return self._offense_rng.choices(list(weights), weights=list(weights.values()), k=1)[0]

    def select_two_point_defense(self, game: PaydirtGameEngine) -> DefenseType:
        """Choose a goal-line formation without inspecting the stale game clock."""
        situation = game.get_two_point_situation()
        formations = situation["legal_defenses"]
        weights = [3 if defense == DefenseType.SHORT_YARDAGE else 1 for defense in formations]
        if self._defense_rng is None:
            self._defense_rng = random.Random(f"paydirt-defense:{random.getstate()!r}")
        self.last_mode = "Two-Point Try"
        return self._defense_rng.choices(formations, weights=weights, k=1)[0]

    def _get_ai_play_suggestion(self, down: int, distance: int):
        """
        Use chart analysis to get AI's play suggestion.

        Returns play type name (e.g., 'Screen', 'Off Tackle') or None if not available.
        """
        if not self.team_analyzer:
            return None

        try:
            suggestion = self.team_analyzer.suggest_play(down, distance)
            return suggestion.get("recommended_play") or None
        except Exception:
            logging.getLogger(__name__).debug("Operation failed", exc_info=True)
            return None

    def _ai_play_to_play_type(self, play_name):
        """Convert play name from analysis to PlayType enum."""
        if not play_name:
            return None
        play_map = {
            "Line Plunge": PlayType.LINE_PLUNGE,
            "Off Tackle": PlayType.OFF_TACKLE,
            "End Run": PlayType.END_RUN,
            "Draw": PlayType.DRAW,
            "Screen": PlayType.SCREEN,
            "Short": PlayType.SHORT_PASS,
            "Med": PlayType.MEDIUM_PASS,
            "Long": PlayType.LONG_PASS,
            "T/E S/L": PlayType.TE_SHORT_LONG,
        }
        return play_map.get(play_name)

    def select_offense_with_clock_management(self, game: PaydirtGameEngine) -> tuple:
        """
        Select an offensive play with clock management options.

        Returns:
            tuple: (PlayType, out_of_bounds: bool, no_huddle: bool,
                    punt_short_drop: bool, punt_coffin_corner_yards: int, call_spike: bool)
        """
        state = game.state
        down = state.down
        ytg = state.yards_to_go
        field_pos = state.ball_position  # 0=own goal, 100=opponent goal
        time_left = state.time_remaining
        # An overtime period has the same scoring urgency as the final quarter.
        quarter = 4 if state.is_overtime else state.quarter

        # Calculate score differential (positive = winning)
        if state.is_home_possession:
            score_diff = state.home_score - state.away_score
        else:
            score_diff = state.away_score - state.home_score

        # Clock management flags
        use_oob = False
        use_no_huddle = False
        use_spike = False

        # ============================================================
        # SPECIAL SITUATIONS - Time-based checks FIRST (most important)
        # ============================================================

        if game.can_kneel_out_game():
            self.last_mode = "Victory Formation"
            return (PlayType.QB_KNEEL, False, False, False, 0, False)

        # End-of-half FG: kick on any down when time is about to expire and the
        # kicking team's own chart makes the kick worthwhile. Exception: in Q4,
        # don't kick if trailing by more than 3 (need TD instead).
        if quarter in [2, 4] and time_left <= 10 / 60:
            fg_helps = (quarter == 2) or (score_diff >= -3)  # Q2 always; Q4 only if FG ties/wins
            if (self._field_goal_probability(game, 100 - field_pos)
                    >= FG_LAST_SECONDS_PROBABILITY and fg_helps):
                self.last_mode = "End-of-Half FG"
                use_no_huddle = True
                return (PlayType.FIELD_GOAL, use_oob, use_no_huddle, False, 0, False)

        # Last-chance touchdown attempts also take priority over fourth-down
        # conversion plays, which may gain yards without reaching the end zone.
        if quarter in [2, 4] and time_left <= 0.15 and score_diff < 0 and field_pos >= 40:
            self.last_mode = "Two-Minute Drill"
            return (PlayType.HAIL_MARY, False, True, False, 0, False)

        # 4th Down Decision
        if down == 4:
            self.last_mode = "4th Down"
            play, punt_short_drop, punt_coffin_corner_yards = self._fourth_down_decision(
                game, ytg, field_pos, time_left, quarter, score_diff
            )
            last_possession_plan = None
            if (quarter == 4 and score_diff < 0 and time_left <= 2.0
                    and play not in (PlayType.PUNT, PlayType.FIELD_GOAL)):
                last_possession_plan = self._last_possession_fourth_down_plan(
                    game, ytg, field_pos, time_left, score_diff
                )
            if last_possession_plan is not None:
                play, use_oob, use_no_huddle = last_possession_plan
                self.last_mode = "Last-Possession 4th Down"
                return (
                    play, use_oob, use_no_huddle, punt_short_drop,
                    punt_coffin_corner_yards, False,
                )
            if self._needs_hurry_up(game, time_left, quarter, score_diff):
                use_no_huddle = True
                if play in [
                    PlayType.SHORT_PASS,
                    PlayType.MEDIUM_PASS,
                    PlayType.LONG_PASS,
                    PlayType.SCREEN,
                ] and random.random() < self.ai_behavior.strategic.oob_designation_aggression:
                    use_oob = True
            return (play, use_oob, use_no_huddle, punt_short_drop, punt_coffin_corner_yards, False)

        # 2-Minute Drill (time-critical - end of half, aggressive clock management)
        if self._is_two_minute_drill(game, time_left, quarter, score_diff):
            self.last_mode = "Two-Minute Drill"
            if self._offense_rng is None:
                self._offense_rng = random.Random(f"paydirt-offense:{random.getstate()!r}")
            weights = self.get_hurry_up_weights(game)
            play = self._offense_rng.choices(list(weights), weights=list(weights.values()), k=1)[0]
            use_no_huddle = True
            # Use OOB designation on passing plays based on aggression
            if (play in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN]) and (self._offense_rng.random() < self.ai_behavior.strategic.oob_designation_aggression):
                use_oob = True
            # Spike modifier: add spike to stop clock after play (only on 1st/2nd down, not 3rd)
            # On 3rd down, spiking wastes the down and we need to punt/kick on 4th
            spike_chance = self.ai_behavior.strategic.spike_ball_chance
            if spike_chance > 0 and time_left < 1.0 and down <= 2:
                prev = game.play_log[-1] if game.play_log else None
                is_prev_completion = (
                    prev is not None
                    and prev.result.result_type.value
                    not in ("incomplete", "interception", "fumble")
                    and prev.yards_gained > 0
                )
                if is_prev_completion and ytg >= 5 and self._offense_rng.random() < spike_chance:
                    self.last_mode = "Play + Spike"
                    use_spike = True
            return (play, use_oob, use_no_huddle, False, 0, use_spike)

        # Running Out Clock (time-critical - protecting lead)
        if self._should_run_clock(time_left, quarter, score_diff):
            self.last_mode = "Clock Killing"
            play = self._clock_killing_offense(down, ytg, time_left, field_pos)
            return (
                play,
                False,
                False,
                False,
                0,
                False,
            )  # No hurry, let clock run - no punt options

        # ============================================================
        # FIELD-POSITION BASED SITUATIONS
        # ============================================================

        # Goal Line (inside 5 yard line)
        if field_pos >= 95:
            self.last_mode = "Goal Line"
            play = self._goal_line_offense(ytg)
            if self._needs_hurry_up(game, time_left, quarter, score_diff):
                use_no_huddle = True
            return (play, use_oob, use_no_huddle, False, 0, False)

        # Red Zone (inside 20)
        if field_pos >= 80:
            self.last_mode = "Red Zone"
            play = self._red_zone_offense(down, ytg)
            use_oob, use_no_huddle = self._hurry_up_flags(
                game, play, time_left, quarter, score_diff,
            )
            return (play, use_oob, use_no_huddle, False, 0, False)

        # ============================================================
        # STANDARD SITUATIONS
        # ============================================================
        self.last_mode = None  # Clear mode for standard plays

        # Hard selects a mixture directly, not a winner-only override of a
        # separate random call. Coaching priorities above still take precedence.
        if self.offense_strategy is not None:
            weights = self.offense_strategy.weights(
                down, ytg, game.offensive_call_history, state.is_home_possession)
            if weights:
                if self._offense_rng is None:
                    self._offense_rng = random.Random(f"paydirt-offense:{random.getstate()!r}")
                play = self._offense_rng.choices(list(weights), weights=list(weights.values()), k=1)[0]
                use_oob, use_no_huddle = self._hurry_up_flags(
                    game, play, time_left, quarter, score_diff,
                )
                return (play, use_oob, use_no_huddle, False, 0, False)

        # 3rd Down
        if down == 3:
            play = self._third_down_offense(ytg, field_pos)
        # 2nd Down
        elif down == 2:
            play = self._second_down_offense(ytg)
        # 1st Down - balanced attack
        else:
            play = self._first_down_offense(field_pos)

        use_oob, use_no_huddle = self._hurry_up_flags(
            game, play, time_left, quarter, score_diff,
        )
        return (play, use_oob, use_no_huddle, False, 0, False)

    def _multi_score_fourth_down_urgent(
        self, game: PaydirtGameEngine, distance: int, field_position: int,
        minutes_left: float, deficit: int,
    ) -> bool:
        """Estimate whether punting leaves time for the required scoring drives.

        This is a bounded coaching estimate, not a win-probability model. Budget
        eighty seconds per later drive, a field-position-sensitive current drive,
        and a defensive stop shortened by the offense's remaining timeouts.
        """
        scores_needed = game.season_rules.scores_needed(deficit)
        if scores_needed < 2 or minutes_left >= 5 or distance > 10:
            return False
        state = game.state
        timeouts = state.home_timeouts if state.is_home_possession else state.away_timeouts
        defensive_stop_seconds = 120 - 20 * max(0, min(3, timeouts))
        current_drive_seconds = 45 + (100 - field_position) * .5
        scoring_seconds = current_drive_seconds + 80 * (scores_needed - 1)
        return minutes_left * 60 <= scoring_seconds + defensive_stop_seconds + 10

    def _effective_aggression(self) -> float:
        """Era fourth-down baseline shifted by difficulty, clamped to [0, 1]."""
        era = getattr(getattr(self.ai_behavior, "strategic", None),
                      "fourth_down_aggression", 0.5)
        if not isinstance(era, (int, float)):
            era = 0.5
        return min(1.0, max(0.0, era + (self.aggression - 0.5)))

    def _decision_random(self) -> random.Random:
        """Coaching-noise stream, seeded lazily and never the gameplay dice."""
        if self._decision_rng is None:
            self._decision_rng = random.Random(f"paydirt-decision:{random.getstate()!r}")
        return self._decision_rng

    def _perceived_field_goal_probability(self, probability: float) -> float:
        """Adjust the chart's make chance for the difficulty's imprecision.

        Lower difficulties overrate their kicker and may misread a borderline
        case. The adjustment is bounded: it can move a call at most one band
        and never touches obvious kicks or punts.

        Args:
            probability: The engine's chart-weighted make probability.

        Returns:
            The probability this coach acts on, in [0, 1].
        """
        profile = self.precision
        if profile is None:
            return probability
        seen = min(1.0, max(0.0, probability + profile.fg_optimism))
        if profile.band_confusion <= 0:
            return seen
        near_edge = any(abs(seen - edge) <= profile.band_margin for edge in FG_BAND_EDGES)
        rng = self._decision_random()
        if near_edge and rng.random() < profile.band_confusion:
            seen = min(1.0, max(
                0.0, seen + rng.uniform(-profile.band_margin, profile.band_margin)))
        return seen

    def _field_goal_probability(self, game, distance_to_goal: int) -> float:
        """Chart-weighted make chance, with an explicit uncharted fallback.

        Args:
            game: Engine supplying the possession team's chart, or None.
            distance_to_goal: Yards from the line of scrimmage to the goal line.

        Returns:
            Probability in [0, 1]. Chartless callers get the documented legacy
            curve rather than an implicit 1983 tier.
        """
        query = getattr(game, "field_goal_make_probability", None)
        if callable(query):
            probability = query(distance_to_goal)
            if probability is not None:
                return probability
        return _uncharted_field_goal_probability(distance_to_goal + 17)

    def _fourth_down_decision(self, game, ytg, field_pos, time_left, quarter, score_diff) -> tuple:
        """
        Decide what to do on fourth down from the kicking team's own chart.

        The engine reports the dice-weighted chance that the possession team's
        Field Goal column reaches the goal line from this spot, so a weak 1983
        chart and a strong modern chart are not treated alike. The season
        profile's ``fourth_down_aggression`` sets the era baseline and the
        difficulty aggression shifts it.

        Returns: tuple of (PlayType, punt_short_drop: bool, punt_coffin_corner_yards: int)
        """
        distance_to_goal = 100 - field_pos
        p_make = self._field_goal_probability(game, distance_to_goal)
        aggression = self._effective_aggression()

        # Bands are coaching preferences over the chart's actual make chance.
        fg_easy = p_make >= FG_EASY_PROBABILITY       # routine kick
        fg_makeable = p_make >= FG_KICK_PROBABILITY   # worth taking
        fg_long = p_make >= FG_LONG_PROBABILITY       # aggressive attempt only

        # Determine punt options (default: normal punt)
        punt_short_drop = False
        punt_coffin_corner_yards = 0

        # Check for short-drop punt (inside own 5-yard line)
        # Conservative coaches more likely to use it
        if (field_pos <= 5) and (self.aggression < 0.3):
            punt_short_drop = True

        # Coffin corner: pin a late opponent deep. More aggressive AI uses it more.
        if (field_pos >= 50) and ((quarter >= 2 and time_left < 5.0)
                                  and (self.aggression > 0.6 and random.random() < 0.3)):
            punt_coffin_corner_yards = random.choice([15, 18, 20])

        # ============================================================
        # DESPERATION SITUATIONS (4th quarter, trailing, low time)
        # ============================================================

        if quarter == 4 and score_diff < 0:
            # Must score to win/tie
            if time_left <= 2.0:
                # Under 2 minutes, trailing
                if fg_easy and score_diff >= -3:
                    return (
                        PlayType.FIELD_GOAL,
                        punt_short_drop,
                        punt_coffin_corner_yards,
                    )  # FG ties or wins
                elif fg_makeable and score_diff >= -3:
                    return (
                        PlayType.FIELD_GOAL,
                        punt_short_drop,
                        punt_coffin_corner_yards,
                    )  # Take the points
                else:
                    # Must go for it - need TD or can't kick
                    go_play, _, _ = self._go_for_it_play(ytg)
                    return (go_play, punt_short_drop, punt_coffin_corner_yards)

            # 2-5 minutes left, trailing. A field goal that removes one needed
            # possession remains useful; otherwise preserve a scarce drive.
            if time_left < 5.0:
                deficit = -score_diff
                scores_needed = game.season_rules.scores_needed(deficit)
                scores_after_fg = game.season_rules.scores_needed(max(0, deficit - 3))
                if scores_needed >= 2 and fg_makeable and scores_after_fg < scores_needed:
                    return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)
                if self._multi_score_fourth_down_urgent(game, ytg, field_pos, time_left, deficit):
                    go_play, _, _ = self._go_for_it_play(ytg)
                    return (go_play, punt_short_drop, punt_coffin_corner_yards)
                if fg_easy and score_diff >= -3:
                    return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)
                elif ytg <= 2:
                    go_play, _, _ = self._go_for_it_play(ytg)
                    return (
                        go_play,
                        punt_short_drop,
                        punt_coffin_corner_yards,
                    )  # Short yardage, go for it
                elif fg_makeable and score_diff >= -3:
                    return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)
                elif field_pos >= 50:
                    go_play, _, _ = self._go_for_it_play(ytg)
                    return (
                        go_play,
                        punt_short_drop,
                        punt_coffin_corner_yards,
                    )  # In opponent territory, be aggressive

        # ============================================================
        # FIELD GOAL DECISIONS (season- and team-aware)
        # ============================================================

        # Difficulty imprecision applies to ordinary judgement only. Endgame
        # rules above (last-second kicks, urgent multi-score drives) stay sharp.
        p_make = self._perceived_field_goal_probability(p_make)
        fg_easy = p_make >= FG_EASY_PROBABILITY
        fg_makeable = p_make >= FG_KICK_PROBABILITY
        fg_long = p_make >= FG_LONG_PROBABILITY

        # Routine kick - almost always take the points.
        if fg_easy:
            # Only go for it on 4th and inches inside the 5 with high aggression
            if ytg <= 1 and aggression > 0.8 and field_pos >= 95:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)

        # Worth taking - kick unless a short conversion is attractive.
        if fg_makeable:
            if ytg <= 1 and aggression >= 0.5:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)

        # Long but plausible - short yardage and aggressive coaches try it.
        if fg_long:
            if ytg <= 1 and aggression >= 0.5:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)

            if ytg <= 2 and aggression > 0.8:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)

            if aggression >= 0.7:
                return (PlayType.FIELD_GOAL, punt_short_drop, punt_coffin_corner_yards)
            return (PlayType.PUNT, punt_short_drop, punt_coffin_corner_yards)

        # ============================================================
        # OUTSIDE PLAUSIBLE FG RANGE
        # ============================================================

        # Just outside FG range (around 40-45 yard line)
        if field_pos >= 55:
            # 4th and 1 - go for it
            if ytg <= 1:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            # 4th and 2 with aggression
            if ytg <= 2 and aggression > 0.6:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            # Otherwise punt - too far for FG, don't want to give up field position
            return (PlayType.PUNT, punt_short_drop, punt_coffin_corner_yards)

        # At midfield (45-55 yard line)
        if field_pos >= 45:
            # 4th and 1 - go for it
            if ytg <= 1:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            # 4th and 2 with high aggression only
            if ytg <= 2 and aggression > 0.7:
                go_play, _, _ = self._go_for_it_play(ytg)
                return (go_play, punt_short_drop, punt_coffin_corner_yards)
            # Otherwise punt from midfield
            return (PlayType.PUNT, punt_short_drop, punt_coffin_corner_yards)

        # In own territory (inside own 45) - almost always punt
        if ytg <= 1 and aggression > 0.9:
            # Only go for it on 4th and inches with extreme aggression
            go_play, _, _ = self._go_for_it_play(ytg)
            return (go_play, punt_short_drop, punt_coffin_corner_yards)
        return (PlayType.PUNT, punt_short_drop, punt_coffin_corner_yards)

    def _go_for_it_play(self, ytg: int) -> tuple:
        """Select a play when going for it on 4th down."""
        if ytg <= 1:
            # 4th and 1 - power run (75%+) or QB Sneak
            return (
                random.choice(
                    [
                        PlayType.LINE_PLUNGE,
                        PlayType.LINE_PLUNGE,
                        PlayType.LINE_PLUNGE,
                        PlayType.OFF_TACKLE,
                        PlayType.OFF_TACKLE,
                        PlayType.QB_SNEAK,
                    ]
                ),
                False,
                0,
            )
        elif ytg <= 3:
            # 4th and short - mix of run and pass
            return (
                random.choice(
                    [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.DRAW]
                ),
                False,
                0,
            )
        elif ytg <= 6:
            # 4th and medium - quick passes
            return (random.choice([PlayType.SHORT_PASS, PlayType.SCREEN, PlayType.DRAW]), False, 0)
        else:
            # 4th and long - need a chunk play
            return (
                random.choice([PlayType.MEDIUM_PASS, PlayType.SHORT_PASS, PlayType.LONG_PASS]),
                False,
                0,
            )

    def _last_possession_fourth_down_plan(
        self,
        game: PaydirtGameEngine,
        ytg: int,
        field_pos: int,
        time_left: float,
        score_diff: int,
    ) -> tuple[PlayType, bool, bool] | None:
        """Choose a clock-aware conversion when little time remains.

        A no-huddle run can consume 15-25 seconds, so a trailing offense with
        roughly half a minute left must stop the clock on a conversion attempt.
        This is a bounded coaching rule, not a win-probability model. It applies
        only when the ordinary fourth-down decision already chose to go for it,
        preserving the existing end-of-half, Hail Mary and kick priorities.

        Args:
            game: Engine supplying the possession team's state and rules.
            ytg: Yards needed for a first down or touchdown.
            field_pos: Ball position, where 100 is the opponent's goal line.
            time_left: Minutes remaining in the quarter.
            score_diff: Possession team's score minus its opponent's score.

        Returns:
            ``(play, out_of_bounds, no_huddle)`` for a clock-critical attempt,
            or ``None`` when ordinary fourth-down selection should continue.
        """
        if score_diff >= 0 or time_left > 2.0:
            return None
        deficit = -score_diff
        points_per_score = 8 if game.season_rules.two_point_conversion else 7
        scores_needed = max(1, ceil(deficit / points_per_score))
        seconds_left = time_left * 60
        # Reserve the engine's longest no-huddle play plus a quick next snap.
        # Above this window, ordinary hurry-up selection remains varied.
        if seconds_left > FOURTH_DOWN_NO_HUDDLE_SECONDS + FOURTH_DOWN_NEXT_SNAP_SECONDS:
            return None

        if field_pos >= 95:
            # A short touchdown can win the game outright. Otherwise only a
            # pass stops the clock here: the auto-game caller does not request
            # an offensive timeout, so a banked timeout cannot save a run.
            touchdown_is_enough = deficit <= points_per_score
            if touchdown_is_enough:
                candidates = [
                    PlayType.LINE_PLUNGE,
                    PlayType.OFF_TACKLE,
                    PlayType.SHORT_PASS,
                    PlayType.TE_SHORT_LONG,
                    PlayType.SCREEN,
                ]
            else:
                candidates = [
                    PlayType.SHORT_PASS,
                    PlayType.SHORT_PASS,
                    PlayType.TE_SHORT_LONG,
                    PlayType.SCREEN,
                    PlayType.MEDIUM_PASS,
                ]
        elif ytg <= 3:
            candidates = [
                PlayType.SHORT_PASS,
                PlayType.SHORT_PASS,
                PlayType.SCREEN,
                PlayType.TE_SHORT_LONG,
                PlayType.MEDIUM_PASS,
            ]
        elif ytg <= 10:
            candidates = [
                PlayType.SHORT_PASS,
                PlayType.MEDIUM_PASS,
                PlayType.MEDIUM_PASS,
                PlayType.TE_SHORT_LONG,
                PlayType.SCREEN,
            ]
        else:
            candidates = [
                PlayType.MEDIUM_PASS,
                PlayType.MEDIUM_PASS,
                PlayType.LONG_PASS,
                PlayType.LONG_PASS,
                PlayType.TE_SHORT_LONG,
            ]
        if scores_needed > 1 and field_pos < 95:
            candidates.extend([PlayType.MEDIUM_PASS, PlayType.LONG_PASS])

        play = random.choice(candidates)
        use_no_huddle = True
        # This path cannot assume a timeout follows the play, so a pass always
        # needs the sideline designation; its five-yard cost is the only way to
        # preserve a later snap for a completion in this window.
        use_oob = is_passing_play(play)
        return play, use_oob, use_no_huddle

    def _goal_line_offense(self, ytg) -> PlayType:
        """Play calling inside the 5 yard line."""
        if ytg <= 1:
            # Goal line stand - power run or QB Sneak
            return random.choice(
                [PlayType.QB_SNEAK, PlayType.LINE_PLUNGE, PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE]
            )
        elif ytg <= 3:
            # Short yardage - mix run/pass
            return random.choice([PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS])
        else:
            # Need more yards
            return random.choice([PlayType.SHORT_PASS, PlayType.DRAW, PlayType.OFF_TACKLE])

    def _red_zone_offense(self, down, ytg) -> PlayType:
        """Play calling inside the 20."""
        if down == 3:
            if ytg <= 3:
                return random.choice([PlayType.SHORT_PASS, PlayType.DRAW, PlayType.LINE_PLUNGE])
            elif ytg <= 7:
                return random.choice([PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.SCREEN])
            else:
                return random.choice([PlayType.MEDIUM_PASS, PlayType.SHORT_PASS])

        # Early downs in red zone - balanced
        return random.choice(
            [
                PlayType.LINE_PLUNGE,
                PlayType.OFF_TACKLE,
                PlayType.SHORT_PASS,
                PlayType.DRAW,
                PlayType.SCREEN,
            ]
        )

    def get_hurry_up_weights(self, game: PaydirtGameEngine) -> dict[PlayType, float]:
        """Preview credible calls with gradual clock/deficit passing pressure.

        Pace is decided separately. The multiplier is a coaching preference,
        not a pass quota: it cannot admit an ineligible call or ban a credible
        run. Hard retains chart strength, target sensitivity and recent history.
        Easy/Medium use situational weights, with Medium's supported run bias.
        """
        state = game.state
        down, distance = state.down, state.yards_to_go
        if self.offense_strategy is not None:
            weights = self.offense_strategy.weights(
                down, distance, game.offensive_call_history, state.is_home_possession)
        else:
            # All nine primary calls remain possible; later/long downs favor passes.
            run_weight = .45 if down >= 3 and distance > 3 else 1.0
            if self.use_team_strength and down <= 2:
                run_weight *= exp(self._run_bias)
            weights = {play: 1.0 if is_passing_play(play) else run_weight
                       for play in CHART_PLAY_TYPES}
        # Preserve compact-field route restrictions without altering engine resolution.
        if state.ball_position >= 80:
            weights.pop(PlayType.LONG_PASS, None)
        if not weights:
            weights = {PlayType.SHORT_PASS: 1.0}
        score_diff = (state.home_score - state.away_score) * (1 if state.is_home_possession else -1)
        points_per_score = 8 if game.season_rules.two_point_conversion else 7
        scores_needed = max(1, ceil(max(0, -score_diff) / points_per_score))
        # Two minutes per needed score is a smooth urgency scale, not a timing rule.
        # Bound pressure so runs retain positive weight even in genuine desperation.
        pressure = exp(min(4.0, 2.0 * scores_needed / max(.25, state.time_remaining)))
        return {play: weight * (pressure if is_passing_play(play) else 1.0)
                for play, weight in weights.items()}

    def _clock_killing_offense(self, down, ytg, time_left, field_pos) -> PlayType:
        """Conservative offense when protecting a lead."""

        # Victory formation is selected only via the engine's safe-clock query.
        # 3rd down - still try to convert but safely
        if down == 3:
            if ytg <= 3:
                return random.choice([PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.DRAW])
            else:
                return random.choice([PlayType.SHORT_PASS, PlayType.DRAW, PlayType.SCREEN])

        # Run the ball to kill clock
        return random.choice(
            [
                PlayType.LINE_PLUNGE,
                PlayType.LINE_PLUNGE,
                PlayType.OFF_TACKLE,
                PlayType.OFF_TACKLE,
                PlayType.DRAW,
                PlayType.END_RUN,
            ]
        )

    def _third_down_offense(self, ytg, field_pos) -> PlayType:
        """3rd down play calling - must convert."""

        if ytg <= 2:
            # 3rd and short - run or quick pass
            return random.choice(
                [
                    PlayType.LINE_PLUNGE,
                    PlayType.OFF_TACKLE,
                    PlayType.DRAW,
                    PlayType.SHORT_PASS,
                    PlayType.SCREEN,
                ]
            )
        elif ytg <= 5:
            # 3rd and medium - balanced
            return random.choice(
                [
                    PlayType.SHORT_PASS,
                    PlayType.MEDIUM_PASS,
                    PlayType.DRAW,
                    PlayType.SCREEN,
                    PlayType.OFF_TACKLE,
                ]
            )
        elif ytg <= 10:
            # 3rd and long - passing downs
            return random.choice(
                [
                    PlayType.MEDIUM_PASS,
                    PlayType.SHORT_PASS,
                    PlayType.SCREEN,
                    PlayType.DRAW,  # Draw can catch blitzing defense
                ]
            )
        else:
            # 3rd and very long - need chunk play
            return random.choice([PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN])

    def _choose_early_down(self, plays: list[PlayType]) -> PlayType:
        """Tilt category probabilities only; preserve the existing within-category mix."""
        if not self.use_team_strength or not self._run_bias:
            return random.choice(plays)
        run_count = sum(not is_passing_play(play) for play in plays)
        pass_count = len(plays) - run_count
        if not run_count or not pass_count:
            return random.choice(plays)
        run_probability = max(0.0, min(1.0, run_count / len(plays) + self._run_bias))
        weights = [(1 - run_probability) / pass_count if is_passing_play(play)
                   else run_probability / run_count for play in plays]
        return random.choices(plays, weights=weights, k=1)[0]

    def _second_down_offense(self, ytg) -> PlayType:
        """2nd down play calling."""

        if ytg <= 3:
            # 2nd and short - stay balanced, set up 3rd and short
            return self._choose_early_down(
                [
                    PlayType.LINE_PLUNGE,
                    PlayType.OFF_TACKLE,
                    PlayType.SHORT_PASS,
                    PlayType.DRAW,
                    PlayType.END_RUN,
                ]
            )
        elif ytg <= 7:
            # 2nd and medium - balanced attack
            return self._choose_early_down(
                [
                    PlayType.OFF_TACKLE,
                    PlayType.SHORT_PASS,
                    PlayType.MEDIUM_PASS,
                    PlayType.DRAW,
                    PlayType.END_RUN,
                    PlayType.SCREEN,
                ]
            )
        else:
            # 2nd and long - need to get some back
            return self._choose_early_down(
                [
                    PlayType.SHORT_PASS,
                    PlayType.MEDIUM_PASS,
                    PlayType.DRAW,
                    PlayType.SCREEN,
                    PlayType.OFF_TACKLE,
                ]
            )

    def _first_down_offense(self, field_pos) -> PlayType:
        """1st down play calling - establish the offense."""

        # Deep in own territory - be careful
        if field_pos < 20:
            return self._choose_early_down(
                [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.DRAW]
            )

        # Normal field position - balanced attack
        return self._choose_early_down(
            [
                PlayType.LINE_PLUNGE,
                PlayType.OFF_TACKLE,
                PlayType.END_RUN,
                PlayType.SHORT_PASS,
                PlayType.MEDIUM_PASS,
                PlayType.DRAW,
                PlayType.SCREEN,
            ]
        )

    def _season_aware_two_score_urgency(
        self, game: PaydirtGameEngine, time_left: float, score_diff: int,
        threshold: float,
    ) -> bool:
        """Identify a regulation-Q4 multi-score deficit inside the pace window."""
        state = game.state
        if (state.is_overtime or state.quarter != 4 or score_diff >= 0
                or time_left >= threshold):
            return False
        return game.season_rules.scores_needed(-score_diff) >= 2

    def _hurry_up_flags(
        self, game: PaydirtGameEngine, play: PlayType, time_left: float,
        quarter: int, score_diff: int,
    ) -> tuple[bool, bool]:
        """Return sideline and no-huddle requests for a selected play."""
        if not self._needs_hurry_up(game, time_left, quarter, score_diff):
            return False, False
        if self._offense_rng is None:
            self._offense_rng = random.Random(f"paydirt-offense:{random.getstate()!r}")
        passing_play = play in (
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN,
        )
        use_oob = (
            passing_play
            and self._offense_rng.random()
            < self.ai_behavior.strategic.oob_designation_aggression
        )
        return use_oob, True

    def _is_two_minute_drill(
        self, game: PaydirtGameEngine, time_left: float, quarter: int,
        score_diff: int,
    ) -> bool:
        """Check if we should be in hurry-up mode."""
        tmd = self.ai_behavior.two_minute_drill
        if game.state.is_overtime:
            return False
        if game.state.quarter == 4 and score_diff < 0:
            scores_needed = game.season_rules.scores_needed(-score_diff)
            if (scores_needed >= 2
                    and time_left <= tmd.q4_deficit_9_minutes):
                if time_left == tmd.q4_deficit_9_minutes:
                    return False
                return self._season_aware_two_score_urgency(
                    game, time_left, score_diff, tmd.q4_deficit_9_minutes,
                )
        if quarter == 2 and time_left < 2.0 and score_diff < tmd.skip_when_leading_by:
            return True
        if (game.state.quarter == 4 and score_diff < 0
                and game.season_rules.two_point_conversion
                and score_diff == -8
                and time_left >= tmd.q4_always_minutes):
            return False
        if quarter == 4 and score_diff < 0:
            if score_diff <= -9 and time_left < tmd.q4_deficit_9_minutes:
                return True
            if score_diff <= -4 and time_left < tmd.q4_deficit_4_minutes:
                return True
            if time_left < tmd.q4_always_minutes:
                return True
        return bool(quarter == 4 and score_diff <= -14)

    def _needs_hurry_up(
        self, game: PaydirtGameEngine, time_left: float, quarter: int,
        score_diff: int,
    ) -> bool:
        """Check if we need to hurry (no-huddle, OOB designation)."""
        hur = self.ai_behavior.hurry_up
        if game.state.is_overtime:
            return False
        if game.state.quarter == 4 and score_diff < 0:
            scores_needed = game.season_rules.scores_needed(-score_diff)
            if (scores_needed >= 2
                    and time_left <= hur.q4_deficit_9_minutes):
                if time_left == hur.q4_deficit_9_minutes:
                    return False
                return self._season_aware_two_score_urgency(
                    game, time_left, score_diff, hur.q4_deficit_9_minutes,
                )
        if (game.state.quarter == 4 and score_diff < 0
                and game.season_rules.two_point_conversion
                and score_diff == -8
                and time_left >= hur.q4_any_minutes):
            return False
        if quarter == 4 and score_diff < 0:
            if score_diff <= -9 and time_left < hur.q4_deficit_9_minutes:
                return True
            if score_diff <= -4 and time_left < hur.q4_deficit_4_minutes:
                return True
            if time_left < hur.q4_any_minutes:
                return True
        return bool(quarter == 2 and time_left < 2.0 and score_diff < 0)

    def _should_run_clock(self, time_left, quarter, score_diff) -> bool:
        """Check if we should be killing clock."""
        clk = self.ai_behavior.clock_killing
        if quarter == 4 and score_diff > 0:
            if clk.clock_run_on_any_lead and time_left < clk.q4_any_lead_minutes:
                return True
            if score_diff >= 14 and time_left < clk.q4_big_lead_minutes:
                return True
        return bool(quarter >= 3 and score_diff >= 14)

    @staticmethod
    def analyze_team_strength(offense: OffenseChart) -> str:
        """
        Analyze a team's offensive chart to determine if they favor running or passing.

        Returns:
            'run' if team is better at running
            'pass' if team is better at passing
            'balanced' if roughly equal
        """

        def count_positive_results(chart_column: dict) -> int:
            """Count results that are likely positive (yardage gains, breakaways)."""
            positive = 0
            for result in chart_column.values():
                if not result:
                    continue
                result_str = str(result).upper()
                if any(
                    x in result_str for x in ["OFF", "DEF", "F ", "F+", "F-", "INT", "SK", "BK"]
                ):
                    continue
                if result_str.startswith("B"):
                    positive += 2
                    continue
                try:
                    if any(x in result_str for x in ["DS", "T1", "T2", "T3", "X"]):
                        positive += 1
                        continue
                    yards = int(result_str.split()[0].replace("(", "").replace(")", ""))
                    if yards > 0:
                        positive += 1
                except (ValueError, IndexError):
                    pass
            return positive

        run_positive = (
            count_positive_results(offense.line_plunge)
            + count_positive_results(offense.off_tackle)
            + count_positive_results(offense.end_run)
            + count_positive_results(offense.draw)
        )

        pass_positive = (
            count_positive_results(offense.screen)
            + count_positive_results(offense.short_pass)
            + count_positive_results(offense.medium_pass)
            + count_positive_results(offense.long_pass)
            + count_positive_results(offense.te_short_long)
        )

        run_avg = run_positive / 4
        pass_avg = pass_positive / 5

        if run_avg > pass_avg * 1.15:
            return "run"
        elif pass_avg > run_avg * 1.15:
            return "pass"
        else:
            return "balanced"

    def should_go_for_two(self, game: PaydirtGameEngine, *, try_pending: bool = False) -> bool:
        """
        Determine if CPU should go for 2-point conversion.

        Generally kicks extra point (default), but goes for 2 when:
        - Late in game and need 2 points to tie
        - Down by 2 (2-point makes it a tie)
        - Down by 8 or 9 (need 2 to have chance to tie with another TD)
        - Up by 1 (2-point makes it a 3-point lead)

        Args:
            game: Engine supplying the score, clock and season rules.
            try_pending: Caller confirms a touchdown try is still owed. This
                permits a regulation try at 0:00, never an overtime-winning try.
        """
        state = game.state
        if not game.season_rules.two_point_conversion:
            return False
        if try_pending and not game.can_attempt_conversion_after_touchdown():
            return False
        if state.game_over and not try_pending:
            return False

        if state.is_home_possession:
            score_diff = state.home_score - state.away_score
        else:
            score_diff = state.away_score - state.home_score

        final_period = state.quarter == 4 or state.is_overtime
        late_game = final_period and state.time_remaining < 5.0

        if late_game:
            if score_diff == -2:
                return True
            if score_diff == -8 or score_diff == -9:
                return True
            if score_diff == 1:
                return True

        return False

    def should_onside_kick(self, game: PaydirtGameEngine) -> bool:
        """
        Determine if CPU should attempt an onside kick.

        Only attempts onside kick in desperation situations:
        - 4th quarter, trailing, and running out of time
        - Need the ball back to have a chance to win
        """
        state = game.state

        if state.is_home_possession:
            score_diff = state.home_score - state.away_score
        else:
            score_diff = state.away_score - state.home_score

        if state.quarter != 4:
            return False

        if score_diff >= 0:
            return False

        time_left = state.time_remaining

        if time_left <= 2.0 and score_diff < 0:
            return True

        return bool(time_left < 5.0 and score_diff <= -9)

    def select_defense(self, game: PaydirtGameEngine) -> DefenseType:
        """
        Select a defensive formation based on game situation.

        Decision factors:
        1. Down and distance (predict run vs pass)
        2. Field position
        3. Time remaining
        4. Score differential
        5. Opponent tendencies (if use_analysis=True)
        """
        state = game.state
        down = state.down
        ytg = state.yards_to_go
        field_pos = state.ball_position
        time_left = state.time_remaining
        quarter = state.quarter

        # Calculate score differential (positive = defense is winning)
        if state.is_home_possession:
            score_diff = state.away_score - state.home_score  # Defense perspective
        else:
            score_diff = state.home_score - state.away_score

        # ============================================================
        # USE OPPONENT MODELING (Phase 2) if enabled
        # ============================================================

        if self.use_analysis and self.opponent_model:
            # The model describes the opponent (offense), not our defense.
            defense_rec = self.opponent_model.predict_defense(
                down, ytg, -score_diff, quarter, time_left
            )
            pressure_defense = self._late_trailing_defense(game, score_diff)
            if pressure_defense is not None:
                return pressure_defense
            # Convert to DefenseType
            defense_map = {
                "A": DefenseType.STANDARD,
                "B": DefenseType.SHORT_YARDAGE,
                "C": DefenseType.SPREAD,
                "D": DefenseType.SHORT_PASS,
                "E": DefenseType.LONG_PASS,
                "F": DefenseType.BLITZ,
            }
            return defense_map.get(defense_rec, DefenseType.STANDARD)

        # ============================================================
        # SPECIAL SITUATIONS
        # ============================================================

        # Goal line defense (inside our 5)
        if field_pos >= 95:
            return self._goal_line_defense(down, ytg)

        # Red zone defense
        if field_pos >= 80:
            return self._red_zone_defense(down, ytg)

        # Prevent defense (protect big lead late)
        if self._should_play_prevent(time_left, quarter, score_diff):
            return self._prevent_defense(down, ytg)

        # Two-minute defense (opponent in hurry-up)
        if self._opponent_in_hurry_up(time_left, quarter, score_diff):
            return self._two_minute_defense(down, ytg)

        # ============================================================
        # STANDARD SITUATIONS
        # ============================================================

        # 4th down - they might go for it or kick
        if down == 4:
            return self._fourth_down_defense(ytg, field_pos)

        # 3rd down - key down
        if down == 3:
            return self._third_down_defense(ytg)

        # Early downs - read and react
        return self._early_down_defense(down, ytg)

    def _late_trailing_defense(
        self, game: PaydirtGameEngine, score_diff: int,
    ) -> DefenseType | None:
        """Mix calculated risks when Hard's defense needs multiple late stops.

        Args:
            game: Engine supplying time, field position, and conversion rules.
            score_diff: Defense's score minus the opposing offense's score.

        Returns:
            A weighted A/B/F choice, or None to retain the existing policy.
            Red-zone and goal-line behavior is deliberately left unchanged.
        """
        state = game.state
        max_score = 8 if game.season_rules.two_point_conversion else 7
        deficit = -score_diff
        if (state.quarter != 4 or not 0 < state.time_remaining < 5.0
                or state.game_over or not 0 < state.ball_position < 80
                or state.down not in (1, 2, 3, 4) or deficit <= max_score):
            return None

        # Keep balanced defense available; increase risk with the required stops.
        weights = (40, 35, 25) if deficit > 2 * max_score else (55, 30, 15)
        if state.down >= 3 and state.yards_to_go >= 7:
            weights = (45, 10, 45)
        elif state.yards_to_go <= 3:
            weights = (weights[0] - 10, weights[1] + 10, weights[2])

        if self._defense_rng is None:
            # Derive a namespaced seed without advancing engine dice. Do not
            # clone its stream: that would correlate formations with next rolls.
            self._defense_rng = random.Random(f"paydirt-late-defense:{random.getstate()!r}")
        return self._defense_rng.choices(
            (DefenseType.STANDARD, DefenseType.SHORT_YARDAGE, DefenseType.BLITZ),
            weights=weights, k=1,
        )[0]

    def _goal_line_defense(self, down, ytg) -> DefenseType:
        """Defense inside our own 5 yard line."""
        if ytg <= 2:
            # Expect power run
            return random.choice(
                [
                    DefenseType.SHORT_YARDAGE,
                    DefenseType.SHORT_YARDAGE,
                    DefenseType.STANDARD,
                    DefenseType.BLITZ,
                ]
            )
        else:
            return random.choice(
                [DefenseType.SHORT_YARDAGE, DefenseType.SHORT_PASS, DefenseType.STANDARD]
            )

    def _red_zone_defense(self, down, ytg) -> DefenseType:
        """Defense inside our 20."""
        if down == 3:
            if ytg <= 3:
                return random.choice(
                    [DefenseType.SHORT_YARDAGE, DefenseType.BLITZ, DefenseType.SHORT_PASS]
                )
            else:
                return random.choice(
                    [DefenseType.SHORT_PASS, DefenseType.BLITZ, DefenseType.STANDARD]
                )

        # Tighten up in red zone
        return random.choice(
            [DefenseType.STANDARD, DefenseType.SHORT_PASS, DefenseType.SHORT_YARDAGE]
        )

    def _prevent_defense(self, down, ytg) -> DefenseType:
        """Soft coverage to prevent big plays."""
        return random.choice(
            [
                DefenseType.LONG_PASS,
                DefenseType.LONG_PASS,
                DefenseType.SPREAD,
                DefenseType.SHORT_PASS,
            ]
        )

    def _two_minute_defense(self, down, ytg) -> DefenseType:
        """Defense against hurry-up offense."""
        if down == 3:
            if ytg <= 5:
                return random.choice([DefenseType.SHORT_PASS, DefenseType.BLITZ])
            else:
                return random.choice(
                    [DefenseType.LONG_PASS, DefenseType.BLITZ, DefenseType.SHORT_PASS]
                )

        # Expect quick passes
        return random.choice([DefenseType.SHORT_PASS, DefenseType.SPREAD, DefenseType.BLITZ])

    def _fourth_down_defense(self, ytg, field_pos) -> DefenseType:
        """Defense on 4th down."""
        # If they're likely to kick, standard
        if field_pos < 50 or (field_pos >= 60 and ytg > 3):
            return DefenseType.STANDARD

        # Short yardage - expect run
        if ytg <= 2:
            return random.choice([DefenseType.SHORT_YARDAGE, DefenseType.BLITZ])

        # Medium/long - expect pass
        return random.choice([DefenseType.SHORT_PASS, DefenseType.BLITZ])

    def _third_down_defense(self, ytg) -> DefenseType:
        """3rd down defense - get off the field."""
        if ytg <= 2:
            # 3rd and short - expect run, but watch for play action
            return random.choice(
                [DefenseType.SHORT_YARDAGE, DefenseType.STANDARD, DefenseType.BLITZ]
            )
        elif ytg <= 5:
            # 3rd and medium - could be run or pass
            return random.choice([DefenseType.SHORT_PASS, DefenseType.BLITZ, DefenseType.STANDARD])
        elif ytg <= 10:
            # 3rd and long - passing situation
            return random.choice([DefenseType.SHORT_PASS, DefenseType.LONG_PASS, DefenseType.BLITZ])
        else:
            # 3rd and very long - prevent the first down
            return random.choice(
                [DefenseType.LONG_PASS, DefenseType.SHORT_PASS, DefenseType.SPREAD]
            )

    def _early_down_defense(self, down, ytg) -> DefenseType:
        """1st and 2nd down defense."""
        if ytg <= 3:
            # Short yardage situation
            return random.choice(
                [DefenseType.SHORT_YARDAGE, DefenseType.STANDARD, DefenseType.BLITZ]
            )

        # Standard downs - balanced defense
        return random.choice(
            [
                DefenseType.STANDARD,
                DefenseType.STANDARD,
                DefenseType.SPREAD,
                DefenseType.SHORT_PASS,
                DefenseType.BLITZ,
            ]
        )

    def _should_play_prevent(self, time_left, quarter, score_diff) -> bool:
        """Check if we should play soft prevent defense."""
        # Big lead late in game
        if quarter == 4 and time_left < 5.0 and score_diff >= 14:
            return True
        # Comfortable lead at end of half
        return bool(quarter == 2 and time_left < 1.0 and score_diff >= 10)

    def _opponent_in_hurry_up(self, time_left, quarter, score_diff) -> bool:
        """Check if opponent is likely in hurry-up mode."""
        # End of half, they're trailing
        if quarter == 2 and time_left < 2.0 and score_diff > 0:
            return True
        # End of game, they're trailing
        return bool(quarter == 4 and time_left < 4.0 and score_diff > 0)

    def should_call_timeout_on_defense(self, game: PaydirtGameEngine) -> bool:
        """
        Decide if CPU should call a timeout when on defense.

        Call timeouts when:
        - Trailing late in the game and opponent has the ball
        - Need to stop the clock to get the ball back
        - Have timeouts remaining
        """
        state = game.state
        time_left = state.time_remaining
        quarter = 4 if state.is_overtime else state.quarter

        # Get score differential from CPU's perspective (CPU is on defense)
        if state.is_home_possession:
            # Home team has ball, CPU is away (defense)
            cpu_score = state.away_score
            opp_score = state.home_score
            cpu_timeouts = state.away_timeouts
        else:
            # Away team has ball, CPU is home (defense)
            cpu_score = state.home_score
            opp_score = state.away_score
            cpu_timeouts = state.home_timeouts

        score_diff = cpu_score - opp_score  # Negative = trailing

        # No timeouts available
        if cpu_timeouts <= 0:
            return False

        # Only use timeouts in 4th quarter or end of 2nd quarter
        if quarter not in [2, 4]:
            return False

        # End of 4th quarter - trailing and need to get ball back
        # Trailing by any amount with < 5 minutes left
        # More aggressive timeout usage when further behind or less time
        if (quarter == 4) and (score_diff < 0 and time_left <= 5.0):
            if time_left <= 2.0:
                return True  # Always use timeouts in final 2 minutes when trailing
            if score_diff <= -8 and time_left <= 4.0:
                return True  # Down by more than a TD with < 4 min
            if score_diff <= -14 and time_left <= 5.0:
                return True  # Down by 2+ TDs with < 5 min

        # End of 2nd quarter - trailing and want to get ball before half
        if quarter == 2 and score_diff < 0 and time_left <= 2.0:
            if time_left <= 1.0:
                return True  # Final minute of half when trailing
            if score_diff <= -7:
                return True  # Down by TD+ with < 2 min in half

        return False

    def should_call_timeout_on_offense(self, game: PaydirtGameEngine) -> bool:
        """
        Decide if CPU should call a timeout when on offense to preserve clock.

        Call timeouts when:
        - End of half/game and trying to score
        - Clock is running and need to stop it
        - Have timeouts remaining
        """
        state = game.state
        time_left = state.time_remaining
        quarter = 4 if state.is_overtime else state.quarter

        # Get score differential and timeouts from CPU's perspective (CPU is on offense)
        if state.is_home_possession:
            # Home team has ball, CPU is home (offense)
            cpu_score = state.home_score
            opp_score = state.away_score
            cpu_timeouts = state.home_timeouts
        else:
            # Away team has ball, CPU is away (offense)
            cpu_score = state.away_score
            opp_score = state.home_score
            cpu_timeouts = state.away_timeouts

        score_diff = cpu_score - opp_score

        # No timeouts available
        if cpu_timeouts <= 0:
            return False

        # Only use timeouts at end of Q2 or Q4
        if quarter not in [2, 4]:
            return False

        # End of Q2 - use timeouts to try to score before half
        # Use timeout if not leading by a lot (still want to score)
        if (quarter == 2 and time_left <= 1.0) and (score_diff < 14):
            return True

        # End of Q4 - use timeouts when trailing to preserve clock
        if quarter == 4:
            if score_diff < 0 and time_left <= 2.0:
                return True  # Trailing in final 2 minutes
            if score_diff <= -8 and time_left <= 4.0:
                return True  # Down by more than TD with < 4 min

        return False

    def should_accept_penalty(
        self,
        outcome,
        is_human_offense: bool,
        human_is_home: bool,
        game: PaydirtGameEngine | None = None,
    ) -> tuple[bool, int | None]:
        """
        Decide if CPU should accept the play result or the penalty.

        Per Paydirt rules, the offended team may accept either:
        - The result of the play (down counts)
        - The penalty yardage (down replayed)

        Args:
            outcome: PlayOutcome with pending_penalty_decision=True
            is_human_offense: Whether the human is on offense
            human_is_home: Whether the human is the home team

        Returns:
            Tuple of (accept_play: bool, penalty_index: Optional[int])
            If accept_play is True, penalty_index is not used.
            If accept_play is False, penalty_index is an index into
            outcome.penalty_choice.penalty_options (not the filtered list).
        """
        penalty_choice = outcome.penalty_choice
        play_result = penalty_choice.play_result

        is_fg_penalty = outcome.play_type == PlayType.FIELD_GOAL
        is_punt_penalty = outcome.play_type == PlayType.PUNT
        is_kickoff_penalty = outcome.play_type == PlayType.KICKOFF

        offended_is_offense = penalty_choice.offended_team == "offense"

        if offended_is_offense:
            filtered_penalties = [
                opt for opt in penalty_choice.penalty_options if opt.penalty_type in ["DEF", "PI"]
            ]
        else:
            filtered_penalties = [
                opt for opt in penalty_choice.penalty_options if opt.penalty_type == "OFF"
            ]

        if not filtered_penalties:
            return (True, None)

        play_yards = play_result.yards
        play_turnover = play_result.turnover
        play_td = play_result.touchdown is True or outcome.projected_touchdown is True

        accept_play = True
        best_penalty_idx = penalty_choice.penalty_options.index(filtered_penalties[0])

        if (is_punt_penalty and play_result.result_type == ResultType.FUMBLE
                and play_result.fumble_recovered):
            # A live returner loss gives the kicking team a fresh possession.
            # Keep that recovery, or erase our own return fumble by replaying.
            return (offended_is_offense, best_penalty_idx)

        if penalty_choice.kick_phase == "return_fumble":
            # The recovering team keeps the ball rather than hand it back for yards.
            return (True, best_penalty_idx)

        # The offended CPU can keep its own score or erase its opponent's.
        # Turnover is relative to the original offense, not to home/human control.
        if play_td:
            return (offended_is_offense != bool(play_turnover), best_penalty_idx)
        if is_punt_penalty and not offended_is_offense:
            # The engine offers KEEP+ only when the receiver can retain the
            # result and possession with the kicking-team foul added. This
            # dominates declining the same result without its extra yardage.
            for option in filtered_penalties:
                if option.raw_result.startswith("KEEP+"):
                    return (False, penalty_choice.penalty_options.index(option))
        if is_fg_penalty:
            best_penalty = filtered_penalties[0] if filtered_penalties else None
            if outcome.field_goal_made:
                # A made kick still offers the offended defense the foul: enforce
                # the longest one and make the offense re-kick from farther back
                # instead of scoring. More enforced yards never help the kicker,
                # including a half-distance enforcement.
                if best_penalty is not None and not offended_is_offense:
                    accepted = max(filtered_penalties, key=lambda option: option.yards)
                    accepted_index = penalty_choice.penalty_options.index(accepted)
                    if _field_goal_foul_costs_a_won_game(game, outcome, accepted_index):
                        # The made kick is a won game; replaying the down is not.
                        return (True, None)
                    accept_play = False
                    best_penalty_idx = accepted_index
                else:
                    accept_play = True
            elif best_penalty and offended_is_offense:
                accept_play = False
            else:
                accept_play = True
        elif is_punt_penalty or is_kickoff_penalty:
            best_penalty = filtered_penalties[0] if filtered_penalties else None
            if best_penalty:
                if best_penalty.auto_first_down:
                    accept_play = False  # Accept penalty for automatic first down
                elif (is_punt_penalty or is_kickoff_penalty) and offended_is_offense:
                    accept_play = False  # Accept the penalty and replay the kick.
                else:
                    accept_play = True  # Keep the play when no better kick option is offered.
            else:
                accept_play = True
        elif play_turnover:
            if offended_is_offense:
                accept_play = False
            else:
                accept_play = True
        elif offended_is_offense:
            retained = outcome.retained_play_situation
            if retained is not None and retained.first_down is True:
                # Once both choices earn a first down, an automatic-first flag
                # adds no value. Compare engine-enforced spots, not nominal yards.
                best_position = retained.ball_position
                chosen_index = None
                for index, situation in outcome.penalty_situations.items():
                    if situation.first_down and situation.ball_position > best_position:
                        best_position = situation.ball_position
                        chosen_index = index
                # Keep the actual gain on a tie; never discard it for a shorter
                # equivalent first down, including a half-distance penalty.
                return (chosen_index is None, chosen_index)
            best_penalty = None
            if filtered_penalties:
                # Sort penalties: Prefer auto_first_down, then most yards
                filtered_penalties.sort(key=lambda p: (p.auto_first_down, p.yards), reverse=True)
                best_penalty = filtered_penalties[0]

            if (best_penalty) and (best_penalty.auto_first_down or best_penalty.yards > play_yards):
                accept_play = False
                best_penalty_idx = penalty_choice.penalty_options.index(best_penalty)
        else:
            retained = outcome.retained_play_situation
            situations = outcome.penalty_situations
            if isinstance(retained, PenaltySituation) and isinstance(situations, dict):
                # An offensive foul replays the down from the previous spot.
                # Keep the play unless enforcement is strictly better for the
                # defense; never discard a play for an equivalent situation.
                best_index = None
                best_rank = _defensive_situation_rank(retained)
                for index, situation in situations.items():
                    if not isinstance(situation, PenaltySituation):
                        continue
                    rank = _defensive_situation_rank(situation)
                    if rank > best_rank:
                        best_rank, best_index = rank, index
                accept_play = best_index is None
                if best_index is not None:
                    best_penalty_idx = best_index
                if game is not None and _foul_hands_offense_a_kneel_out(
                    game, outcome, best_index,
                ):
                    # Late, a defense that must get the ball back should not
                    # enforce a foul that lets the offense kneel the game out
                    # when declining the play preserves a real possession.
                    return (True, None)
            elif play_yards > 0:
                accept_play = False

        return (accept_play, best_penalty_idx)


def create_computer_ai(
    difficulty: str, game: PaydirtGameEngine, cpu_is_home: bool
) -> ComputerAI:
    """Create a difficulty-configured opponent for any game interface.

    Args:
        difficulty: Easy, medium, or hard; unknown values default to medium.
        game: Engine supplying season behavior and team charts.
        cpu_is_home: Whether the CPU controls the home team.

    Returns:
        AI with season settings and, in hard mode, its own team analyzer.
    """
    difficulty = (difficulty or "medium").lower()
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"
    aggression = {"easy": 0.3, "medium": 0.5, "hard": 0.7}[difficulty]
    precision = {
        "easy": EASY_PRECISION, "medium": MEDIUM_PRECISION, "hard": HARD_PRECISION,
    }[difficulty]
    ai = ComputerAI(
        aggression=aggression,
        use_analysis=difficulty == "hard",
        ai_behavior=game.season_rules.ai_behavior,
        precision=precision,
    )
    ai.use_team_strength = difficulty == "medium"
    ai.set_team(game.state.home_chart if cpu_is_home else game.state.away_chart)
    return ai


# Convenience functions for backward compatibility
def computer_select_offense(game: PaydirtGameEngine) -> PlayType:
    """Select offensive play using default AI."""
    ai = ComputerAI(aggression=0.5)
    return ai.select_offense(game)


def computer_select_defense(game: PaydirtGameEngine) -> DefenseType:
    """Select defensive formation using default AI."""
    ai = ComputerAI(aggression=0.5)
    return ai.select_defense(game)


def computer_should_call_timeout_on_defense(game: PaydirtGameEngine) -> bool:
    """Check if CPU should call a timeout when on defense."""
    ai = ComputerAI(aggression=0.5)
    return ai.should_call_timeout_on_defense(game)


def computer_should_call_timeout_on_offense(game: PaydirtGameEngine) -> bool:
    """Check if CPU should call a timeout when on offense to preserve clock."""
    ai = ComputerAI(aggression=0.5)
    return ai.should_call_timeout_on_offense(game)


def cpu_should_go_for_two(
    game: PaydirtGameEngine, ai: ComputerAI | None = None, *, try_pending: bool = False,
) -> bool:
    """
    Determine if CPU should go for 2-point conversion.

    Args:
        game: The game engine
        ai: Optional ComputerAI instance (creates default if not provided)
        try_pending: True only when a touchdown conversion is still owed.

    Returns:
        True if should go for 2, False to kick extra point
    """
    if ai is None:
        ai = ComputerAI(aggression=0.5)
    return ai.should_go_for_two(game, try_pending=try_pending)


def cpu_should_onside_kick(game: PaydirtGameEngine, ai: ComputerAI | None = None) -> bool:
    """
    Determine if CPU should attempt an onside kick.

    Args:
        game: The game engine
        ai: Optional ComputerAI instance (creates default if not provided)

    Returns:
        True for onside kick, False for regular kickoff
    """
    if ai is None:
        ai = ComputerAI(aggression=0.5)
    return ai.should_onside_kick(game)


def cpu_should_accept_penalty(
    outcome,
    is_human_offense: bool,
    human_is_home: bool,
    ai: ComputerAI | None = None,
    *,
    game: PaydirtGameEngine | None = None,
) -> tuple[bool, int | None]:
    """
    Decide if CPU should accept the play result or the penalty.

    Args:
        outcome: PlayOutcome with pending_penalty_decision=True
        is_human_offense: Whether the human is on offense
        human_is_home: Whether the human is the home team
        ai: Optional ComputerAI instance (creates default if not provided)
        game: Optional live engine; enables clock/score/timeout-aware choices

    Returns:
        Tuple of (accept_play: bool, penalty_index: Optional[int])
    """
    if ai is None:
        ai = ComputerAI(aggression=0.5)
    return ai.should_accept_penalty(
        outcome, is_human_offense, human_is_home, game=game,
    )


def cpu_should_attempt_end_zone_return(game, outcome, return_team_is_home: bool) -> bool:
    """Decide an own-end-zone interception return from catch depth and situation.

    Args:
        game: The game engine (supplies score, clock and period).
        outcome: Pending outcome carrying the engine-reported catch depth.
        return_team_is_home: Whether the intercepting team is home.

    Returns:
        True to attempt the return, False to take the touchback. The decision
        never inspects the pending return dice.
    """
    from .interception_policy import should_attempt_end_zone_return

    depth = getattr(outcome, "int_catch_depth", None)
    if depth is None:
        return False
    score_diff = (
        game.state.home_score - game.state.away_score
        if return_team_is_home
        else game.state.away_score - game.state.home_score
    )
    return should_attempt_end_zone_return(
        catch_depth=depth,
        score_differential=score_diff,
        quarter=game.state.quarter,
        time_remaining=game.state.time_remaining,
        is_overtime=game.state.is_overtime,
    )
