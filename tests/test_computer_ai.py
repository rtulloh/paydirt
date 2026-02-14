"""
Tests for computer AI offensive and defensive play selection.
"""
import pytest
from unittest.mock import MagicMock

from paydirt.computer_ai import ComputerAI
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import PlayType, DefenseType
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


def create_mock_chart(short_name: str = "TEST", team_name: str = "Test Team") -> TeamChart:
    """Create a minimal mock TeamChart for testing."""
    return TeamChart(
        peripheral=PeripheralData(
            year=1983,
            team_name=team_name,
            team_nickname="Testers",
            power_rating=50,
            short_name=short_name
        ),
        offense=MagicMock(spec=OffenseChart),
        defense=MagicMock(spec=DefenseChart),
        special_teams=MagicMock(spec=SpecialTeamsChart)
    )


@pytest.fixture
def game():
    """Create a game engine for testing."""
    home_chart = create_mock_chart("HOME", "Home Team")
    away_chart = create_mock_chart("AWAY", "Away Team")
    return PaydirtGameEngine(home_chart, away_chart)


@pytest.fixture
def cpu_ai():
    """Create a CPU AI with default aggression."""
    return ComputerAI(aggression=0.5)


class TestSelectOffenseFirstDown:
    """Tests for first down play selection."""
    
    def test_first_and_10_returns_valid_play(self, game, cpu_ai):
        """First and 10 should return a valid offensive play."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 25  # Own 25
        
        play = cpu_ai.select_offense(game)
        
        assert play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN,
                       PlayType.DRAW, PlayType.SCREEN, PlayType.SHORT_PASS,
                       PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.TE_SHORT_LONG]
    
    def test_first_down_deep_in_own_territory_favors_runs(self, game, cpu_ai):
        """Deep in own territory, should favor conservative plays."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 10  # Own 10
        
        # Run multiple times to check distribution
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have some running plays
        run_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, 
                                                PlayType.END_RUN, PlayType.DRAW]]
        assert len(run_plays) > 0


class TestSelectOffenseSecondDown:
    """Tests for second down play selection."""
    
    def test_second_and_long_favors_passes(self, game, cpu_ai):
        """Second and long should favor passing plays."""
        game.state.down = 2
        game.state.yards_to_go = 8
        game.state.ball_position = 50
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have some passing plays
        pass_plays = [p for p in plays if p in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                                                 PlayType.LONG_PASS, PlayType.SCREEN,
                                                 PlayType.TE_SHORT_LONG]]
        assert len(pass_plays) > 0
    
    def test_second_and_short_can_run(self, game, cpu_ai):
        """Second and short should allow running plays."""
        game.state.down = 2
        game.state.yards_to_go = 2
        game.state.ball_position = 50
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have some running plays
        run_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
                                                PlayType.END_RUN, PlayType.DRAW]]
        assert len(run_plays) > 0


class TestSelectOffenseThirdDown:
    """Tests for third down play selection."""
    
    def test_third_and_short_favors_runs(self, game, cpu_ai):
        """Third and short should favor running plays."""
        game.state.down = 3
        game.state.yards_to_go = 1
        game.state.ball_position = 50
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have running plays for short yardage
        run_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
                                                PlayType.END_RUN, PlayType.DRAW]]
        assert len(run_plays) > 0
    
    def test_third_and_long_favors_passes(self, game, cpu_ai):
        """Third and long should favor passing plays."""
        game.state.down = 3
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have passing plays
        pass_plays = [p for p in plays if p in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                                                 PlayType.LONG_PASS, PlayType.SCREEN,
                                                 PlayType.TE_SHORT_LONG]]
        assert len(pass_plays) > 0


class TestFourthDownDecision:
    """Tests for fourth down decision making."""
    
    def test_fourth_down_deep_in_own_territory_punts(self, game, cpu_ai):
        """Fourth down deep in own territory should punt."""
        game.state.down = 4
        game.state.yards_to_go = 5
        game.state.ball_position = 25  # Own 25
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        
        play = cpu_ai.select_offense(game)
        
        assert play == PlayType.PUNT
    
    def test_fourth_down_in_fg_range_kicks(self, game, cpu_ai):
        """Fourth down in FG range should attempt field goal."""
        game.state.down = 4
        game.state.yards_to_go = 5
        game.state.ball_position = 75  # Opponent's 25, ~42 yard FG
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        
        play = cpu_ai.select_offense(game)
        
        assert play == PlayType.FIELD_GOAL
    
    def test_fourth_and_inches_may_go_for_it(self, game):
        """Fourth and inches with aggressive AI may go for it."""
        aggressive_ai = ComputerAI(aggression=0.8)
        game.state.down = 4
        game.state.yards_to_go = 1
        game.state.ball_position = 70  # Opponent's 30
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        
        # With high aggression, might go for it on 4th and 1
        play = aggressive_ai.select_offense(game)
        
        # Could be FG or go for it
        assert play in [PlayType.FIELD_GOAL, PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
                       PlayType.QB_SNEAK]
    
    def test_fourth_down_trailing_late_goes_for_it(self, game, cpu_ai):
        """Fourth down trailing late in game should go for it if needed."""
        game.state.down = 4
        game.state.yards_to_go = 5
        game.state.ball_position = 60  # Opponent's 40
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # 1 minute left
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing by 7
        game.state.is_home_possession = True
        
        play = cpu_ai.select_offense(game)
        
        # Should go for it when trailing late and need TD
        assert play not in [PlayType.PUNT]


class TestGoalLineOffense:
    """Tests for goal line offense."""
    
    def test_goal_line_favors_power_plays(self, game, cpu_ai):
        """Goal line should favor power running plays."""
        game.state.down = 1
        game.state.yards_to_go = 3
        game.state.ball_position = 97  # 3 yard line
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should have power plays
        power_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
                                                  PlayType.QB_SNEAK]]
        assert len(power_plays) > 0
        
        # Check mode was set
        assert cpu_ai.last_mode == "Goal Line"


class TestRedZoneOffense:
    """Tests for red zone offense."""
    
    def test_red_zone_sets_mode(self, game, cpu_ai):
        """Red zone should set the mode correctly."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 85  # Opponent's 15
        
        cpu_ai.select_offense(game)
        
        assert cpu_ai.last_mode == "Red Zone"


class TestTwoMinuteDrill:
    """Tests for two-minute drill offense."""
    
    def test_two_minute_drill_trailing_uses_passes(self, game, cpu_ai):
        """Two-minute drill when trailing should use passing plays."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 30
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing by 7
        game.state.is_home_possession = True
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should favor passing plays in two-minute drill
        pass_plays = [p for p in plays if p in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS,
                                                 PlayType.LONG_PASS, PlayType.SCREEN,
                                                 PlayType.TE_SHORT_LONG]]
        assert len(pass_plays) > 5  # Majority should be passes
        
        # Check mode was set
        assert cpu_ai.last_mode == "Two-Minute Drill"


class TestClockKillingOffense:
    """Tests for clock killing offense."""
    
    def test_clock_killing_favors_runs(self, game, cpu_ai):
        """Clock killing when leading should favor running plays."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 3.0  # 3 minutes left
        game.state.home_score = 21
        game.state.away_score = 14  # Leading by 7
        game.state.is_home_possession = True
        
        plays = [cpu_ai.select_offense(game) for _ in range(20)]
        
        # Should favor running plays to kill clock
        run_plays = [p for p in plays if p in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE,
                                                PlayType.END_RUN, PlayType.DRAW]]
        assert len(run_plays) > 5  # Majority should be runs
        
        # Check mode was set
        assert cpu_ai.last_mode == "Clock Killing"


class TestSelectDefense:
    """Tests for defensive play selection."""
    
    def test_defense_returns_valid_type(self, game, cpu_ai):
        """Defense selection should return a valid DefenseType."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        
        defense = cpu_ai.select_defense(game)
        
        assert defense in [DefenseType.STANDARD, DefenseType.SHORT_YARDAGE,
                          DefenseType.SPREAD, DefenseType.SHORT_PASS,
                          DefenseType.LONG_PASS, DefenseType.BLITZ]
    
    def test_goal_line_defense(self, game, cpu_ai):
        """Goal line should use appropriate defense."""
        game.state.down = 1
        game.state.yards_to_go = 3
        game.state.ball_position = 97  # Offense at 3 yard line
        
        defenses = [cpu_ai.select_defense(game) for _ in range(20)]
        
        # Should use goal line or short yardage defense at least sometimes
        goal_line_defenses = [d for d in defenses if d in [DefenseType.SHORT_YARDAGE, 
                                                            DefenseType.STANDARD,
                                                            DefenseType.SHORT_PASS]]
        assert len(goal_line_defenses) > 0
    
    def test_third_and_long_defense(self, game, cpu_ai):
        """Third and long should use pass defense."""
        game.state.down = 3
        game.state.yards_to_go = 12
        game.state.ball_position = 50
        
        defenses = [cpu_ai.select_defense(game) for _ in range(20)]
        
        # Should favor pass defense
        pass_defenses = [d for d in defenses if d in [DefenseType.SHORT_PASS,
                                                       DefenseType.LONG_PASS,
                                                       DefenseType.BLITZ]]
        assert len(pass_defenses) > 0
    
    def test_short_yardage_defense(self, game, cpu_ai):
        """Short yardage should use appropriate defense."""
        game.state.down = 3
        game.state.yards_to_go = 1
        game.state.ball_position = 50
        
        defenses = [cpu_ai.select_defense(game) for _ in range(20)]
        
        # Should have short yardage defense
        short_defenses = [d for d in defenses if d in [DefenseType.SHORT_YARDAGE,
                                                        DefenseType.STANDARD]]
        assert len(short_defenses) > 0


class TestAggressionLevels:
    """Tests for different aggression levels."""
    
    def test_conservative_ai_punts_more(self, game):
        """Conservative AI should punt more often on 4th down."""
        conservative_ai = ComputerAI(aggression=0.2)
        game.state.down = 4
        game.state.yards_to_go = 2
        game.state.ball_position = 55  # Opponent's 45
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        
        play = conservative_ai.select_offense(game)
        
        # Conservative should punt or kick FG
        assert play in [PlayType.PUNT, PlayType.FIELD_GOAL]
    
    def test_aggressive_ai_goes_for_it_more(self, game):
        """Aggressive AI should go for it more on 4th down."""
        aggressive_ai = ComputerAI(aggression=0.9)
        game.state.down = 4
        game.state.yards_to_go = 1
        game.state.ball_position = 65  # Opponent's 35
        game.state.quarter = 2
        game.state.time_remaining = 10.0
        
        # Run multiple times - aggressive AI should sometimes go for it
        plays = [aggressive_ai.select_offense(game) for _ in range(10)]
        
        # Should have some go-for-it plays
        go_for_it = [p for p in plays if p not in [PlayType.PUNT, PlayType.FIELD_GOAL]]
        # With 90% aggression on 4th and 1, should go for it
        assert len(go_for_it) > 0


class TestClockManagement:
    """Tests for AI clock management when trailing late in game."""

    def test_two_minute_drill_uses_no_huddle(self, game, cpu_ai):
        """Trailing in Q4 with < 2 min should use no-huddle."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing by 7

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        assert use_no_huddle is True

    def test_two_minute_drill_uses_oob_on_passes(self, game, cpu_ai):
        """Trailing in Q4 with < 2 min should use OOB on passing plays."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # 1:00 left
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing by 7

        # Run multiple times to get passing plays
        oob_count = 0
        for _ in range(20):
            play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)
            if play in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN]:
                if use_oob:
                    oob_count += 1

        # Should use OOB on most passing plays
        assert oob_count > 0

    def test_trailing_by_two_scores_triggers_hurry_up_earlier(self, game, cpu_ai):
        """Trailing by 9+ points should trigger hurry-up with 8+ minutes left."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 7.0  # 7:00 left
        game.state.is_home_possession = True
        game.state.home_score = 10
        game.state.away_score = 20  # Trailing by 10

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should be in hurry-up mode
        assert use_no_huddle is True

    def test_leading_does_not_use_hurry_up(self, game, cpu_ai):
        """Leading in Q4 should NOT use hurry-up."""
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 3.0  # 3:00 left
        game.state.is_home_possession = True
        game.state.home_score = 21
        game.state.away_score = 14  # Leading by 7

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should NOT be in hurry-up mode when leading
        assert use_no_huddle is False
        assert use_oob is False

    def test_two_minute_offense_avoids_running_plays(self, game, cpu_ai):
        """Under 2 minutes trailing, should avoid running plays."""
        game.state.down = 2
        game.state.yards_to_go = 8
        game.state.ball_position = 50
        game.state.quarter = 4
        game.state.time_remaining = 1.0  # 1:00 left
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 21  # Trailing by 7

        # Run multiple times
        running_plays = 0
        for _ in range(20):
            play, _, _ = cpu_ai.select_offense_with_clock_management(game)
            if play in [PlayType.LINE_PLUNGE, PlayType.OFF_TACKLE, PlayType.END_RUN, PlayType.DRAW]:
                running_plays += 1

        # Should have very few running plays under 2 minutes
        assert running_plays < 5  # Less than 25% running plays


class TestEndOfHalfClockManagement:
    """Tests for clock management at end of half - ensures time-based checks come before field position."""

    def test_red_zone_at_end_of_half_uses_two_minute_drill(self, game, cpu_ai):
        """
        When in red zone at end of half with time running out, should use two-minute drill.
        
        This tests the fix for the bug where CPU would enter red zone offense
        instead of using clock management (OOB designation) at the end of the half.
        """
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 87  # Enemy 13 (inside red zone)
        game.state.quarter = 2
        game.state.time_remaining = 0.4  # 0:24 left
        game.state.is_home_possession = True
        game.state.home_score = 21
        game.state.away_score = 17  # Leading by 4

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should be in two-minute drill mode, not red zone
        assert cpu_ai.last_mode == "Two-Minute Drill"
        # Should use no-huddle and OOB to stop clock
        assert use_no_huddle is True

    def test_red_zone_end_of_half_uses_oob_on_passes(self, game, cpu_ai):
        """
        In red zone at end of half, passing plays should use OOB designation.
        
        This ensures the CPU stops the clock on incomplete passes.
        """
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 85  # Enemy 15 (red zone)
        game.state.quarter = 2
        game.state.time_remaining = 0.5  # 0:30 left
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 10  # Leading by 4

        # Run multiple times to get a passing play
        oob_count = 0
        pass_count = 0
        for _ in range(30):
            play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)
            if play in [PlayType.SHORT_PASS, PlayType.MEDIUM_PASS, PlayType.LONG_PASS, PlayType.SCREEN]:
                pass_count += 1
                if use_oob:
                    oob_count += 1

        # Should have gotten some passing plays with OOB
        assert pass_count > 0
        # All passing plays should use OOB in two-minute drill
        assert oob_count == pass_count

    def test_leading_at_end_of_half_uses_two_minute_not_clock_killing(self, game, cpu_ai):
        """
        At end of half while leading, should use two-minute drill, not clock killing.
        
        Even when leading, teams should try to score more points before halftime.
        """
        game.state.down = 2
        game.state.yards_to_go = 5
        game.state.ball_position = 60  # Enemy 40
        game.state.quarter = 2
        game.state.time_remaining = 1.0  # 1:00 left
        game.state.is_home_possession = True
        game.state.home_score = 17
        game.state.away_score = 10  # Leading by 7

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should be in two-minute drill, not clock killing
        assert cpu_ai.last_mode == "Two-Minute Drill"
        # Should use no-huddle to hurry up
        assert use_no_huddle is True

    def test_very_late_in_half_hail_mary_option(self, game, cpu_ai):
        """
        At very end of half with no timeouts, should consider Hail Mary.
        """
        game.state.down = 1
        game.state.yards_to_go = 10
        game.state.ball_position = 60  # Enemy 40
        game.state.quarter = 2
        game.state.time_remaining = 0.1  # 6 seconds left
        game.state.is_home_possession = True
        game.state.home_score = 17
        game.state.away_score = 20  # Trailing by 3

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should be in two-minute drill
        assert cpu_ai.last_mode == "Two-Minute Drill"
        assert use_no_huddle is True

    def test_goal_line_at_end_of_half_uses_two_minute_drill(self, game, cpu_ai):
        """
        At goal line at end of half with time running out, should use two-minute drill.
        
        Time management is more important than field position when time is running out.
        """
        game.state.down = 1
        game.state.yards_to_go = 3
        game.state.ball_position = 97  # Enemy 3 (goal line)
        game.state.quarter = 2
        game.state.time_remaining = 0.3  # 0:18 left
        game.state.is_home_possession = True
        game.state.home_score = 14
        game.state.away_score = 14  # Tied

        play, use_oob, use_no_huddle = cpu_ai.select_offense_with_clock_management(game)

        # Should be in two-minute drill mode, not goal line
        assert cpu_ai.last_mode == "Two-Minute Drill"
        assert use_no_huddle is True
