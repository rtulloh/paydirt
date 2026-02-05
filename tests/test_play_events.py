"""
Tests for the transaction-based play event model.
"""
import pytest

from paydirt.play_events import (
    EventType,
    PlayEvent,
    PlayTransaction,
    PendingDecision,
    DecisionOption,
    create_chart_lookup_event,
    create_fumble_event,
    create_recovery_event,
    create_interception_event,
    create_return_event,
    create_penalty_event,
    create_touchdown_event,
)


class TestPlayEvent:
    """Tests for PlayEvent dataclass."""
    
    def test_basic_event_creation(self):
        """Can create a basic play event."""
        event = PlayEvent(
            event_type=EventType.CHART_LOOKUP,
            description="Test play",
            dice_roll=24,
            dice_desc="B2+W2+W2=24",
            chart_result="6"
        )
        assert event.event_type == EventType.CHART_LOOKUP
        assert event.dice_roll == 24
        assert event.description == "Test play"
    
    def test_format_action_line(self):
        """Action line returns description."""
        event = PlayEvent(
            event_type=EventType.FUMBLE,
            description="FUMBLE at +8 yards!"
        )
        assert event.format_action_line() == "FUMBLE at +8 yards!"
    
    def test_format_dice_line_with_roll(self):
        """Dice line formats roll and result."""
        event = PlayEvent(
            event_type=EventType.FUMBLE_RECOVERY,
            description="Recovery roll",
            dice_roll=24,
            dice_desc="B2+W2+W2=24",
            chart_result="Recovered"
        )
        dice_line = event.format_dice_line()
        assert "B2+W2+W2=24" in dice_line
        assert "Recovered" in dice_line
    
    def test_format_dice_line_no_roll(self):
        """Dice line is empty when no roll."""
        event = PlayEvent(
            event_type=EventType.TOUCHDOWN,
            description="TOUCHDOWN!"
        )
        assert event.format_dice_line() == ""


class TestPlayTransaction:
    """Tests for PlayTransaction dataclass."""
    
    def test_add_event(self):
        """Can add events to transaction."""
        txn = PlayTransaction()
        event = PlayEvent(event_type=EventType.CHART_LOOKUP, description="Test")
        txn.add_event(event)
        assert len(txn.events) == 1
        assert txn.events[0] == event
    
    def test_get_events_by_type(self):
        """Can filter events by type."""
        txn = PlayTransaction()
        txn.add_event(PlayEvent(event_type=EventType.CHART_LOOKUP, description="Chart"))
        txn.add_event(PlayEvent(event_type=EventType.FUMBLE, description="Fumble"))
        txn.add_event(PlayEvent(event_type=EventType.FUMBLE_RECOVERY, description="Recovery"))
        
        fumble_events = txn.get_events_by_type(EventType.FUMBLE)
        assert len(fumble_events) == 1
        assert fumble_events[0].description == "Fumble"
    
    def test_has_event_type(self):
        """Can check if event type occurred."""
        txn = PlayTransaction()
        txn.add_event(PlayEvent(event_type=EventType.INTERCEPTION, description="INT"))
        
        assert txn.has_event_type(EventType.INTERCEPTION) is True
        assert txn.has_event_type(EventType.FUMBLE) is False
    
    def test_format_display(self):
        """Can format all events for display."""
        txn = PlayTransaction()
        txn.add_event(PlayEvent(
            event_type=EventType.CHART_LOOKUP,
            description="Off Tackle run",
            dice_roll=24,
            dice_desc="B2+W2+W2=24"
        ))
        txn.add_event(PlayEvent(
            event_type=EventType.FUMBLE,
            description="FUMBLE!"
        ))
        
        display = txn.format_display()
        assert len(display) == 2
        assert display[0][0] == "Off Tackle run"  # Action line
        assert "B2+W2+W2=24" in display[0][1]  # Dice line
        assert display[1][0] == "FUMBLE!"


class TestEventFactoryFunctions:
    """Tests for event factory functions."""
    
    def test_create_chart_lookup_event(self):
        """Creates chart lookup event with all details."""
        event = create_chart_lookup_event(
            offense_roll=24,
            offense_desc="B2+W2+W2=24",
            offense_result="6",
            defense_row="3",
            defense_result="(3)",
            priority="(#)",
            acting_team="DEN"
        )
        assert event.event_type == EventType.CHART_LOOKUP
        assert event.dice_roll == 24
        assert "O:24" in event.description
        assert "D:3" in event.description
    
    def test_create_fumble_event_positive_yards(self):
        """Creates fumble event with positive yards."""
        event = create_fumble_event(
            yards_before_fumble=8,
            fumble_spot=48,
            acting_team="TB"
        )
        assert event.event_type == EventType.FUMBLE
        assert "+8" in event.description
        assert event.yards == 8
        assert event.spot == 48
    
    def test_create_fumble_event_negative_yards(self):
        """Creates fumble event with negative yards."""
        event = create_fumble_event(
            yards_before_fumble=-3,
            fumble_spot=37,
            acting_team="TB"
        )
        assert "-3" in event.description
        assert event.yards == -3
    
    def test_create_recovery_event_offense_recovers(self):
        """Creates recovery event when offense recovers."""
        event = create_recovery_event(
            recovery_roll=24,
            recovery_desc="B2+W2+W2=24",
            offense_recovers=True,
            recovery_range=(11, 29),
            acting_team="TB"
        )
        assert event.event_type == EventType.FUMBLE_RECOVERY
        assert "RECOVERED" in event.description
        assert event.possession_change is False
    
    def test_create_recovery_event_defense_recovers(self):
        """Creates recovery event when defense recovers."""
        event = create_recovery_event(
            recovery_roll=37,
            recovery_desc="B3+W3+W4=37",
            offense_recovers=False,
            recovery_range=(11, 29),
            acting_team="TB"
        )
        assert "LOST" in event.description
        assert event.possession_change is True
    
    def test_create_interception_event(self):
        """Creates interception event."""
        event = create_interception_event(
            int_spot=47,
            int_yards_downfield=13,
            acting_team="DEN"
        )
        assert event.event_type == EventType.INTERCEPTION
        assert "INTERCEPTED" in event.description
        assert "13" in event.description
        assert event.possession_change is True
    
    def test_create_return_event_with_yards(self):
        """Creates return event with positive yards."""
        event = create_return_event(
            event_type=EventType.INT_RETURN,
            return_roll=34,
            return_desc="B3+W2+W2=34",
            return_yards=25,
            chart_result="25",
            acting_team="PIT"
        )
        assert event.event_type == EventType.INT_RETURN
        assert "25 yards" in event.description
        assert event.yards == 25
    
    def test_create_return_event_touchdown(self):
        """Creates return event for touchdown."""
        event = create_return_event(
            event_type=EventType.INT_RETURN,
            return_roll=39,
            return_desc="B3+W4+W5=39",
            return_yards=60,
            chart_result="TD",
            is_touchdown=True,
            acting_team="PIT"
        )
        assert "TOUCHDOWN" in event.description
    
    def test_create_penalty_event(self):
        """Creates penalty event."""
        event = create_penalty_event(
            penalty_type="DEF",
            yards=15,
            description="Defensive holding",
            offended_team="offense"
        )
        assert event.event_type == EventType.PENALTY_DETECTED
        assert "FLAG" in event.description
        assert event.yards == 15


class TestPendingDecision:
    """Tests for PendingDecision handling."""
    
    def test_create_penalty_decision(self):
        """Can create a pending penalty decision."""
        decision = PendingDecision(
            decision_type="penalty_choice",
            deciding_team="offense",
            options=[
                DecisionOption(
                    option_id="accept_play",
                    description="Accept play result: 8 yard gain",
                    yards=8,
                    replays_down=False
                ),
                DecisionOption(
                    option_id="accept_penalty",
                    description="Accept penalty: DEF 15, automatic first down",
                    yards=15,
                    replays_down=True
                )
            ],
            prompt="Penalty on defense. Accept play or penalty?"
        )
        assert decision.decision_type == "penalty_choice"
        assert len(decision.options) == 2
        assert decision.options[0].option_id == "accept_play"
        assert decision.options[1].replays_down is True


class TestTransactionWithDecision:
    """Tests for transactions with pending decisions."""
    
    def test_transaction_with_pending_decision(self):
        """Transaction can have pending decision."""
        txn = PlayTransaction()
        txn.add_event(PlayEvent(event_type=EventType.CHART_LOOKUP, description="Play"))
        txn.add_event(PlayEvent(event_type=EventType.PENALTY_DETECTED, description="FLAG"))
        
        txn.pending_decision = PendingDecision(
            decision_type="penalty_choice",
            deciding_team="offense",
            options=[
                DecisionOption(option_id="accept_play", description="Accept play"),
                DecisionOption(option_id="accept_penalty", description="Accept penalty")
            ]
        )
        
        assert txn.pending_decision is not None
        assert txn.is_complete is False
    
    def test_transaction_complete_after_decision(self):
        """Transaction marked complete after decision resolved."""
        txn = PlayTransaction()
        txn.add_event(PlayEvent(event_type=EventType.CHART_LOOKUP, description="Play"))
        
        # Simulate resolving decision
        txn.is_complete = True
        txn.final_ball_position = 58
        txn.yards_gained = 8
        
        assert txn.is_complete is True
        assert txn.yards_gained == 8


class TestComplexPlayScenarios:
    """Tests for complex multi-event plays."""
    
    def test_fumble_recovered_by_offense(self):
        """Simulate fumble recovered by offense."""
        txn = PlayTransaction()
        
        # Chart lookup
        txn.add_event(create_chart_lookup_event(
            offense_roll=15,
            offense_desc="B1+W2+W3=15",
            offense_result="F+8",
            defense_row="3",
            defense_result="(3)",
            priority="F-#",
            acting_team="TB"
        ))
        
        # Fumble
        txn.add_event(create_fumble_event(
            yards_before_fumble=8,
            fumble_spot=48,
            acting_team="TB"
        ))
        
        # Recovery - offense recovers
        txn.add_event(create_recovery_event(
            recovery_roll=24,
            recovery_desc="B2+W2+W2=24",
            offense_recovers=True,
            recovery_range=(11, 29),
            acting_team="TB"
        ))
        
        # Verify chain
        assert len(txn.events) == 3
        assert txn.has_event_type(EventType.FUMBLE)
        assert txn.has_event_type(EventType.FUMBLE_RECOVERY)
        
        # No possession change
        recovery = txn.get_events_by_type(EventType.FUMBLE_RECOVERY)[0]
        assert recovery.possession_change is False
    
    def test_interception_with_return(self):
        """Simulate interception with return."""
        txn = PlayTransaction()
        
        # Chart lookup
        txn.add_event(create_chart_lookup_event(
            offense_roll=38,
            offense_desc="B3+W4+W4=38",
            offense_result="INT 13",
            defense_row="2",
            defense_result="",
            priority="INT",
            acting_team="DEN"
        ))
        
        # Interception
        txn.add_event(create_interception_event(
            int_spot=47,
            int_yards_downfield=13,
            acting_team="DEN"
        ))
        
        # Return
        txn.add_event(create_return_event(
            event_type=EventType.INT_RETURN,
            return_roll=34,
            return_desc="B3+W2+W2=34",
            return_yards=25,
            chart_result="25",
            acting_team="PIT"
        ))
        
        # Set final state
        txn.turnover = True
        txn.final_ball_position = 72  # 47 + 25
        txn.is_complete = True
        
        # Verify
        assert txn.turnover is True
        assert len(txn.events) == 3
        
        # Display should show all events
        display = txn.format_display()
        assert len(display) == 3
    
    def test_play_with_penalty_decision(self):
        """Simulate play with penalty requiring decision."""
        txn = PlayTransaction()
        
        # Initial play - penalty detected
        txn.add_event(create_chart_lookup_event(
            offense_roll=24,
            offense_desc="B2+W2+W2=24",
            offense_result="DEF 15",
            defense_row="3",
            defense_result="4",
            priority="DEF",
            acting_team="TB"
        ))
        
        # Penalty event
        txn.add_event(create_penalty_event(
            penalty_type="DEF",
            yards=15,
            description="Defensive holding",
            offended_team="offense"
        ))
        
        # Pending decision
        txn.pending_decision = PendingDecision(
            decision_type="penalty_choice",
            deciding_team="offense",
            options=[
                DecisionOption(
                    option_id="accept_play",
                    description="Accept play: 4 yard gain, down counts",
                    yards=4
                ),
                DecisionOption(
                    option_id="accept_penalty",
                    description="Accept penalty: 15 yards, replay down",
                    yards=15,
                    replays_down=True
                )
            ]
        )
        
        # Transaction not complete until decision made
        assert txn.is_complete is False
        assert txn.pending_decision is not None
        assert len(txn.pending_decision.options) == 2
