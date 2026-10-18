"""Public fictional teams must load real, moderate, closely matched charts."""

import csv
from collections import Counter
from itertools import product
from pathlib import Path

import pytest

from paydirt.ai_analysis import OffenseAnalyzer
from paydirt.chart_loader import load_team_chart
from paydirt.play_resolver import DefenseType, get_defense_modifier
from paydirt.priority_chart import apply_priority_chart


SEASON = Path(__file__).resolve().parents[1] / "seasons" / "2026"
TEAMS = ("Thunderhawks", "Ironclads")
PLAYS = ("Line Plunge", "Off Tackle", "End Run", "Draw", "Screen", "Short", "Med", "Long", "T/E S/L")


def chart_weights() -> Counter:
    """Exact face weights, including capped white sums, rather than equal rows."""
    return Counter(black * 10 + min(one + two, 9)
                   for black, one, two in product((1, 1, 2, 2, 3, 3), range(6), range(6)))


@pytest.mark.parametrize("team", TEAMS)
@pytest.mark.parametrize("filename,width,count", [("defense.csv", 12, 30), ("offense.csv", 13, 30), ("special.csv", 8, 30)])
def test_public_csv_rows_match_loader_schema(team: str, filename: str, width: int, count: int) -> None:
    with (SEASON / team / filename).open(newline="") as source:
        rows = list(csv.reader(source))
    assert len(rows[0]) == width
    assert len(rows[1:]) == count
    assert all(len(row) == width for row in rows[1:]), "Truncated/misaligned cells silently change chart meaning"
    if filename == "defense.csv":
        assert {(row[1], int(row[2])) for row in rows[1:]} == set(product("ABCDEF", range(1, 6)))
    else:
        assert {int(row[0]) for row in rows[1:]} == set(range(10, 40))


@pytest.mark.parametrize("team", TEAMS)
def test_all_defensive_formations_reach_the_engine(team: str) -> None:
    chart = load_team_chart(str(SEASON / team)).defense
    assert set(chart.modifiers) == set(product("ABCDEF", range(1, 6)))
    signatures = []
    for letter in "ABCDEF":
        cells = tuple(get_defense_modifier(chart, DefenseType(letter), col, sub)
                      for sub in range(1, 6) for col in range(1, 10))
        assert any(cells)
        signatures.append(cells)
    assert len(set(signatures)) == 6


@pytest.mark.parametrize("team", TEAMS)
def test_moderate_offense_and_special_teams(team: str) -> None:
    chart = load_team_chart(str(SEASON / team))
    analyzer = OffenseAnalyzer(chart.offense)
    for play in PLAYS:
        column_name = {
            "Line Plunge": "line_plunge", "Off Tackle": "off_tackle", "End Run": "end_run",
            "Draw": "draw", "Screen": "screen", "Short": "short_pass", "Med": "medium_pass",
            "Long": "long_pass", "T/E S/L": "te_short_long",
        }[play]
        column = getattr(chart.offense, column_name)
        scoring_rows = [roll for roll, value in column.items() if value == "TD"]
        assert len(scoring_rows) <= 3, (team, play, scoring_rows)
        non_scoring = dict(column)
        for roll in scoring_rows:
            non_scoring[roll] = "BLACK"
        original = getattr(chart.offense, column_name)
        setattr(chart.offense, column_name, non_scoring)
        try:
            stats = analyzer.analyze_play_type(play)
        finally:
            setattr(chart.offense, column_name, original)
        low, high = (2, 6.5) if play in PLAYS[:4] else (2, 10)
        assert low <= stats.avg_yards <= high, (team, play, stats.avg_yards)
    weights = chart_weights()
    for cells, low, high in ((chart.special_teams.kickoff, 55, 65), (chart.special_teams.punt, 35, 45)):
        total = sum(float(str(cells[roll]).rstrip("*")) * weight for roll, weight in weights.items()
                    if str(cells[roll]).rstrip("*").isdigit())
        valid = sum(weight for roll, weight in weights.items() if str(cells[roll]).rstrip("*").isdigit())
        assert low <= total / valid <= high
    for column in (chart.offense.line_plunge, chart.offense.off_tackle, chart.offense.end_run,
                   chart.offense.draw, chart.offense.screen, chart.offense.short_pass,
                   chart.offense.medium_pass, chart.offense.long_pass, chart.offense.te_short_long):
        for value in column.values():
            assert value != "*", "An out-of-bounds marker needs an actual result"
            if value.rstrip("*").lstrip("-").isdigit():
                assert abs(int(value.rstrip("*"))) <= 40


def test_public_teams_have_close_offensive_strength_and_kicking() -> None:
    teams = [load_team_chart(str(SEASON / name)) for name in TEAMS]
    averages = [[OffenseAnalyzer(team.offense).analyze_play_type(play).avg_yards for play in PLAYS]
                for team in teams]
    differences = [a - b for a, b in zip(*averages)]
    assert all(abs(difference) <= 1.25 for difference in differences)
    assert abs(sum(differences) / len(differences)) <= .5
    # Neither side gets a hidden special-teams advantage on top of its style.
    assert teams[0].special_teams != teams[1].special_teams
    assert teams[0].offense != teams[1].offense
    assert teams[0].defense != teams[1].defense
    weights = chart_weights()
    for field in ("kickoff", "kickoff_return", "punt", "punt_return", "field_goal"):
        means = [sum(float(str(getattr(team.special_teams, field)[roll]).rstrip("*")) * weight
                     for roll, weight in weights.items()) / 216 for team in teams]
        assert abs(means[0] - means[1]) <= 3


@pytest.mark.parametrize("team", TEAMS)
def test_defensive_run_counter_tradeoffs_are_live(team: str) -> None:
    chart = load_team_chart(str(SEASON / team)).defense
    # Resolve a constant four-yard offense through the actual priority chart.
    def average(formation: str, column: int) -> float:
        total = 0
        for red, green in product((1, 1, 1, 2, 2, 3), (0, 0, 0, 0, 1, 2)):
            modifier = get_defense_modifier(chart, DefenseType(formation), column, red + green)
            result = apply_priority_chart("4", modifier)
            total += result.final_yards
        return total / 36

    assert 2 <= average("A", 1) <= 5
    assert average("B", 1) <= average("A", 1) - 1
    assert average("B", 4) >= average("A", 4) + 1
    assert average("B", 5) >= average("A", 5) + 1
    blitz = [get_defense_modifier(chart, DefenseType.BLITZ, 8, sub) for sub in range(1, 6)]
    assert "QT" in blitz and any(cell.startswith("INT") for cell in blitz)


@pytest.mark.parametrize("team", TEAMS)
@pytest.mark.parametrize("sub", [4, 5])
def test_each_team_has_live_rare_big_play_weaknesses(team: str, sub: int) -> None:
    chart = load_team_chart(str(SEASON / team)).defense
    holes = [value for (formation, roll), cells in chart.modifiers.items()
             if formation in "ABCDEF" and roll == sub for value in cells.values() if value == "(TD)"]
    assert holes, (team, sub, "Rare defensive rolls must expose a genuine touchdown hole")
    assert all(apply_priority_chart("BLACK", hole).is_touchdown for hole in holes)
