"""Opt-in ordered source projection uses synthetic evidence, never season data."""
import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from paydirt import nflverse_play_by_play as source

MODE = "ordered_ledger_v1"
POLICY = "source_reported_gain_proxy_v1"


def compound(kind: str = "own_sack", **changes: object) -> dict[str, object]:
    """Build supported ownership patterns without private source fixtures."""
    row: dict[str, object] = {
        "season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-joint",
        "play_id": 1, "posteam": "AAA", "defteam": "BBB", "play_type": "pass",
        "pass_attempt": 1, "sack": 1, "air_yards": 5, "yards_gained": -7,
        "passer_player_id": "carrier", "passer_player_name": "A.Carrier",
        "fumble": 1, "fumble_lost": 1,
        "fumbled_1_team": "AAA", "fumbled_1_player_id": "carrier", "fumbled_1_player_name": "A.Carrier",
        "fumble_recovery_1_team": "AAA", "fumble_recovery_1_player_id": "recoverer", "fumble_recovery_1_player_name": "R.Recoverer",
        "fumbled_2_team": "AAA", "fumbled_2_player_id": "recoverer", "fumbled_2_player_name": "R.Recoverer",
        "fumble_recovery_2_team": "BBB", "fumble_recovery_2_player_id": "last", "fumble_recovery_2_player_name": "L.Last",
        "desc": "A.Carrier sacked for -7 yards. FUMBLES, recovered by AAA-R.Recoverer at AAA 33. "
                "R.Recoverer to AAA 32 for -1 yards. FUMBLES, recovered by BBB-L.Last.",
    }
    if kind == "opponent_sack":
        row.update(fumble_recovery_1_team="BBB", fumbled_2_team="BBB",
                   desc="A.Carrier sacked for -7 yards. FUMBLES, recovered by BBB-R.Recoverer at AAA 33. "
                        "R.Recoverer to AAA 32 for 1 yard. FUMBLES, recovered by BBB-L.Last.")
    if kind in {"run_touchback", "punt_snap", "same_player"}:
        row.update(play_type="run", pass_attempt=0, sack=0, rush_attempt=1,
                   rusher_player_id="carrier", rusher_player_name="A.Carrier",
                   run_location="left", run_gap="end", yards_gained=0)
    if kind == "run_touchback":
        row.update(yards_gained=-6, fumble_recovery_1_team="BBB", fumbled_2_team="BBB",
                   fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
                   desc="A.Carrier FUMBLES, recovered by BBB-R.Recoverer at AAA 40. "
                        "R.Recoverer to AAA 0 for 40 yards. FUMBLES out of bounds in end zone, Touchback.")
    elif kind == "punt_snap":
        row.update(rusher_player_id="recoverer", rusher_player_name="R.Recoverer", fumble_lost=0,
                   fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
                   desc="(Punt formation) A.Carrier Aborted. FUMBLES, recovered by AAA-R.Recoverer at AAA 5. "
                        "R.Recoverer to AAA 0 for -5 yards. FUMBLES out of bounds in end zone, SAFETY.")
    elif kind == "same_player":
        row.update(fumble_lost=0, fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
                   fumble_recovery_1_player_id="carrier", fumble_recovery_1_player_name="A.Carrier",
                   fumble_recovery_2_team="AAA",
                   desc="A.Carrier FUMBLES, recovered by AAA-A.Carrier at AAA 30. "
                        "A.Carrier to AAA 31 for 1 yard. FUMBLES, recovered by AAA-L.Last.")
    row.update(changes)
    return row


def losses(kind: str) -> tuple[bool, bool]:
    return {"own_sack": (False, True), "opponent_sack": (True, False),
            "run_touchback": (True, True), "punt_snap": (False, False),
            "same_player": (False, False)}[kind]


def reviews(row: dict[str, object], flags: tuple[bool, ...]) -> tuple[source.FumbleLossReview, ...]:
    ledger = source.build_fumble_ledger(row)
    return tuple(source.FumbleLossReview(ledger.raw_play_sha256, event.ordinal,
                 event.fumbling_team, event.fumbling_player_id, lost, "a" * 64, 2)
                 for event, lost in zip(ledger.events, flags))


def classify(rows: list[dict[str, object]], **kwargs: Any) -> source.ClassifiedNflverseSeason:
    return source.classify_nflverse_rows(rows, fumble_gain_policy=POLICY,
                                        fumble_projection_mode=MODE, **kwargs)


@pytest.mark.parametrize("kind", ["own_sack", "opponent_sack", "run_touchback", "punt_snap", "same_player"])
def test_synthetic_projection_fixture_control(kind: str) -> None:
    row = compound(kind)
    ledger = source.apply_fumble_loss_reviews(source.build_fumble_ledger(row), reviews(row, losses(kind)))
    projected = source.project_fumble_ledger(ledger, policy=POLICY)
    assert projected.complete and len(projected.events) == 2
    assert [event.lost for event in projected.events] == list(losses(kind))
    assert [event.exposure for event in projected.events] == ["primary", "shared_return"]


def test_default_compound_guard_control() -> None:
    result = source.classify_nflverse_rows([compound()], fumble_gain_policy=POLICY)
    assert not result.fumbles and len(result.unsupported_fields) == 1


@pytest.mark.parametrize("kind", ["own_sack", "opponent_sack", "run_touchback", "punt_snap", "same_player"])
def test_opt_in_consumes_reviewed_primary_once_and_keeps_conditional_separate(kind: str) -> None:
    row = compound(kind)
    result = classify([row], fumble_loss_reviews=reviews(row, losses(kind)))
    assert not result.unsupported_fields
    assert len(result.joint_fumble_projections) == 1
    assert len(result.shared_return_fumbles) == 1
    assert result.shared_return_fumbles[0].source_event_id == "synthetic-joint:1:F2"
    assert result.shared_return_fumbles[0].lost == losses(kind)[1]
    assert [(event.team, event.unit, event.lost) for event in result.fumbles] == [
        ("AAA", "punt_snap" if kind == "punt_snap" else "passing" if "sack" in kind else "rushing", losses(kind)[0])]
    primary = [p for p in result.plays if p.result.startswith("F")]
    assert len(primary) == 1
    assert (primary[0].unit, primary[0].chart) == (
        ("special_teams", "punt") if kind == "punt_snap" else ("offense", "qb_time") if "sack" in kind else ("offense", "end_run"))
    assert sum(p.result == "QT" for p in result.plays) == int("sack" in kind)
    assert result.fumble_ledgers[0].events[1].individual_lost == losses(kind)[1]
    if kind == "punt_snap":
        assert result.joint_fumble_projections[0].events[0].statistical_player_id == "recoverer"


@pytest.mark.parametrize("bad", ["missing", "wrong_hash", "wrong_actor", "duplicate", "unused", "untyped"])
def test_invalid_or_incomplete_reviews_do_not_open_compound_guard(bad: str) -> None:
    row = compound()
    stream: tuple = reviews(row, losses("own_sack"))
    if bad == "missing":
        result = classify([row], fumble_loss_reviews=stream[:1])
        assert result.unsupported_fields and not result.fumbles and not result.shared_return_fumbles
        return
    if bad == "wrong_hash":
        stream = (replace(stream[0], raw_play_sha256="b" * 64), stream[1])
    elif bad == "wrong_actor":
        stream = (replace(stream[0], fumbling_player_id="wrong"), stream[1])
    elif bad == "duplicate":
        stream = (*stream, stream[0])
    elif bad == "unused":
        stream = (*stream, replace(stream[0], raw_play_sha256="b" * 64))
    else:
        stream = ({"lost": False},)
    with pytest.raises(ValueError):
        classify([row], fumble_loss_reviews=stream)


def test_reviews_require_explicit_projection_mode() -> None:
    row = compound()
    with pytest.raises(ValueError, match="projection mode"):
        source.classify_nflverse_rows([row], fumble_gain_policy=POLICY,
                                      fumble_loss_reviews=reviews(row, losses("own_sack")))


@pytest.mark.parametrize("flags,retained", [({}, True), ({"play_type": "no_play"}, False),
                                         ({"desc": "A.Carrier FUMBLES. Penalties offsetting."}, False)])
def test_retained_foul_primary_credit_is_separate_from_penalty_sample(flags: dict, retained: bool) -> None:
    row = compound(fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
                   fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
                   fumble_recovery_1_team="BBB", penalty=1, penalty_team="AAA", penalty_type="Offensive Holding", penalty_yards=10,
                   desc="A.Carrier sacked for -7 yards. FUMBLES, recovered by BBB-R.Recoverer. Penalty on AAA: Offensive Holding, 10 yards (accepted).")
    row.update(flags)
    result = classify([row])
    assert not result.unsupported_fields
    assert len(result.fumbles) == int(retained)
    if retained:
        assert result.fumbles[0].lost is True
        assert [p.result for p in result.plays] == ["OFF 10"]


def test_interception_fumble_is_shared_once_and_never_primary() -> None:
    row = compound(sack=0, interception=1, yards_gained=0, return_team="BBB", return_yards=29,
                   fumbled_1_team="BBB", fumble_lost=0, fumble_recovery_1_team="BBB",
                   fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
                   fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
                   desc="Pass INTERCEPTED by BBB-A.Carrier at BBB 5. A.Carrier to BBB 34 for 29 yards. FUMBLES, recovered by BBB-R.Recoverer.")
    result = classify([row])
    assert not result.unsupported_fields and not result.fumbles
    assert len(result.shared_return_fumbles) == 1
    assert result.interception_return_outcomes["BBB"] == {"synthetic-joint:1:F1": "F + 29"}
    assert sum(p.chart == "interception_return" for p in result.plays) == 1


def test_unknown_conditional_gain_remains_blocked() -> None:
    row = compound(desc="A.Carrier FUMBLES, recovered by AAA-R.Recoverer. R.Recoverer FUMBLES, recovered by BBB-L.Last.")
    result = classify([row], fumble_loss_reviews=reviews(row, losses("own_sack")))
    assert result.unsupported_fields and not result.fumbles and not result.shared_return_fumbles


def test_interception_owner_conflict_cannot_enter_shared_inventory() -> None:
    row = compound(sack=0, interception=1, return_team="BBB", return_yards=4,
                   fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
                   fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
                   fumble_lost=0,
                   desc="Pass INTERCEPTED by BBB-D.Defender. A.Carrier to AAA 34 for 4 yards. FUMBLES, recovered by AAA-R.Recoverer.")
    result = classify([row])
    assert result.unsupported_fields and not result.shared_return_fumbles


@pytest.mark.parametrize("kind", ["punt", "kickoff"])
def test_compound_return_cannot_bypass_ordered_guard_in_early_special_branch(kind: str) -> None:
    row = compound(play_type=kind, sack=0, pass_attempt=0, return_team="AAA", return_yards=3,
                   desc="A.Carrier to AAA 30 for 3 yards. FUMBLES, recovered by AAA-R.Recoverer at AAA 30. "
                        "R.Recoverer to AAA 31 for 1 yard. FUMBLES, recovered by BBB-L.Last.")
    blocked = classify([row])
    assert blocked.unsupported_fields and not blocked.plays and not blocked.shared_return_fumbles
    supported = classify([row], fumble_loss_reviews=reviews(row, (False, True)))
    assert not supported.unsupported_fields and not supported.fumbles
    assert len(supported.shared_return_fumbles) == 1
    assert supported.shared_return_fumbles[0].source_event_id.endswith(":F2")


@pytest.mark.parametrize("damage", ["none", "stale_pdf", "missing_pdf", "bad_page"])
def test_command_reviews_bind_relative_pdf_bytes_and_pages(tmp_path: Path, damage: str) -> None:
    import generate_nflverse_charts as command

    pdf = tmp_path / "evidence.pdf"
    pdf.write_bytes(b"%PDF-1.7\n1 0 obj << /Type /Pages /Count 2 /Kids [2 0 R 3 0 R] >> endobj\n%%EOF")
    stream = reviews(compound(), losses("own_sack"))
    records = [{**asdict(r), "evidence_file": "evidence.pdf", "evidence_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()} for r in stream]
    if damage == "bad_page":
        records[0]["evidence_page"] = 3
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps(records))
    if damage == "stale_pdf":
        pdf.write_bytes(pdf.read_bytes() + b"changed")
    elif damage == "missing_pdf":
        pdf.unlink()
    if damage == "none":
        loaded, bound = command._load_fumble_reviews(path)
        assert all(isinstance(r, source.FumbleLossReview) for r in loaded)
        assert loaded[0].evidence_page == 2 and pdf.resolve() in bound
    else:
        with pytest.raises(ValueError):
            command._load_fumble_reviews(path)


@pytest.mark.parametrize("damage", ["none", "stale_measurement", "wrong_source", "wrong_count", "pending"])
def test_command_requires_hash_bound_measured_complete_team_exposures(tmp_path: Path, damage: str) -> None:
    import generate_nflverse_charts as command

    raw = tmp_path / "source.csv"
    raw.write_text("synthetic source bytes")
    measurement = tmp_path / "measurement.json"
    receipt = {"shared_final_retention_pending": int(damage == "pending"), "source_schedules_completed": 1,
               "games_completed": 1, "by_team_consumer": {"AAA:interception": {"retained_terminal_segments": 2}}}
    measurement.write_text(json.dumps(receipt))
    data = {"source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "measurement_file": "measurement.json",
            "measurement_sha256": hashlib.sha256(measurement.read_bytes()).hexdigest(), "terminal_exposures_by_team": {"AAA": 2}}
    if damage == "wrong_source":
        data["source_sha256"] = "b" * 64
    elif damage == "wrong_count":
        data["terminal_exposures_by_team"] = {"AAA": 3}
    path = tmp_path / "exposures.json"
    path.write_text(json.dumps(data))
    if damage == "stale_measurement":
        measurement.write_text("{}")
    if damage == "none":
        counts, bound = command._load_shared_exposures(path, raw, {"AAA"}, expected_games=1)
        assert counts == {"AAA": 2} and measurement.resolve() in bound
    else:
        with pytest.raises(ValueError):
            command._load_shared_exposures(path, raw, {"AAA"}, expected_games=1)


def test_generation_mode_requires_measured_exposure_before_source_loading(tmp_path: Path) -> None:
    from unittest.mock import patch

    import generate_nflverse_charts as command

    with (patch.object(command, "load_nflverse_play_by_play") as loading,
          pytest.raises(ValueError, match="measured.*exposure")):
        command.main(["--pbp", "source.csv", "--stats-dir", "stats", "--template-season", "template",
                      "--team-map", "map.json", "--output", str(tmp_path / "out"), "--audit-dir", str(tmp_path / "audit"),
                      "--fumble-gain-policy", POLICY, "--fumble-projection-mode", MODE])
    loading.assert_not_called()


@pytest.mark.parametrize("source_games,schedules,measured_games", [
    (1, 1, 1), (2, 1, 1), (2, 2, 3), (2, 2, 4),
])
def test_opt_in_command_allocates_shared_column_once_and_binds_evidence(
    tmp_path: Path, source_games: int, schedules: int, measured_games: int,
) -> None:
    from unittest.mock import patch

    import generate_nflverse_charts as command
    from paydirt.chart_loader import load_team_chart

    stats, template = tmp_path / "stats", tmp_path / "template"
    stats.mkdir()
    template.mkdir()
    (template / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n")
    for code, name in (("AAA", "Alphas"), ("BBB", "Betas")):
        payload = {"season": 2026, "team_name": name, "short_name": code,
                   "offense": {"rushing": {"attempts": 100, "yards": 450, "fumbles": 2, "fumbles_lost": 1},
                               "passing": {"attempts": 100, "completions": 65, "yards": 750}},
                   "defense": {"rushing": {"attempts": 100, "yards": 430},
                               "passing": {"attempts": 100, "completions": 62, "yards": 700}}}
        (stats / f"{name}.json").write_text(json.dumps(payload))
    mapping = tmp_path / "teams.json"
    mapping.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
    rows = [compound()]
    for i in range(2, 26):
        offense, defense = ("AAA", "BBB") if i < 14 else ("BBB", "AAA")
        rows.append({"season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-joint", "play_id": i,
                     "posteam": offense, "defteam": defense, "play_type": "run", "rush_attempt": 1,
                     "yards_gained": 4, "run_location": "middle", "run_gap": "guard", "desc": "Runner for 4 yards."})
    for i, (offense, defense) in enumerate((("AAA", "BBB"), ("BBB", "AAA")), start=26):
        rows.append({"season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-joint", "play_id": i,
                     "posteam": offense, "defteam": defense, "play_type": "pass", "pass_attempt": 1,
                     "interception": 1, "return_team": defense, "return_yards": 4, "air_yards": 5,
                     "yards_gained": 0, "desc": "Pass intercepted and returned 4 yards."})
    if source_games == 2:
        rows[-1]["game_id"] = "synthetic-second-game"
    raw = tmp_path / "source.csv"
    with raw.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set().union(*(r.keys() for r in rows))))
        writer.writeheader()
        writer.writerows(rows)
    with raw.open() as stream:
        serialized = list(csv.DictReader(stream))
    pdf = tmp_path / "evidence.pdf"
    pdf.write_bytes(b"%PDF-1.7\n1 0 obj << /Type /Pages /Count 2 /Kids [2 0 R 3 0 R] >> endobj\n%%EOF")
    review_path = tmp_path / "reviews.json"
    review_path.write_text(json.dumps([{**asdict(r), "evidence_file": "evidence.pdf",
                                       "evidence_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
                                      for r in reviews(serialized[0], losses("own_sack"))]))
    measurement = tmp_path / "measurement.json"
    measurement.write_text(json.dumps({"shared_final_retention_pending": 0, "source_schedules_completed": schedules,
                                      "games_completed": measured_games, "by_team_consumer": {
                                          "AAA:interception": {"retained_terminal_segments": 10, "current_range": [10, 24]},
                                          "BBB:interception": {"retained_terminal_segments": 10, "current_range": [10, 39]}}}))
    exposure = tmp_path / "exposure.json"
    exposure.write_text(json.dumps({"source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                                   "measurement_file": "measurement.json", "measurement_sha256": hashlib.sha256(measurement.read_bytes()).hexdigest(),
                                   "terminal_exposures_by_team": {"AAA": 10 / schedules, "BBB": 10 / schedules},
                                   "fumble_ranges_by_team": {"AAA": [[10, 24], [25, 39]], "BBB": [[10, 39], [0, 0]]}}))
    with patch.object(command, "project_shared_return_column", wraps=command.project_shared_return_column) as allocate:
        argv = ["--pbp", str(raw), "--stats-dir", str(stats), "--template-season", str(template),
                "--team-map", str(mapping), "--output", str(tmp_path / "out"), "--audit-dir", str(tmp_path / "audit"),
                "--fumble-gain-policy", POLICY, "--fumble-projection-mode", MODE,
                "--fumble-loss-reviews", str(review_path), "--shared-return-exposures", str(exposure)]
        if measured_games != source_games * schedules:
            with (patch.object(command, "adjust_empirical_offense", wraps=command.adjust_empirical_offense) as fitting,
                  pytest.raises(ValueError, match="incomplete")):
                command.main(argv)
            fitting.assert_not_called()
            allocate.assert_not_called()
            return
        assert command.main(argv) == 0
    assert allocate.call_count == 2
    assert sum(len(call.kwargs["shared_fumble_outcomes"]) for call in allocate.call_args_list) == 1
    manifest = json.loads((tmp_path / "out/generation-manifest.json").read_text())
    model = manifest["ordered_fumble_projection"]
    assert model["fit_accepted"] is False and len(model["shared_allocations"]) == 2
    assert model["shared_allocations"]["AAA"]["source_shared_fumbles"] == 1
    assert model["primary_range_inputs"]["AAA"]["after"]["passing_F"] == 1
    assert manifest["input_hashes"]["fumble_review_evidence/evidence.pdf"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert manifest["input_hashes"]["projection_code/chart_generator.py"] == hashlib.sha256(Path(command.__file__).parent.joinpath("paydirt/chart_generator.py").read_bytes()).hexdigest()
    joint = json.loads((tmp_path / "audit/joint-fumble-projections.json").read_text())
    assert joint["source_bindings"][0]["raw_play_sha256"] == source.build_fumble_ledger(serialized[0]).raw_play_sha256
    assert joint["source_bindings"][0]["events"][1]["individual_lost"] is True
    assert load_team_chart(tmp_path / "out/Alphas").peripheral.fumble_recovered_range == (10, 24)


@pytest.mark.parametrize("damage", ["none", "missing", "mismatch"])
def test_diagnostic_ranges_are_complete_and_equal_measured_baseline(tmp_path: Path, damage: str) -> None:
    import generate_nflverse_charts as command

    measurement = tmp_path / "measurement.json"
    measurement.write_text(json.dumps({"by_team_consumer": {"AAA:interception": {"current_range": [10, 24]}}}))
    payload = {"measurement_file": "measurement.json", "fumble_ranges_by_team": {"AAA": [[10, 24], [25, 39]]}}
    if damage == "missing":
        payload.pop("fumble_ranges_by_team")
    elif damage == "mismatch":
        payload["fumble_ranges_by_team"] = {"AAA": [[10, 25], [26, 39]]}
    path = tmp_path / "ranges.json"
    path.write_text(json.dumps(payload))
    if damage == "none":
        assert command._load_shared_ranges(path, {"AAA"}) == {"AAA": ((10, 24), (25, 39))}
    else:
        with pytest.raises(ValueError):
            command._load_shared_ranges(path, {"AAA"})


@pytest.fixture
def range_command(tmp_path: Path) -> tuple[list[str], Path, Path]:
    """A complete synthetic ordered source with a deliberately different prior."""
    stats, template = tmp_path / "stats", tmp_path / "template"
    stats.mkdir()
    template.mkdir()
    (template / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n")
    for code, name in (("AAA", "Alphas"), ("BBB", "Betas")):
        payload = {"season": 2026, "team_name": name, "short_name": code,
                   "offense": {"rushing": {"attempts": 100, "yards": 450},
                               "passing": {"attempts": 100, "completions": 65, "yards": 750}},
                   "defense": {"rushing": {"attempts": 100, "yards": 430},
                               "passing": {"attempts": 100, "completions": 62, "yards": 700}}}
        (stats / f"{name}.json").write_text(json.dumps(payload))
    mapping = tmp_path / "teams.json"
    mapping.write_text(json.dumps({"AAA": "Alphas", "BBB": "Betas"}))
    rows = [compound()]
    for i in range(2, 26):
        offense, defense = ("AAA", "BBB") if i < 14 else ("BBB", "AAA")
        rows.append({"season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-joint", "play_id": i,
                     "posteam": offense, "defteam": defense, "play_type": "run", "rush_attempt": 1,
                     "yards_gained": 4, "run_location": "middle", "run_gap": "guard", "desc": "Runner for 4 yards."})
    for i, (offense, defense) in enumerate((("AAA", "BBB"), ("BBB", "AAA")), start=26):
        rows.append({"season_type": "REG", "two_point_attempt": 0, "game_id": "synthetic-joint", "play_id": i,
                     "posteam": offense, "defteam": defense, "play_type": "pass", "pass_attempt": 1,
                     "interception": 1, "return_team": defense, "return_yards": 4, "air_yards": 5,
                     "yards_gained": 0, "desc": "Pass intercepted and returned 4 yards."})
    raw = tmp_path / "source.csv"
    with raw.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set().union(*(r.keys() for r in rows))))
        writer.writeheader()
        writer.writerows(rows)
    with raw.open() as stream:
        serialized = list(csv.DictReader(stream))
    pdf = tmp_path / "evidence.pdf"
    pdf.write_bytes(b"%PDF-1.7\n1 0 obj << /Type /Pages /Count 2 /Kids [2 0 R 3 0 R] >> endobj\n%%EOF")
    review_path = tmp_path / "reviews.json"
    review_path.write_text(json.dumps([{**asdict(r), "evidence_file": "evidence.pdf",
                                       "evidence_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
                                      for r in reviews(serialized[0], losses("own_sack"))]))
    measurement = tmp_path / "measurement.json"
    measurement.write_text(json.dumps({"shared_final_retention_pending": 0, "source_schedules_completed": 1,
                                      "games_completed": 1, "by_team_consumer": {
                                          "AAA:interception": {"retained_terminal_segments": 10, "current_range": [10, 24]},
                                          "BBB:interception": {"retained_terminal_segments": 10, "current_range": [10, 39]}}}))
    exposure = tmp_path / "exposure.json"
    exposure.write_text(json.dumps({"source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                                    "measurement_file": "measurement.json", "measurement_sha256": hashlib.sha256(measurement.read_bytes()).hexdigest(),
                                    "terminal_exposures_by_team": {"AAA": 10, "BBB": 10},
                                    "fumble_ranges_by_team": {"AAA": [[10, 24], [25, 39]], "BBB": [[10, 39], [0, 0]]}}))
    argv = ["--pbp", str(raw), "--stats-dir", str(stats), "--template-season", str(template),
            "--team-map", str(mapping), "--output", str(tmp_path / "out"), "--audit-dir", str(tmp_path / "audit"),
            "--fumble-gain-policy", POLICY, "--fumble-projection-mode", MODE,
            "--fumble-loss-reviews", str(review_path), "--shared-return-exposures", str(exposure)]
    return argv, exposure, tmp_path / "out"


@pytest.mark.parametrize("selected", [None, "measured_diagnostic_v1", "source_primary_v1"])
def test_ordered_range_policy_is_explicit_and_changes_only_range_application(range_command: tuple, selected: str | None) -> None:
    from unittest.mock import patch

    import generate_nflverse_charts as command
    from paydirt.chart_loader import load_team_chart

    argv, _exposure, output = range_command
    if selected is not None:
        argv += ["--fumble-range-policy", selected]
    with patch.object(command, "generate_team_charts", wraps=command.generate_team_charts) as generate:
        assert command.main(argv) == 0
    model = json.loads((output / "generation-manifest.json").read_text())["ordered_fumble_projection"]
    expected = selected or "measured_diagnostic_v1"
    assert model["range_policy"] == expected
    assert model["fit_accepted"] is False
    pair = load_team_chart(output / "Alphas").peripheral.fumble_recovered_range
    if expected == "source_primary_v1":
        assert all(call.kwargs["fumble_range_override"] is None for call in generate.call_args_list)
        assert pair == (10, 39)  # Primary carrier recovers; shared return loss is separate.
        assert model["primary_range_inputs"]["AAA"]["applied_range_cells"] == [[10, 39], [0, 0]]
    else:
        assert generate.call_args_list[0].kwargs["fumble_range_override"] == ((10, 24), (25, 39))
        assert pair == (10, 24)
        assert model["primary_range_inputs"]["AAA"]["applied_range_cells"] == [[10, 24], [25, 39]]


@pytest.mark.parametrize("selected", ["measured_diagnostic_v1", "source_primary_v1"])
@pytest.mark.parametrize("damage", ["source_hash", "measurement_hash", "range_missing", "range_mismatch", "count", "pending"])
def test_source_ranges_never_bypass_measured_receipt_validation(range_command: tuple, selected: str, damage: str) -> None:
    from unittest.mock import patch

    import generate_nflverse_charts as command

    argv, exposure, _output = range_command
    data = json.loads(exposure.read_text())
    if damage == "source_hash":
        data["source_sha256"] = "0" * 64
    elif damage == "measurement_hash":
        data["measurement_sha256"] = "0" * 64
    elif damage == "range_missing":
        data["fumble_ranges_by_team"].pop("AAA")
    elif damage == "range_mismatch":
        data["fumble_ranges_by_team"]["AAA"] = [[10, 25], [26, 39]]
    elif damage == "count":
        data["terminal_exposures_by_team"]["AAA"] = 11
    else:
        path = exposure.parent / "measurement.json"
        report = json.loads(path.read_text())
        report["shared_final_retention_pending"] = 1
        path.write_text(json.dumps(report))
        data["measurement_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    exposure.write_text(json.dumps(data))
    with (patch.object(command, "generate_team_charts", wraps=command.generate_team_charts) as generate,
          pytest.raises(ValueError)):
        command.main([*argv, "--fumble-range-policy", selected])
    generate.assert_not_called()


@pytest.mark.parametrize("selected", ["source_primary_v1", "measured_diagnostic_v1"])
def test_source_range_selection_requires_ordered_projection(range_command: tuple, selected: str) -> None:
    import generate_nflverse_charts as command
    argv, _exposure, _output = range_command
    for flag in ("--fumble-projection-mode", "--fumble-loss-reviews", "--shared-return-exposures"):
        index = argv.index(flag)
        del argv[index:index+2]
    with pytest.raises(ValueError, match="range policy.*ordered"):
        command.main([*argv, "--fumble-range-policy", selected])
