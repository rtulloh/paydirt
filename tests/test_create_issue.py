"""Synthetic issue authoring and release scheduling regressions."""

from pathlib import Path

import pytest

from scripts import build_issue_index as index
from scripts import create_issue as author


@pytest.fixture
def issue_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(index, "ROOT", tmp_path)
    monkeypatch.setattr(index, "ISSUES", tmp_path / "issues")
    monkeypatch.setattr(index, "INDEX", tmp_path / "issue-tracker.md")
    return tmp_path


def test_legacy_authoring_control(issue_store: Path) -> None:
    path = author.create_issue("TEST", "Synthetic control", "Description", ["Verify"])
    assert path.is_file()
    assert "[TEST-001]" in index.INDEX.read_text()


def create_ticket(**kwargs: object) -> Path:
    return author.create_issue("TEST", "Synthetic issue", "A synthetic description",
                               ["Verify the behavior"], **kwargs)


@pytest.mark.parametrize("release", ["v1.10.5", "v1.0.0-beta.71", "v2.0.0-rc.1+build.42"])
def test_api_records_target_release_and_schedules_in_index(
    issue_store: Path, release: str,
) -> None:
    path = create_ticket(target_release=release)
    assert index.read_front_matter(path)["target-release"] == release
    rendered = index.INDEX.read_text()
    assert "| Target release |" in rendered
    assert f"| {release} |" in rendered


def test_cli_propagates_explicit_target_release(
    issue_store: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.argv", [
        "create_issue.py", "--prefix", "TEST", "--title", "Synthetic issue",
        "--description", "Synthetic description", "--acceptance", "Verify",
        "--target-release", "v1.10.5",
    ])
    author.main()
    path = issue_store / "issues/TEST/TEST-001.md"
    assert index.read_front_matter(path)["target-release"] == "v1.10.5"
    assert "| v1.10.5 |" in index.INDEX.read_text()


@pytest.mark.parametrize("release", [
    "1.10.5", "v1.10", "v01.10.5", "v1.10.5-01", "v1.10.5-",
    "v1.10.5+", "v1.10.5-rc..1", "v1.10.5\nstatus: closed",
    " ", "Bowl Bound milestone 2", 5, False, ["v1.10.5"],
])
def test_invalid_api_target_fails_before_any_write(issue_store: Path, release: object) -> None:
    with pytest.raises(ValueError, match="target.release"):
        create_ticket(target_release=release)
    assert list(issue_store.iterdir()) == []


def test_invalid_cli_target_fails_before_any_write(
    issue_store: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", [
        "create_issue.py", "--prefix", "TEST", "--title", "Synthetic issue",
        "--description", "Synthetic description", "--acceptance", "Verify",
        "--target-release", "milestone-2",
    ])
    with pytest.raises(SystemExit) as error:
        author.main()
    assert error.value.code == 1
    assert "target-release" in capsys.readouterr().err
    assert list(issue_store.iterdir()) == []


def test_omitted_target_and_legacy_ticket_keep_working(issue_store: Path) -> None:
    path = create_ticket()
    assert not index.read_front_matter(path).get("target-release")
    legacy = path.read_text().replace("target-release:\n", "")
    path.write_text(legacy)
    assert "target-release" not in index.read_front_matter(path)
    rendered = index.render_index(index.ISSUES)
    assert "| Target release |" in rendered
    assert "| — |" in rendered


def test_index_rejects_invalid_imported_release_before_overwriting(
    issue_store: Path,
) -> None:
    path = create_ticket()
    previous = index.INDEX.read_text()
    text = path.read_text().replace("target-release:\n", "target-release: milestone-2\n")
    path.write_text(text)
    with pytest.raises(ValueError, match="target.release"):
        index.main()
    assert index.INDEX.read_text() == previous


@pytest.mark.parametrize("entry", ["api", "cli"])
def test_explicit_empty_target_serializes_as_unscheduled(
    issue_store: Path, monkeypatch: pytest.MonkeyPatch, entry: str,
) -> None:
    if entry == "api":
        path = create_ticket(target_release="")
    else:
        monkeypatch.setattr("sys.argv", [
            "create_issue.py", "--prefix", "TEST", "--title", "Synthetic issue",
            "--description", "Description", "--acceptance", "Verify",
            "--target-release", "",
        ])
        author.main()
        path = issue_store / "issues/TEST/TEST-001.md"
    assert "target-release:\n" in path.read_text()
    assert index.read_front_matter(path)["target-release"] == ""
    assert "| — |" in index.INDEX.read_text()
