"""Create a public-safe repository-local ticket and regenerate its index."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

if __package__:
    from . import build_issue_index as index
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_issue_index as index


class _FrontMatterDumper(yaml.SafeDumper):
    """SafeDumper that serializes None as an empty scalar (like 'resolved-at:')."""


def _represent_empty_none(dumper: yaml.SafeDumper, _value: None):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


_FrontMatterDumper.add_representer(type(None), _represent_empty_none)


def _represent_sequence(dumper: yaml.SafeDumper, data: list):
    """Dump empty lists as a bare 'key:' to match the tracker's line-based parser."""
    if not data:
        return dumper.represent_scalar("tag:yaml.org,2002:seq", "")
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data)


_FrontMatterDumper.add_representer(list, _represent_sequence)


def create_issue(
    prefix: str,
    title: str,
    description: str,
    acceptance: list[str],
    *,
    priority: str = "Medium",
    tags: list[str] | None = None,
    target_release: str | None = None,
) -> Path:
    """Validate and exclusively create the next ticket; never discard on index failure."""
    if not re.fullmatch(r"[A-Z]{2,12}", prefix):
        raise ValueError("prefix must contain 2..12 uppercase letters")
    if not description.strip() or not acceptance or any(not item.strip() for item in acceptance):
        raise ValueError("description and at least one nonempty acceptance criterion are required")
    folder = index.ISSUES / prefix
    if any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ValueError("ticket destination must not use symlinks")
    fields = {
        "id": prefix + "-001",
        "title": title,
        "status": "open",
        "priority": priority,
        "target-release": target_release,
        "created-at": date.today(),
        "resolved-at": None,
        "closed-at": None,
        "tags": tags or [],
        "links": [],
        "commits": [],
    }
    body = (
        "\n## Description\n\n"
        + description.strip()
        + "\n\n## Resolution / verification\n\n"
        + "\n".join("- " + item.strip() for item in acceptance)
        + "\n\n## Comments\n\n--- "
        + date.today().isoformat()
        + " 00:00 ---\n"
        + "Created with scripts/create_issue.py. Keep evidence public-safe.\n"
    )
    index._validate(fields, body, folder / (prefix + "-001.md"))
    if fields["target-release"] == "":
        fields["target-release"] = None
    existing = [int(p.stem.split("-")[-1]) for p in folder.glob(prefix + "-[0-9][0-9][0-9].md")]
    registry = index.ISSUES / "retired-ids.yaml"
    if registry.exists():
        try:
            retired = yaml.safe_load(registry.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ValueError("invalid retired issue-ID registry YAML") from error
        if not isinstance(retired, dict) or not all(
            isinstance(old, str)
            and isinstance(new, str)
            and re.fullmatch(r"[A-Z]+-\d{3}", old)
            and re.fullmatch(r"[A-Z]+-\d{3}", new)
            for old, new in retired.items()
        ):
            raise ValueError("retired issue-ID registry must map old IDs to canonical IDs")
        existing.extend(
            int(old.rsplit("-", 1)[1]) for old in retired if old.startswith(prefix + "-")
        )
    number = max(existing, default=0) + 1
    folder.mkdir(parents=True, exist_ok=True)
    while number <= 999:
        fields["id"] = f"{prefix}-{number:03d}"
        path = folder / (fields["id"] + ".md")
        text = (
            "---\n" + yaml.dump(fields, Dumper=_FrontMatterDumper, sort_keys=False, allow_unicode=True, indent=2) + "---\n" + body
        )
        try:
            with path.open("x", encoding="utf-8") as output:
                output.write(text)
            break
        except FileExistsError:
            number += 1
    else:
        raise ValueError("no three-digit ticket IDs remain for this prefix")
    try:
        rendered = index.render_index(index.ISSUES)
        index.INDEX.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise RuntimeError(f"Created {path}; index regeneration failed: {error}") from error
    return path


def main() -> None:
    """Run independently of OpenCode, an API server or the caller's current folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--acceptance", action="append", required=True)
    parser.add_argument("--priority", choices=index.PRIORITIES, default="Medium")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--target-release", help="Optional release target, for example v1.10.5")
    args = parser.parse_args()
    try:
        path = create_issue(
            args.prefix,
            args.title,
            args.description,
            args.acceptance,
            priority=args.priority,
            tags=args.tag,
            target_release=args.target_release,
        )
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(path)


if __name__ == "__main__":
    main()
