#!/usr/bin/env python3
"""Generate docs/dev-notes/issue-tracker.md from the per-issue files.

The index is derived data: every issue lives in its own file under
docs/dev-notes/issues/<PREFIX>/<ID>.md and this script renders the status view.
tests/test_issue_tracker.py fails when the committed index is stale.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "docs" / "dev-notes" / "issues"
INDEX = ROOT / "docs" / "dev-notes" / "issue-tracker.md"
STATUS_ORDER = ("open", "resolved", "closed")
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
PRIORITIES = ("High", "Medium", "Low")
STATUSES = ("open", "resolved", "closed")

TARGET_RELEASE_PATTERN = re.compile(
    r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def validate_target_release(value: object) -> None:
    """Accept an empty target or a v-prefixed semantic release version."""
    if value is None or value == "":
        return
    match = TARGET_RELEASE_PATTERN.fullmatch(value) if isinstance(value, str) else None
    if match is not None:
        prerelease = match.group("prerelease")
        if not prerelease or all(
            not (part.isdigit() and len(part) > 1 and part.startswith("0"))
            for part in prerelease.split(".")
        ):
            return
    raise ValueError("target-release must be empty or a v-prefixed semantic version, e.g. v1.10.5")


def _day(value: object) -> date | None:
    """Parse an ISO yyyy-mm-dd date; empty and None mean 'not reached yet'."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"not a date: {value!r}")
    text = value.strip()
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError(f"date must be ISO yyyy-mm-dd: {value!r}")
    return parsed
STATUS_HEADINGS = {
    "open": ("Open", "Confirmed work remains, or an observation whose cause is not yet established."),
    "resolved": (
        "Resolved (awaiting play-test confirmation)",
        "A fix is committed with tests. A play-test audit must confirm it before the issue is closed.",
    ),
    "closed": ("Closed", "A play-test audit confirmed the issue no longer occurs."),
}

def _validate(fields: dict[str, Any], text: str, path: Path) -> None:
    issue_id = fields.get("id", "")
    if not isinstance(issue_id, str) or not re.fullmatch(r"[A-Z]+-\d{3}", issue_id):
        raise ValueError(f"{path}: invalid issue ID")
    if path.stem != issue_id or path.parent.name != issue_id.split("-")[0]:
        raise ValueError(f"{path}: ID must match filename and prefix directory")
    title = fields.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 120 or "\n" in title:
        raise ValueError(f"{path}: title must be one line of 1..120 characters")
    validate_target_release(fields.get("target-release"))
    status = fields.get("status")
    if status not in STATUSES or fields.get("priority") not in PRIORITIES:
        raise ValueError(f"{path}: invalid status or priority")
    try:
        created, resolved, closed = (
            _day(fields.get(key)) for key in ("created-at", "resolved-at", "closed-at")
        )
    except ValueError as error:
        raise ValueError(f"{path}: invalid ticket date") from error
    if (
        created is None
        or (resolved and resolved < created)
        or (closed and closed < (resolved or created))
    ):
        raise ValueError(f"{path}: missing or out-of-order dates")
    if (
        (status == "open" and (resolved or closed))
        or (status == "resolved" and (not resolved or closed))
        or (status == "closed" and not closed)
    ):
        raise ValueError(f"{path}: dates do not match status")
    for key in ("tags", "links", "commits"):
        values = fields.get(key) or []
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f"{path}: {key} must be a list of strings")
        fields[key] = values
    if status in {"resolved", "closed"} and resolved and not fields["commits"]:
        raise ValueError(f"{path}: resolved fix requires a commit reference")
    if status == "closed" and "Play-test confirmation:" not in text:
        exceptions = {"duplicate", "re-scoped", "wont-fix"}
        if not exceptions.intersection(fields["tags"]):
            raise ValueError(f"{path}: closure requires play-test confirmation")
    for heading in ("Description", "Resolution / verification", "Comments"):
        if f"## {heading}\n" not in text:
            raise ValueError(f"{path}: missing {heading} section")


def read_front_matter(path: Path) -> dict:
    """Parse the simple key/value + list front matter used by the issue files."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    _, front, _ = text.split("---\n", 2)
    fields: dict[str, object] = {}
    key = None
    for line in front.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            if not isinstance(fields.get(key), list):
                fields[key] = []  # "key:" with no inline value opens a list
            fields[key].append(line[4:].strip())
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        fields[key] = value.strip()
    validate_target_release(fields.get("target-release"))
    return fields


def load_issues(issues_dir: Path) -> list[dict]:
    issues = []
    for path in sorted(issues_dir.glob("*/*.md")):
        fields = read_front_matter(path)
        fields["path"] = path.relative_to(issues_dir.parent).as_posix()
        issues.append(fields)
    return issues


def _sort_key(issue: dict) -> tuple:
    prefix, _, number = str(issue["id"]).partition("-")
    return (PRIORITY_ORDER.get(str(issue.get("priority")), 9), prefix, int(number))


def render_index(issues_dir: Path) -> str:
    issues = load_issues(issues_dir)
    counts = ", ".join(
        f"{sum(1 for issue in issues if issue.get('status') == status)} {status}"
        for status in STATUS_ORDER
    )
    lines = [
        "# Developer Issue Tracker",
        "",
        "**Developer-only working record, not a player guide or a release promise.**",
        "",
        "*Generated from [`issues/`](issues/README.md) by `python3 scripts/build_issue_index.py`; do not edit by hand.*",
        "Open an issue's own file for its description, verification and comments.",
        "See the [conventions and work order](issues/README.md) and the",
        "[developer-note disclaimer](README.md).",
        "",
        f"{len(issues)} issues: {counts}.",
    ]
    for status in STATUS_ORDER:
        group = sorted((i for i in issues if i.get("status") == status), key=_sort_key)
        heading, blurb = STATUS_HEADINGS[status]
        lines += ["", f"## {heading} ({len(group)})", "", blurb, ""]
        if not group:
            lines += ["None.", ""]
            continue
        lines += [
            "| ID | Priority | Target release | Title | Dates | Links |",
            "|----|----------|----------------|-------|-------|-------|",
        ]
        for issue in group:
            dates = f"created {issue.get('created-at') or '—'}"
            if issue.get("resolved-at"):
                dates += f", resolved {issue['resolved-at']}"
            if issue.get("closed-at"):
                dates += f", closed {issue['closed-at']}"
            links = ", ".join(str(link).split(":", 1)[0].strip() for link in issue.get("links", []))
            lines.append(
                f"| [{issue['id']}]({issue['path']}) | {issue.get('priority')} "
                f"| {issue.get('target-release') or '—'} | {issue.get('title')} "
                f"| {dates} | {links or '—'} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    INDEX.write_text(render_index(ISSUES), encoding="utf-8")
    print(f"Wrote {INDEX.relative_to(ROOT)} from {len(load_issues(ISSUES))} issue files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
