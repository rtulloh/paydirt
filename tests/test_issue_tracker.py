"""The issue tracker is a directory of per-issue files with a generated index.

Each issue lives in docs/dev-notes/issues/<PREFIX>/<ID>.md with YAML front
matter (id, title, status, priority, dates, links, commits) followed by
Description, Resolution / verification and Comments sections. The index
docs/dev-notes/issue-tracker.md is generated from those files, so it can never
drift from them. Status model: open -> resolved (fix committed with tests) ->
closed (a play-test audit confirmed the issue no longer occurs).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

ISSUES = Path(__file__).resolve().parents[1] / "docs" / "dev-notes" / "issues"
INDEX = Path(__file__).resolve().parents[1] / "docs" / "dev-notes" / "issue-tracker.md"
ID_PATTERN = re.compile(r"^(?P<prefix>[A-Z]+)-(?P<number>\d{3})$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMENT_SEPARATOR = re.compile(r"^--- \d{4}-\d{2}-\d{2} \d{2}:\d{2} ---$")
STATUSES = ("open", "resolved", "closed")
PRIORITIES = ("High", "Medium", "Low")
SECTIONS = ("## Description", "## Resolution / verification", "## Comments")


def issue_files() -> list[Path]:
    return sorted(ISSUES.glob("*/*.md"))


def parse_issue(path: Path) -> tuple[dict, str]:
    """Split an issue file into its front matter and body (no YAML dependency)."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: must open with YAML front matter"
    _, front, body = text.split("---\n", 2)
    fields: dict[str, object] = {}
    key = None
    for line in front.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            assert key, f"{path.name}: list item before any field"
            if not isinstance(fields.get(key), list):
                assert not fields.get(key), f"{path.name}: {key} mixes an inline value and a list"
                fields[key] = []  # "key:" with no inline value opens a list
            fields[key].append(line[4:].strip())
            continue
        assert ":" in line, f"{path.name}: unparsable front-matter line {line!r}"
        key, _, value = line.partition(":")
        key = key.strip()
        assert key not in fields, f"{path.name}: duplicate field {key}"
        fields[key] = value.strip()
    return fields, body


def all_ids() -> set[str]:
    return {path.stem for path in issue_files()}


def test_the_issue_directory_exists_and_is_populated() -> None:
    assert ISSUES.is_dir(), "docs/dev-notes/issues must exist"
    assert len(issue_files()) >= 80, "every tracker row must have become an issue file"
    assert (ISSUES / "README.md").is_file(), "conventions and work order live in issues/README.md"


@pytest.mark.parametrize("path", issue_files(), ids=lambda p: p.stem)
def test_issue_file_is_well_formed(path: Path) -> None:
    fields, body = parse_issue(path)
    match = ID_PATTERN.match(path.stem)
    assert match, f"{path.name}: file name must be <PREFIX>-<NNN>.md"
    assert fields.get("id") == path.stem, "the id field must match the file name"
    assert path.parent.name == match.group("prefix"), "issues are filed in a folder per prefix"

    assert fields.get("title"), "every issue needs a one-line title"
    assert len(str(fields["title"])) <= 120, "keep the title to one line"
    assert fields.get("status") in STATUSES, f"status must be one of {STATUSES}"
    assert fields.get("priority") in PRIORITIES, f"priority must be one of {PRIORITIES}"

    for key in ("created-at", "resolved-at", "closed-at"):
        assert key in fields, f"{path.name}: {key} must be present (empty when not reached)"
        value = str(fields[key])
        if value:
            assert DATE_PATTERN.match(value), f"{key} must be ISO yyyy-mm-dd"
            assert value <= date.today().isoformat(), f"{key} must not be in the future"

    status = fields["status"]
    if status in ("resolved", "closed"):
        assert fields["resolved-at"], "a resolved issue records when the fix landed"
    else:
        assert not fields["resolved-at"], "an open issue has no resolved-at"
    if status == "closed":
        assert fields["closed-at"], "a closed issue records when a play-test confirmed it"
        assert str(fields["closed-at"]) >= str(fields["resolved-at"]), "closed-at follows resolved-at"
    else:
        assert not fields["closed-at"], "only a closed issue has closed-at"
    assert str(fields["created-at"]) <= (str(fields["resolved-at"]) or "9999-12-31")

    for section in SECTIONS:
        assert f"\n{section}\n" in f"\n{body}", f"{path.name}: missing section {section}"
    description = body.split("## Description", 1)[1].split("##", 1)[0].strip()
    assert description, "every issue needs a description"


@pytest.mark.parametrize("path", issue_files(), ids=lambda p: p.stem)
def test_links_and_comments(path: Path) -> None:
    fields, body = parse_issue(path)
    known = all_ids()
    for link in fields.get("links", []):
        target = link.split(":", 1)[0].strip()
        assert target in known, f"{path.name}: links to unknown issue {target}"
        assert target != path.stem, f"{path.name}: must not link to itself"
    for commit in fields.get("commits", []):
        assert re.match(r"^[0-9a-f]{7,40}$", commit.strip()), f"{path.name}: {commit!r} is not a commit"
    comments = body.split("## Comments", 1)[1]
    for line in comments.splitlines():
        if line.startswith("---"):
            assert COMMENT_SEPARATOR.match(line), (
                f"{path.name}: comment separators are '--- yyyy-mm-dd HH:MM ---', got {line!r}"
            )
    if comments.strip():
        assert comments.strip().startswith("--- "), "comments start with a timestamped separator"


def test_links_are_symmetric() -> None:
    linked: dict[str, set[str]] = {}
    for path in issue_files():
        fields, _ = parse_issue(path)
        linked[path.stem] = {link.split(":", 1)[0].strip() for link in fields.get("links", [])}
    for issue, targets in linked.items():
        for target in targets:
            assert issue in linked[target], f"{target} must link back to {issue}"


def test_index_is_generated_from_the_issue_files() -> None:
    from scripts.build_issue_index import render_index

    assert INDEX.read_text(encoding="utf-8") == render_index(ISSUES), (
        "docs/dev-notes/issue-tracker.md is generated: run python3 scripts/build_issue_index.py"
    )


def test_index_lists_every_issue_with_its_status() -> None:
    index = INDEX.read_text(encoding="utf-8")
    for path in issue_files():
        fields, _ = parse_issue(path)
        assert f"[{path.stem}]" in index, f"{path.stem} is missing from the index"
        assert str(fields["title"]) in index, f"{path.stem}'s title is missing from the index"
