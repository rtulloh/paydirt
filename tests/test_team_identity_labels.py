"""Public sample charts must expose authoritative metadata display labels."""

import shutil
from pathlib import Path

import pytest

from paydirt.chart_loader import load_team_chart, load_team_metadata


@pytest.mark.parametrize("short_name", ["SD '83", "STL '83", "LA '83", "HBI"])
def test_metadata_label_reaches_loaded_chart(tmp_path: Path, short_name: str) -> None:
    """Use public charts with synthetic metadata, never historical chart fixtures."""
    source = Path(__file__).resolve().parents[1] / "seasons/2026/Ironclads"
    target = tmp_path / "Synthetic"
    shutil.copytree(source, target)
    (target / "team.yaml").write_text(
        f'team_name: Synthetic\nshort_name: "{short_name}"\nnickname: Synthetic\n'
    )
    metadata = load_team_metadata(str(target))
    assert metadata is not None
    assert metadata.short_name == short_name
    assert load_team_chart(str(target)).short_name == short_name
