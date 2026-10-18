"""Keep the documentation's local links and heading fragments navigable."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def prose_lines(text: str) -> list[str]:
    lines = []
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^\s*(\x60{3,}|~{3,})", line)
        if marker:
            run = marker.group(1)
            if not fence:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = ""
            continue
        if not fence:
            lines.append(line)
    return lines


def test_documentation_local_links_and_fragments() -> None:
    pages = [ROOT / "README.md", ROOT / "paydirt-web/README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    errors = []
    for page in pages:
        for line in prose_lines(page.read_text()):
            for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", line):
                if ":" in target or target.startswith("/"):
                    continue
                path, _, fragment = target.partition("#")
                destination = page.parent / path if path else page
                if not destination.is_file():
                    errors.append(f"{page.relative_to(ROOT)}: missing {target}")
                    continue
                if fragment and destination.suffix == ".md":
                    anchors = set()
                    for heading in prose_lines(destination.read_text()):
                        match = re.match(r"^#{1,6} (.+?)(?: +#+)?$", heading)
                        if match:
                            slug = re.sub(r"[^\w -]", "", match.group(1).lower()).replace(" ", "-")
                            anchor = slug
                            suffix = 1
                            while anchor in anchors:
                                anchor = f"{slug}-{suffix}"
                                suffix += 1
                            anchors.add(anchor)
                    if fragment not in anchors:
                        errors.append(f"{page.relative_to(ROOT)}: missing fragment {target}")
    assert not errors, "\n".join(errors)
