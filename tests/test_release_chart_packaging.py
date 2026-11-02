"""Verify release builds publish generated charts with their attribution."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_FILES = (
    "paydirt.spec",
    "paydirt_dir.spec",
    "paydirt_onefile.spec",
    "__main__.spec",
)


def test_pyinstaller_specs_bundle_public_seasons_and_chart_attribution() -> None:
    """Every supported PyInstaller entry point includes the same public chart data."""
    for relative_path in SPEC_FILES:
        text = (ROOT / relative_path).read_text()
        assert "('seasons/1983-generated', 'seasons/1983')" in text, relative_path
        assert "('seasons/2024', 'seasons/2024')" in text, relative_path
        assert "('seasons/2026', 'seasons/2026')" in text, relative_path
        assert "CHART_ATTRIBUTION.md" in text, relative_path


def test_platform_packages_expose_chart_attribution() -> None:
    """Installed applications leave the chart source notice available to players."""
    package_files = (
        "packaging/macos/create_app.sh",
        "packaging/linux/create_appimage.sh",
        "packaging/windows/installer.nsi",
    )
    for relative_path in package_files:
        text = (ROOT / relative_path).read_text()
        assert "CHART_ATTRIBUTION.md" in text, relative_path


def test_public_generated_seasons_are_not_ignored() -> None:
    """Generated release data is tracked while original and intermediate charts stay private."""
    ignore_text = (ROOT / ".gitignore").read_text()
    assert "seasons/1983-generated/" not in ignore_text
    assert "seasons/2024/" not in ignore_text
    assert "seasons/1983/" in ignore_text
    assert "seasons/1983-pbp-joint-final/" in ignore_text


def test_chart_attribution_describes_generated_sources_and_license() -> None:
    """The distributed notice identifies both data sources and the chart license."""
    text = (ROOT / "CHART_ATTRIBUTION.md").read_text()
    assert "independent statistical reconstructions" in text
    assert "Pro Football Reference" in text
    assert "nflverse" in text
    assert "CC BY 4.0" in text
    assert "MIT License" in text
    assert "No original Paydirt team charts" in text

    in_app_notice = (ROOT / "docs/seasons.md").read_text()
    assert "archived Pro Football Reference" in in_app_notice
    assert "nflverse play-by-play is provided under CC BY 4.0" in in_app_notice
