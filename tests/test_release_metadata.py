"""Keep release version metadata consistent across packages and installers."""

import ast
import json
from pathlib import Path
import re
import subprocess

import pytest

from paydirt import __version__


ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "path, pattern",
    [
        ("pyproject.toml", r'^version = "([^"]+)"'),
        ("packaging/windows/installer.nsi", r'^!define PRODUCT_VERSION "([^"]+)"'),
        ("packaging/macos/create_app.sh", r'^VERSION="[$][{]GITHUB_REF_NAME:-([^}]+)[}]"'),
        ("packaging/linux/create_appimage.sh", r'^VERSION="[$][{]GITHUB_REF_NAME:-([^}]+)[}]"'),
    ],
)
def test_package_and_installer_versions_match(path: str, pattern: str) -> None:
    """Local build defaults and installer versions must match the Python package."""
    match = re.search(pattern, (ROOT / path).read_text(), re.MULTILINE)
    assert match is not None, f"Version metadata missing from {path}"
    assert match.group(1) == __version__


def test_frontend_versions_match() -> None:
    """The frontend manifest and both root lockfile versions must agree."""
    frontend = ROOT / "paydirt-web" / "frontend"
    manifest = json.loads((frontend / "package.json").read_text())
    lock = json.loads((frontend / "package-lock.json").read_text())
    assert manifest["version"] == __version__
    assert lock["version"] == __version__
    assert lock["packages"][""]["version"] == __version__


@pytest.mark.parametrize("path", ["paydirt/__main__.py", "paydirt-web/backend/main.py"])
def test_api_versions_match(path: str) -> None:
    """Check both FastAPI entry points without importing optional web dependencies."""
    tree = ast.parse((ROOT / path).read_text())
    versions = [
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FastAPI"
        for keyword in node.keywords
        if keyword.arg == "version" and isinstance(keyword.value, ast.Constant)
    ]
    assert versions == [__version__]


@pytest.mark.parametrize("prefix", ["", "v"])
def test_macos_bundle_version_strips_tag_prefix(prefix: str) -> None:
    """The macOS bundle version must be numeric, even when built from a v-prefixed tag."""
    script = (ROOT / "packaging/macos/create_app.sh").read_text()
    assignments = "\n".join(line for line in script.splitlines() if line.startswith("VERSION="))
    result = subprocess.run(
        ["bash", "-c", assignments + '\nprintf "%s" "$VERSION"'],
        env={"GITHUB_REF_NAME": prefix + __version__},
        capture_output=True, text=True, check=True,
    )
    assert result.stdout == __version__
