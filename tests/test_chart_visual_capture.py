"""Bound browser captures are one component, never chart or owner certification."""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

import paydirt.chart_release_gate as gate
from tests import test_chart_readiness_freeze as freeze_support

freeze_files = freeze_support.freeze_files


def bound(root: Path, path: Path, value: dict | bytes) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def png(width: int = 200, height: int = 200) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff" * width * 3) * height)) + chunk(b"IEND", b""))


@pytest.fixture
def capture_files(freeze_files: tuple) -> tuple[Path, dict, dict]:
    root, freeze = freeze_files
    contexts = []
    for cohort in freeze["cohorts"]:
        folder = root / ".ai-audits" / "visual" / cohort
        game_state = {"game_id": cohort, "quarter": 1, "score": [0, 0],
                      "home_team": {"id": "Synthetic0"}, "away_team": {"id": "Synthetic1"}}
        state = bound(root, folder / "before.json", game_state)
        after = bound(root, folder / "after.json", game_state)
        sections = {}
        for view in ("offense", "defense", "special_teams"):
            keys = [f"{letter}{sub}" for letter in "ABCDEF" for sub in range(1, 6)] if view == "defense" else [str(i) for i in range(10, 40)]
            table = {"row_keys": keys, "left": 0, "top": 20, "right": 90, "bottom": 190,
                     "scroll_width": 90, "client_width": 90, "scroll_height": 170, "client_height": 170}
            tables = {view: table}
            if view == "offense":
                tables["special_plays"] = {**deepcopy(table), "left": 100, "right": 190}
            sections[view] = {
                "url": f"http://127.0.0.1:5176/?charts={cohort}&side=home&view={view}",
                "http_status": 200,
                "screenshot": bound(root, folder / f"{view}.png", png()),
                "tables": tables,
            }
        receipt = {"schema_version": 1, "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
                   "engine_fingerprint": freeze["engine_fingerprint"], "cohort": cohort, "team": "Synthetic0",
                   "chart_fingerprint": freeze["cohorts"][cohort]["chart_fingerprint"],
                   "viewport": {"width": 200, "height": 200}, "browser_errors": [],
                   "state_before": state, "state_after": after, "sections": sections}
        contexts.append({"cohort": cohort, "team": "Synthetic0",
                         "capture": bound(root, folder / "capture.json", receipt)})
    return root, freeze, {"schema_version": 1, "freeze_sha256": gate.readiness_freeze_fingerprint(freeze),
                          "contexts": contexts}


def audit(files: tuple) -> dict:
    function = getattr(gate, "audit_visual_capture_evidence", None)
    assert callable(function), "Readiness must independently validate bound chart-preview captures"
    return function(*files)


def rewrite(root: Path, context: dict, receipt: dict) -> None:
    context["capture"] = bound(root, root / context["capture"]["path"], receipt)


def test_complete_captures_remain_a_noncertifying_component(capture_files: tuple) -> None:
    result = audit(capture_files)
    assert result["passed"], result["errors"]
    assert result["release_certified"] is False
    assert result["selection_validated"] is False
    assert result["candidate_content_validated"] is False
    assert result["context_count"] == 2
    assert result["section_count"] == 6


@pytest.mark.parametrize("mutation", [
    "version", "freeze", "missing-cohort", "duplicate-context", "unknown-team", "extra-field",
    "stale-receipt", "stale-runtime", "stale-chart", "wrong-identity", "changed-receipt",
    "missing-section", "extra-section", "missing-auxiliary", "extra-table", "missing-row",
    "wrong-order", "duplicate-row", "row-bool", "clipped-bottom", "clipped-left", "overflow-x",
    "overflow-y", "nan-metric", "bool-metric", "zero-viewport", "bool-viewport",
    "changed-state", "empty-state", "browser-error", "failed-http", "remote-url", "wrong-view",
    "different-game", "different-side", "wrong-image-size", "not-png", "changed-image",
    "missing-image", "symlink-image", "outside-artifact", "duplicate-json", "extra-receipt-field",
])
def test_stale_incomplete_or_unreadable_captures_fail(capture_files: tuple, mutation: str) -> None:
    root, freeze, original = capture_files
    data = deepcopy(original)
    context = data["contexts"][0]
    receipt_path = root / context["capture"]["path"]
    receipt = json.loads(receipt_path.read_text())
    section = receipt["sections"]["offense"]
    table = section["tables"]["offense"]
    image = root / section["screenshot"]["path"]
    if mutation == "version": data["schema_version"] = True
    elif mutation == "freeze": data["freeze_sha256"] = "0" * 64
    elif mutation == "missing-cohort": data["contexts"].pop()
    elif mutation == "duplicate-context": data["contexts"].append(deepcopy(context))
    elif mutation == "unknown-team": context["team"] = "Unknown"
    elif mutation == "extra-field": data["passed"] = True
    elif mutation == "stale-receipt": receipt["freeze_sha256"] = "0" * 64
    elif mutation == "stale-runtime": receipt["engine_fingerprint"] = "0" * 64
    elif mutation == "stale-chart": receipt["chart_fingerprint"] = "0" * 64
    elif mutation == "wrong-identity": receipt["team"] = "Synthetic1"
    elif mutation == "changed-receipt": receipt_path.write_text("{}"); return assert_rejected((root, freeze, data))
    elif mutation == "missing-section": del receipt["sections"]["defense"]
    elif mutation == "extra-section": receipt["sections"]["other"] = deepcopy(section)
    elif mutation == "missing-auxiliary": del section["tables"]["special_plays"]
    elif mutation == "extra-table": section["tables"]["other"] = deepcopy(table)
    elif mutation == "missing-row": table["row_keys"].pop()
    elif mutation == "wrong-order": table["row_keys"].reverse()
    elif mutation == "duplicate-row": table["row_keys"][-1] = "10"
    elif mutation == "row-bool": table["row_keys"][0] = True
    elif mutation == "clipped-bottom": table["bottom"] = 201
    elif mutation == "clipped-left": table["left"] = -1
    elif mutation == "overflow-x": table["scroll_width"] += 1
    elif mutation == "overflow-y": table["scroll_height"] += 1
    elif mutation == "nan-metric": table["bottom"] = float("nan")
    elif mutation == "bool-metric": table["bottom"] = True
    elif mutation == "zero-viewport": receipt["viewport"]["width"] = 0
    elif mutation == "bool-viewport": receipt["viewport"]["height"] = True
    elif mutation == "changed-state": receipt["state_after"] = bound(root, root / receipt["state_after"]["path"], {"score": [7, 0]})
    elif mutation == "empty-state": receipt["state_before"] = bound(root, root / receipt["state_before"]["path"], {})
    elif mutation == "browser-error": receipt["browser_errors"].append("Uncaught error")
    elif mutation == "failed-http": section["http_status"] = 500
    elif mutation == "remote-url": section["url"] = section["url"].replace("127.0.0.1", "example.com")
    elif mutation == "wrong-view": section["url"] = section["url"].replace("view=offense", "view=defense")
    elif mutation == "different-game": section["url"] = section["url"].replace(f"charts={context['cohort']}", "charts=other")
    elif mutation == "different-side": section["url"] = section["url"].replace("side=home", "side=away")
    elif mutation == "wrong-image-size": section["screenshot"] = bound(root, image, png(201, 200))
    elif mutation == "not-png": section["screenshot"] = bound(root, image, b"Not an image")
    elif mutation == "changed-image": image.write_bytes(png(201, 200))
    elif mutation == "missing-image": image.unlink()
    elif mutation == "symlink-image":
        target = image.with_suffix(".target")
        image.rename(target)
        image.symlink_to(target)
    elif mutation == "outside-artifact":
        target = root / "external.png"
        target.write_bytes(image.read_bytes())
        section["screenshot"] = {"path": "external.png", "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    elif mutation == "duplicate-json":
        receipt_path.write_text('{"schema_version":1,"schema_version":1}')
        context["capture"]["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        return assert_rejected((root, freeze, data))
    elif mutation == "extra-receipt-field": receipt["passed"] = True
    rewrite(root, context, receipt)
    assert_rejected((root, freeze, data))


def assert_rejected(files: tuple) -> None:
    result = audit(files)
    assert result["passed"] is False, result
    assert result["errors"]
    assert result["release_certified"] is False


def test_each_context_is_checked_after_an_earlier_capture_failure(capture_files: tuple) -> None:
    root, freeze, data = capture_files
    (root / data["contexts"][0]["capture"]["path"]).unlink()
    (root / data["contexts"][1]["capture"]["path"]).unlink()
    result = audit((root, freeze, data))
    assert not result["passed"]
    assert len([error for error in result["errors"] if "capture.json" in error]) == 2


def test_changes_during_capture_validation_are_rejected(capture_files: tuple) -> None:
    root, freeze, data = capture_files
    receipt = root / data["contexts"][0]["capture"]["path"]
    original_read = Path.read_bytes

    def read(path: Path) -> bytes:
        value = original_read(path)
        if path == receipt and value != b"{}":
            receipt.write_bytes(b"{}")
        return value

    with patch.object(Path, "read_bytes", read):
        assert_rejected((root, freeze, data))

@pytest.mark.parametrize("url", [None, 123, [], {}, "http://[invalid/?charts=x&side=home&view=offense"])
def test_malformed_urls_are_recorded_as_capture_failures(capture_files: tuple, url: object) -> None:
    root, freeze, data = capture_files
    context = data["contexts"][0]
    receipt = json.loads((root / context["capture"]["path"]).read_text())
    receipt["sections"]["offense"]["url"] = url
    rewrite(root, context, receipt)
    assert_rejected((root, freeze, data))


@pytest.mark.parametrize("mutation", ["bad-checksum", "truncated-data", "invalid-scanline", "trailing-data"])
def test_invalid_png_image_data_cannot_validate(capture_files: tuple, mutation: str) -> None:
    root, freeze, data = capture_files
    context = data["contexts"][0]
    receipt = json.loads((root / context["capture"]["path"]).read_text())
    section = receipt["sections"]["offense"]
    image = png()
    if mutation == "bad-checksum": image = image[:29] + b"xxxx" + image[33:]
    elif mutation == "truncated-data": image = image[:-12]
    elif mutation == "trailing-data": image += b"extra"
    elif mutation == "invalid-scanline":
        def chunk(kind: bytes, payload: bytes) -> bytes:
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
        image = image[:33] + chunk(b"IDAT", zlib.compress(b"invalid pixels")) + chunk(b"IEND", b"")
    section["screenshot"] = bound(root, root / section["screenshot"]["path"], image)
    rewrite(root, context, receipt)
    assert_rejected((root, freeze, data))


def test_overlapping_auxiliary_table_cannot_validate(capture_files: tuple) -> None:
    root, freeze, data = capture_files
    context = data["contexts"][0]
    receipt = json.loads((root / context["capture"]["path"]).read_text())
    tables = receipt["sections"]["offense"]["tables"]
    tables["special_plays"] = deepcopy(tables["offense"])
    rewrite(root, context, receipt)
    assert_rejected((root, freeze, data))


@pytest.mark.parametrize("mutation", ["missing-game", "different-game", "different-team", "missing-team"])
def test_state_evidence_must_belong_to_the_displayed_game_and_team(capture_files: tuple, mutation: str) -> None:
    root, freeze, data = capture_files
    context = data["contexts"][0]
    receipt = json.loads((root / context["capture"]["path"]).read_text())
    state = json.loads((root / receipt["state_before"]["path"]).read_text())
    if mutation == "missing-game": del state["game_id"]
    elif mutation == "different-game": state["game_id"] = "other"
    elif mutation == "different-team": state["home_team"]["id"] = "Synthetic1"
    elif mutation == "missing-team": del state["home_team"]
    for name in ("state_before", "state_after"):
        receipt[name] = bound(root, root / receipt[name]["path"], state)
    rewrite(root, context, receipt)
    assert_rejected((root, freeze, data))


def test_away_side_captures_can_validate_with_matching_state(capture_files: tuple) -> None:
    root, freeze, data = capture_files
    for context in data["contexts"]:
        receipt = json.loads((root / context["capture"]["path"]).read_text())
        state = json.loads((root / receipt["state_before"]["path"]).read_text())
        state["home_team"], state["away_team"] = state["away_team"], state["home_team"]
        for name in ("state_before", "state_after"):
            receipt[name] = bound(root, root / receipt[name]["path"], state)
        for section in receipt["sections"].values():
            section["url"] = section["url"].replace("side=home", "side=away")
        rewrite(root, context, receipt)
    result = audit((root, freeze, data))
    assert result["passed"], result["errors"]
