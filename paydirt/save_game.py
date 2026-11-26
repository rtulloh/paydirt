"""
Save and load game state for resuming games.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from .ai_save import save_ai_data
from .chart_loader import load_team_chart
from .game_engine import PaydirtGameEngine, ScoringPlay, TeamStats

DEFAULT_SAVE_FILE = "paydirt_save.json"


def save_game(engine: PaydirtGameEngine, filepath: str = DEFAULT_SAVE_FILE,
              human_is_away: bool = True, human_is_home: bool = False,
              cpu_ai = None) -> str:
    """
    Save the current game state to a JSON file.
    
    Args:
        engine: The game engine with current state
        filepath: Path to save file (default: paydirt_save.json)
        human_is_away: Whether human controls away team
        human_is_home: Whether human controls home team
        cpu_ai: The computer AI object (for saving opponent model data)
    
    Returns:
        The filepath where the game was saved
    """
    state = engine.state
    
    # Debug: Print the team paths being saved
    print(f"  [DEBUG] Saving game - away: {state.away_chart.team_dir}, home: {state.home_chart.team_dir}")
    
    # Build save data
    save_data = {
        "version": 1,
        "saved_at": datetime.now().isoformat(),
        # Team paths for reloading charts
        "away_team_path": state.away_chart.team_dir,
        "home_team_path": state.home_chart.team_dir,
        # Human control settings
        "human_is_away": human_is_away,
        "human_is_home": human_is_home,
        # Core game state
        "home_score": state.home_score,
        "away_score": state.away_score,
        "quarter": state.quarter,
        "time_remaining": state.time_remaining,
        "is_home_possession": state.is_home_possession,
        "opening_kicking_home": state.opening_kicking_home,
        "ball_position": state.ball_position,
        "down": state.down,
        "yards_to_go": state.yards_to_go,
        "game_over": state.game_over,
        # Timeouts
        "home_timeouts": state.home_timeouts,
        "away_timeouts": state.away_timeouts,
        # 2-minute warning
        "two_minute_warning_called": state.two_minute_warning_called,
        # Overtime
        "is_overtime": state.is_overtime,
        "ot_period": state.ot_period,
        "ot_first_possession_complete": state.ot_first_possession_complete,
        "ot_first_possession_scored": state.ot_first_possession_scored,
        "ot_first_possession_was_td": state.ot_first_possession_was_td,
        "ot_coin_toss_winner_is_home": state.ot_coin_toss_winner_is_home,
        "is_playoff": state.is_playoff,
        "untimed_down_pending": state.untimed_down_pending,
        # Team stats
        "home_stats": asdict(state.home_stats),
        "away_stats": asdict(state.away_stats),
        # Scoring plays
        "scoring_plays": [
            {
                "quarter": sp.quarter,
                "time": sp.time_remaining,
                "team": sp.team,
                "is_home_team": sp.is_home_team,
                "play_type": sp.play_type,
                "description": sp.description,
                "points": sp.points,
                "try_result": sp.try_result,
                "try_kind": sp.try_kind,
            }
            for sp in state.scoring_plays
        ],
        # Optional game-local coaching context; absent in legacy version-1 saves.
        "offensive_call_history": engine.offensive_call_history,
        # Engine-owned post-score procedure. Scores are already applied and
        # logged; this only records whether a try or free kick is still owed.
        "pending_post_score_action": engine.pending_post_score_action(),
        "last_play_start_quarter": engine._last_play_start_quarter,
        "home_end_zone_interception_return": engine.home_end_zone_interception_return,
        "away_end_zone_interception_return": engine.away_end_zone_interception_return,
        "home_end_zone_interception_policy": engine.home_end_zone_interception_policy,
        "away_end_zone_interception_policy": engine.away_end_zone_interception_policy,
    }

    pending_interception = engine._end_zone_interception_state_for_save()
    if pending_interception is not None:
        save_data["pending_end_zone_interception"] = pending_interception
        # Preserve the dice stream captured when the choice was deferred, so a
        # resumed game rolls the same return rather than replaying earlier dice.
        # Reset to the state captured when the choice was deferred, so reloading
        # cannot reroll the interception or earlier dice. A pending decision
        # restored from disk has no capture of its own; current state is then
        # the best available deterministic continuation.
        random_state = (
            engine._pending_end_zone_interception.get("random_state")
            or random.getstate()
        )
        whole, inner, gauss_next = random_state
        save_data["dice_random_state"] = {
            "version": whole,
            "internal": list(inner),
            "gauss_next": gauss_next,
        }

    # Version-1 readers ignore this optional metadata. Without it, a later load
    # would mistake defaulted component counters for a complete legacy history.
    from .team_stats import validate_team_stats_context
    save_data["team_stats_context"] = validate_team_stats_context(engine._team_stats_context)
    save_data["extended_team_stats"] = {
        name: getattr(getattr(state, name), "_extended_team_stats", None) for name in ("home_stats", "away_stats")
    }
    save_data["offensive_attempt_stats"] = {
        name: getattr(state, name)._offensive_attempt_stats for name in ("home_stats", "away_stats")
    }
    save_data["field_goal_stats"] = {
        name: getattr(state, name)._field_goal_stats for name in ("home_stats", "away_stats")
    }
    incomplete = [
        name for name in ("home_stats", "away_stats")
        if not getattr(state, name)._turnover_breakdown_complete
    ]
    if incomplete:
        save_data["incomplete_turnover_stats"] = incomplete
    try:
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
            f.flush()
    except Exception as e:
        print(f"  [ERROR] Failed to save game: {e}")
        raise
    
    # Verify file was actually written
    if os.path.exists(filepath):
        print(f"  [DEBUG] Save file verified - size: {os.path.getsize(filepath)} bytes")
    else:
        print("  [ERROR] Save file not found after write!")
    
    # Save AI opponent model data (if AI is enabled)
    if cpu_ai and cpu_ai.use_analysis and cpu_ai.opponent_model:
        save_dir = os.path.dirname(filepath) or "."
        ai_filepath = save_ai_data(cpu_ai, state.away_chart.team_dir, state.home_chart.team_dir, save_dir)
        if ai_filepath:
            print(f"  [DEBUG] AI data saved to {ai_filepath}")
    
    return filepath


def load_game(filepath: str = DEFAULT_SAVE_FILE) -> tuple | None:
    """
    Load a saved game state from a JSON file.
    
    Args:
        filepath: Path to save file
    
    Returns:
        Tuple of (engine, human_is_away, human_is_home) or None if file not found
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        save_data = json.load(f)
    
    # Check version
    version = save_data.get("version", 1)
    if version != 1:
        raise ValueError(f"Unsupported save file version: {version}")
    
    # Load team charts
    away_chart = load_team_chart(save_data["away_team_path"])
    home_chart = load_team_chart(save_data["home_team_path"])
    
    # Create engine with loaded charts (constructor takes home_chart, away_chart)
    engine = PaydirtGameEngine(home_chart, away_chart)
    state = engine.state
    engine.restore_offensive_call_history(save_data.get("offensive_call_history", []))
    engine.home_end_zone_interception_return = save_data.get("home_end_zone_interception_return", False)
    engine.away_end_zone_interception_return = save_data.get("away_end_zone_interception_return", False)
    for home, key in ((True, "home_end_zone_interception_policy"),
                      (False, "away_end_zone_interception_policy")):
        policy = save_data.get(key)
        if policy:
            engine.set_end_zone_interception_policy(home, policy)
    
    # Restore core game state
    state.home_score = save_data["home_score"]
    state.away_score = save_data["away_score"]
    state.quarter = save_data["quarter"]
    state.time_remaining = save_data["time_remaining"]
    state.is_home_possession = save_data["is_home_possession"]
    state.opening_kicking_home = save_data.get("opening_kicking_home")
    state.ball_position = save_data["ball_position"]
    state.down = save_data["down"]
    state.yards_to_go = save_data["yards_to_go"]
    state.game_over = save_data["game_over"]
    
    # Restore timeouts
    state.home_timeouts = save_data["home_timeouts"]
    state.away_timeouts = save_data["away_timeouts"]
    
    # Restore 2-minute warning
    state.two_minute_warning_called = save_data["two_minute_warning_called"]
    
    # Restore overtime state
    state.is_overtime = save_data.get("is_overtime", False)
    state.ot_period = save_data.get("ot_period", 0)
    state.ot_first_possession_complete = save_data.get("ot_first_possession_complete", False)
    state.ot_first_possession_scored = save_data.get("ot_first_possession_scored", False)
    state.ot_first_possession_was_td = save_data.get("ot_first_possession_was_td", False)
    state.ot_coin_toss_winner_is_home = save_data.get("ot_coin_toss_winner_is_home", False)
    state.is_playoff = save_data.get("is_playoff", False)
    state.untimed_down_pending = save_data.get("untimed_down_pending", False)
    engine._last_play_start_quarter = save_data.get(
        "last_play_start_quarter", state.quarter
    )
    
    # Repair stale aggregates only when the component history is complete.
    # Legacy totals without a full breakdown cannot safely be reconstructed.
    incomplete = save_data.get("incomplete_turnover_stats", [])
    for name in ("home_stats", "away_stats"):
        data = save_data.get(name, {})
        stats = TeamStats(**data)
        from .kicking_stats import validate_field_goal_stats
        from .offense_stats import validate_offensive_attempt_stats
        from .team_stats import validate_extended_team_stats
        stats._extended_team_stats = validate_extended_team_stats(
            save_data.get("extended_team_stats", {}).get(name))
        stats._offensive_attempt_stats = validate_offensive_attempt_stats(
            save_data.get("offensive_attempt_stats", {}).get(name))
        stats._field_goal_stats = validate_field_goal_stats(
            save_data.get("field_goal_stats", {}).get(name))
        stats._turnover_breakdown_complete = (
            name not in incomplete
            and "interceptions_thrown" in data and "fumbles_lost" in data
        )
        known_losses = stats.interceptions_thrown + stats.fumbles_lost
        stats.turnovers = (known_losses if stats._turnover_breakdown_complete
                           else max(stats.turnovers, known_losses))
        setattr(state, name, stats)
    
    # Restore scoring plays
    state.scoring_plays = [
        ScoringPlay(
            quarter=sp["quarter"],
            time_remaining=sp["time"],
            team=sp["team"],
            is_home_team=sp.get("is_home_team", True),
            play_type=sp["play_type"],
            description=sp["description"],
            points=sp["points"],
            try_result=sp.get("try_result", ""),
            try_kind=sp.get("try_kind", ""),
        )
        for sp in save_data.get("scoring_plays", [])
    ]

    pending_interception = save_data.get("pending_end_zone_interception")
    if pending_interception:
        engine.restore_pending_end_zone_interception(
            pending_interception,
            random_state=save_data.get("dice_random_state"),
        )

    # Scores are applied and logged by the engine at play time. A field
    # position at a goal line is not evidence that points are still owed.
    has_marker = "pending_post_score_action" in save_data
    pending_score = save_data.get("pending_post_score_action")
    if has_marker:
        engine._pending_post_score_action = pending_score
        pending_score = engine.resume_pending_post_score_action()

    # Legacy saves predate the explicit marker. Only those may infer a
    # follow-up from the scoring log, and never a score from field position.
    # A modern save recording no owed action means the score is complete.
    if not has_marker and state.ball_position >= 100:
        last_score = state.scoring_plays[-1] if state.scoring_plays else None
        if (
            last_score is not None
            and last_score.play_type == "TD"
            and engine.can_attempt_conversion_after_touchdown()
        ):
            pending_score = "try"
            engine.setup_for_pat()
        elif last_score is not None and last_score.play_type == "TD":
            pending_score = None
        else:
            raise ValueError(
                "Save has an end-zone field position without a pending score or "
                "touchdown record; it cannot be resumed safely"
            )
    elif not has_marker and state.ball_position <= 0:
        last_score = state.scoring_plays[-1] if state.scoring_plays else None
        if last_score is not None and last_score.play_type == "Safety":
            pending_score = "safety_free_kick"
            engine.setup_for_kickoff(from_safety=True)
        else:
            raise ValueError(
                "Save has an own-end-zone field position without a pending safety "
                "record; it cannot be resumed safely"
            )

    from .team_stats import validate_team_stats_context
    engine._team_stats_context = validate_team_stats_context(save_data.get("team_stats_context", {}))
    if engine._team_stats_context and not engine.has_pending_end_zone_interception:
        raise ValueError("Team-stat capture has no resumable pending engine choice")
    engine._pending_post_score_action = pending_score

    # Return engine and human control settings
    human_is_away = save_data.get("human_is_away", True)
    human_is_home = save_data.get("human_is_home", False)
    
    return engine, human_is_away, human_is_home, pending_score


def get_save_info(filepath: str = DEFAULT_SAVE_FILE) -> dict | None:
    """
    Get summary info about a save file without fully loading it.
    
    Returns:
        Dict with save info or None if file not found
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        save_data = json.load(f)
    
    return {
        "saved_at": save_data.get("saved_at", "Unknown"),
        "away_team": os.path.basename(save_data.get("away_team_path", "Unknown")),
        "home_team": os.path.basename(save_data.get("home_team_path", "Unknown")),
        "quarter": save_data.get("quarter", 0),
        "time_remaining": save_data.get("time_remaining", 0),
        "away_score": save_data.get("away_score", 0),
        "home_score": save_data.get("home_score", 0),
    }
