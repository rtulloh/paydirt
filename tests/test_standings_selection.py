"""CLI selection must follow displayed week order."""
import sys

import pytest

from paydirt import standings


@pytest.mark.parametrize("weeks", [(2, 1, 1), (1, 1, 2)])
@pytest.mark.parametrize("command", ["edit", "delete"])
def test_selection_matches_display(tmp_path, monkeypatch, capsys, weeks, command):
    manager = standings.StandingsManager(tmp_path)
    season = standings.Season(2026)
    for i, week in enumerate(weeks):
        season.add_game("Bills", 10 + i, "Jets", 3, week=week)
    manager.save_season(season)
    ordered = sorted(range(3), key=lambda i: weeks[i])
    target = ordered[0]
    monkeypatch.setattr(standings, "StandingsManager", lambda: manager)
    standings.display_games(season)
    assert f"{10 + target:>3}" in capsys.readouterr().out.split("  1.")[1].splitlines()[0]
    argv = ["standings", command, "2026", "1"]
    if command == "edit":
        argv += ["--home-score", "31", "--week", "4"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert standings.main() == 0
    loaded = manager.load_season(2026)
    if command == "edit":
        assert loaded.games[target].home_score == 31
        assert loaded.games[target].week == 4
        assert [g.home_score for i, g in enumerate(loaded.games) if i != target] == [10 + i for i in range(3) if i != target]
    else:
        assert [g.home_score for g in loaded.games] == [10 + i for i in range(3) if i != target]
    assert f"Week {weeks[target]}" in capsys.readouterr().out


def test_week_edit_changes_next_selection(tmp_path, monkeypatch):
    manager = standings.StandingsManager(tmp_path)
    season = standings.Season(2026)
    season.add_game("Bills", 10, "Jets", 3, week=2)
    season.add_game("Bears", 20, "Lions", 7, week=1)
    manager.save_season(season)
    monkeypatch.setattr(standings, "StandingsManager", lambda: manager)
    monkeypatch.setattr(sys, "argv", ["standings", "edit", "2026", "1", "--week", "3"])
    assert standings.main() == 0
    monkeypatch.setattr(sys, "argv", ["standings", "edit", "2026", "1", "--home-score", "31"])
    assert standings.main() == 0
    assert [(g.week, g.home_score) for g in manager.load_season(2026).games] == [(2, 31), (3, 20)]


@pytest.mark.parametrize("number", ["0", "3"])
def test_invalid_selection_does_not_persist(tmp_path, monkeypatch, number):
    manager = standings.StandingsManager(tmp_path)
    season = standings.Season(2026)
    season.add_game("Bills", 10, "Jets", 3, week=1)
    manager.save_season(season)
    before = (tmp_path / "season_2026.json").read_bytes()
    monkeypatch.setattr(standings, "StandingsManager", lambda: manager)
    monkeypatch.setattr(sys, "argv", ["standings", "delete", "2026", number])
    assert standings.main() == 1
    assert (tmp_path / "season_2026.json").read_bytes() == before


def test_cancelled_delete_preserves_records(tmp_path, monkeypatch):
    manager = standings.StandingsManager(tmp_path)
    season = standings.Season(2026)
    season.add_game("Bills", 10, "Jets", 3, week=2)
    season.add_game("Bears", 20, "Lions", 7, week=1)
    manager.save_season(season)
    before = (tmp_path / "season_2026.json").read_bytes()
    monkeypatch.setattr(standings, "StandingsManager", lambda: manager)
    monkeypatch.setattr(sys, "argv", ["standings", "delete", "2026", "1"])
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert standings.main() == 0
    assert (tmp_path / "season_2026.json").read_bytes() == before
