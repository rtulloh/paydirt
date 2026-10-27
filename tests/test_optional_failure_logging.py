"""Optional data failures retain their fallback and emit debug diagnostics."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from paydirt.ai_save import get_ai_filepath, load_ai_data
from paydirt.chart_loader import load_team_metadata


def test_metadata_failure_keeps_fallback_and_logs(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    (tmp_path / "team.yaml").write_text("team_name: Synthetic\n")
    with (caplog.at_level(logging.DEBUG, logger="paydirt.chart_loader"),
          patch("paydirt.chart_loader.yaml.safe_load", side_effect=RuntimeError("synthetic failure"))):
        assert load_team_metadata(str(tmp_path)) is None
    assert any(record.name == "paydirt.chart_loader" and record.exc_info
               for record in caplog.records)


def test_ai_restore_failure_keeps_fallback_and_logs(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    away, home = "2026/SyntheticAway", "2026/SyntheticHome"
    filepath = Path(get_ai_filepath(away, home, str(tmp_path)))
    filepath.write_text(json.dumps({
        "version": 1,
        "metadata": {"away_team_path": away, "home_team_path": home},
        "opponent_model": {"synthetic": True},
    }))
    with (caplog.at_level(logging.DEBUG, logger="paydirt.ai_save"),
          patch("paydirt.ai_save.OpponentModel.from_dict", side_effect=RuntimeError("synthetic failure"))):
        assert load_ai_data(away, home, str(tmp_path)) is None
    assert any(record.name == "paydirt.ai_save" and record.exc_info
               for record in caplog.records)
