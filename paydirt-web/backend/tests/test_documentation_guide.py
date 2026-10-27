"""Offline guide loading and packaging regressions."""

import ast
import sys
from pathlib import Path

import pytest
import routes
from fastapi.testclient import TestClient
from main import app

PAGES = (
    "installation", "web-interface", "playing", "priority-chart", "clock-management",
    "ai-difficulty", "seasons", "chart-generator", "saved-games-and-standings",
)
client = TestClient(app)


@pytest.fixture
def guide_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    for page in PAGES:
        (docs / f"{page}.md").write_text(f"# {page.title()}\n\n{page} instructions.\n")
    monkeypatch.setattr(routes, "_get_docs_path", lambda: docs)
    return docs


def test_guide_loads_topic_files_not_landing_readme(guide_docs: Path) -> None:
    response = client.get("/api/guide")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Paydirt User Guide"
    for page in PAGES:
        assert f"{page} instructions." in data["content"]
    assert "[Installation](#installation)" in data["content"]
    assert "development.md" not in data["content"]


def test_guide_rewrites_local_links_and_images_without_touching_code(guide_docs: Path) -> None:
    (guide_docs / "playing.md").write_text(
        '# Playing\n\n## Choices\n\n'
        '[Clock](clock-management.md) [Timeouts](clock-management.md#choices)\n'
        '[Here](#choices) [Docs](README.md) [Dev](development.md)\n'
        '![Field](images/offense.png)\n'
        '~~~text\n## Choices\n[Example](clock-management.md)\n~~~\n'
    )
    (guide_docs / "clock-management.md").write_text('# Clock Management\n\n## Choices\n')
    content = client.get("/api/guide").json()["content"]
    assert "[Clock](#clock-management)" in content
    assert "[Timeouts](#choices-1)" in content
    assert "[Here](#choices)" in content
    assert "[Docs](#paydirt-user-guide)" in content
    assert "[Dev](https://github.com/rtulloh/paydirt/blob/main/docs/development.md)" in content
    assert "![Field](/api/docs/images/offense.png)" in content
    assert '~~~text\n## Choices\n[Example](clock-management.md)\n~~~' in content


@pytest.mark.parametrize("missing", ["all", "one"])
def test_missing_guide_content_returns_404_not_an_incomplete_manual(
    guide_docs: Path, monkeypatch: pytest.MonkeyPatch, missing: str,
) -> None:
    if missing == "all":
        monkeypatch.setattr(routes, "_get_docs_path", lambda: None)
    else:
        (guide_docs / "chart-generator.md").unlink()
    assert client.get("/api/guide").status_code == 404


@pytest.mark.parametrize("bundle_style", ["meipass", "executable"])
def test_offline_bundle_loads_its_own_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bundle_style: str,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    for page in PAGES:
        (docs / f"{page}.md").write_text(f"# {page}\nOffline {page}.\n")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    if bundle_style == "meipass":
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    else:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        monkeypatch.setattr(sys, "executable", str(tmp_path / "paydirt"))
    response = client.get("/api/guide")
    assert response.status_code == 200
    assert "Offline chart-generator." in response.json()["content"]


@pytest.mark.parametrize("spec", ["paydirt.spec", "paydirt_dir.spec", "paydirt_onefile.spec", "__main__.spec"])
def test_packaging_includes_markdown_guides_and_images(spec: str) -> None:
    root = Path(__file__).resolve().parents[3]
    tree = ast.parse((root / spec).read_text())
    data = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "datas" for t in node.targets) or isinstance(node, ast.keyword) and node.arg == "datas" and isinstance(node.value, ast.List):
            data.extend(ast.literal_eval(node.value))
    assert ("docs/*.md", "docs") in data
    assert ("docs/images", "docs/images") in data


def test_player_guide_includes_priority_reference_and_examples() -> None:
    response = client.get("/api/guide")
    assert response.status_code == 200
    content = response.json()["content"]
    assert "# Priority Chart Reference" in content
    assert "[Priority Chart Reference](#priority-chart-reference)" in content
    assert "## Worked Priority Examples" in content
    assert "BLACK" in content


def test_player_priority_chart_preserves_source_ascii_reference() -> None:
    root = Path(__file__).resolve().parents[3]
    source = ast.get_docstring(ast.parse((root / "paydirt/priority_chart.py").read_text()))
    chart = "\n".join(
        line.removeprefix("# ")
        for line in source.split("# Priority Chart Reference:\n", 1)[1].splitlines()
    )
    content = client.get("/api/guide").json()["content"]
    assert f"```text\n{chart}\n```" in content
