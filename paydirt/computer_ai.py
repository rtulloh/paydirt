"""
Computer AI for Paydirt play calling.
Makes intelligent decisions based on:
- Down and distance
- Field position
- Time remaining
- Score differential
- Game situation (2-minute drill, goal line, etc.)
"""
import random

from .play_resolver import PlayType, DefenseType
from .game_engine import PaydirtGameEngine


class ComputerAI:
    """
    Intelligent computer opponent for Paydirt.
    
    Play calling philosophy:
    - Balanced attack on early downs
    - Situational awareness for 3rd/4th down
    - Clock management in late-game situations
    - Aggressive when trailing, conservative when leading
    """

    def __init__(self, aggression: float = 0.5):
        """
        Initialize AI with aggression level.
        
        Args:
            aggression: 0.0 = very conservative, 1.0 = very aggressive
        """
        self.aggression = aggression
        self.last_mode = None  # Track current mode for logging

    def select_offense(self, game: PaydirtGameEngine) -> PlayType:
        """
        Select an offensive play based on game situation.
        
        Decision factors:
        1. Down and distance
        2. Field position
        3. Time remaining
        4. Score differential
        5. Quarter
        """
        play_type, _, _ = self.select_offense_with_clock_management(game)
        return play_type

    def select_offense_with_clock_management(self, game: PaydirtGameEngine) -> tuple:
        """
        Select an offensive play with clock management options.
        
        Returns:
            tuple: (PlayType, out_of_bounds: bool, no_huddle: bool)
        """
        state = game.state
        down = state.down
        ytg = state.yards_to_go
        field_pos = state.ball_position  # 0=own goal, 100=opponent goal
        time_left = state.time_remaining
        quarter = state.quarter

        # Calculate score differential (positive = winning)
        if state.is_home_possession:
            score_diff = state.home_score - state.away_score
        else:
            score_diff = state.away_score - state.home_score
        
        # Clock management flags
        use_oob = False
        use_no_huddle = False

        # ============================================================
        # SPECIAL SITUATIONS - Time-based checks FIRST (most important)
        # ============================================================

        # 4th Down Decision
        if down == 4:
            self.last_mode = "4th Down"
            play = self._fourth_down_decision(game, ytg, field_pos, time_left, quarter, score_diff)
            # Use OOB on passing plays in hurry-up 4th down situations
            if self._needs_hurry_up(time_left, quarter, score_diff):
                use_no_huddle = True
                if play in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN]:
                    use_oob = True
            return (play, use_oob, use_no_huddle)

        # 2-Minute Drill (time-critical - end of half, aggressive clock management)
        if self._is_two_minute_drill(time_left, quarter, score_diff):
            self.last_mode = "Two-Minute Drill"
            play = self._two_minute_offense(down, ytg, field_pos, score_diff, time_left)
            use_no_huddle = True
            # Use OOB designation on passing plays to guarantee clock stops
            if play in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN]:
                use_oob = True
            return (play, use_oob, use_no_huddle)

        # Running Out Clock (time-critical - protecting lead)
        if self._should_run_clock(time_left, quarter, score_diff):
            self.last_mode = "Clock Killing"
            play = self._clock_killing_offense(down, ytg, time_left, field_pos)
            return (play, False, False)  # No hurry, let clock run

        # ============================================================
        # FIELD-POSITION BASED SITUATIONS
        # ============================================================

        # Goal Line (inside 5 yard line)
        if field_pos >= 95:
            self.last_mode = "Goal Line"
            play = self._goal_line_offense(ytg)
            if self._needs_hurry_up(time_left, quarter, score_diff):
                use_no_huddle = True
            return (play, use_oob, use_no_huddle)

        # Red Zone (inside 20)
        if field_pos >= 80:
            self.last_mode = "Red Zone"
            play = self._red_zone_offense(down, ytg)
            if self._needs_hurry_up(time_left, quarter, score_diff):
                use_no_huddle = True
            return (play, use_oob, use_no_huddle)

        # ============================================================
        # STANDARD SITUATIONS
        # ============================================================
        self.last_mode = None  # Clear mode for standard plays

        # 3rd Down
        if down == 3:
            play = self._third_down_offense(ytg, field_pos)
            return (play, use_oob, use_no_huddle)

        # 2nd Down
        if down == 2:
            play = self._second_down_offense(ytg)
            return (play, use_oob, use_no_huddle)

        # 1st Down - balanced attack
        play = self._first_down_offense(field_pos)
        return (play, use_oob, use_no_huddle)

    def _fourth_down_decision(self, game, ytg, field_pos, time_left, quarter, score_diff) -> PlayType:
        """
        Decide what to do on 4th down using 1983 NFL decision patterns.
        
        Historical context (1983 NFL):
        - Between opponent's 30-40: ~58% FG, ~30% punt, ~12% go for it
        - FG accuracy: 40-49 yards ~65%, 50+ yards ~35%
        - League average FG accuracy: ~71.5%
        - Going for it was reserved for 4th-and-inches or desperation
        - Coaches were significantly more conservative than modern era
        
        Returns: PlayType.PUNT, PlayType.FIELD_GOAL, or a go-for-it play
        """

        # Calculate field goal distance and range
        # Ball on 30 = 47 yard FG, ball on 40 = 57 yard FG
        fg_distance = 100 - field_pos + 17  # End zone + holder

        # 1983-era field goal probability tiers
        fg_easy = fg_distance <= 35      # ~80%+ make rate (chip shot)
        fg_makeable = fg_distance <= 47  # ~65% make rate (inside 30)
        fg_long = fg_distance <= 55      # ~35% make rate (30-40 yard line)

        # ============================================================
        # DESPERATION SITUATIONS (4th quarter, trailing, low time)
        # ============================================================

        if quarter == 4 and score_diff < 0:
            # Must score to win/tie
            if time_left < 2.0:
                # Under 2 minutes, trailing
                if fg_easy and score_diff >= -3:
                    return PlayType.FIELD_GOAL  # FG ties or wins
                elif fg_makeable and score_diff >= -3:
                    return PlayType.FIELD_GOAL  # Take the points
                else:
                    # Must go for it - need TD or can't kick
                    return self._go_for_it_play(ytg)

            # 2-5 minutes left, trailing
            if time_left < 5.0:
                if fg_easy and score_diff >= -3:
                    return PlayType.FIELD_GOAL
                elif ytg <= 2:
                    return self._go_for_it_play(ytg)  # Short yardage, go for it
                elif fg_makeable and score_diff >= -3:
                    return PlayType.FIELD_GOAL
                elif field_pos >= 50:
                    return self._go_for_it_play(ytg)  # In opponent territory, be aggressive

        # ============================================================
        # FIELD GOAL DECISIONS (1983 conservative approach)
        # ============================================================

        # Easy field goal (inside 20) - almost always kick
        if fg_easy:
            # Only go for it on 4th and inches inside the 5 with high aggression
            if ytg <= 1 and self.aggression > 0.8 and field_pos >= 95:
                return self._go_for_it_play(ytg)
            return PlayType.FIELD_GOAL

        # Makeable field goal (inside 30, 47 yards or less)
        # 1983: ~65% success rate, almost always kick
        if fg_makeable:
            # 4th and 1 - moderately aggressive coaches go for it
            if ytg <= 1 and self.aggression >= 0.5:
                return self._go_for_it_play(ytg)
            return PlayType.FIELD_GOAL

        # Long field goal range (30-40 yard line, 47-57 yard kick)
        # 1983 pattern: ~58% FG, ~30% punt, ~12% go for it
        if fg_long:
            # 4th and 1 - go for it with moderate aggression
            if ytg <= 1 and self.aggression >= 0.5:
                return self._go_for_it_play(ytg)

            # 4th and 2 - rare to go for it in 1983
            if ytg <= 2 and self.aggression > 0.8:
                return self._go_for_it_play(ytg)

            # Decision between FG and punt based on distance and aggression
            # Closer to 30 (shorter FG) = more likely to kick
            # Closer to 40 (longer FG) = more likely to punt if conservative
            if fg_distance <= 50:
                # 47-50 yard range - mostly kick FG
                return PlayType.FIELD_GOAL
            else:
                # 50-57 yard range - split between FG and punt
                # Aggressive coaches try the long FG, conservative punt
                if self.aggression >= 0.5:
                    return PlayType.FIELD_GOAL
                else:
                    return PlayType.PUNT

        # ============================================================
        # OUTSIDE FG RANGE (beyond opponent's 40)
        # ============================================================

        # Just outside FG range (around 40-45 yard line)
        if field_pos >= 55:
            # 4th and 1 - go for it
            if ytg <= 1:
                return self._go_for_it_play(ytg)
            # 4th and 2 with aggression
            if ytg <= 2 and self.aggression > 0.6:
                return self._go_for_it_play(ytg)
            # Otherwise punt - too far for FG, don't want to give up field position
            return PlayType.PUNT

        # At midfield (45-55 yard line)
        if field_pos >= 45:
            # 4th and 1 - go for it
            if ytg <= 1:
                return self._go_for_it_play(ytg)
            # 4th and 2 with high aggression only
            if ytg <= 2 and self.aggression > 0.7:
                return self._go_for_it_play(ytg)
            # Otherwise punt from midfield
            return PlayType.PUNT

        # In own territory (inside own 45) - almost always punt
        # 1983 coaches were very conservative here
        if ytg <= 1 and self.aggression > 0.9:
            # Only go for it on 4th and inches with extreme aggression
            return self._go_for_it_play(ytg)
        return PlayType.PUNT

    def _go_for_it_play(self, ytg: int) -> PlayType:
        """Select a play when going for it on 4th down."""
        if ytg <= 1:
            # 4th and 1 - power run (75%+) or QB Sneak
            return random.choice([PlayType.LINE_PLUNGE, PlayType.LINE_PLUNGE, PlayType.LINE_PLUNGE,
                                  PlayType.OFF_TACKLE, PlayType.OFF_TACKLE, PlayType.QB_SNEAK])
        elif ytg <= 3:
            # 4th and short - mix of run and pass
            return random.choice([PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.DRAW])
        elif ytg <= 6:
            # 4th and medium - quick passes
            return random.choice([PlayType.SHORT_PASS, PlayType.SCREEN, PlayType.DRAW])
        else:
            # 4th and long - need a chunk play
            return random.choice([PlayType.MEDIUM_PASS, PlayType.SHORT_PASS, PlayType.LONG_PASS])

    def _goal_line_offense(self, ytg) -> PlayType:
        """Play calling inside the 5 yard line."""
        if ytg <= 1:
            # Goal line stand - power run or QB Sneak
            return random.choice([PlayType.QB_SNEAK, PlayType.LINE_PLUNGE, PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE])
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
        return random.choice([
            PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS,
            PlayType.DRAW, PlayType.SCREEN
        ])

    def _two_minute_offense(self, down, ytg, field_pos, score_diff, time_left) -> PlayType:
        """Hurry-up offense when trailing late. Prioritize passing to stop clock."""

        # Hail Mary - last play of half/game, need TD, in range
        if time_left <= 0.15 and field_pos >= 40 and score_diff < 0:
            # ~10 seconds left, need a miracle
            return PlayType.HAIL_MARY

        # Spike Ball - stop clock after a big gain if very low on time
        # (AI would need to track previous play, so this is situational)

        # Need big play if way behind - BUT NOT in the red zone/goal line
        # Don't throw long passes from inside the 20 yard line
        if score_diff <= -14 and field_pos < 80:
            return random.choice([PlayType.LONG_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS])

        # Under 2 minutes - ONLY pass plays (clock stops on incomplete)
        # Avoid running plays that keep clock running
        if time_left < 2.0:
            if down == 3:
                if ytg <= 5:
                    return random.choice([PlayType.SHORT_PASS, PlayType.SCREEN])
                else:
                    return random.choice([PlayType.MEDIUM_PASS, PlayType.SHORT_PASS, PlayType.LONG_PASS])
            # Early downs - quick passes (avoid long passes in red zone)
            if score_diff <= -7 or field_pos < 50:
                # Don't use LONG_PASS from red zone (inside 20)
                if field_pos >= 80:
                    return random.choice([PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.SCREEN])
                return random.choice([PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SHORT_PASS])
            return random.choice([PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.SCREEN])

        # 3rd down - must convert (can use draw as surprise)
        if down == 3:
            if ytg <= 5:
                return random.choice([PlayType.SHORT_PASS, PlayType.SCREEN, PlayType.DRAW])
            else:
                return random.choice([PlayType.MEDIUM_PASS, PlayType.SHORT_PASS])

        # Quick passes to stop clock and move chains (minimize running plays)
        plays = [
            PlayType.SHORT_PASS, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.SCREEN
        ]

        # Add long pass if need chunk plays (but not from red zone)
        if (score_diff <= -7 or field_pos < 50) and field_pos >= 80:
            # Red zone - use shorter routes only
            pass  # Don't add LONG_PASS
        elif score_diff <= -7 or field_pos < 50:
            plays.extend([PlayType.LONG_PASS, PlayType.MEDIUM_PASS])

        return random.choice(plays)

    def _clock_killing_offense(self, down, ytg, time_left, field_pos) -> PlayType:
        """Conservative offense when protecting a lead."""

        # QB Kneel when very late in game and can run out clock
        # Each kneel uses 40 seconds, so 3 kneels = 2 minutes
        if time_left <= 2.0 and down <= 3:
            # Can kneel out the clock - do it (unless too close to own goal)
            if field_pos >= 5:  # Not in danger of safety
                return PlayType.QB_KNEEL

        # 3rd down - still try to convert but safely
        if down == 3:
            if ytg <= 3:
                return random.choice([PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.DRAW])
            else:
                return random.choice([PlayType.SHORT_PASS, PlayType.DRAW, PlayType.SCREEN])

        # Run the ball to kill clock
        return random.choice([
            PlayType.LINE_PLUNGE, PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
            PlayType.OFF_TACKLE, PlayType.DRAW, PlayType.END_RUN
        ])

    def _third_down_offense(self, ytg, field_pos) -> PlayType:
        """3rd down play calling - must convert."""

        if ytg <= 2:
            # 3rd and short - run or quick pass
            return random.choice([
                PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.DRAW,
                PlayType.SHORT_PASS, PlayType.SCREEN
            ])
        elif ytg <= 5:
            # 3rd and medium - balanced
            return random.choice([
                PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.DRAW,
                PlayType.SCREEN, PlayType.OFF_TACKLE
            ])
        elif ytg <= 10:
            # 3rd and long - passing downs
            return random.choice([
                PlayType.MEDIUM_PASS, PlayType.SHORT_PASS, PlayType.SCREEN,
                PlayType.DRAW  # Draw can catch blitzing defense
            ])
        else:
            # 3rd and very long - need chunk play
            return random.choice([
                PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN
            ])

    def _second_down_offense(self, ytg) -> PlayType:
        """2nd down play calling."""

        if ytg <= 3:
            # 2nd and short - stay balanced, set up 3rd and short
            return random.choice([
                PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS,
                PlayType.DRAW, PlayType.END_RUN
            ])
        elif ytg <= 7:
            # 2nd and medium - balanced attack
            return random.choice([
                PlayType.OFF_TACKLE, PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                PlayType.DRAW, PlayType.END_RUN, PlayType.SCREEN
            ])
        else:
            # 2nd and long - need to get some back
            return random.choice([
                PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.DRAW,
                PlayType.SCREEN, PlayType.OFF_TACKLE
            ])

    def _first_down_offense(self, field_pos) -> PlayType:
        """1st down play calling - establish the offense."""

        # Deep in own territory - be careful
        if field_pos < 20:
            return random.choice([
                PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.SHORT_PASS,
                PlayType.DRAW
            ])

        # Normal field position - balanced attack
        return random.choice([
            PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN,
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.DRAW,
            PlayType.SCREEN
        ])

    def _is_two_minute_drill(self, time_left, quarter, score_diff) -> bool:
        """Check if we should be in hurry-up mode."""
        # End of half - try to score regardless of lead (unless huge lead)
        # Even when leading, smart teams try to add points before halftime
        if quarter == 2 and time_left < 2.0:
            # Only skip hurry-up if leading by 14+ (comfortable cushion)
            if score_diff < 14:
                return True
        # End of game, trailing - be more aggressive based on deficit
        if quarter == 4 and score_diff < 0:
            # Down by 2+ scores (9+) - hurry up with 8+ minutes left
            if score_diff <= -9 and time_left < 8.0:
                return True
            # Down by 1-2 scores - hurry up with 5+ minutes left
            if score_diff <= -4 and time_left < 5.0:
                return True
            # Down by any amount - hurry up with 4 minutes left
            if time_left < 4.0:
                return True
        # Way behind anytime in 4th quarter
        if quarter == 4 and score_diff <= -14:
            return True
        return False

    def _needs_hurry_up(self, time_left, quarter, score_diff) -> bool:
        """Check if we need to hurry (no-huddle, OOB designation)."""
        # More aggressive than two-minute drill - use no-huddle earlier
        if quarter == 4 and score_diff < 0:
            # Down by 2+ scores - no huddle with 10+ minutes left
            if score_diff <= -9 and time_left < 10.0:
                return True
            # Down by 1 score - no huddle with 6+ minutes left
            if score_diff <= -4 and time_left < 6.0:
                return True
            # Down by any amount - no huddle with 5 minutes left
            if time_left < 5.0:
                return True
        # End of half trailing
        if quarter == 2 and time_left < 2.0 and score_diff < 0:
            return True
        return False

    def _should_run_clock(self, time_left, quarter, score_diff) -> bool:
        """Check if we should be killing clock."""
        # Leading in 4th quarter
        if quarter == 4 and score_diff > 0:
            return True
        # Big lead in 2nd half
        if quarter >= 3 and score_diff >= 14:
            return True
        return False

    def select_defense(self, game: PaydirtGameEngine) -> DefenseType:
        """
        Select a defensive formation based on game situation.
        
        Decision factors:
        1. Down and distance (predict run vs pass)
        2. Field position
        3. Time remaining
        4. Score differential
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

    def _goal_line_defense(self, down, ytg) -> DefenseType:
        """Defense inside our own 5 yard line."""
        if ytg <= 2:
            # Expect power run
            return random.choice([
                DefenseType.SHORT_YARDAGE, DefenseType.SHORT_YARDAGE,
                DefenseType.STANDARD, DefenseType.BLITZ
            ])
        else:
            return random.choice([
                DefenseType.SHORT_YARDAGE, DefenseType.SHORT_PASS, DefenseType.STANDARD
            ])

    def _red_zone_defense(self, down, ytg) -> DefenseType:
        """Defense inside our 20."""
        if down == 3:
            if ytg <= 3:
                return random.choice([DefenseType.SHORT_YARDAGE, DefenseType.BLITZ, DefenseType.SHORT_PASS])
            else:
                return random.choice([DefenseType.SHORT_PASS, DefenseType.BLITZ, DefenseType.STANDARD])

        # Tighten up in red zone
        return random.choice([
            DefenseType.STANDARD, DefenseType.SHORT_PASS, DefenseType.SHORT_YARDAGE
        ])

    def _prevent_defense(self, down, ytg) -> DefenseType:
        """Soft coverage to prevent big plays."""
        return random.choice([
            DefenseType.LONG_PASS, DefenseType.LONG_PASS, DefenseType.SPREAD,
            DefenseType.SHORT_PASS
        ])

    def _two_minute_defense(self, down, ytg) -> DefenseType:
        """Defense against hurry-up offense."""
        if down == 3:
            if ytg <= 5:
                return random.choice([DefenseType.SHORT_PASS, DefenseType.BLITZ])
            else:
                return random.choice([DefenseType.LONG_PASS, DefenseType.BLITZ, DefenseType.SHORT_PASS])

        # Expect quick passes
        return random.choice([
            DefenseType.SHORT_PASS, DefenseType.SPREAD, DefenseType.BLITZ
        ])

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
            return random.choice([
                DefenseType.SHORT_YARDAGE, DefenseType.STANDARD, DefenseType.BLITZ
            ])
        elif ytg <= 5:
            # 3rd and medium - could be run or pass
            return random.choice([
                DefenseType.SHORT_PASS, DefenseType.BLITZ, DefenseType.STANDARD
            ])
        elif ytg <= 10:
            # 3rd and long - passing situation
            return random.choice([
                DefenseType.SHORT_PASS, DefenseType.LONG_PASS, DefenseType.BLITZ
            ])
        else:
            # 3rd and very long - prevent the first down
            return random.choice([
                DefenseType.LONG_PASS, DefenseType.SHORT_PASS, DefenseType.SPREAD
            ])

    def _early_down_defense(self, down, ytg) -> DefenseType:
        """1st and 2nd down defense."""
        if ytg <= 3:
            # Short yardage situation
            return random.choice([
                DefenseType.SHORT_YARDAGE, DefenseType.STANDARD, DefenseType.BLITZ
            ])

        # Standard downs - balanced defense
        return random.choice([
            DefenseType.STANDARD, DefenseType.STANDARD, DefenseType.SPREAD,
            DefenseType.SHORT_PASS, DefenseType.BLITZ
        ])

    def _should_play_prevent(self, time_left, quarter, score_diff) -> bool:
        """Check if we should play soft prevent defense."""
        # Big lead late in game
        if quarter == 4 and time_left < 5.0 and score_diff >= 14:
            return True
        # Comfortable lead at end of half
        if quarter == 2 and time_left < 1.0 and score_diff >= 10:
            return True
        return False

    def _opponent_in_hurry_up(self, time_left, quarter, score_diff) -> bool:
        """Check if opponent is likely in hurry-up mode."""
        # End of half, they're trailing
        if quarter == 2 and time_left < 2.0 and score_diff > 0:
            return True
        # End of game, they're trailing
        if quarter == 4 and time_left < 4.0 and score_diff > 0:
            return True
        return False

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
        quarter = state.quarter
        
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
        if quarter == 4:
            # Trailing by any amount with < 5 minutes left
            if score_diff < 0 and time_left <= 5.0:
                # More aggressive timeout usage when further behind or less time
                if time_left <= 2.0:
                    return True  # Always use timeouts in final 2 minutes when trailing
                if score_diff <= -8 and time_left <= 4.0:
                    return True  # Down by more than a TD with < 4 min
                if score_diff <= -14 and time_left <= 5.0:
                    return True  # Down by 2+ TDs with < 5 min
        
        # End of 2nd quarter - trailing and want to get ball before half
        if quarter == 2:
            if score_diff < 0 and time_left <= 2.0:
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
        quarter = state.quarter
        
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
        if quarter == 2 and time_left <= 1.0:
            # Use timeout if not leading by a lot (still want to score)
            if score_diff < 14:
                return True
        
        # End of Q4 - use timeouts when trailing to preserve clock
        if quarter == 4:
            if score_diff < 0 and time_left <= 2.0:
                return True  # Trailing in final 2 minutes
            if score_diff <= -8 and time_left <= 4.0:
                return True  # Down by more than TD with < 4 min
        
        return False


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
