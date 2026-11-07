"""Explicit starter-table sides must not depend on HTML table order."""

import pytest

from paydirt.pfr_play_by_play import parse_pfr_boxscore


def game_html(before: str = "", after: str = "") -> str:
    return f'''<html><body>{before}<table id="pbp"><thead><tr>
      <th data-stat="pbp_score_aw" aria-label="FOX">FOX</th>
      <th data-stat="pbp_score_hm" aria-label="OWL">OWL</th>
      </tr></thead><tbody><tr><th data-stat="quarter">1</th>
      <td data-stat="qtr_time_remain">10:00</td><td data-stat="down">1</td>
      <td data-stat="yds_to_go">10</td><td data-stat="location">FOX 40</td>
      <td data-stat="detail"><a name="pbp_1.000"></a>
      <a href="/players/C/Center00.htm">Casey Center</a> for no gain.</td>
      </tr></tbody></table>{after}</body></html>'''


def starter(table: str, player: str = "Center00", team: str = "") -> str:
    return f'''<table id="{table}"><tbody><tr>
      <th data-stat="player" data-append-csv="{player}">Casey Center</th>
      <td data-stat="pos">C</td><td data-stat="team">{team}</td>
      </tr></tbody></table>'''


@pytest.mark.parametrize("before", [True, False])
@pytest.mark.parametrize("table,team", [("vis_starters", "FOX"), ("home_starters", "OWL")])
def test_starter_side_resolves_after_game_identity_independent_of_order(
    before: bool, table: str, team: str,
) -> None:
    html = game_html(starter(table) if before else "", "" if before else starter(table))
    game = parse_pfr_boxscore(html, "synthetic-2026")
    assert game.player_teams["Center00"] == team
    assert game.player_positions["Center00"] == "C"
    assert game.plays[0].player_ids == ("Center00",)


def test_commented_starter_table_retains_explicit_side() -> None:
    game = parse_pfr_boxscore(game_html("<!--" + starter("vis_starters") + "-->"), "synthetic-2026")
    assert game.player_teams["Center00"] == "FOX"


@pytest.mark.parametrize("tables", [
    starter("home_starters", team="FOX"),
    starter("home_starters") + starter("vis_starters"),
    starter("player_offense", team="FOX") + starter("home_starters"),
])
def test_contradictory_starter_team_identity_is_not_silently_overwritten(tables: str) -> None:
    with pytest.raises(ValueError):
        parse_pfr_boxscore(game_html(tables), "synthetic-2026")


def test_position_and_link_without_explicit_team_or_side_remain_unknown() -> None:
    game = parse_pfr_boxscore(game_html(starter("player_offense")), "synthetic-2026")
    assert "Center00" not in game.player_teams
    assert game.player_positions["Center00"] == "C"
