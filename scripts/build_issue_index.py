#!/usr/bin/env python3
"""Generate docs/dev-notes/issue-tracker.md from the per-issue files.

The index is derived data: every issue lives in its own file under
docs/dev-notes/issues/<PREFIX>/<ID>.md and this script renders the status view.
tests/test_issue_tracker.py fails when the committed index is stale.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "docs" / "dev-notes" / "issues"
INDEX = ROOT / "docs" / "dev-notes" / "issue-tracker.md"
STATUS_ORDER = ("open", "resolved", "closed")
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
STATUS_HEADINGS = {
    "open": ("Open", "Confirmed work remains, or an observation whose cause is not yet established."),
    "resolved": (
        "Resolved (awaiting play-test confirmation)",
        "A fix is committed with tests. A play-test audit must confirm it before the issue is closed.",
    ),
    "closed": ("Closed", "A play-test audit confirmed the issue no longer occurs."),
}


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
        "*Generated from [`issues/`](issues/) by `python3 scripts/build_issue_index.py`; do not edit by hand.*",
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
            "| ID | Priority | Title | Dates | Links |",
            "|----|----------|-------|-------|-------|",
        ]
        for issue in group:
            dates = f"created {issue.get('created-at') or '—'}"
            if issue.get("resolved-at"):
                dates += f", resolved {issue['resolved-at']}"
            if issue.get("closed-at"):
                dates += f", closed {issue['closed-at']}"
            links = ", ".join(str(link).split(":", 1)[0].strip() for link in issue.get("links", []))
            lines.append(
                f"| [{issue['id']}]({issue['path']}) | {issue.get('priority')} | {issue.get('title')} "
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
