"""Compare preview observations with core-loaded chart values, without resolving plays."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .chart_loader import TeamChart

PLAY_COLUMNS = (
    ("line_plunge", "Line Plunge"), ("off_tackle", "Off Tackle"), ("end_run", "End Run"),
    ("draw", "Draw"), ("screen", "Screen"), ("short_pass", "Short"), ("medium_pass", "Med"),
    ("long_pass", "Long"), ("te_short_long", "T/E S/L"),
)
FORMATIONS = (("A", "Standard"), ("B", "Short Ydg"), ("C", "Spread"),
              ("D", "Short Pass"), ("E", "Long Pass"), ("F", "Blitz"))
SPECIAL_COLUMNS = (
    ("kickoff", "Kickoff"), ("kickoff_return", "KO Return"), ("punt", "Punt"),
    ("punt_return", "Punt Return"), ("interception_return", "INT Return"),
    ("fumble_return", "Fumble Return"), ("field_goal", "Field Goal"), ("extra_point", "Extra Point"),
)
TABLE_TITLES = {"offense": "Offense", "defense": "Defense", "special_plays": "Special Plays", "special_teams": "Special Teams"}


def _candidate_tables(chart: TeamChart) -> dict[str, dict[str, Any]]:
    """Project the same values the engine loads; this performs no play resolution."""
    recovered, lost = chart.peripheral.fumble_recovered_range, chart.peripheral.fumble_lost_range
    tables = {}
    for key, title in TABLE_TITLES.items():
        pairs = (PLAY_COLUMNS if key in {"offense", "defense"} else SPECIAL_COLUMNS if key == "special_teams"
                 else (("breakaway", "B · Breakaway"), ("qb_time", "QT · QB Time"), ("fumble", "Fumble")))
        columns = [{"key": name, "label": label,
                    "number": index if key in {"offense", "defense"} else None,
                    "group": ("Rushing plays" if index <= 4 else "Passing plays") if key in {"offense", "defense"} else None}
                   for index, (name, label) in enumerate(pairs, 1)]
        rows = []
        identities = [(letter, sub, name) for letter, name in FORMATIONS for sub in range(1, 6)] if key == "defense" else [("", roll, "") for roll in range(10, 40)]
        for letter, roll, name in identities:
            values = []
            for index, (column, _label) in enumerate(pairs, 1):
                if key == "defense":
                    value = chart.defense.modifiers.get((letter, roll), {}).get(index, "")
                elif key == "special_plays" and column == "fumble":
                    value = "R" if recovered[0] <= roll <= recovered[1] else "L" if lost[0] <= roll <= lost[1] else ""
                elif column == "extra_point":
                    value = "NG" if roll in chart.special_teams.extra_point_no_good else "GOOD"
                else:
                    source = chart.special_teams if key == "special_teams" else chart.offense
                    value = getattr(source, column).get(roll, "")
                values.append(value)
            rows.append({"key": letter + str(roll), "label": str(roll),
                         "description": f"{letter} {name}, row {roll}" if letter else f"Chart roll {roll}",
                         "group": {"key": letter, "label": name} if letter else None, "labels": values})
        tables[key] = {"title": title, "columns": columns, "rows": rows}
    return tables


def compare_preview_book(
    chart: TeamChart, book: Mapping[str, Any], team: Mapping[str, Any], season: int,
) -> dict[str, dict[str, Any]]:
    """Return required DOM observations after comparing every API cell to the candidate.

    Palette categories are checked for API/DOM correspondence, not interpreted as
    game rules or evidence of the rendered pixel colors.
    """
    fields = {"team", "season", "note", *TABLE_TITLES, "legend", "symbols"}
    if (not isinstance(team, Mapping) or not isinstance(book, Mapping) or set(book) != fields or book["team"] != team
            or not isinstance(team.get("name"), str) or not team["name"] or book["season"] != str(season)
            or not isinstance(book["note"], str) or not book["note"]
            or not isinstance(book["legend"], list) or not book["legend"]
            or not isinstance(book["symbols"], list) or not book["symbols"]):
        raise ValueError("API chart book identity, season or display envelope differs from the selected game")
    result = {}
    for key, expected in _candidate_tables(chart).items():
        table = book[key]
        if (not isinstance(table, dict) or set(table) != {"key", "title", "roll_label", "columns", "rows"}
                or table["key"] != key or table["title"] != expected["title"] or table["roll_label"] != "#"):
            raise ValueError(f"{key}: API table identity or structure differs from the candidate")
        columns = table["columns"]
        if not isinstance(columns, list) or columns != expected["columns"]:
            raise ValueError(f"{key}: API call columns, names, numbers or groups differ from the candidate")
        for column in columns:
            if column["number"] is not None and type(column["number"]) is not int:
                raise TypeError(f"{key}: API call numbers must be integers")
        rows = table["rows"]
        if not isinstance(rows, list) or len(rows) != 30:
            raise ValueError(f"{key}: API requires all thirty candidate rows")
        observations = []
        for row, candidate in zip(rows, expected["rows"], strict=True):
            if (not isinstance(row, dict) or set(row) != {"label", "description", "group", "cells"}
                    or any(row[field] != candidate[field] for field in ("label", "description", "group"))
                    or not isinstance(row["cells"], list) or len(row["cells"]) != len(candidate["labels"])):
                raise ValueError(f"{key}: API row identity or width differs from the candidate")
            colors = []
            for cell, value in zip(row["cells"], candidate["labels"], strict=True):
                if (not isinstance(cell, dict) or set(cell) != {"label", "color", "description"}
                        or cell["label"] != value or cell["description"] != (value or "Blank chart entry")
                        or cell["color"] not in {"neutral", "green", "red", "yellow", "black"}):
                    raise ValueError(f"{key}/{candidate['key']}: API cell differs from the loaded candidate or display palette")
                colors.append(cell["color"])
            observations.append({"key": candidate["key"], "labels": candidate["labels"], "colors": colors})
        result[key] = {
            "caption": f"{expected['title']} · {team['name']}",
            "columns": [column["label"] for column in expected["columns"]],
            "numbers": [str(column["number"]) for column in expected["columns"] if column["number"] is not None],
            "column_groups": ([{"label": "Rushing plays", "span": 4}, {"label": "Passing plays", "span": 5}]
                              if key in {"offense", "defense"} else []),
            "rows": observations,
        }
    return result


def compare_preview_dom(observation: Mapping[str, Any], url: str, heading: str, tables: dict[str, dict]) -> int:
    """Compare one actual DOM observation with the already validated API values."""
    if (not isinstance(observation, Mapping) or set(observation) != {"url", "heading", "tables"}
            or observation["url"] != url or observation["heading"] != heading
            or observation["tables"] != tables):
        raise ValueError("DOM heading, URL, table/call/row identities, cell labels or palette differ from the candidate/API")
    for table in observation["tables"].values():
        if any(type(group["span"]) is not int for group in table["column_groups"]):
            raise TypeError("DOM column-group spans must be integers")
    return sum(len(row["labels"]) for table in tables.values() for row in table["rows"])
