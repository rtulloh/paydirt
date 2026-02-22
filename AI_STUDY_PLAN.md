# AI Study Plan - Smart Play Calling

## Overview

This plan outlines improvements to the AI to make it "study" the game and opponent, enabling smarter play calling in both hard and easy modes.

**Core Principle**: Ignore penalties and turnovers. Focus only on actual play outcomes.

---

## Phase 1: Chart Analysis

### Goal
Build a statistical model of the team's strengths/weaknesses by analyzing their offense and defense charts.

### 1.1 Offense Chart Analysis

Parse the offense CSV and calculate for each die roll (2-12):

```
For each die roll:
  - Count plays by type (run vs pass)
  - Calculate % runs vs % passes
  - Calculate average yards per play type
  - Identify "signature plays" (highest yards, most consistent)
```

**Data Structure**:
```python
class OffenseAnalysis:
    die_roll_stats: dict[int, RollStats]  # 2-12
    
    # Aggregated by down/distance
    downs_and_distances: dict[tuple[int, int], DownDistanceStats]
    
    # Best plays for situation
    best_run_plays: list[tuple[PlayType, float]]  # (play_type, avg_yards)
    best_pass_plays: list[tuple[PlayType, float]]
```

### 1.2 Defense Chart Analysis

Parse the defense CSV and understand:

```
For each formation (A-F) and sub-row (1-5):
  - What dice rolls favor defense vs offense?
  - Identify "soft spots" (where opponent scores well)
  - Identify "tough spots" (where opponent struggles)
```

### 1.3 Success Metrics (Non-Penalty, Non-Turnover Only)

Filter out penalties and turnovers when calculating success:

```python
def calculate_success_rate(play_type, down, distance, chart_data):
    outcomes = get_outcomes(play_type, down, distance, chart_data)
    
    # Filter: exclude BLACK (incomplete), F (fumble), INT (interception)
    valid_outcomes = [o for o in outcomes if o not in ['BLACK', 'F', 'INT']]
    
    # Success = positive yardage or first down
    success_count = sum(1 for o in valid_outcomes if yards(o) > 0 or is_first_down(o))
    
    return success_count / len(valid_outcomes) if valid_outcomes else 0
```

---

## Phase 2: Opponent Modeling

### Goal
Track and predict what the opponent will do based on historical play choices.

### 2.1 Tendency Tracking

```python
class OpponentTendencies:
    # Track by down/distance situation
    situation_history: dict[tuple[int, int], list[PlayType]]
    
    # Rolling percentages
    run_vs_pass_bySituation: dict[tuple[int, int], float]  # % passes
    
    # Pattern detection
    play_streak: list[PlayType]  # Last N plays
    comeback_mode: bool  # Trailing in 4th quarter
    protect_lead: bool  # Leading, running out clock
```

### 2.2 Prediction Model

```python
def predict_opponent_play(tendencies: OpponentTendencies, situation: tuple[int, int]) -> PlayType:
    # Base prediction from historical data
    base_prediction = predict_from_history(tendencies.situation_history[situation])
    
    # Adjust for game state
    if game_state.is_protect_lead:
        # Likely to run more
        base_prediction.weight_toward_run()
    elif game_state.is_comeback:
        # Likely to pass more
        base_prediction.weight_toward_pass()
    
    # Consider recent streaks
    if len(tendencies.play_streak) >= 3:
        if all(p == PlayType.PASS for p in tendencies.play_streak[-3:]):
            # Opponent on pass streak, expect continued pass
            pass
    
    return base_prediction
```

---

## Phase 3: Hard Mode AI (CPU vs CPU / Competitive)

### Decision Engine

The hard AI considers **4 factors** in priority order:

1. **Opponent Prediction** (Highest Priority)
   - What will the opponent do on defense?
   - Match our play to their weakness

2. **Game State**
   - Score differential
   - Time remaining
   - Quarter
   - Field position

3. **Our Team Strengths**
   - What plays work best for our team
   - Down and distance analysis

4. **Risk/Reward**
   - 4th down decisions
   - Two-point conversion decisions

### 3.1 Hard Mode Selection Logic

```python
def hard_mode_decision(ai: ComputerAI, game: PaydirtGameEngine, my_team: TeamChart):
    down = game.state.down
    distance = game.state.yards_to_go
    field_pos = game.state.ball_position
    score_diff = game.state.home_score - game.state.away_score
    time_left = game.state.time_remaining
    quarter = game.state.quarter
    
    # 1. Predict opponent defense
    opponent_tendency = ai.get_opponent_tendency()
    predicted_defense = predict_defense_formation(opponent_tendency)
    
    # 2. Get our best play against that defense
    best_play = my_team.offense_analysis.get_best_play(
        down=down,
        distance=distance,
        vs_formation=predicted_defense
    )
    
    # 3. Adjust for game state
    if quarter >= 4 and score_diff > 0 and time_left < 5.0:
        # Protect lead - prefer runs
        best_play = adjust_for_clock(best_play)
    
    if is_fourth_down_situation(down, distance, field_pos):
        # Fourth down decision
        best_play = fourth_down_strategy(distance, field_pos, score_diff)
    
    return best_play
```

### 3.2 Key Hard Mode Behaviors

| Situation | Hard AI Behavior |
|-----------|------------------|
| 3rd & long | Pass, study if opponent passes a lot on defense |
| 4th & short | Go for it if ahead, punt if behind |
| Late lead | Run, run, run |
| Trailing late | Pass, no-huddle |
| Red zone | Study team's best red zone plays |

---

## Phase 4: Easy Mode AI (Helper for Human)

### Goal
Help the human player by suggesting plays and providing information.

### 4.1 Helper Features

```python
class EasyModeHelper:
    def suggest_play(self, game: PaydirtGameEngine, player_team: TeamChart):
        """Suggest best play for current situation"""
        down = game.state.down
        distance = game.state.yards_to_go
        
        # Get success rates for all plays
        suggestions = player_team.offense_analysis.get_all_success_rates(down, distance)
        
        # Rank by success rate
        suggestions.sort(key=lambda x: x.success_rate, reverse=True)
        
        return suggestions[:3]  # Top 3 suggestions
    
    def explain_why(self, play: PlayType, game: PaydirtGameEngine):
        """Explain why a play is recommended"""
        stats = self.get_play_stats(play, game.state.down, game.state.yards_to_go)
        return f"{play} has {stats.success_rate}% success rate, avg {stats.avg_yards} yards"
    
    def warn_danger(self, game: PaydirtGameEngine):
        """Warn about dangerous opponent tendencies"""
        # "They've blitzed on 3 of last 4 third downs"
        # "Watch out - opponent has intercepted 3 passes this quarter"
        pass
```

### 4.2 Easy Mode Display

```
=== YOUR AI HELPER ===
Suggested plays for 3rd & 7:
  1. MED PASS - 68% success, avg 8.2 yards
  2. SHORT PASS - 72% success, avg 5.1 yards  
  3. DRAW - 45% success, avg 3.2 yards

Tip: Opponent passes on defense 70% of time on 3rd & long.
```

### 4.3 "Opposite" Suggestions

Easy mode can also suggest "tricky" plays that might work because opponent doesn't expect them:

```python
def suggest_tricky_play(self, game: PaydirtGameEngine, player_team: TeamChart):
    """Suggest unexpected plays that might work"""
    
    # If opponent expects pass, suggest run
    if opponent_expects_pass:
        # Draw or play action might work
        return suggest_run_play()
    
    # If opponent expects run, suggest pass
    if opponent_expects_run:
        # Screen or quick pass might work
        return suggest_pass_play()
```

---

## Implementation Priority

### Step 1: Chart Analysis Utilities (Priority: High)
- `OffenseAnalyzer` class
- `DefenseAnalyzer` class  
- Success rate calculations (excluding penalties/turnovers)
- Best play identification per situation

### Step 2: Tendency Tracking (Priority: High)
- `OpponentTendencyTracker` class
- Track play choices by situation
- Rolling statistics calculation

### Step 3: Hard Mode Integration (Priority: High)
- Update `ComputerAI.select_offense()` to use analysis
- Update `ComputerAI.select_defense()` to use analysis

### Step 4: Easy Mode Helper (Priority: Medium)
- `EasyModeHelper` class
- Display suggestions in interactive game
- Help text and explanations

---

## Key Files to Modify

1. **`paydirt/computer_ai.py`** - Main AI logic
2. **`paydirt/chart_loader.py`** - Add analysis methods
3. **`paydirt/interactive_game.py`** - Add easy mode helper display
4. **`paydirt/game_state.py`** - Add tendency tracking state

---

## Success Metrics

- Hard AI win rate improves vs current AI
- Easy mode provides helpful, accurate suggestions
- AI makes statistically sound decisions
- No penalties or turnovers considered in analysis
