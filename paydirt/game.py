"""
Main game engine for Paydirt football simulation.
"""
import random

from .models import (
    GameState, Team, PlayType, DefenseType, PlayOutcome, PlayResult
)
from .team_charts import (
    resolve_play, resolve_field_goal, resolve_punt,
    resolve_extra_point, resolve_two_point_conversion, roll_dice
)


class PaydirtGame:
    """
    Main game class that manages the flow of a Paydirt football game.
    """

    def __init__(self, home_team: Team, away_team: Team):
        """
        Initialize a new game.
        
        Args:
            home_team: The home team
            away_team: The away team
        """
        self.state = GameState(home_team=home_team, away_team=away_team)
        self.play_history: list[dict] = []
        self.home_team = home_team
        self.away_team = away_team

    def kickoff(self, receiving_team_is_home: bool = False) -> dict:
        """
        Perform a kickoff to start the game or half.
        
        Args:
            receiving_team_is_home: True if home team receives
            
        Returns:
            Dict with kickoff result details
        """
        dice_roll = roll_dice()

        # Kickoff return yardage based on dice roll
        return_yards = {
            2: 5,    # Touchback/poor return
            3: 10,
            4: 15,
            5: 18,
            6: 20,
            7: 22,
            8: 25,
            9: 28,
            10: 35,
            11: 45,
            12: 75,  # Possible return TD
        }

        yards = return_yards[dice_roll]

        # Set possession
        self.state.is_home_possession = receiving_team_is_home
        self.state.possession = self.home_team if receiving_team_is_home else self.away_team

        # Ball starts at the return yardage (from own goal line)
        self.state.ball_position = yards
        self.state.down = 1
        self.state.yards_to_go = 10

        # Check for return touchdown
        touchdown = yards >= 100
        if touchdown:
            self.state.ball_position = 100
            self.state.score_touchdown()

        result = {
            "type": "kickoff",
            "dice_roll": dice_roll,
            "return_yards": yards,
            "touchdown": touchdown,
            "receiving_team": self.state.possession.name,
            "ball_position": self.state.get_field_position_description(),
        }

        self.play_history.append(result)
        self._use_play_time()

        return result

    def run_play(self, play_type: PlayType, defense_type: DefenseType) -> dict:
        """
        Execute an offensive play.
        
        Args:
            play_type: The offensive play to run
            defense_type: The defensive formation
            
        Returns:
            Dict with play result details
        """
        if self.state.game_over:
            return {"error": "Game is over"}

        offense = self.state.possession
        defense = self.home_team if not self.state.is_home_possession else self.away_team

        # Handle special teams plays
        if play_type == PlayType.PUNT:
            return self._handle_punt()
        elif play_type == PlayType.FIELD_GOAL:
            return self._handle_field_goal()

        # Resolve the play
        dice_roll, outcome = resolve_play(play_type, defense_type, offense, defense)

        # Track stats
        is_pass = play_type in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                                PlayType.LONG_PASS, PlayType.SCREEN_PASS]

        # Build result
        result = {
            "type": "play",
            "play_type": play_type.value,
            "defense_type": defense_type.value,
            "dice_roll": dice_roll,
            "result": outcome.result.value,
            "yards": outcome.yards,
            "description": outcome.description,
            "offense": offense.name,
            "down": self.state.down,
            "yards_to_go": self.state.yards_to_go,
            "ball_position_before": self.state.get_field_position_description(),
        }

        # Handle turnovers
        if outcome.turnover:
            self._handle_turnover(outcome)
            result["turnover"] = True
            result["new_possession"] = self.state.possession.name
        else:
            # Advance the ball
            first_down = self.state.advance_ball(outcome.yards)

            # Check for touchdown
            if self.state.ball_position >= 100:
                self.state.score_touchdown()
                result["touchdown"] = True
                result["scoring"] = True
            # Check for safety
            elif self.state.ball_position <= 0:
                self.state.score_safety()
                self._handle_safety()
                result["safety"] = True
                result["scoring"] = True
            elif not first_down:
                self.state.next_down()

        # Update stats
        if outcome.yards > 0:
            offense.stats.total_yards += outcome.yards
            if is_pass:
                offense.stats.passing_yards += outcome.yards
            else:
                offense.stats.rushing_yards += outcome.yards

        if outcome.turnover:
            offense.stats.turnovers += 1

        result["ball_position_after"] = self.state.get_field_position_description()
        result["down_after"] = self.state.down
        result["yards_to_go_after"] = self.state.yards_to_go
        result["score"] = f"{self.away_team.abbreviation} {self.state.away_score} - {self.home_team.abbreviation} {self.state.home_score}"

        self.play_history.append(result)
        self._use_play_time()

        return result

    def _handle_punt(self) -> dict:
        """Handle a punt play."""
        punter_rating = self.state.possession.special_teams
        dice_roll, punt_distance = resolve_punt(punter_rating)

        result = {
            "type": "punt",
            "dice_roll": dice_roll,
            "punt_distance": punt_distance,
            "punting_team": self.state.possession.name,
            "ball_position_before": self.state.get_field_position_description(),
        }

        # Calculate where the ball lands
        new_position = self.state.ball_position + punt_distance

        # Touchback if it goes into end zone
        if new_position >= 100:
            new_position = 80  # Touchback, ball at opponent's 20
            result["touchback"] = True

        # Switch possession and flip field
        self.state.switch_possession()
        self.state.ball_position = 100 - new_position

        # Ensure ball position is valid
        if self.state.ball_position < 1:
            self.state.ball_position = 20  # Touchback

        result["ball_position_after"] = self.state.get_field_position_description()
        result["receiving_team"] = self.state.possession.name

        self.play_history.append(result)
        self._use_play_time()

        return result

    def _handle_field_goal(self) -> dict:
        """Handle a field goal attempt."""
        # Field goal distance is ball position + 17 yards (end zone + snap)
        distance = (100 - self.state.ball_position) + 17
        kicker_rating = self.state.possession.special_teams

        dice_roll, success = resolve_field_goal(distance, kicker_rating)

        result = {
            "type": "field_goal",
            "dice_roll": dice_roll,
            "distance": distance,
            "success": success,
            "kicking_team": self.state.possession.name,
            "ball_position_before": self.state.get_field_position_description(),
        }

        if success:
            self.state.score_field_goal()
            result["scoring"] = True
            # Kickoff after field goal
            result["next"] = "kickoff"
        else:
            # Missed field goal - other team gets ball at spot of kick (or 20)
            spot = max(20, self.state.ball_position)
            self.state.switch_possession()
            self.state.ball_position = 100 - spot
            result["ball_position_after"] = self.state.get_field_position_description()

        result["score"] = f"{self.away_team.abbreviation} {self.state.away_score} - {self.home_team.abbreviation} {self.state.home_score}"

        self.play_history.append(result)
        self._use_play_time()

        return result

    def attempt_extra_point(self) -> dict:
        """Attempt an extra point after a touchdown."""
        kicker_rating = self.state.possession.special_teams
        dice_roll, success = resolve_extra_point(kicker_rating)

        result = {
            "type": "extra_point",
            "dice_roll": dice_roll,
            "success": success,
            "kicking_team": self.state.possession.name,
        }

        if success:
            self.state.score_extra_point()

        result["score"] = f"{self.away_team.abbreviation} {self.state.away_score} - {self.home_team.abbreviation} {self.state.home_score}"

        self.play_history.append(result)

        return result

    def attempt_two_point_conversion(self, play_type: PlayType) -> dict:
        """Attempt a two-point conversion after a touchdown."""
        offense = self.state.possession
        defense = self.home_team if not self.state.is_home_possession else self.away_team

        dice_roll, success = resolve_two_point_conversion(play_type, offense, defense)

        result = {
            "type": "two_point_conversion",
            "play_type": play_type.value,
            "dice_roll": dice_roll,
            "success": success,
            "offense": offense.name,
        }

        if success:
            self.state.score_two_point_conversion()

        result["score"] = f"{self.away_team.abbreviation} {self.state.away_score} - {self.home_team.abbreviation} {self.state.home_score}"

        self.play_history.append(result)

        return result

    def _handle_turnover(self, outcome: PlayOutcome):
        """Handle a turnover (interception or fumble)."""
        # For interceptions, the return might gain/lose yards
        if outcome.result == PlayResult.INTERCEPTION:
            return_yards = random.randint(0, 20)
        else:
            return_yards = 0

        # Switch possession
        self.state.switch_possession()

        # Adjust ball position for return
        self.state.ball_position = min(99, self.state.ball_position + return_yards)

    def _handle_safety(self):
        """Handle a safety - other team gets free kick."""
        # After safety, team that was scored on kicks off from their 20
        self.state.switch_possession()
        self.state.ball_position = 20

    def _use_play_time(self, seconds: float = None):
        """Use game clock time for a play."""
        if seconds is None:
            # Random time between 5 and 40 seconds per play
            seconds = random.uniform(5, 40)

        self.state.use_time(seconds)

    def get_game_status(self) -> dict:
        """Get the current game status."""
        return {
            "quarter": self.state.quarter,
            "time_remaining": f"{int(self.state.time_remaining)}:{int((self.state.time_remaining % 1) * 60):02d}",
            "score": {
                "away": {"team": self.away_team.abbreviation, "score": self.state.away_score},
                "home": {"team": self.home_team.abbreviation, "score": self.state.home_score},
            },
            "possession": self.state.possession.abbreviation,
            "ball_position": self.state.get_field_position_description(),
            "down": self.state.down,
            "yards_to_go": self.state.yards_to_go,
            "game_over": self.state.game_over,
        }

    def get_stats(self) -> dict:
        """Get game statistics for both teams."""
        return {
            "away": {
                "team": self.away_team.name,
                "score": self.state.away_score,
                "total_yards": self.away_team.stats.total_yards,
                "rushing_yards": self.away_team.stats.rushing_yards,
                "passing_yards": self.away_team.stats.passing_yards,
                "turnovers": self.away_team.stats.turnovers,
            },
            "home": {
                "team": self.home_team.name,
                "score": self.state.home_score,
                "total_yards": self.home_team.stats.total_yards,
                "rushing_yards": self.home_team.stats.rushing_yards,
                "passing_yards": self.home_team.stats.passing_yards,
                "turnovers": self.home_team.stats.turnovers,
            },
        }


def simulate_drive(game: PaydirtGame, max_plays: int = 20) -> list[dict]:
    """
    Simulate an entire offensive drive with AI play calling.
    
    Args:
        game: The game instance
        max_plays: Maximum plays before giving up
        
    Returns:
        List of play results
    """
    results = []
    plays = 0

    while plays < max_plays and not game.state.game_over:
        # Simple AI play calling based on situation
        play_type = _ai_select_play(game.state)
        defense_type = _ai_select_defense(game.state)

        # Check for special teams situations
        if play_type in [PlayType.PUNT, PlayType.FIELD_GOAL]:
            result = game.run_play(play_type, defense_type)
            results.append(result)
            break

        result = game.run_play(play_type, defense_type)
        results.append(result)
        plays += 1

        # Check if drive ended
        if result.get("touchdown") or result.get("turnover") or result.get("safety"):
            break

        # Check if possession changed (turnover on downs)
        if game.state.possession != (game.home_team if game.state.is_home_possession else game.away_team):
            break

    return results


def _ai_select_play(state: GameState) -> PlayType:
    """Simple AI to select an offensive play based on game situation."""
    ball_pos = state.ball_position
    down = state.down
    yards_to_go = state.yards_to_go

    # 4th down decisions
    if down == 4:
        # In field goal range (inside opponent's 35)
        if ball_pos >= 65:
            return PlayType.FIELD_GOAL
        # Deep in own territory - punt
        elif ball_pos < 50:
            return PlayType.PUNT
        # Go for it in no-man's land or short yardage
        elif yards_to_go <= 2:
            return random.choice([PlayType.RUN_MIDDLE, PlayType.SHORT_PASS])
        else:
            return PlayType.PUNT

    # Goal line (inside 5)
    if ball_pos >= 95:
        return random.choice([PlayType.RUN_MIDDLE, PlayType.RUN_LEFT, PlayType.SHORT_PASS])

    # Red zone (inside 20)
    if ball_pos >= 80:
        return random.choice([
            PlayType.RUN_MIDDLE, PlayType.RUN_RIGHT,
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS
        ])

    # Long yardage (need 7+)
    if yards_to_go >= 7:
        return random.choice([
            PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
            PlayType.LONG_PASS, PlayType.SCREEN_PASS
        ])

    # Short yardage (need 3 or less)
    if yards_to_go <= 3:
        return random.choice([
            PlayType.RUN_MIDDLE, PlayType.RUN_LEFT,
            PlayType.RUN_RIGHT, PlayType.SHORT_PASS
        ])

    # Normal situation - mix it up
    return random.choice([
        PlayType.RUN_LEFT, PlayType.RUN_RIGHT, PlayType.RUN_MIDDLE,
        PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.DRAW,
        PlayType.SCREEN_PASS
    ])


def _ai_select_defense(state: GameState) -> DefenseType:
    """Simple AI to select a defensive formation based on game situation."""
    ball_pos = state.ball_position
    down = state.down
    yards_to_go = state.yards_to_go

    # Goal line defense
    if ball_pos >= 95:
        return DefenseType.GOAL_LINE

    # Prevent defense in obvious passing situations
    if yards_to_go >= 15:
        return DefenseType.PREVENT

    # Blitz on 3rd and medium
    if down == 3 and 4 <= yards_to_go <= 8:
        return random.choice([DefenseType.BLITZ, DefenseType.NORMAL])

    # Normal defense most of the time
    return DefenseType.NORMAL
