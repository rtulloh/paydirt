"""Historical runner regressions use synthetic 2026 schedules, never season data."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from tests import run_full_season as runner


def synthetic_spec(modern: bool = False) -> dict:
    """Construct a complete fictional source calendar and historical bracket."""
    count = 32 if modern else 28
    groups = {}
    for conference in ("A", "B"):
        names = [f"{conference}{i:02d}" for i in range(count // 2)]
        sizes = [4] * 4 if modern else [5, 4, 5]
        groups[conference] = {}
        offset = 0
        for number, size in enumerate(sizes):
            groups[conference][f"D{number}"] = names[offset:offset + size]
            offset += size
    teams = [t for ds in groups.values() for members in ds.values() for t in members]
    games = []

    def add(phase: str, week: int, away: str, home: str) -> str:
        games.append({"game_id": f"synthetic-{len(games):03d}", "phase": phase, "week": week,
                      "date": f"2026-09-{week:02d}", "away": away, "home": home,
                      "away_score": 0, "home_score": 3, "neutral": phase == "SB"})
        return home

    for away, home in zip(teams[::2], teams[1::2]):
        add("REG", 1, away, home)
    seeds = {c: ([f"{c}{i:02d}" for i in (0, 4, 8, 12, 1, 2, 3)] if modern else
                 [f"{c}{i:02d}" for i in (0, 5, 9, 1, 2)]) for c in ("A", "B")}
    survivors = {}
    for c, order in seeds.items():
        if modern:
            wild = [add("WC", 2, order[6], order[1]), add("WC", 2, order[5], order[2]),
                    add("WC", 2, order[4], order[3])]
            survivors[c] = [order[0], *wild]
        else:
            wild = add("WC", 2, order[4], order[3])
            survivors[c] = [order[0], order[1], order[2], wild]
    champions = []
    for c, alive in survivors.items():
        first, second, third, wild = alive
        if modern:
            pairs = ((wild, first), (third, second))
        else:
            pairs = ((third, first), (wild, second))
        winners = [add("DIV", 3, away, home) for away, home in pairs]
        champions.append(add("CON", 4, winners[1], winners[0]))
    add("SB", 5, champions[0], champions[1])
    games.sort(key=lambda row: (row["date"], row["game_id"]))
    return {"schema_version": 1, "season": 2026, "games_per_team": 1, "regular_weeks": 1,
            "postseason_format": "fourteen_team" if modern else "ten_team",
            "divisions": groups, "games": games,
            "attribution": [{"url": "https://example.org/synthetic", "sha256": "a" * 64}],
            "tiebreaker": "win_pct_point_diff_points_for_name"}


@pytest.fixture
def source_file(tmp_path: Path):
    def create(data: dict) -> Path:
        target = tmp_path / f"schedule-{len(list(tmp_path.iterdir()))}.json"
        target.write_text(json.dumps(data))
        return target
    return create


@pytest.mark.parametrize("modern", [False, True])
def test_loads_exact_source_calendar_with_year_membership(source_file, modern: bool) -> None:
    original = synthetic_spec(modern)
    result = runner.load_historical_schedule(source_file(original), 2026)
    assert result == original
    assert Counter(r["phase"] for r in result["games"]) == (
        {"REG": 16, "WC": 6, "DIV": 4, "CON": 2, "SB": 1} if modern else
        {"REG": 14, "WC": 2, "DIV": 4, "CON": 2, "SB": 1})
    assert len(result["divisions"]["A"]) == (4 if modern else 3)


@pytest.mark.parametrize("problem", [
    "year", "missing-game", "duplicate-id", "duplicate-week-team", "unknown-team",
    "self-game", "missing-score", "boolean-score", "negative-score", "missing-date",
    "wrong-date-year", "missing-round", "postseason-tie", "loser-advances",
    "duplicate-membership", "unknown-format", "wrong-membership-format", "missing-source",
])
def test_unsupported_or_incomplete_source_fails_before_games(source_file, problem: str) -> None:
    data = synthetic_spec()
    if problem == "year":
        data["season"] = 2025
    elif problem == "missing-game":
        data["games"].pop(0)
    elif problem == "duplicate-id":
        data["games"][1]["game_id"] = data["games"][0]["game_id"]
    elif problem == "duplicate-week-team":
        data["games"][1]["away"] = data["games"][0]["away"]
    elif problem == "unknown-team":
        data["games"][0]["away"] = "Unknown"
    elif problem == "self-game":
        data["games"][0]["away"] = data["games"][0]["home"]
    elif problem == "missing-score":
        del data["games"][0]["home_score"]
    elif problem == "boolean-score":
        data["games"][0]["home_score"] = True
    elif problem == "negative-score":
        data["games"][0]["home_score"] = -1
    elif problem == "missing-date":
        del data["games"][0]["date"]
    elif problem == "wrong-date-year":
        data["games"][0]["date"] = "2024-09-01"
    elif problem == "missing-round":
        data["games"] = [r for r in data["games"] if r["phase"] != "CON"]
    elif problem == "postseason-tie":
        data["games"][-1]["away_score"] = 3
    elif problem == "loser-advances":
        wildcard = next(r for r in data["games"] if r["phase"] == "WC")
        divisional = next(r for r in data["games"] if r["phase"] == "DIV"
                          and r["away"] == wildcard["home"])
        divisional["away"] = wildcard["away"]
    elif problem == "duplicate-membership":
        data["divisions"]["B"]["D0"][0] = data["divisions"]["A"]["D0"][0]
    elif problem == "unknown-format":
        data["postseason_format"] = "guessed"
    elif problem == "wrong-membership-format":
        data["postseason_format"] = "fourteen_team"
    else:
        data["attribution"] = []
    with pytest.raises((ValueError, KeyError)):
        runner.load_historical_schedule(source_file(data), 2026)


def test_missing_source_never_falls_back_to_generated_schedule(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        runner.load_historical_schedule(tmp_path / "absent.json", 2026)


def game_receipt(away: str, home: str, seed: int, playoff: bool, *, upset: bool = False) -> dict:
    return {"away": away, "home": home, "seed": seed, "home_score": 0 if upset else 3,
            "away_score": 3 if upset else 0, "game_over": True, "untimed_down": False,
            "is_playoff": playoff, "ot_period": 0, "accounting_errors": [], "selected_calls": []}


@pytest.mark.parametrize("modern", [False, True])
def test_actual_regular_calendar_and_counterfactual_bracket_use_generated_charts_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_file, modern: bool,
) -> None:
    spec = runner.load_historical_schedule(source_file(synthetic_spec(modern)), 2026)
    charts = tmp_path / "2026-generated"
    calls = []

    def simulate(directory, away, home, seed, *, is_playoff, policy):
        assert directory == charts
        calls.append((away, home, seed, is_playoff, policy))
        return game_receipt(away, home, seed, is_playoff, upset=True)

    monkeypatch.setattr(runner.historical, "simulate_historical_game", simulate)
    report = runner.audit_historical_season(spec, charts, master=20261108, policy="hard")
    assert report["passed"], report["errors"]
    regular = [r for r in spec["games"] if r["phase"] == "REG"]
    assert [(a, h) for a, h, *_ in calls[:len(regular)]] == [(r["away"], r["home"]) for r in regular]
    expected = 13 if modern else 9
    assert len(calls) == len(regular) + expected
    assert len({c[2] for c in calls}) == len(calls)
    assert all(c[-1] == "hard" for c in calls)
    assert report["postseason"]["mode"] == "simulated_standings"
    assert report["postseason"]["expected_games"] == expected
    assert Counter(r["phase"] for r in report["game_receipts"] if r["phase"] != "REG") == (
        {"WC": 6, "DIV": 4, "CON": 2, "SB": 1} if modern else
        {"WC": 2, "DIV": 4, "CON": 2, "SB": 1})
    assert report["postseason"]["seeds"]["A"][0] == "A00"
    actual_wc = {(r["away"], r["home"]) for r in spec["games"] if r["phase"] == "WC"}
    simulated_wc = {(r["away"], r["home"]) for r in report["game_receipts"] if r["phase"] == "WC"}
    assert actual_wc != simulated_wc  # No forced historical qualification.
    assert report["historical_comparison"]["regular_games"] == len(regular)
    assert report["historical_comparison"]["exact_score_matches"] == 0
    assert report["historical_comparison"]["teams"]["A00"]["simulated"]["wins"] == 1
    assert report["historical_comparison"]["teams"]["A00"]["historical"]["wins"] == 0
    assert report["developer_reference"] == "not_requested"
    assert report["release_certified"] is False


@pytest.mark.parametrize("modern", [False, True])
def test_historical_postseason_replay_is_explicit_and_does_not_reseed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, modern: bool,
) -> None:
    spec = synthetic_spec(modern)
    calls = []

    def simulate(directory, away, home, seed, *, is_playoff, policy):
        calls.append((away, home, is_playoff))
        return game_receipt(away, home, seed, is_playoff, upset=True)

    monkeypatch.setattr(runner.historical, "simulate_historical_game", simulate)
    report = runner.audit_historical_season(spec, tmp_path, postseason_mode="historical")
    assert report["passed"], report["errors"]
    assert calls == [(r["away"], r["home"], r["phase"] != "REG") for r in spec["games"]]
    assert report["postseason"]["mode"] == "historical_fixture_replay"
    assert report["postseason"]["champion"] is None  # Replay winners do not form a counterfactual bracket.


@pytest.mark.parametrize("problem", ["exception", "incomplete", "wrong-rules", "tie", "accounting"])
def test_failed_playoff_never_advances_and_missing_games_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, problem: str,
) -> None:
    spec = synthetic_spec(True)
    failed = []

    def simulate(directory, away, home, seed, *, is_playoff, policy):
        receipt = game_receipt(away, home, seed, is_playoff)
        if is_playoff and not failed:
            failed.extend([away, home])
            if problem == "exception":
                raise RuntimeError("injected")
            if problem == "incomplete":
                receipt["game_over"] = False
            elif problem == "wrong-rules":
                receipt["is_playoff"] = False
            elif problem == "tie":
                receipt["away_score"] = receipt["home_score"]
            else:
                receipt["accounting_errors"] = ["box mismatch"]
        return receipt

    monkeypatch.setattr(runner.historical, "simulate_historical_game", simulate)
    report = runner.audit_historical_season(spec, tmp_path)
    assert not report["passed"]
    assert report["errors"]
    assert report["postseason"]["champion"] is None
    assert report["postseason"]["not_played"] > 0
    later = [r for r in report["game_receipts"] if r["phase"] in ("DIV", "CON", "SB")]
    assert all(not set(failed).intersection((r["away"], r["home"])) for r in later)


def test_regular_failure_attempts_remaining_fixtures_but_blocks_postseason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    calls = []

    def simulate(directory, away, home, seed, *, is_playoff, policy):
        calls.append((away, home, is_playoff))
        if len(calls) == 1:
            raise RuntimeError("bad regular game")
        return game_receipt(away, home, seed, is_playoff)

    monkeypatch.setattr(runner.historical, "simulate_historical_game", simulate)
    report = runner.audit_historical_season(synthetic_spec(), tmp_path)
    assert not report["passed"]
    assert len(calls) == 14
    assert not any(c[-1] for c in calls)
    assert report["postseason"]["not_played"] == 9
    assert report["historical_comparison"] is None


@pytest.mark.parametrize("problem", [None, "missing-fixture", "chart-preflight", "overwrite"])
def test_cli_selects_year_and_generated_charts_and_preserves_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_file, problem: str | None,
) -> None:
    source = source_file(synthetic_spec())
    charts = tmp_path / "2026-generated"
    output = Path(".ai-audits") / f"pytest-season-{tmp_path.name}.json"
    calls = []
    monkeypatch.setattr(runner, "SEASON_DIR", tmp_path / "absent-private")

    def preflight(spec, directory):
        assert spec["season"] == 2026 and directory == charts.resolve()
        if problem == "chart-preflight":
            raise ValueError("missing source-year rules")
        return {"synthetic": "a" * 64}

    def audit(spec, directory, **kwargs):
        calls.append((spec, directory, kwargs))
        return {"passed": True, "errors": [], "game_receipts": [],
                "historical_comparison": {}, "postseason": {"mode": "simulated_standings"},
                "release_certified": False}

    monkeypatch.setattr(runner.historical, "validate_chart_inputs", preflight)
    monkeypatch.setattr(runner, "audit_historical_season", audit)
    if problem == "missing-fixture":
        source = tmp_path / "missing.json"
    if problem == "overwrite":
        output.write_text("preserved")
    try:
        status = runner.main(["2026", "--charts", str(charts), "--schedule", str(source),
                              "--output", str(output), "--policy", "balanced"])
        assert status == int(problem is not None)
        assert len(calls) == int(problem is None)
        if problem == "overwrite":
            assert output.read_text() == "preserved"
        elif problem is None:
            report = json.loads(output.read_text())
            assert report["year"] == 2026
            assert report["developer_reproductions"] == "not_applicable"
            assert calls[0][2]["policy"] == "balanced"
            assert report["inventory_unchanged"] is True
    finally:
        output.unlink(missing_ok=True)


@pytest.mark.parametrize("policy", ["balanced", "hard"])
def test_real_public_game_keeps_typed_receipts_and_restores_random(policy: str) -> None:
    import random

    before = random.getstate()
    receipt = runner.historical.simulate_historical_game(
        Path("seasons/2026").resolve(), "Ironclads", "Thunderhawks", 20261108,
        is_playoff=False, policy=policy)
    assert random.getstate() == before
    assert receipt["game_over"] is True
    assert receipt["untimed_down"] is False
    assert not receipt["accounting_errors"]
    assert receipt["selected_calls"]
    assert all({"before", "after", "play", "defense", "result", "yards"}.issubset(r)
               for r in receipt["selected_calls"])
    assert sum(r["home"] for r in receipt["periods"]) == receipt["home_score"]
    assert sum(r["away"] for r in receipt["periods"]) == receipt["away_score"]
    json.dumps(receipt, allow_nan=False)


def test_source_change_during_parse_blocks_games(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_file,
) -> None:
    source = source_file(synthetic_spec())
    output = Path(".ai-audits") / f"pytest-season-race-{tmp_path.name}.json"
    original = runner.load_historical_schedule
    calls = []

    def changed_load(path, year):
        loaded = original(path, year)
        changed = json.loads(path.read_text())
        changed["games"][0]["home_score"] += 1
        path.write_text(json.dumps(changed))
        return loaded

    monkeypatch.setattr(runner, "load_historical_schedule", changed_load)
    monkeypatch.setattr(runner.historical, "validate_chart_inputs", lambda *args: {})
    monkeypatch.setattr(runner, "audit_historical_season",
                        lambda *args, **kwargs: calls.append(True) or {
                            "passed": True, "errors": [], "game_receipts": []})
    try:
        assert runner.main(["2026", "--schedule", str(source), "--charts", str(tmp_path),
                            "--output", str(output)]) == 1
        assert calls == []
    finally:
        output.unlink(missing_ok=True)


def test_chart_identity_binds_optional_roster(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    spec = synthetic_spec()
    for divisions in spec["divisions"].values():
        for members in divisions.values():
            for team in members:
                folder = tmp_path / team
                folder.mkdir()
                for name in ("offense.csv", "defense.csv", "special.csv", "team.yaml"):
                    (folder / name).write_text("synthetic")
    roster = tmp_path / "A00/roster.json"
    roster.write_text("{}")
    monkeypatch.setattr(runner.historical, "load_season_rules",
                        lambda path: SimpleNamespace(season=2026))
    monkeypatch.setattr(runner.historical, "load_team_chart",
                        lambda path: SimpleNamespace(peripheral=SimpleNamespace(short_name=path.name)))
    before = runner.historical.validate_chart_inputs(spec, tmp_path)
    roster.write_text('{"synthetic": "changed"}')
    after = runner.historical.validate_chart_inputs(spec, tmp_path)
    assert before != after
    assert "A00/roster.json" in before


def eight_team_spec() -> dict:
    """Use fictional source fixtures for the three-winner/one-wildcard era."""
    data = synthetic_spec()
    data["postseason_format"] = "eight_team"
    data["games"] = [row for row in data["games"] if row["phase"] != "WC"]
    for row in data["games"]:
        if row["phase"] != "REG":
            row["week"] -= 1
            row["date"] = f"2026-09-{row['week']:02d}"
    return data


def test_eight_team_calendar_has_seven_postseason_games_without_wildcard_round(source_file) -> None:
    spec = runner.load_historical_schedule(source_file(eight_team_spec()), 2026)
    assert Counter(row["phase"] for row in spec["games"]) == {
        "REG": 14, "DIV": 4, "CON": 2, "SB": 1}
    invalid = eight_team_spec()
    invalid["games"].append(next(row for row in synthetic_spec()["games"] if row["phase"] == "WC"))
    with pytest.raises(ValueError):
        runner.load_historical_schedule(source_file(invalid), 2026)


@pytest.mark.parametrize("failure", [None, "tie", "exception"])
@pytest.mark.parametrize("wildcard_same_division", [False, True])
def test_eight_team_simulated_bracket_uses_one_wildcard_and_never_advances_failed_games(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str | None, wildcard_same_division: bool,
) -> None:
    failed = []
    def simulate(directory, away, home, seed, *, is_playoff, policy):
        receipt = game_receipt(away, home, seed, is_playoff, upset=True)
        if not is_playoff:
            winning_scores = {"00": 30, "06": 27, "10": 24,
                              "02" if wildcard_same_division else "08": 21}
            receipt["away_score"] = winning_scores.get(away[1:], 3)
        if is_playoff and failure and not failed:
            failed.extend([away, home])
            if failure == "exception":
                raise RuntimeError("injected")
            receipt["away_score"] = receipt["home_score"]
        return receipt
    monkeypatch.setattr(runner.historical, "simulate_historical_game", simulate)
    report = runner.audit_historical_season(eight_team_spec(), tmp_path)
    assert report["passed"] is (failure is None), report["errors"]
    assert report["postseason"]["expected_games"] == 7
    assert all(len(order) == 4 for order in report["postseason"]["seeds"].values())
    assert all(row["phase"] != "WC" for row in report["game_receipts"])
    if failure:
        assert report["postseason"]["not_played"] > 0
        assert report["postseason"]["champion"] is None
        assert all(not set(failed).intersection((r["away"], r["home"]))
                   for r in report["game_receipts"] if r["phase"] in {"CON", "SB"})
    else:
        assert Counter(r["phase"] for r in report["game_receipts"]) == {
            "REG": 14, "DIV": 4, "CON": 2, "SB": 1}
        assert {r["phase"]: r["week"] for r in report["game_receipts"]} == {
            "REG": 1, "DIV": 2, "CON": 3, "SB": 4}
        for conference, order in report["postseason"]["seeds"].items():
            divisions = eight_team_spec()["divisions"][conference]
            division = {t: d for d, members in divisions.items() for t in members}
            games = [r for r in report["game_receipts"] if r["phase"] == "DIV"
                     and r["home"] in order]
            assert {r["home"] for r in games} == set(order[:2])
            assert {r["away"] for r in games} == set(order[2:])
            assert all(division[r["away"]] != division[r["home"]] for r in games)
            assert (division[order[3]] == division[order[0]]) is wildcard_same_division
            wildcard_game = next(r for r in games if r["away"] == order[3])
            assert wildcard_game["home"] == order[1 if wildcard_same_division else 0]
