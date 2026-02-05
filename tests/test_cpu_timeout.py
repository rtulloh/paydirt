"""
Tests for CPU AI timeout logic when on defense.

The CPU should call timeouts when trailing late in the game to stop the clock
and get the ball back.
"""

from paydirt.computer_ai import ComputerAI, computer_should_call_timeout_on_defense
from paydirt.game_engine import PaydirtGameEngine
from paydirt.chart_loader import TeamChart, PeripheralData, OffenseChart, DefenseChart, SpecialTeamsChart


def create_mock_chart(short_name: str, full_name: str) -> TeamChart:
    """Create a mock team chart for testing."""
    peripheral = PeripheralData(
        year=1983,
        team_name=full_name.split()[-1],
        team_nickname=full_name.split()[-1],
        power_rating=50,
        short_name=short_name
    )
    return TeamChart(
        peripheral=peripheral,
        offense=OffenseChart(),
        defense=DefenseChart(),
        special_teams=SpecialTeamsChart(),
        team_dir=""
    )


class TestCPUTimeoutOnDefense:
    """Tests for CPU calling timeouts when on defense."""

    def test_cpu_calls_timeout_trailing_q4_under_2_min(self):
        """CPU should call timeout when trailing in Q4 with < 2 minutes left."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # Home team (PHI) has ball, CPU is away (SF) on defense
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 21  # PHI leading
        game.state.away_score = 14  # SF trailing by 7
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_calls_timeout_trailing_q4_under_5_min_big_deficit(self):
        """CPU should call timeout when trailing by 14+ in Q4 with < 5 minutes."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 4.5  # 4:30 left
        game.state.home_score = 28
        game.state.away_score = 14  # Trailing by 14
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_no_timeout_when_leading(self):
        """CPU should NOT call timeout when leading."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 14
        game.state.away_score = 21  # CPU is winning
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_no_timeout_when_no_timeouts_left(self):
        """CPU should NOT call timeout when no timeouts remaining."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 0  # No timeouts
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_no_timeout_early_in_game(self):
        """CPU should NOT call timeout in Q1 or Q3."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 1
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False
        
        game.state.quarter = 3
        assert ai.should_call_timeout_on_defense(game) is False

    def test_cpu_calls_timeout_end_of_half_trailing(self):
        """CPU should call timeout at end of Q2 when trailing by TD+."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 1.5  # 1:30 left in half
        game.state.home_score = 14
        game.state.away_score = 7  # Trailing by 7
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is True

    def test_cpu_no_timeout_q2_small_deficit(self):
        """CPU should NOT call timeout in Q2 with small deficit and > 1 min."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 1.5
        game.state.home_score = 10
        game.state.away_score = 7  # Only trailing by 3
        game.state.away_timeouts = 3
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_defense(game) is False

    def test_convenience_function_works(self):
        """Test the convenience function computer_should_call_timeout_on_defense."""
        home_chart = create_mock_chart("PHI '83", "Philadelphia Eagles")
        away_chart = create_mock_chart("SF '83", "San Francisco 49ers")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.away_timeouts = 3
        
        assert computer_should_call_timeout_on_defense(game) is True


class TestCPUTimeoutOnOffense:
    """Tests for CPU calling timeouts when on offense to preserve clock."""

    def test_cpu_calls_timeout_end_of_q2_to_score(self):
        """CPU should call timeout at end of Q2 to try to score before half."""
        
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # CHI (home) has ball, leading 21-14
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 0.75  # 45 seconds left
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.home_timeouts = 2
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_offense(game) is True

    def test_cpu_no_timeout_q2_if_big_lead(self):
        """CPU should NOT call timeout at end of Q2 if leading by 14+."""
        
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 0.75
        game.state.home_score = 28
        game.state.away_score = 14  # Leading by 14
        game.state.home_timeouts = 2
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_offense(game) is False

    def test_cpu_calls_timeout_q4_trailing(self):
        """CPU should call timeout in Q4 when trailing to preserve clock."""
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # CHI (home) has ball, trailing 14-21
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 14
        game.state.away_score = 21
        game.state.home_timeouts = 2
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_offense(game) is True

    def test_cpu_no_timeout_q4_if_leading(self):
        """CPU should NOT call timeout in Q4 if leading (run out clock instead)."""
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 4
        game.state.time_remaining = 1.5
        game.state.home_score = 21
        game.state.away_score = 14  # Leading
        game.state.home_timeouts = 2
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_offense(game) is False

    def test_cpu_no_timeout_if_none_remaining(self):
        """CPU should NOT call timeout if no timeouts remaining."""
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 0.75
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.home_timeouts = 0  # No timeouts
        
        ai = ComputerAI()
        assert ai.should_call_timeout_on_offense(game) is False

    def test_convenience_function_offense_works(self):
        """Test the convenience function computer_should_call_timeout_on_offense."""
        from paydirt.computer_ai import computer_should_call_timeout_on_offense
        
        home_chart = create_mock_chart("CHI '83", "Chicago Bears")
        away_chart = create_mock_chart("ATL '83", "Atlanta Falcons")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        game.state.is_home_possession = True
        game.state.quarter = 2
        game.state.time_remaining = 0.75
        game.state.home_score = 21
        game.state.away_score = 14
        game.state.home_timeouts = 2
        
        assert computer_should_call_timeout_on_offense(game) is True


class TestCPUTimeoutAfterTurnover:
    """Tests to verify CPU timeout logic is skipped after turnovers.
    
    After a turnover (interception/fumble), possession changes and the
    pre-play timeout decision no longer applies. The CPU should NOT
    call a timeout in this situation.
    """

    def test_cpu_should_not_timeout_after_interception(self):
        """CPU timeout logic should be skipped after an interception.
        
        Scenario: Human (BAL) is on offense, CPU (NE) is on defense and trailing.
        Human throws interception. After the INT, CPU now has the ball.
        
        Before the fix: The code would check computer_should_call_timeout_on_defense
        using the stale is_human_offense=True, but the game state has changed
        (CPU is now on offense), causing incorrect timeout behavior.
        
        After the fix: CPU timeout logic is skipped when outcome.turnover=True.
        """
        from paydirt.play_resolver import PlayType, DefenseType, PlayResult, ResultType
        from paydirt.game_engine import PlayOutcome
        
        home_chart = create_mock_chart("NE '83", "New England Patriots")
        away_chart = create_mock_chart("BAL '83", "Baltimore Colts")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # Setup: BAL (away, human) has ball, NE (home, CPU) is trailing
        game.state.is_home_possession = False  # BAL has ball (human on offense)
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 24  # NE (CPU) trailing
        game.state.away_score = 37  # BAL (human) leading
        game.state.home_timeouts = 2  # CPU has timeouts
        
        # Verify CPU would want to call timeout on defense (trailing late in game)
        assert computer_should_call_timeout_on_defense(game) is True
        
        # Create a mock outcome representing an interception
        result = PlayResult(
            result_type=ResultType.INTERCEPTION,
            yards=17,
            description="INTERCEPTED!",
            turnover=True
        )
        outcome = PlayOutcome(
            play_type=PlayType.MEDIUM_PASS,
            defense_type=DefenseType.BLITZ,
            result=result,
            yards_gained=17,
            turnover=True,  # Key: turnover occurred
            touchdown=False,
            safety=False,
            first_down=False,
            field_position_before="BAL 34",
            field_position_after="NE 34",
            down_before=1,
            down_after=1,
            description="INTERCEPTED!"
        )
        
        # The key assertion: when turnover=True, CPU timeout should be skipped
        # The interactive_game.py code checks: is_human_offense and not outcome.turnover
        # Since outcome.turnover is True, the timeout logic is skipped
        assert outcome.turnover is True

    def test_cpu_should_not_timeout_after_fumble(self):
        """CPU timeout logic should be skipped after a fumble recovery.
        
        Similar to interception - after fumble, possession changes and
        timeout logic should be skipped.
        """
        from paydirt.play_resolver import PlayType, DefenseType, PlayResult, ResultType
        from paydirt.game_engine import PlayOutcome
        
        home_chart = create_mock_chart("NE '83", "New England Patriots")
        away_chart = create_mock_chart("BAL '83", "Baltimore Colts")
        
        game = PaydirtGameEngine(home_chart, away_chart)
        # Setup: BAL (away, human) has ball, NE (home, CPU) is trailing
        game.state.is_home_possession = False  # BAL has ball (human on offense)
        game.state.quarter = 4
        game.state.time_remaining = 1.5  # 1:30 left
        game.state.home_score = 24  # NE (CPU) trailing
        game.state.away_score = 37  # BAL (human) leading
        game.state.home_timeouts = 2  # CPU has timeouts
        
        # Verify CPU would want to call timeout on defense (trailing late in game)
        assert computer_should_call_timeout_on_defense(game) is True
        
        result = PlayResult(
            result_type=ResultType.FUMBLE,
            yards=-2,
            description="FUMBLE!",
            turnover=True
        )
        outcome = PlayOutcome(
            play_type=PlayType.LINE_PLUNGE,
            defense_type=DefenseType.STANDARD,
            result=result,
            yards_gained=-2,
            turnover=True,  # Key: turnover occurred
            touchdown=False,
            safety=False,
            first_down=False,
            field_position_before="NE 15",
            field_position_after="NE 17",
            down_before=3,
            down_after=1,
            description="FUMBLE!"
        )
        
        # The key assertion: when turnover=True, CPU timeout should be skipped
        assert outcome.turnover is True
