"""Display models for engine-loaded charts; no play resolution happens here."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from paydirt.chart_layout import chart_cell_color
from paydirt.chart_loader import TeamChart


class ChartCell(BaseModel):
    label: str
    color: str = "neutral"
    description: str


class ChartColumn(BaseModel):
    key: str
    label: str
    number: Optional[int] = None
    group: Optional[str] = None


class ChartGroup(BaseModel):
    key: str
    label: str


class ChartRow(BaseModel):
    label: str
    description: str
    cells: list[ChartCell]
    group: Optional[ChartGroup] = None


class ChartTable(BaseModel):
    key: str
    title: str
    roll_label: str = "#"
    columns: list[ChartColumn]
    rows: list[ChartRow]


class ChartBookResponse(BaseModel):
    team: dict[str, Any]
    season: str
    note: str
    offense: ChartTable
    defense: ChartTable
    special_plays: ChartTable
    special_teams: ChartTable
    legend: list[dict[str, str]]
    symbols: list[dict[str, str]]


PLAY_COLUMNS = (
    ("line_plunge", "Line Plunge"), ("off_tackle", "Off Tackle"),
    ("end_run", "End Run"), ("draw", "Draw"), ("screen", "Screen"),
    ("short_pass", "Short"), ("medium_pass", "Med"),
    ("long_pass", "Long"), ("te_short_long", "T/E S/L"),
)
FORMATIONS = (
    ("A", "Standard"), ("B", "Short Ydg"), ("C", "Spread"),
    ("D", "Short Pass"), ("E", "Long Pass"), ("F", "Blitz"),
)
SPECIAL_COLUMNS = (
    ("kickoff", "Kickoff"), ("kickoff_return", "KO Return"),
    ("punt", "Punt"), ("punt_return", "Punt Return"),
    ("interception_return", "INT Return"), ("fumble_return", "Fumble Return"),
    ("field_goal", "Field Goal"), ("extra_point", "Extra Point"),
)


def _cell(raw: str) -> ChartCell:
    """Assign a display fill while retaining the exact loaded chart symbol."""
    return ChartCell(label=raw, color=chart_cell_color(raw), description=raw or "Blank chart entry")


def _roll_table(key: str, title: str, columns: list[ChartColumn], values: dict[str, dict[int, str]]) -> ChartTable:
    """Keep all thirty chart rows, including blank entries."""
    return ChartTable(
        key=key, title=title, columns=columns,
        rows=[ChartRow(
            label=str(roll), description=f"Chart roll {roll}",
            cells=[_cell(values[column.key].get(roll, "")) for column in columns],
        ) for roll in range(10, 40)],
    )


def build_chart_book(chart: TeamChart, team: dict[str, Any], season: str) -> ChartBookResponse:
    """Serialize the active chart object without reading files or mutating play state.

    Args:
        chart: Chart already loaded into the active game engine.
        team: Team identity already used by the game's API.
        season: Season selected for the game.

    Returns:
        Tables and display metadata for the chart reference viewer.
    """
    play_columns = [ChartColumn(
        key=key, label=label, number=number,
        group="Rushing plays" if number <= 4 else "Passing plays",
    ) for number, (key, label) in enumerate(PLAY_COLUMNS, start=1)]
    offense = _roll_table("offense", "Offense", play_columns, {
        key: getattr(chart.offense, key) for key, _ in PLAY_COLUMNS
    })
    defense = ChartTable(
        key="defense", title="Defense", columns=play_columns,
        rows=[ChartRow(
            label=str(sub), description=f"{letter} {name}, row {sub}",
            group=ChartGroup(key=letter, label=name),
            cells=[_cell(chart.defense.modifiers.get((letter, sub), {}).get(number, ""))
                   for number in range(1, 10)],
        ) for letter, name in FORMATIONS for sub in range(1, 6)],
    )
    recovered = chart.peripheral.fumble_recovered_range
    lost = chart.peripheral.fumble_lost_range
    recovery = {
        roll: "R" if recovered[0] <= roll <= recovered[1] else
        "L" if lost[0] <= roll <= lost[1] else ""
        for roll in range(10, 40)
    }
    auxiliary = [("breakaway", "B · Breakaway"), ("qb_time", "QT · QB Time"), ("fumble", "Fumble")]
    special_plays = _roll_table("special_plays", "Special Plays", [
        ChartColumn(key=key, label=label) for key, label in auxiliary
    ], {"breakaway": chart.offense.breakaway, "qb_time": chart.offense.qb_time, "fumble": recovery})
    special_values = {key: getattr(chart.special_teams, key) for key, _ in SPECIAL_COLUMNS if key != "extra_point"}
    special_values["extra_point"] = {
        roll: "NG" if roll in chart.special_teams.extra_point_no_good else "GOOD"
        for roll in range(10, 40)
    }
    special_teams = _roll_table("special_teams", "Special Teams", [
        ChartColumn(key=key, label=label) for key, label in SPECIAL_COLUMNS
    ], special_values)
    note = "Reference charts for this game. The game engine resolves all plays."
    if chart.peripheral.special_defense:
        note += f" Special defense: {chart.peripheral.special_defense}."
    return ChartBookResponse(
        team=team, season=season, note=note, offense=offense, defense=defense,
        special_plays=special_plays, special_teams=special_teams,
        legend=[
            {"color": "green", "label": "Green", "description": "Positive yardage, breakaway or touchdown"},
            {"color": "red", "label": "Red", "description": "Negative yardage, sack, fumble, interception or missed kick"},
            {"color": "yellow", "label": "Yellow", "description": "Penalty entry"},
            {"color": "black", "label": "Black", "description": "BLACK or INC entry"},
            {"color": "neutral", "label": "White", "description": "Blank, zero or other chart symbol"},
        ],
        symbols=[
            {"label": "( ) / [ ]", "description": "Replacement entry; keep the chart's printed symbols"},
            {"label": "B / QT", "description": "Breakaway / quarterback time; see Special Plays"},
            {"label": "SACK 0", "description": "Quarterback sack with zero yards lost"},
            {"label": "R / L", "description": "Fumble recovered / lost"},
            {"label": "* / †", "description": "Sideline markers retained from the chart"},
            {"label": "GOOD / NG", "description": "Extra point good / no good"},
        ],
    )
