"""AUD-023: metadata repeated a nickname in the matchup banner."""

import pytest

from paydirt.chart_loader import PeripheralData, TeamChart


def team(name: str, nickname: str) -> TeamChart:
    return TeamChart(
        peripheral=PeripheralData(
            year=1983, team_name=name, team_nickname=nickname,
            power_rating=50, short_name="TST",
        ),
        offense=None,
        defense=None,
        special_teams=None,
    )


@pytest.mark.parametrize("name,nickname", [
    ("Cleveland", "Browns"),
    ("Browns", "Browns"),
    ("Miami Dolphins", "Dolphins"),
])
def test_full_name_never_repeats_the_same_display_component(name: str, nickname: str) -> None:
    full_name = team(name, nickname).full_name
    if name == nickname:
        assert full_name == f"1983 {nickname}"
    else:
        assert full_name.count(nickname) == 1


def test_distinct_city_and_nickname_still_both_render() -> None:
    assert team("Cleveland", "Browns").full_name == "1983 Cleveland Browns"


def test_public_sample_team_with_equal_metadata_has_one_component() -> None:
    from pathlib import Path

    from paydirt.chart_loader import load_team_chart

    chart = load_team_chart(str(Path(__file__).parent.parent / "seasons" / "2026" / "Ironclads"))
    assert chart.full_name == "2026 Ironclads"
