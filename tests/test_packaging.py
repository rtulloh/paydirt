"""
Tests for packaging.py functions.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.packaging import (
    is_bundled,
    get_user_data_path,
    get_user_seasons_path,
    get_builtin_seasons_path,
    get_seasons_path,
    get_all_season_paths,
    get_season_path,
    get_team_path,
)


class TestIsBundled:
    """Tests for is_bundled() function."""

    def test_not_bundled_in_development(self):
        """Should return False when not running as PyInstaller bundle."""
        # In normal test environment, we're not bundled
        assert is_bundled() is False

    def test_bundled_when_frozen_and_meipass(self):
        """Should return True when sys.frozen and sys._MEIPASS are set."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True):
                assert is_bundled() is True

    def test_not_bundled_when_frozen_without_meipass(self):
        """Should return False when frozen but no _MEIPASS (e.g., cx_Freeze)."""
        with patch.object(sys, "frozen", True, create=True):
            # Make sure _MEIPASS doesn't exist
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
            assert is_bundled() is False


class TestGetUserDataPath:
    """Tests for get_user_data_path() function."""

    def test_returns_none_in_development(self):
        """Should return None when not running as bundled app."""
        # In development mode (not bundled), should return None
        assert get_user_data_path() is None

    @patch("paydirt.packaging.is_bundled")
    def test_macos_path(self, mock_bundled, tmp_path):
        """Should return Application Support path on macOS."""
        mock_bundled.return_value = True

        with patch.object(sys, "platform", "darwin"):
            with patch.object(Path, "home", return_value=tmp_path):
                result = get_user_data_path()
                expected = tmp_path / "Library" / "Application Support" / "Paydirt"
                assert result == expected
                assert result.exists()  # Directory should be created

    @patch("paydirt.packaging.is_bundled")
    def test_windows_path_with_localappdata(self, mock_bundled, tmp_path):
        """Should use LOCALAPPDATA environment variable on Windows."""
        mock_bundled.return_value = True

        with patch.object(sys, "platform", "win32"):
            with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}):
                result = get_user_data_path()
                expected = tmp_path / "Paydirt"
                assert result == expected
                assert result.exists()

    @patch("paydirt.packaging.is_bundled")
    def test_windows_path_fallback(self, mock_bundled, tmp_path):
        """Should fall back to AppData/Local on Windows without LOCALAPPDATA."""
        mock_bundled.return_value = True

        with patch.object(sys, "platform", "win32"):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Path, "home", return_value=tmp_path):
                    result = get_user_data_path()
                    expected = tmp_path / "AppData" / "Local" / "Paydirt"
                    assert result == expected

    @patch("paydirt.packaging.is_bundled")
    def test_linux_path_with_xdg(self, mock_bundled, tmp_path):
        """Should use XDG_DATA_HOME on Linux when set."""
        mock_bundled.return_value = True

        with patch.object(sys, "platform", "linux"):
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
                result = get_user_data_path()
                expected = tmp_path / "Paydirt"
                assert result == expected
                assert result.exists()

    @patch("paydirt.packaging.is_bundled")
    def test_linux_path_fallback(self, mock_bundled, tmp_path):
        """Should fall back to ~/.local/share on Linux without XDG_DATA_HOME."""
        mock_bundled.return_value = True

        with patch.object(sys, "platform", "linux"):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Path, "home", return_value=tmp_path):
                    result = get_user_data_path()
                    expected = tmp_path / ".local" / "share" / "Paydirt"
                    assert result == expected


class TestGetUserSeasonsPath:
    """Tests for get_user_seasons_path() function."""

    def test_returns_none_in_development(self):
        """Should return None when not running as bundled app."""
        assert get_user_seasons_path() is None

    @patch("paydirt.packaging.get_user_data_path")
    def test_returns_seasons_subdirectory(self, mock_user_data, tmp_path):
        """Should return seasons/ subdirectory of user data path."""
        mock_user_data.return_value = tmp_path

        result = get_user_seasons_path()
        expected = tmp_path / "seasons"
        assert result == expected

    @patch("paydirt.packaging.get_user_data_path")
    def test_returns_none_when_user_data_none(self, mock_user_data):
        """Should return None when get_user_data_path returns None."""
        mock_user_data.return_value = None

        result = get_user_seasons_path()
        assert result is None


class TestGetBuiltinSeasonsPath:
    """Tests for get_builtin_seasons_path() function."""

    def test_development_path(self):
        """Should return repo seasons/ directory in development mode."""
        result = get_builtin_seasons_path()
        # In development, should be relative to the paydirt package
        assert result.name == "seasons"
        assert result.exists()

    @patch("paydirt.packaging.is_bundled")
    def test_bundled_path(self, mock_bundled):
        """Should return _MEIPASS/seasons when bundled."""
        mock_bundled.return_value = True

        with patch.object(sys, "_MEIPASS", "/tmp/fake_meipass", create=True):
            result = get_builtin_seasons_path()
            assert result == Path("/tmp/fake_meipass/seasons")


class TestGetSeasonsPath:
    """Tests for get_seasons_path() function (backwards compatibility)."""

    def test_returns_builtin_path(self):
        """Should return the built-in seasons path."""
        result = get_seasons_path()
        builtin = get_builtin_seasons_path()
        assert result == builtin


class TestGetAllSeasonPaths:
    """Tests for get_all_season_paths() function."""

    def test_development_returns_only_builtin(self):
        """In development mode, should return only built-in path."""
        result = get_all_season_paths()
        assert len(result) == 1
        assert result[0] == get_builtin_seasons_path()

    @patch("paydirt.packaging.get_user_seasons_path")
    def test_bundled_without_user_dir(self, mock_user_seasons):
        """When user seasons directory doesn't exist, return only built-in."""
        mock_user_seasons.return_value = Path("/nonexistent/path")

        result = get_all_season_paths()
        # User path doesn't exist, so only built-in
        assert len(result) == 1
        assert result[0] == get_builtin_seasons_path()

    @patch("paydirt.packaging.get_user_seasons_path")
    def test_bundled_with_user_dir(self, mock_user_seasons, tmp_path):
        """When user seasons directory exists, return it first."""
        user_seasons = tmp_path / "seasons"
        user_seasons.mkdir()
        mock_user_seasons.return_value = user_seasons

        result = get_all_season_paths()
        # User path should be first (takes precedence)
        assert len(result) == 2
        assert result[0] == user_seasons
        assert result[1] == get_builtin_seasons_path()


class TestGetSeasonPath:
    """Tests for get_season_path() function."""

    def test_returns_year_subdirectory(self):
        """Should return seasons/YEAR path."""
        result = get_season_path(2026)
        assert result.name == "2026"
        assert result.parent == get_seasons_path()


class TestGetTeamPath:
    """Tests for get_team_path() function."""

    def test_returns_team_subdirectory(self):
        """Should return seasons/YEAR/TEAM path."""
        result = get_team_path(2026, "Ironclads")
        assert result.name == "Ironclads"
        assert result.parent.name == "2026"
