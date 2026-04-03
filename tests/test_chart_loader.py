"""
Tests for chart_loader.py functions.
"""

import tempfile
import shutil
from pathlib import Path

import pytest

from paydirt.chart_loader import find_team_charts


class TestFindTeamCharts:
    """Tests for find_team_charts() function."""

    @pytest.fixture
    def temp_seasons_dir(self):
        """Create a temporary seasons directory structure for testing."""
        temp_dir = tempfile.mkdtemp()
        seasons_path = Path(temp_dir)

        yield seasons_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def _create_team(self, seasons_path: Path, year: str, team_name: str):
        """Helper to create a valid team directory with required CSV files."""
        team_dir = seasons_path / year / team_name
        team_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal required CSV files
        (team_dir / "offense.csv").write_text("header\ndata\n")
        (team_dir / "defense.csv").write_text("header\ndata\n")
        (team_dir / "special.csv").write_text("header\ndata\n")

    def test_finds_valid_numeric_season(self, temp_seasons_dir):
        """Should find teams in directories with numeric year names."""
        self._create_team(temp_seasons_dir, "2026", "Ironclads")

        charts = find_team_charts(str(temp_seasons_dir))

        assert len(charts) == 1
        assert charts[0][0] == "2026"
        assert charts[0][1] == "Ironclads"

    def test_excludes_non_numeric_directory(self, temp_seasons_dir):
        """Should exclude directories that don't have numeric names."""
        # Create a valid numeric season
        self._create_team(temp_seasons_dir, "2026", "Ironclads")

        # Create non-numeric directories that should be excluded
        self._create_team(temp_seasons_dir, "samples", "TestTeam")
        self._create_team(temp_seasons_dir, "notes", "AnotherTeam")
        self._create_team(temp_seasons_dir, "backup", "BackupTeam")

        charts = find_team_charts(str(temp_seasons_dir))

        # Should only find the 2026 team
        assert len(charts) == 1
        assert charts[0][0] == "2026"
        assert charts[0][1] == "Ironclads"

    def test_excludes_hidden_directories(self, temp_seasons_dir):
        """Should exclude hidden directories (starting with dot)."""
        self._create_team(temp_seasons_dir, "2026", "Ironclads")
        self._create_team(temp_seasons_dir, ".hidden", "HiddenTeam")

        charts = find_team_charts(str(temp_seasons_dir))

        assert len(charts) == 1
        assert charts[0][0] == "2026"

    def test_finds_multiple_seasons(self, temp_seasons_dir):
        """Should find teams across multiple valid seasons."""
        self._create_team(temp_seasons_dir, "1983", "Bears")
        self._create_team(temp_seasons_dir, "2026", "Ironclads")
        self._create_team(temp_seasons_dir, "2026", "Thunderhawks")

        charts = find_team_charts(str(temp_seasons_dir))

        assert len(charts) == 3
        years = [c[0] for c in charts]
        assert "1983" in years
        assert "2026" in years

    def test_returns_empty_for_nonexistent_path(self):
        """Should return empty list if seasons directory doesn't exist."""
        charts = find_team_charts("/nonexistent/path/to/seasons")

        assert charts == []

    def test_excludes_teams_missing_required_files(self, temp_seasons_dir):
        """Should exclude team directories missing required CSV files."""
        # Create a complete team
        self._create_team(temp_seasons_dir, "2026", "Ironclads")

        # Create an incomplete team (missing defense.csv)
        incomplete_dir = temp_seasons_dir / "2026" / "IncompleteTeam"
        incomplete_dir.mkdir(parents=True, exist_ok=True)
        (incomplete_dir / "offense.csv").write_text("header\n")
        (incomplete_dir / "special.csv").write_text("header\n")
        # defense.csv is missing

        charts = find_team_charts(str(temp_seasons_dir))

        assert len(charts) == 1
        assert charts[0][1] == "Ironclads"

    def test_results_are_sorted(self, temp_seasons_dir):
        """Should return results in sorted order."""
        self._create_team(temp_seasons_dir, "2026", "Zebras")
        self._create_team(temp_seasons_dir, "2026", "Aardvarks")
        self._create_team(temp_seasons_dir, "1983", "Bears")

        charts = find_team_charts(str(temp_seasons_dir))

        # Should be sorted by (year, team_name)
        assert charts[0] == ("1983", "Bears", str(temp_seasons_dir / "1983" / "Bears"))
        assert charts[1][1] == "Aardvarks"
        assert charts[2][1] == "Zebras"
