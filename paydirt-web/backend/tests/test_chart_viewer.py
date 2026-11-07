"""The chart reference API displays the active game's engine-loaded charts."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from main import app
from routes import games


@pytest.fixture
def chart_game():
    """Create an isolated game with public sample teams only."""
    with TestClient(app) as client:
        response = client.post("/api/game/new", json={
            "player_team": "Ironclads", "opponent_team": "Thunderhawks",
            "season": "2026", "play_as_home": True,
        })
        assert response.status_code == 200
        game_id = response.json()["game_id"]
        try:
            yield client, game_id, games[game_id]
        finally:
            client.delete(f"/api/game/{game_id}")


def test_chart_game_control_is_available(chart_game) -> None:
    client, game_id, _ = chart_game
    assert client.get(f"/api/game/state/{game_id}").status_code == 200


@pytest.mark.parametrize("side", ["home", "away"])
def test_chart_viewer_preserves_loaded_chart_values(chart_game, side: str) -> None:
    client, game_id, game = chart_game
    engine = game["engine"]
    chart = getattr(engine.state, f"{side}_chart")
    state_before = deepcopy(engine.state)
    response = client.get(f"/api/game/charts/{game_id}", params={"side": side})
    assert response.status_code == 200
    book = response.json()
    assert book["team"]["id"] == game[f"{side}_team"].id
    assert book["season"] == "2026"
    assert "team_dir" not in response.text
    assert book["legend"] and book["symbols"]
    for section in ("offense", "special_plays", "special_teams"):
        assert [row["label"] for row in book[section]["rows"]] == [str(n) for n in range(10, 40)]
    offense = book["offense"]
    assert [column["number"] for column in offense["columns"]] == list(range(1, 10))
    assert [column["group"] for column in offense["columns"]] == ["Rushing plays"] * 4 + ["Passing plays"] * 5
    for row in offense["rows"]:
        for column, cell in zip(offense["columns"], row["cells"], strict=True):
            assert cell["label"] == getattr(chart.offense, column["key"]).get(int(row["label"]), "")
    defense = book["defense"]
    assert len(defense["rows"]) == 30
    assert [row["group"]["key"] for row in defense["rows"]] == [letter for letter in "ABCDEF" for _ in range(5)]
    for row in defense["rows"]:
        modifiers = chart.defense.modifiers.get((row["group"]["key"], int(row["label"])), {})
        assert [cell["label"] for cell in row["cells"]] == [modifiers.get(n, "") for n in range(1, 10)]
    for row in book["special_plays"]["rows"]:
        roll = int(row["label"])
        assert row["cells"][0]["label"] == chart.offense.breakaway.get(roll, "")
        assert row["cells"][1]["label"] == chart.offense.qb_time.get(roll, "")
    special = book["special_teams"]
    for row in special["rows"]:
        roll = int(row["label"])
        for column, cell in zip(special["columns"], row["cells"], strict=True):
            if column["key"] == "extra_point":
                assert cell["label"] == ("NG" if roll in chart.special_teams.extra_point_no_good else "GOOD")
            else:
                assert cell["label"] == getattr(chart.special_teams, column["key"]).get(roll, "")
    assert engine.state == state_before


@pytest.mark.parametrize(("token", "color"), [
    ("", "neutral"), ("0", "neutral"), ("5", "green"), ("-3", "red"),
    ("OFF 15", "yellow"), ("DEF 5X", "yellow"), ("PI 37", "yellow"),
    ("BLACK", "black"), ("INC", "black"), ("INT 7", "red"),
    ("F + 2", "red"), ("(2)", "green"), ("(-7)", "red"),
    ("[TD]", "green"), ("(TD)", "green"), ("B*", "green"),
    ("QT", "neutral"), ("DS-", "red"),
])
def test_chart_cell_colors_and_symbols_preserve_raw_tokens(chart_game, token: str, color: str) -> None:
    client, game_id, game = chart_game
    game["engine"].state.home_chart.offense.line_plunge[10] = token
    response = client.get(f"/api/game/charts/{game_id}")
    assert response.status_code == 200
    cell = response.json()["offense"]["rows"][0]["cells"][0]
    assert cell["label"] == token
    assert cell["color"] == color
    assert cell["description"]


def test_chart_viewer_keeps_missing_rows_and_recovery_ranges(chart_game) -> None:
    client, game_id, game = chart_game
    chart = game["engine"].state.home_chart
    chart.offense.line_plunge.pop(10)
    chart.defense.modifiers.pop(("A", 1))
    chart.peripheral.fumble_recovered_range = (10, 27)
    chart.peripheral.fumble_lost_range = (28, 39)
    response = client.get(f"/api/game/charts/{game_id}")
    assert response.status_code == 200
    book = response.json()
    assert book["offense"]["rows"][0]["cells"][0]["label"] == ""
    assert [cell["label"] for cell in book["defense"]["rows"][0]["cells"]] == [""] * 9
    recovery = {row["label"]: row["cells"][2]["label"] for row in book["special_plays"]["rows"]}
    assert recovery["10"] == recovery["27"] == "R"
    assert recovery["28"] == recovery["39"] == "L"


def test_unknown_game_charts_return_explicit_404() -> None:
    with TestClient(app) as client:
        response = client.get("/api/game/charts/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"


def test_chart_viewer_rejects_invalid_side(chart_game) -> None:
    client, game_id, _ = chart_game
    assert client.get(f"/api/game/charts/{game_id}", params={"side": "other"}).status_code == 422


@pytest.mark.parametrize("token", ["SACK 0", "SACK 0*"])
def test_zero_yard_sack_chart_reference_preserves_token_and_explains_symbol(chart_game, token: str) -> None:
    client, game_id, game = chart_game
    game["engine"].state.home_chart.offense.qb_time[10] = token
    book = client.get(f"/api/game/charts/{game_id}").json()
    cell = book["special_plays"]["rows"][0]["cells"][1]
    assert cell["label"] == token and cell["color"] == "red"
    assert any(symbol["label"] == "SACK 0" and "zero" in symbol["description"].lower()
               for symbol in book["symbols"])


@pytest.mark.parametrize("side", ["home", "away"])
def test_layout_color_features_match_actual_viewer_in_all_four_tables(chart_game, side: str) -> None:
    from paydirt.chart_layout import _outcome_features

    client, game_id, _ = chart_game
    book = client.get(f"/api/game/charts/{game_id}", params={"side": side}).json()
    for section in ("offense", "defense", "special_plays", "special_teams"):
        for row in book[section]["rows"]:
            for cell in row["cells"]:
                labels = _outcome_features(cell["label"])
                assert {label for label in labels if label.startswith("color:")} == {
                    "color:" + cell["color"]}
