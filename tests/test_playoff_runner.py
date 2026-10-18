"""Synthetic/public-only checks for the generated postseason regression runner."""

from types import SimpleNamespace

import pytest

from paydirt.standings import Season, TeamRecord
from tests import run_full_season as runner
from tests.game_fixtures import make_sample_game
from tests.test_untimed_down_flow import run_seeded_cli_game


def synthetic_season() -> Season:
    season = Season(1983)
    season.divisions = {
        conference: {
            "East": [f"{conference}{i:02d}" for i in range(5)],
            "Central": [f"{conference}{i:02d}" for i in range(5, 9)],
            "West": [f"{conference}{i:02d}" for i in range(9, 14)],
        } for conference in ("A", "B")
    }
    records = {
        team: TeamRecord(team, wins=14 - i, losses=2 + i)
        for divisions in season.divisions.values() for members in divisions.values()
        for team in members for i in [int(team[1:])]
    }
    season.get_standings = lambda: records
    return season


def final_game(home: int = 3, away: int = 0, playoff: bool = True, ot: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(game_over=True, home_score=home, away_score=away,
                              is_playoff=playoff, ot_period=ot,
                              scoring_plays=[SimpleNamespace(points=home, is_home_team=True),
                                             SimpleNamespace(points=away, is_home_team=False)]),
        has_untimed_down=lambda: False,
        get_period_scores=lambda: [{"home": home, "away": away}],
    )


def test_playoff_tie_is_rejected_but_regular_season_tie_is_allowed() -> None:
    runner.validate_game(final_game(3, 3, playoff=False), "FINAL")
    with pytest.raises(ValueError, match="[Tt]ie"):
        runner.validate_game(final_game(3, 3), "FINAL")


def test_postseason_qualifies_division_winners_and_two_wildcards() -> None:
    season = synthetic_season()
    expected = {conf: [f"{conf}{i:02d}" for i in (0, 5, 9, 1, 2)] for conf in ("A", "B")}
    assert runner.seed_playoffs(season) == expected
    # Insertion order must not affect seeds.
    season.divisions = dict(reversed(list(season.divisions.items())))
    assert runner.seed_playoffs(season) == expected


def test_seeding_counts_ties_and_has_reproducible_tiebreakers() -> None:
    season = synthetic_season()
    records = season.get_standings()
    # 10-4-2 outranks 10-6; an equal record uses point differential, then PF/name.
    records["A00"] = TeamRecord("A00", wins=10, losses=6)
    records["A01"] = TeamRecord("A01", wins=10, losses=4, ties=2)
    records["A02"] = TeamRecord("A02", wins=10, losses=4, ties=2, points_for=10)
    records["A03"] = TeamRecord("A03", wins=10, losses=4, ties=2, points_for=10)
    seeds = runner.seed_playoffs(season)
    assert seeds["A"][0] == "A02"
    assert seeds["A"][3:] == ["A03", "A01"]


@pytest.mark.parametrize("problem", ["missing-record", "duplicate", "wrong-conferences"])
def test_invalid_postseason_inputs_are_not_silently_accepted(problem: str) -> None:
    season = synthetic_season()
    if problem == "missing-record":
        del season.get_standings()["A00"]
    elif problem == "duplicate":
        season.divisions["A"]["East"][1] = "A00"
    else:
        del season.divisions["B"]
    with pytest.raises(ValueError):
        runner.seed_playoffs(season)


@pytest.mark.parametrize("upset", [False, True])
def test_all_nine_playoffs_use_playoff_rules_and_advance_actual_winners(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, upset: bool,
) -> None:
    season = synthetic_season()
    calls = []

    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        assert is_playoff
        calls.append((away.split("/")[-1], home.split("/")[-1], seed))
        print("FINAL")
        return final_game(0 if upset else 3, 3 if upset else 0, ot=2 if len(calls) == 9 else 0)

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_playoffs(season) == 0
    output = capsys.readouterr()
    assert len(calls) == 9
    assert len({call[2] for call in calls}) == 9
    assert all(seed > 19831614 for _, _, seed in calls)
    assert calls[:2] == [("A02", "A01", 19831701), ("B02", "B01", 19831702)]
    wildcard_winner = "02" if upset else "01"
    # Avoid a same-division divisional rematch for the top seed.
    assert calls[2][:2] == ("A09", "A00")
    assert calls[3][:2] == (f"A{wildcard_winner}", "A05")
    assert calls[6][:2] == ((f"A{wildcard_winner}", "A09") if upset else ("A05", "A00"))
    expected_champion = f"A{wildcard_winner}" if upset else "B00"
    assert f"Champion: {expected_champion}" in output.out
    assert "Generated playoffs: 9/9 passed; 0 failed" in output.out
    assert "1 OT games; 0 ties" in output.out
    assert all(round_name in output.out for round_name in (
        "Wild Card", "Divisional", "Conference Championships", "Championship"))
    assert not output.err


@pytest.mark.parametrize("problem", ["tie", "exception", "wrong-rules", "incomplete"])
def test_playoff_failures_stop_advancement_and_report_reproduction_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, problem: str,
) -> None:
    calls = []

    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        calls.append((away, home, seed))
        print("FINAL")
        if len(calls) == 1:
            if problem == "exception":
                raise RuntimeError("injected playoff failure")
            game = final_game(3, 3 if problem == "tie" else 0, playoff=problem != "wrong-rules")
            game.state.game_over = problem != "incomplete"
            return game
        return final_game()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_playoffs(synthetic_season()) == 1
    output = capsys.readouterr()
    assert "seed=19831701" in output.err
    assert "A02@A01" in output.err
    assert "Wild Card" in output.err
    assert "Champion:" not in output.out
    assert "1 failed" in output.out
    assert "not played" in output.out
    assert ("1 ties" if problem == "tie" else "0 ties") in output.out
    # Neither participant in the failed wildcard can be promoted by a coin flip/seed.
    assert not any("A01" in (away.split("/")[-1], home.split("/")[-1]) or
                   "A02" in (away.split("/")[-1], home.split("/")[-1])
                   for away, home, _ in calls[1:])


def test_full_season_runs_postseason_from_in_memory_regular_results(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    season = synthetic_season()
    # Use the real record calculation for the generated results.
    del season.get_standings
    teams = [team for divs in season.divisions.values() for members in divs.values() for team in members]
    monkeypatch.setattr(runner, "Season", lambda year: season)
    calls = []

    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        calls.append(is_playoff)
        print("FINAL")
        return final_game(playoff=is_playoff)

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_full_season(teams) == 0
    assert calls == [False] * 224 + [True] * 9
    assert len(season.games) == 224  # Playoffs cannot alter regular-season seeding.
    text = capsys.readouterr().out
    assert "Generated season: 224/224 passed" in text
    assert "Generated playoffs: 9/9 passed" in text


def test_seeded_cli_driver_passes_playoff_flag_without_changing_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from paydirt import interactive_game as cli
    engine = make_sample_game()
    calls = []

    def run(**kwargs):
        calls.append(kwargs)
        cli.PaydirtGameEngine(engine.state.home_chart, engine.state.away_chart)

    monkeypatch.setattr(cli, "run_interactive_game", run)
    assert run_seeded_cli_game(monkeypatch, "Ironclads", "Thunderhawks", 1, is_playoff=True)
    assert run_seeded_cli_game(monkeypatch, "Ironclads", "Thunderhawks", 1)
    assert calls[0]["is_playoff"] is True
    assert calls[1]["is_playoff"] is False


@pytest.mark.parametrize("tie_seed", [19831701, 19831801, 19831901, 19832001])
def test_tied_final_in_any_round_is_a_failure_and_cannot_produce_a_champion(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, tie_seed: int,
) -> None:
    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        print("FINAL")
        return final_game(3, 3 if seed == tie_seed else 0)

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_playoffs(synthetic_season()) == 1
    output = capsys.readouterr()
    assert f"seed={tie_seed}" in output.err
    assert "Tie game in playoffs" in output.err
    assert "1 ties" in output.out
    assert "Champion:" not in output.out


def test_divisional_pairings_when_wildcard_is_from_another_division(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeds = {conf: [f"{conf}{i:02d}" for i in (0, 5, 9, 6, 7)] for conf in ("A", "B")}
    calls = []

    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        calls.append((away.split("/")[-1], home.split("/")[-1]))
        print("FINAL")
        return final_game()

    monkeypatch.setattr(runner, "seed_playoffs", lambda season: seeds)
    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_playoffs(synthetic_season()) == 0
    assert calls[2:4] == [("A06", "A00"), ("A09", "A05")]


def test_playoffs_keep_guard_against_kickoff_after_game_over(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    def simulate(context, away: str, home: str, seed: int, *, is_playoff: bool = False):
        engine = make_sample_game()
        engine.state.game_over = True
        engine.kickoff()

    monkeypatch.setattr(runner, "run_seeded_cli_game", simulate)
    assert runner.run_playoffs(synthetic_season()) == 1
    assert "Kickoff attempted after game over" in capsys.readouterr().err
