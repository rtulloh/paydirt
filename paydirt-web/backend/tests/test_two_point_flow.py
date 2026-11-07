"""Actual chart conversions, season eligibility and the following kickoff."""

import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from routes import games


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("cell", ["3", "BLACK", "INT 0"])
@pytest.mark.parametrize("expired", [False, True])
def test_actual_try_scores_untimed_and_leaves_correct_kickoff_or_final(home: bool, cell: str, expired: bool) -> None:
    with TestClient(app) as client:
        created = client.post("/api/game/new", json={
            "player_team": "Ironclads", "season": "2026", "play_as_home": home,
        }).json()
        game_id = created["game_id"]
        game = games[game_id]
        engine, state = game["engine"], game["engine"].state
        try:
            game["is_kickoff"] = False
            state.is_home_possession = home
            state.quarter, state.time_remaining = (4, 1 / 60) if expired else (1, 10)
            state.ball_position, state.down, state.yards_to_go = 98, 1, 2
            state.defense_team.defense.modifiers = {}
            state.possession_team.offense.line_plunge = {26: "2"}
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "TD26")),
                  patch("paydirt.game_engine.random.uniform", return_value=30)):
                touchdown = client.post("/api/game/execute", json={
                    "game_id": game_id, "player_play": "1", "cpu_play": "A",
                })
            assert touchdown.status_code == 200
            assert touchdown.json()["game_state"]["pending_pat"]
            assert touchdown.json()["game_state"]["can_go_for_two"]
            before = (state.quarter, state.time_remaining, deepcopy(state.home_stats), deepcopy(state.away_stats),
                      len(engine.play_log), deepcopy(engine.offensive_call_history))
            state.possession_team.offense.short_pass = {26: cell}
            state.defense_team.special_teams.interception_return = {26: "0"}
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
                  patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Return26"))):
                response = client.post("/api/game/two-point", json={
                    "game_id": game_id, "offense_play": "6", "defense_play": "A",
                })
            assert response.status_code == 200
            result = response.json()
            assert result["result"]["conversion_success"] is (cell == "3")
            assert result["result"]["defense_points"] == 0
            assert (state.home_score, state.away_score) == ((8 if cell == "3" else 6, 0) if home else (0, 8 if cell == "3" else 6))
            assert (state.quarter, state.time_remaining, state.home_stats, state.away_stats,
                    len(engine.play_log), engine.offensive_call_history) == before
            assert state.is_home_possession is home
            assert result["game_state"]["pending_pat"] is False
            assert result["game_state"]["can_go_for_two"] is False
            assert result["game_state"]["game_over"] is expired
            assert result["game_state"]["is_kickoff"] is not expired
            if not expired:
                state.possession_team.special_teams.kickoff = {26: "60"}
                state.defense_team.special_teams.kickoff_return = {26: "20"}
                with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Kick26")):
                    kicked = client.post("/api/game/kickoff", json={"game_id": game_id})
                assert kicked.status_code == 200
                assert state.is_home_possession is not home
        finally:
            client.delete(f"/api/game/{game_id}")


def test_disallowed_season_hides_and_rejects_two_point_try() -> None:
    with TestClient(app) as client:
        game_id = client.post("/api/game/new", json={"player_team": "Ironclads", "season": "2026"}).json()["game_id"]
        try:
            game = games[game_id]
            game["pending_pat"] = True
            game["engine"].season_rules.two_point_conversion = False
            state = deepcopy(game["engine"].state)
            assert not client.get(f"/api/game/state/{game_id}").json()["can_go_for_two"]
            response = client.post("/api/game/two-point", json={"game_id": game_id, "offense_play": "1", "defense_play": "A"})
            assert response.status_code == 400
            assert game["engine"].state == state
        finally:
            client.delete(f"/api/game/{game_id}")


def _touchdown_before_try(client: TestClient, home: bool, quarter: int, seconds: int) -> tuple[str, dict]:
    game_id = client.post("/api/game/new", json={
        "player_team": "Ironclads", "season": "2026", "play_as_home": home,
    }).json()["game_id"]
    game = games[game_id]
    state = game["engine"].state
    game["is_kickoff"] = False
    state.opening_kicking_home = home
    state.is_home_possession = home
    state.quarter, state.time_remaining = quarter, seconds / 60
    state.ball_position, state.down, state.yards_to_go = 98, 1, 2
    state.defense_team.defense.modifiers = {}
    state.possession_team.offense.line_plunge = {26: "2"}
    with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "TD26")),
          patch("paydirt.game_engine.random.uniform", return_value=30)):
        response = client.post("/api/game/execute", json={
            "game_id": game_id, "player_play": "1", "cpu_play": "A",
        })
    assert response.status_code == 200 and response.json()["game_state"]["pending_pat"]
    return game_id, game


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("cell", ["3", "BLACK", "INT 0"])
def test_actual_two_point_at_halftime_preserves_td_context_and_second_half_kicker(home: bool, cell: str) -> None:
    with TestClient(app) as client:
        game_id, game = _touchdown_before_try(client, home, quarter=2, seconds=1)
        engine, state = game["engine"], game["engine"].state
        try:
            assert (state.quarter, state.time_remaining) == (3, 15)
            touchdown = deepcopy(state.scoring_plays[-1])
            before = (deepcopy(state.home_stats), deepcopy(state.away_stats),
                      deepcopy(engine.play_log), deepcopy(engine.offensive_call_history))
            state.possession_team.offense.short_pass = {26: cell}
            state.defense_team.special_teams.interception_return = {26: "TD"}
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
                  patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Return26"))):
                response = client.post("/api/game/two-point", json={
                    "game_id": game_id, "offense_play": "6", "defense_play": "A",
                })
            assert response.status_code == 200
            result = response.json()
            good, defensive = cell == "3", cell == "INT 0"
            assert result["result"]["conversion_success"] is good
            assert result["result"]["defense_points"] == 2 * defensive
            assert result["result"]["scoring"] is (good or defensive)
            assert (state.home_score, state.away_score) == (
                (6 + 2 * good, 2 * defensive) if home else (2 * defensive, 6 + 2 * good)
            )
            assert (state.quarter, state.time_remaining) == (3, 15)
            assert (state.home_stats, state.away_stats, engine.play_log, engine.offensive_call_history) == before
            assert [score.play_type for score in state.scoring_plays] == (
                ["TD", "2PT"] if good else ["TD", "Def 2PT"] if defensive else ["TD"]
            )
            if good or defensive:
                score = state.scoring_plays[-1]
                assert (score.quarter, score.time_remaining) == (touchdown.quarter, touchdown.time_remaining)
                assert score.is_home_team is (not home if defensive else home)
            assert result["game_state"]["halftime_pending"] is True
            assert result["game_state"]["is_kickoff"] is True
            assert result["game_state"]["pending_pat"] is False
            assert result["game_state"]["can_go_for_two"] is False
            assert not state.game_over
            assert state.is_home_possession is not home, "the opening receiver kicks to start the second half"
            for chart in (state.home_chart, state.away_chart):
                chart.special_teams.kickoff = {26: "60"}
                chart.special_teams.kickoff_return = {26: "20"}
            with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Kick26")):
                kicked = client.post("/api/game/kickoff", json={"game_id": game_id})
            assert kicked.status_code == 200
            assert kicked.json()["game_state"]["halftime_pending"] is False
            assert state.is_home_possession is home, "the opening kicker receives the second half"
        finally:
            client.delete(f"/api/game/{game_id}")


@pytest.mark.parametrize("home", [True, False])
@pytest.mark.parametrize("expired", [False, True])
def test_actual_defensive_two_point_return_keeps_scoring_team_kickoff_or_final(home: bool, expired: bool) -> None:
    with TestClient(app) as client:
        game_id, game = _touchdown_before_try(client, home, quarter=4 if expired else 1, seconds=1 if expired else 600)
        engine, state = game["engine"], game["engine"].state
        try:
            before = (state.quarter, state.time_remaining, deepcopy(state.home_stats), deepcopy(state.away_stats),
                      deepcopy(engine.play_log), deepcopy(engine.offensive_call_history))
            state.possession_team.offense.short_pass = {26: "INT 0"}
            state.defense_team.special_teams.interception_return = {26: "TD"}
            with (patch("paydirt.play_resolver.roll_chart_dice", return_value=(26, "Try26")),
                  patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Return26"))):
                response = client.post("/api/game/two-point", json={
                    "game_id": game_id, "offense_play": "6", "defense_play": "A",
                })
            assert response.status_code == 200
            result = response.json()
            assert result["result"]["conversion_success"] is False
            assert result["result"]["defense_points"] == 2
            assert result["result"]["scoring"] is True
            assert (state.home_score, state.away_score) == ((6, 2) if home else (2, 6))
            assert (state.quarter, state.time_remaining, state.home_stats, state.away_stats,
                    engine.play_log, engine.offensive_call_history) == before
            assert state.is_home_possession is home
            assert result["game_state"]["game_over"] is expired
            assert result["game_state"]["is_kickoff"] is not expired
            assert [score.play_type for score in state.scoring_plays] == ["TD", "Def 2PT"]
            assert state.scoring_plays[-1].is_home_team is not home
            if not expired:
                state.possession_team.special_teams.kickoff = {26: "60"}
                state.defense_team.special_teams.kickoff_return = {26: "20"}
                with patch("paydirt.game_engine.roll_chart_dice", return_value=(26, "Kick26")):
                    kicked = client.post("/api/game/kickoff", json={"game_id": game_id})
                assert kicked.status_code == 200
                assert state.is_home_possession is not home
        finally:
            client.delete(f"/api/game/{game_id}")
