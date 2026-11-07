"""Selected preview cells must match frozen loaded charts and actual DOM observations."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

import paydirt.chart_release_gate as gate
from paydirt.chart_generator import TeamSeasonStats, generate_team_charts
from paydirt.chart_loader import load_team_chart
from tests import test_chart_visual_capture as support
from tests.test_chart_generator import _synthetic_stats

freeze_files = support.freeze_files
capture_files = support.capture_files
bound = support.bound

PLAYS = (("line_plunge", "Line Plunge"), ("off_tackle", "Off Tackle"), ("end_run", "End Run"),
         ("draw", "Draw"), ("screen", "Screen"), ("short_pass", "Short"), ("medium_pass", "Med"),
         ("long_pass", "Long"), ("te_short_long", "T/E S/L"))
FORMATIONS = (("A", "Standard"), ("B", "Short Ydg"), ("C", "Spread"),
              ("D", "Short Pass"), ("E", "Long Pass"), ("F", "Blitz"))
SPECIAL = (("kickoff", "Kickoff"), ("kickoff_return", "KO Return"), ("punt", "Punt"),
           ("punt_return", "Punt Return"), ("interception_return", "INT Return"),
           ("fumble_return", "Fumble Return"), ("field_goal", "Field Goal"), ("extra_point", "Extra Point"))


def api_book(chart: object, season: int) -> dict:
    """Construct a synthetic API observation independently of production validators."""
    def cell(value: str) -> dict:
        return {"label": value, "color": "neutral", "description": value or "Blank chart entry"}
    def table(key: str, title: str, columns: tuple, values: list[list[str]]) -> dict:
        return {"key": key, "title": title, "roll_label": "#",
                "columns": [{"key": key, "label": label, "number": None, "group": None} for key, label in columns],
                "rows": [{"label": str(roll), "description": f"Chart roll {roll}", "group": None,
                          "cells": [cell(value) for value in values[roll - 10]]} for roll in range(10, 40)]}
    offense = table("offense", "Offense", PLAYS,
                    [[getattr(chart.offense, key).get(roll, "") for key, _ in PLAYS] for roll in range(10, 40)])
    for number, column in enumerate(offense["columns"], 1):
        column.update(number=number, group="Rushing plays" if number < 5 else "Passing plays")
    defense = deepcopy(offense)
    defense.update(key="defense", title="Defense", rows=[])
    for letter, name in FORMATIONS:
        for sub in range(1, 6):
            defense["rows"].append({"label": str(sub), "description": f"{letter} {name}, row {sub}",
                                    "group": {"key": letter, "label": name},
                                    "cells": [cell(chart.defense.modifiers.get((letter, sub), {}).get(number, ""))
                                              for number in range(1, 10)]})
    recovered, lost = chart.peripheral.fumble_recovered_range, chart.peripheral.fumble_lost_range
    auxiliary = table("special_plays", "Special Plays",
                      (("breakaway", "B · Breakaway"), ("qb_time", "QT · QB Time"), ("fumble", "Fumble")),
                      [[chart.offense.breakaway.get(roll, ""), chart.offense.qb_time.get(roll, ""),
                        "R" if recovered[0] <= roll <= recovered[1] else "L" if lost[0] <= roll <= lost[1] else ""]
                       for roll in range(10, 40)])
    special = table("special_teams", "Special Teams", SPECIAL,
                    [[("NG" if roll in chart.special_teams.extra_point_no_good else "GOOD") if key == "extra_point"
                      else getattr(chart.special_teams, key).get(roll, "") for key, _ in SPECIAL] for roll in range(10, 40)])
    return {"team": {"id": "Synthetic0", "name": "Synthetic0"}, "season": str(season), "note": "Synthetic chart reference",
            "offense": offense, "defense": defense, "special_plays": auxiliary, "special_teams": special,
            "legend": [{"color": "neutral", "label": "White", "description": "Synthetic legend"}],
            "symbols": [{"label": "F", "description": "Synthetic symbol"}]}


def dom_view(book: dict, view: str, url: str) -> dict:
    tables = {}
    for key in ([view, "special_plays"] if view == "offense" else [view]):
        table = book[key]
        tables[key] = {
            "caption": f"{table['title']} · {book['team']['name']}",
            "columns": [column["label"] for column in table["columns"]],
            "numbers": [str(column["number"]) for column in table["columns"] if column["number"] is not None],
            "column_groups": ([{"label": "Rushing plays", "span": 4}, {"label": "Passing plays", "span": 5}]
                              if key in {"offense", "defense"} else []),
            "rows": [{"key": (row["group"]["key"] if row["group"] else "") + row["label"],
                      "labels": [cell["label"] for cell in row["cells"]],
                      "colors": [cell["color"] for cell in row["cells"]]} for row in table["rows"]],
        }
    return {"url": url, "heading": f"{book['season']} {book['team']['name']}", "tables": tables}


@pytest.fixture
def content_files(capture_files: tuple) -> tuple[Path, dict, dict, dict]:
    root, freeze, captures = capture_files
    contexts = []
    for capture in captures["contexts"]:
        cohort = capture["cohort"]
        season = 1983 if cohort == "1983-generated" else 2024
        directory = root / freeze["cohorts"][cohort]["season_dir"]
        data = _synthetic_stats().to_dict()
        data.update(season=season, team_name="Synthetic0")
        generate_team_charts(TeamSeasonStats.from_dict(data), directory / "Synthetic0", seed=8306)
        freeze["cohorts"][cohort]["chart_fingerprint"] = gate.chart_fingerprint(directory)
    freeze_sha = gate.readiness_freeze_fingerprint(freeze)
    captures["freeze_sha256"] = freeze_sha
    for capture in captures["contexts"]:
        cohort = capture["cohort"]
        directory = root / freeze["cohorts"][cohort]["season_dir"]
        receipt_path = root / capture["capture"]["path"]
        receipt = json.loads(receipt_path.read_text())
        receipt.update(freeze_sha256=freeze_sha, chart_fingerprint=freeze["cohorts"][cohort]["chart_fingerprint"])
        for state_key in ("state_before", "state_after"):
            state = json.loads((root / receipt[state_key]["path"]).read_text())
            state["home_team"]["name"] = "Synthetic0"
            receipt[state_key] = bound(root, root / receipt[state_key]["path"], state)
        capture["capture"] = bound(root, receipt_path, receipt)
        season = 1983 if cohort == "1983-generated" else 2024
        book = api_book(load_team_chart(str(directory / "Synthetic0")), season)
        context = {"cohort": cohort, "team": "Synthetic0", "api_book": bound(root, receipt_path.parent / "api.json", book),
                   "views": {view: bound(root, receipt_path.parent / f"{view}-dom.json", dom_view(book, view, entry["url"]))
                             for view, entry in receipt["sections"].items()}}
        contexts.append(context)
    return root, freeze, captures, {"schema_version": 1, "freeze_sha256": freeze_sha,
                                    "captures_sha256": gate.readiness_freeze_fingerprint(captures), "contexts": contexts}


def audit(files: tuple) -> dict:
    function = getattr(gate, "audit_visual_content_evidence", None)
    assert callable(function), "Readiness must compare candidate/API/DOM chart contents"
    return function(*files)


def test_all_four_tables_match_frozen_loaded_candidate(content_files: tuple) -> None:
    result = audit(content_files)
    assert result["passed"], result["errors"]
    assert result["candidate_content_validated"] is True
    assert result["selection_validated"] is False
    assert result["release_certified"] is False
    assert result["tables_checked"] == 8
    assert result["cells_checked"] == 1740


@pytest.mark.parametrize("mutation", [
    "version", "freeze", "captures-digest", "missing-context", "duplicate-context", "unknown-context", "extra-field",
    "changed-api", "missing-api", "api-team", "api-season", "api-name", "missing-table", "table-key",
    "column-order", "column-name", "call-number", "call-group", "defense-group", "defense-subrow",
    "offense-value", "defense-value", "auxiliary-value", "special-value", "extra-point", "fumble-range",
    "missing-row", "extra-cell", "bool-label", "unknown-color", "cell-description", "duplicate-json",
    "missing-dom", "changed-dom", "dom-url", "dom-heading", "dom-caption", "dom-columns", "dom-numbers",
    "dom-groups", "dom-row-order", "dom-values", "dom-color", "dom-missing-aux", "dom-extra-table",
    "failed-capture", "stale-source", "api-symlink", "dom-nonfinite",
])
def test_unbound_stale_or_substituted_chart_contents_fail(content_files: tuple, mutation: str) -> None:
    root, freeze, captures, original = content_files
    evidence = deepcopy(original)
    context = evidence["contexts"][0]
    api_path = root / context["api_book"]["path"]
    book = json.loads(api_path.read_text())
    dom_path = root / context["views"]["offense"]["path"]
    dom = json.loads(dom_path.read_text())
    api_rewrite, dom_rewrite = False, False
    if mutation == "version": evidence["schema_version"] = True
    elif mutation == "freeze": evidence["freeze_sha256"] = "0" * 64
    elif mutation == "captures-digest": evidence["captures_sha256"] = "0" * 64
    elif mutation == "missing-context": evidence["contexts"].pop()
    elif mutation == "duplicate-context": evidence["contexts"].append(deepcopy(context))
    elif mutation == "unknown-context": context["team"] = "Synthetic1"
    elif mutation == "extra-field": evidence["passed"] = True
    elif mutation == "changed-api": api_path.write_text("{}")
    elif mutation == "missing-api": api_path.unlink()
    elif mutation == "missing-dom": dom_path.unlink()
    elif mutation == "changed-dom": dom_path.write_text("{}")
    elif mutation == "failed-capture": captures["contexts"][0]["capture"]["sha256"] = "0" * 64
    elif mutation == "stale-source": (root / freeze["cohorts"]["2024"]["season_dir"] / "Synthetic0" / "offense.csv").write_text("changed")
    elif mutation == "api-symlink":
        target = api_path.with_suffix(".target")
        api_path.rename(target)
        api_path.symlink_to(target)
    elif mutation == "duplicate-json":
        context["api_book"] = bound(root, api_path, b'{"season":"1983","season":"1983"}')
    elif mutation == "dom-nonfinite":
        context["views"]["offense"] = bound(root, dom_path, b'{"bad":NaN}')
    elif mutation.startswith("dom-"):
        dom_rewrite = True
        table = dom["tables"]["offense"]
        if mutation == "dom-url": dom["url"] = dom["url"].replace("side=home", "side=away")
        elif mutation == "dom-heading": dom["heading"] = "Other team"
        elif mutation == "dom-caption": table["caption"] = "Defense · Synthetic0"
        elif mutation == "dom-columns": table["columns"].reverse()
        elif mutation == "dom-numbers": table["numbers"].reverse()
        elif mutation == "dom-groups": table["column_groups"][0]["span"] = 5
        elif mutation == "dom-row-order": table["rows"].reverse()
        elif mutation == "dom-values": table["rows"][0]["labels"][0] = "999"
        elif mutation == "dom-color": table["rows"][0]["colors"][0] = "red"
        elif mutation == "dom-missing-aux": del dom["tables"]["special_plays"]
        elif mutation == "dom-extra-table": dom["tables"]["other"] = deepcopy(table)
    else:
        api_rewrite = True
        table = book["offense"]
        if mutation == "api-team": book["team"]["id"] = "Synthetic1"
        elif mutation == "api-name": book["team"]["name"] = "Rewritten name"
        elif mutation == "api-season": book["season"] = "2026"
        elif mutation == "missing-table": del book["defense"]
        elif mutation == "table-key": table["key"] = "other"
        elif mutation == "column-order": table["columns"].reverse()
        elif mutation == "column-name": table["columns"][0]["label"] = "Other"
        elif mutation == "call-number": table["columns"][0]["number"] = 9
        elif mutation == "call-group": table["columns"][0]["group"] = "Passing plays"
        elif mutation == "defense-group": book["defense"]["rows"][0]["group"]["key"] = "B"
        elif mutation == "defense-subrow": book["defense"]["rows"][0]["label"] = "2"
        elif mutation in {"offense-value", "defense-value", "auxiliary-value", "special-value"}:
            key = {"offense-value": "offense", "defense-value": "defense", "auxiliary-value": "special_plays", "special-value": "special_teams"}[mutation]
            book[key]["rows"][0]["cells"][0].update(label="999", description="999")
        elif mutation == "extra-point": book["special_teams"]["rows"][0]["cells"][-1].update(label="other", description="other")
        elif mutation == "fumble-range": book["special_plays"]["rows"][0]["cells"][-1].update(label="other", description="other")
        elif mutation == "missing-row": table["rows"].pop()
        elif mutation == "extra-cell": table["rows"][0]["cells"].append(deepcopy(table["rows"][0]["cells"][0]))
        elif mutation == "bool-label": table["rows"][0]["cells"][0]["label"] = True
        elif mutation == "unknown-color": table["rows"][0]["cells"][0]["color"] = "purple"
        elif mutation == "cell-description": table["rows"][0]["cells"][0]["description"] = "Changed"
    if api_rewrite: context["api_book"] = bound(root, api_path, book)
    if dom_rewrite: context["views"]["offense"] = bound(root, dom_path, dom)
    result = audit((root, freeze, captures, evidence))
    assert not result["passed"], result
    assert result["errors"]
    assert result["release_certified"] is False


def test_every_context_retains_its_failure(content_files: tuple) -> None:
    root, freeze, captures, evidence = content_files
    for context in evidence["contexts"]:
        (root / context["api_book"]["path"]).unlink()
    result = audit((root, freeze, captures, evidence))
    assert len([reason for reason in result["errors"] if "api.json" in reason]) == 2


def test_dom_artifacts_are_rechecked_after_comparison(content_files: tuple) -> None:
    root, freeze, captures, evidence = content_files
    target = root / evidence["contexts"][0]["views"]["offense"]["path"]
    original_read = Path.read_bytes
    def read(path: Path) -> bytes:
        value = original_read(path)
        if path == target and value != b"{}": target.write_bytes(b"{}")
        return value
    with patch.object(Path, "read_bytes", read):
        result = audit((root, freeze, captures, evidence))
    assert not result["passed"] and result["errors"]


def test_boolean_call_number_cannot_equal_integer_one(content_files: tuple) -> None:
    root, freeze, captures, evidence = content_files
    context = evidence["contexts"][0]
    path = root / context["api_book"]["path"]
    book = json.loads(path.read_text())
    book["offense"]["columns"][0]["number"] = True
    context["api_book"] = bound(root, path, book)
    assert not audit((root, freeze, captures, evidence))["passed"]


def test_malformed_matching_api_and_state_team_returns_a_failure(content_files: tuple) -> None:
    root, freeze, captures, evidence = content_files
    capture = captures["contexts"][0]
    receipt_path = root / capture["capture"]["path"]
    receipt = json.loads(receipt_path.read_text())
    for name in ("state_before", "state_after"):
        path = root / receipt[name]["path"]
        state = json.loads(path.read_text())
        state["home_team"] = []
        receipt[name] = bound(root, path, state)
    capture["capture"] = bound(root, receipt_path, receipt)
    context = evidence["contexts"][0]
    path = root / context["api_book"]["path"]
    book = json.loads(path.read_text())
    book["team"] = []
    context["api_book"] = bound(root, path, book)
    evidence["captures_sha256"] = gate.readiness_freeze_fingerprint(captures)
    result = audit((root, freeze, captures, evidence))
    assert not result["passed"] and result["errors"]


@pytest.mark.parametrize("valid", [True, False])
def test_existing_cli_can_compare_saved_candidate_api_dom_contents(
    content_files: tuple, monkeypatch: pytest.MonkeyPatch, valid: bool,
) -> None:
    from scripts import audit_generated_charts as cli
    root, freeze, captures, evidence = content_files
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(cli, "run_engine_audit", lambda *args, **kwargs: pytest.fail("Content validation must not start games"))
    if not valid: evidence["contexts"][0]["api_book"]["sha256"] = "0" * 64
    folder = root / ".ai-audits" / "cli"
    folder.mkdir()
    paths = {}
    for name, data in (("freeze", freeze), ("capture", captures), ("content", evidence)):
        paths[name] = folder / f"{name}.json"
        paths[name].write_text(json.dumps(data))
    output = folder / "result.json"
    assert cli.main(["--freeze", str(paths["freeze"]), "--visual-capture", str(paths["capture"]),
                     "--visual-content", str(paths["content"]), "--output", str(output)]) == (0 if valid else 1)
    result = json.loads(output.read_text())
    assert result["passed"] is valid
    assert result["candidate_content_validated"] is valid
    assert result["selection_validated"] is False
    assert result["release_certified"] is False


def test_cli_cannot_keep_content_validation_true_after_input_manifest_changes(
    content_files: tuple, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import audit_generated_charts as cli
    root, freeze, captures, evidence = content_files
    monkeypatch.setattr(cli, "ROOT", root)
    folder = root / ".ai-audits" / "changed-cli"
    folder.mkdir()
    paths = {}
    for name, data in (("freeze", freeze), ("capture", captures), ("content", evidence)):
        paths[name] = folder / f"{name}.json"
        paths[name].write_text(json.dumps(data))
    original_read = Path.read_bytes
    def read(path: Path) -> bytes:
        value = original_read(path)
        if path == paths["content"] and value != b"{}": path.write_bytes(b"{}")
        return value
    output = folder / "result.json"
    with patch.object(Path, "read_bytes", read):
        status = cli.main(["--freeze", str(paths["freeze"]), "--visual-capture", str(paths["capture"]),
                           "--visual-content", str(paths["content"]), "--output", str(output)])
    result = json.loads(output.read_text())
    assert status == 1 and result["passed"] is False
    assert result["candidate_content_validated"] is False
