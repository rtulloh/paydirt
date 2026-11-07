"""Synthetic controls for independently reviewed PFR sack event facts."""

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from paydirt.pfr_play_by_play import PfrGame, PfrPlay, classify_pfr_game


def _game(
    detail: str = "Pat Quarterback for no gain. Pat Quarterback fumbles, recovered by Pat Quarterback at FOX 28",
) -> PfrGame:
    return PfrGame(
        "synthetic-game",
        "FOX",
        "OWL",
        {"passer": "FOX"},
        {"passer": "QB"},
        {"pat quarterback": "passer"},
        (PfrPlay("synthetic-game", 7, 4, "2:10", 2, 2, "FOX 30", 0, 0, detail, ("passer",)),),
    )


def _play_hash(play: PfrPlay) -> str:
    return hashlib.sha256(
        (json.dumps(asdict(play), sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


def _sidecar(tmp_path: Path, game: PfrGame | None = None) -> tuple[Path, dict]:
    game = game or _game()
    evidence = tmp_path / "reviewed-gamebook.pdf"
    evidence.write_bytes(b"synthetic reviewed evidence; no real season data")
    record = {
        "game_id": game.game_id,
        "play_number": game.plays[0].number,
        "raw_game_sha256": hashlib.sha256(b"synthetic raw HTML").hexdigest(),
        "raw_play_sha256": _play_hash(game.plays[0]),
        "credited_sack": True,
        "credited_sack_loss": 2,
        "initial_gain": None,
        "evidence": [
            {
                "file": evidence.name,
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                "url": "https://example.org/official/gamebook.pdf",
                "pages": [3, 9],
            }
        ],
    }
    path = tmp_path / "reconciliations.json"
    path.write_text(json.dumps({"schema_version": 1, "events": [record]}))
    return path, record


def _load(path: Path):
    from paydirt.pfr_event_reconciliation import load_event_reconciliations

    return load_event_reconciliations(path)


def test_credited_sack_and_fumble_survive_unknown_physical_initial_gain(tmp_path: Path) -> None:
    game = _game()
    path, record = _sidecar(tmp_path, game)
    facts = _load(path).for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts)
    assert result.event_counts["FOX"]["sacks"] == 1
    assert result.diagnostics["reconciled_sacks"] == 1
    assert result.diagnostics["unclassified_sacks"] == 1
    assert not result.plays  # Neither no-gain prose nor credited loss invents a QT cell.
    assert len(result.fumbles) == 1
    assert result.fumbles[0].unit == "passing"
    assert result.fumbles[0].lost is False
    assert game.plays[0].detail == _game().plays[0].detail


@pytest.mark.parametrize("initial_gain,expected", [(0, "F"), (-2, "F - 2")])
def test_known_initial_gain_is_separate_from_credited_loss(
    tmp_path: Path,
    initial_gain: int,
    expected: str,
) -> None:
    path, record = _sidecar(tmp_path)
    record["initial_gain"] = initial_gain
    path.write_text(json.dumps({"schema_version": 1, "events": [record]}))
    facts = _load(path).for_game(_game(), record["raw_game_sha256"])
    result = classify_pfr_game(_game(), event_facts=facts)
    assert result.event_counts["FOX"]["sacks"] == 1
    assert [play.result for play in result.plays] == ["QT", expected]
    assert result.diagnostics.get("unclassified_sacks", 0) == 0
    assert result.fumbles[0].unit == "passing"


@pytest.mark.parametrize("initial_gain,expected", [(0, "SACK 0"), (-2, "-2")])
def test_nonfumble_zero_sack_stays_distinct(
    tmp_path: Path, initial_gain: int, expected: str
) -> None:
    game = _game("Pat Quarterback tackled behind the line")
    path, record = _sidecar(tmp_path, game)
    record["initial_gain"] = initial_gain
    path.write_text(json.dumps({"schema_version": 1, "events": [record]}))
    result = classify_pfr_game(
        game, event_facts=_load(path).for_game(game, record["raw_game_sha256"])
    )
    assert [play.result for play in result.plays] == ["QT", expected]
    assert not result.fumbles


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "unknown_field",
        "bool_play",
        "negative_loss",
        "positive_initial",
        "bool_initial",
        "no_sack",
        "no_evidence",
        "bad_hash",
        "bad_evidence_bytes",
        "http_url",
        "zero_page",
        "bool_page",
        "duplicate_page",
        "outside_file",
        "absolute_file",
        "extra_evidence_field",
        "empty_events",
    ],
)
def test_malformed_or_unbound_facts_fail(tmp_path: Path, mutation: str) -> None:
    path, record = _sidecar(tmp_path)
    events = [record]
    if mutation == "duplicate":
        events.append(dict(record))
    elif mutation == "unknown_field":
        record["chart_result"] = "TD"
    elif mutation == "bool_play":
        record["play_number"] = True
    elif mutation == "negative_loss":
        record["credited_sack_loss"] = -2
    elif mutation == "positive_initial":
        record["initial_gain"] = 2
    elif mutation == "bool_initial":
        record["initial_gain"] = False
    elif mutation == "no_sack":
        record["credited_sack"] = False
    elif mutation == "no_evidence":
        record["evidence"] = []
    elif mutation == "bad_hash":
        record["raw_play_sha256"] = "not-a-hash"
    elif mutation == "bad_evidence_bytes":
        (tmp_path / record["evidence"][0]["file"]).write_bytes(b"changed")
    elif mutation == "http_url":
        record["evidence"][0]["url"] = "http://example.org/gamebook.pdf"
    elif mutation == "zero_page":
        record["evidence"][0]["pages"] = [0]
    elif mutation == "bool_page":
        record["evidence"][0]["pages"] = [True]
    elif mutation == "duplicate_page":
        record["evidence"][0]["pages"] = [3, 3]
    elif mutation == "outside_file":
        record["evidence"][0]["file"] = "../reviewed-gamebook.pdf"
    elif mutation == "absolute_file":
        record["evidence"][0]["file"] = str(tmp_path / "reviewed-gamebook.pdf")
    elif mutation == "extra_evidence_field":
        record["evidence"][0]["reviewed"] = True
    elif mutation == "empty_events":
        events = []
    path.write_text(json.dumps({"schema_version": 1, "events": events}))
    with pytest.raises(ValueError):
        _load(path)


@pytest.mark.parametrize(
    "mutation",
    [
        "raw_bytes",
        "play_context",
        "missing_play",
        "nullified",
        "offsetting",
        "offset",
        "wrong_game",
    ],
)
def test_facts_are_bound_to_eligible_source_event(tmp_path: Path, mutation: str) -> None:
    from dataclasses import replace

    game = _game()
    path, record = _sidecar(tmp_path, game)
    raw_hash = record["raw_game_sha256"]
    if mutation == "raw_bytes":
        raw_hash = "0" * 64
    elif mutation == "play_context":
        game = replace(game, plays=(replace(game.plays[0], down=3),))
    elif mutation == "missing_play":
        game = replace(game, plays=())
    elif mutation == "wrong_game":
        game = replace(game, game_id="different-game")
    else:
        game = _game(
            game.plays[0].detail
            + (
                " (no play)"
                if mutation == "nullified"
                else " (offset)"
                if mutation == "offset"
                else " offsetting penalties"
            )
        )
        record["raw_play_sha256"] = _play_hash(game.plays[0])
        path.write_text(json.dumps({"schema_version": 1, "events": [record]}))
    loaded = _load(path)
    with pytest.raises(ValueError):
        loaded.for_game(game, raw_hash)
        loaded.assert_all_applied()


def test_unused_evidence_fails_and_valid_inventory_binds_every_input(tmp_path: Path) -> None:
    path, record = _sidecar(tmp_path)
    loaded = _load(path)
    with pytest.raises(ValueError, match="[Uu]nused"):
        loaded.assert_all_applied()
    facts = loaded.for_game(_game(), record["raw_game_sha256"])
    loaded.assert_all_applied()
    assert len(facts) == 1
    assert set(loaded.input_paths) == {path, tmp_path / "reviewed-gamebook.pdf"}
    assert facts[7].to_dict()["credited_sack_loss"] == 2
    assert facts[7].to_dict()["initial_gain"] is None


def test_ordinary_source_control_keeps_existing_classification() -> None:
    game = _game()
    result = classify_pfr_game(game)
    assert result.diagnostics.get("sacks", 0) == 0
    assert result.fumbles[0].unit == "rushing"
    assert result.fumbles[0].lost is False


def test_same_event_cannot_be_applied_twice(tmp_path: Path) -> None:
    path, record = _sidecar(tmp_path)
    loaded = _load(path)
    loaded.for_game(_game(), record["raw_game_sha256"])
    with pytest.raises(ValueError, match="already applied"):
        loaded.for_game(_game(), record["raw_game_sha256"])


def test_legacy_unknown_sack_preserves_fumble_occurrence_without_severity() -> None:
    result = classify_pfr_game(
        _game(
            "Pat Quarterback sacked by Unknown Defender. Pat Quarterback fumbles, recovered by Pat Quarterback at FOX 28",
        )
    )
    assert result.event_counts["FOX"]["sacks"] == 1
    assert result.diagnostics["unclassified_sacks"] == 1
    assert not result.plays
    assert len(result.fumbles) == 1
    assert result.fumbles[0].unit == "passing"
    assert result.fumbles[0].lost is False


@pytest.mark.parametrize(
    "known_recovery,missing_gain,box_conflict",
    [(True, False, False), (False, False, False), (True, True, False), (True, False, True)],
)
@pytest.mark.parametrize("schema_version", [1, 2])
def test_root_generation_binds_applied_facts_and_evidence_bytes(
    tmp_path: Path,
    known_recovery: bool,
    missing_gain: bool,
    box_conflict: bool,
    schema_version: int,
) -> None:
    from generate_pfr_charts import main
    from paydirt.pfr_play_by_play import parse_pfr_boxscore

    html_dir = tmp_path / "html"
    stats_dir = tmp_path / "stats"
    template_dir = tmp_path / "template"
    html_dir.mkdir()
    stats_dir.mkdir()
    template_dir.mkdir()
    (template_dir / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n")
    html = """<table id="player_offense"><tr>
      <th data-stat="player" data-append-csv="q">Pat Quarterback</th>
      <td data-stat="team">FOX</td><td data-stat="pos">QB</td></tr></table>
    <table id="pbp"><thead><tr>
      <th data-stat="pbp_score_aw" aria-label="FOX">FOX</th>
      <th data-stat="pbp_score_hm" aria-label="OWL">OWL</th></tr></thead><tbody>
      <tr><td data-stat="down">2</td><td data-stat="yds_to_go">2</td>
      <td data-stat="detail"><a href="/players/Q/q.htm">Pat Quarterback</a> for no gain.
      Pat Quarterback fumbles, recovered by Pat Quarterback at FOX 28</td></tr>
      <tr><td data-stat="down">3</td><td data-stat="yds_to_go">4</td>
      <td data-stat="detail"><a href="/players/Q/q.htm">Pat Quarterback</a> middle for 5 yards</td></tr>
    </tbody></table>"""
    raw = html_dir / "202609010fox.htm"
    if not known_recovery:
        html = html.replace("recovered by Pat Quarterback", "recovered by Mystery Actor")
    html = html.replace(
        "</tbody></table>",
        """<tr><td data-stat="down">1</td>
      <td data-stat="yds_to_go">10</td><td data-stat="detail">
      <a href="/players/Q/q.htm">Pat Quarterback</a> middle for 3 yards</td></tr></tbody></table>""",
    )
    if missing_gain:
        html = html.replace("middle for 5 yards", "left tackle")
    if box_conflict:
        html += """<table id="team_stats"><tr><th data-stat="stat">Fumbles-Lost</th>
        <td data-stat="vis_stat">0-0</td><td data-stat="home_stat">0-0</td></tr></table>"""
    raw.write_text(html)
    game = parse_pfr_boxscore(html, raw.stem)
    sidecar, record = _sidecar(tmp_path, game)
    record["raw_game_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps({"schema_version": schema_version, "events": [record]}))
    stats = {
        "season": 2026,
        "team_name": "Foxes",
        "short_name": "FOX",
        "offense": {
            "rushing": {"attempts": 100, "yards": 400},
            "passing": {"attempts": 100, "completions": 60, "yards": 700, "sacks": 1},
        },
        "defense": {
            "rushing": {"attempts": 100, "yards": 400},
            "passing": {"attempts": 100, "completions": 60, "yards": 700},
        },
    }
    (stats_dir / "Foxes.json").write_text(json.dumps(stats))
    team_map = tmp_path / "teams.json"
    team_map.write_text(json.dumps({"FOX": "Foxes"}))
    output = tmp_path / "output"
    audit = tmp_path / "audit"
    arguments = [
        "--html-dir",
        str(html_dir),
        "--stats-dir",
        str(stats_dir),
        "--template-season",
        str(template_dir),
        "--team-map",
        str(team_map),
        "--output",
        str(output),
        "--audit-dir",
        str(audit),
        "--event-reconciliations",
        str(sidecar),
    ]
    if not known_recovery:
        with pytest.raises(ValueError, match="unknown fumble recovery"):
            main(arguments)
        ledger = json.loads((audit / "source-ledger.json").read_text())
        assert ledger["games"][0]["fumble_events"][0]["lost"] is None
        assert ledger["games"][0]["fumble_events"][0]["play_number"] == 1
        assert not (output / "generation-manifest.json").exists()
        return
    if missing_gain:
        with pytest.raises(ValueError, match="missing required gain"):
            main(arguments)
        ledger = json.loads((audit / "source-ledger.json").read_text())
        assert ledger["games"][0]["diagnostics"]["missing_required_gains"] == 1
        assert ledger["games"][0]["unsupported_required_fields"] == [
            {
                "game_id": raw.stem,
                "play_number": 2,
                "team": "FOX",
                "unit": "rushing",
                "field": "initial_gain",
            }
        ]
        assert not (output / "generation-manifest.json").exists()
        return
    if box_conflict:
        with pytest.raises(ValueError, match="inconsistent fumble box"):
            main(arguments)
        assert not (output / "generation-manifest.json").exists()
        return
    assert main(arguments) == 0
    manifest = json.loads((output / "generation-manifest.json").read_text())
    assert manifest["diagnostics"]["sacks"] == 1
    assert manifest["event_reconciliations"]["applied_events"] == 1
    assert manifest["event_reconciliations"]["schema_version"] == schema_version
    for path in [sidecar, tmp_path / "reviewed-gamebook.pdf"]:
        assert (
            manifest["input_hashes"][f"event_reconciliations/{path.name}"]
            == hashlib.sha256(path.read_bytes()).hexdigest()
        )
    ledger = json.loads((audit / "source-ledger.json").read_text())
    assert ledger["games"][0]["event_reconciliations"] == [record]
    assert ledger["games"][0]["fumble_events"] == [
        {
            "game_id": raw.stem,
            "play_number": 1,
            "team": "FOX",
            "unit": "passing",
            "lost": False,
            "retained_incompletion": False,
            "field_goal_snap_result": "",
        }
    ]
    assert ledger["games"][0]["event_counts"]["FOX"]["sacks"] == 1
    assert not any(play["play_number"] == 1 for play in ledger["games"][0]["representations"])


def _fumble_sidecar(tmp_path: Path, game: PfrGame) -> tuple[Path, dict]:
    path, record = _sidecar(tmp_path, game)
    for field in ("credited_sack", "credited_sack_loss", "initial_gain"):
        del record[field]
    record.update(kind="fumble", fumble_lost=False, out_of_bounds=True)
    path.write_text(json.dumps({"schema_version": 2, "events": [record]}))
    return path, record


@pytest.mark.parametrize("lost", [False, True])
def test_reviewed_recovery_preserves_gain_and_does_not_credit_sack(
    tmp_path: Path, lost: bool
) -> None:
    game = _game("Pat Quarterback pass complete to River Runner for 7 yards. River Runner fumbles")
    path, record = _fumble_sidecar(tmp_path, game)
    record.update(fumble_lost=lost, out_of_bounds=not lost)
    path.write_text(json.dumps({"schema_version": 2, "events": [record]}))
    loaded = _load(path)
    facts = loaded.for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts)
    loaded.assert_all_applied()
    assert [play.result for play in result.plays] == ["F + 7"]
    assert result.fumbles[0].lost is lost
    assert result.fumbles[0].unit == "passing"
    assert result.event_counts.get("FOX", {}).get("sacks", 0) == 0
    assert result.diagnostics["reconciled_fumble_recoveries"] == 1
    assert result.diagnostics.get("reconciled_fumble_out_of_bounds", 0) == int(not lost)
    assert facts[7].to_dict() == record


@pytest.mark.parametrize("initial,expected", [(-5, "F - 5"), (0, "F"), (None, None)])
def test_reviewed_completion_gain_is_not_recovery_movement(
    tmp_path: Path, initial: int | None, expected: str | None
) -> None:
    game = _game(
        "Pat Quarterback pass complete, recovered by Pat Quarterback at FOX 25 "
        "to River Runner for -5 yards. River Runner fumbles"
    )
    path, record = _fumble_sidecar(tmp_path, game)
    record["initial_gain"] = initial
    path.write_text(json.dumps({"schema_version": 2, "events": [record]}))
    result = classify_pfr_game(
        game, event_facts=_load(path).for_game(game, record["raw_game_sha256"])
    )
    assert [play.result for play in result.plays] == ([] if expected is None else [expected])
    assert result.fumbles[0].lost is False
    assert result.fumbles[0].unit == "passing"
    assert result.diagnostics.get("missing_required_gains", 0) == int(initial is None)
    assert result.event_counts.get("FOX", {}).get("sacks", 0) == 0
    assert game.plays[0].detail.endswith("River Runner fumbles")


@pytest.mark.parametrize(
    "mutation",
    ["lost_oob", "bool_gain", "bad_lost", "bad_oob", "schema1", "unknown_field",
     "no_fumble", "special_teams", "known_owner_conflict", "known_gain_conflict", "accepted_penalty"],
)
def test_reviewed_fumble_facts_reject_invalid_or_conflicting_claims(
    tmp_path: Path, mutation: str
) -> None:
    game = _game("Pat Quarterback pass complete to River Runner for 7 yards. River Runner fumbles")
    if mutation == "no_fumble":
        game = _game("Pat Quarterback pass complete to River Runner for 7 yards")
    elif mutation == "special_teams":
        game = _game("Pat Quarterback punts 40 yards. River Runner fumbles")
    elif mutation == "known_owner_conflict":
        game = _game()
    elif mutation == "accepted_penalty":
        game = _game(game.plays[0].detail + ". Penalty on Other Defender: Offside, 5 yards (accepted)")
    path, record = _fumble_sidecar(tmp_path, game)
    if mutation in {"lost_oob", "known_owner_conflict"}:
        record["fumble_lost"] = True
        if mutation == "known_owner_conflict":
            record["out_of_bounds"] = False
    elif mutation == "bool_gain":
        record["initial_gain"] = False
    elif mutation == "bad_lost":
        record["fumble_lost"] = 0
    elif mutation == "bad_oob":
        record["out_of_bounds"] = None
    elif mutation == "unknown_field":
        record["chart_result"] = "BLACK"
    elif mutation == "known_gain_conflict":
        record["initial_gain"] = -5
    path.write_text(json.dumps({"schema_version": 1 if mutation == "schema1" else 2,
                                "events": [record]}))
    with pytest.raises(ValueError):
        facts = _load(path).for_game(game, record["raw_game_sha256"])
        classify_pfr_game(game, event_facts=facts)


def _prepass_game() -> PfrGame:
    game = _game("Pat Quarterback fumbles")
    continuation = replace(game.plays[0], number=8,
                           detail="Pat Quarterback pass incomplete intended for River Runner")
    return replace(game, plays=(*game.plays, continuation))


def _prepass_sidecar(tmp_path: Path, game: PfrGame) -> tuple[Path, dict]:
    path, record = _fumble_sidecar(tmp_path, game)
    record.pop("fumble_lost")
    record.pop("out_of_bounds")
    record.update(kind="prepass_fumble", continuation_play_number=game.plays[1].number,
                  continuation_play_sha256=_play_hash(game.plays[1]))
    path.write_text(json.dumps({"schema_version": 2, "events": [record]}))
    return path, record


def test_split_prepass_fumble_is_one_incompletion_without_extra_rush(tmp_path: Path) -> None:
    game = _prepass_game()
    path, record = _prepass_sidecar(tmp_path, game)
    loaded = _load(path)
    facts = loaded.for_game(game, record["raw_game_sha256"])
    result = classify_pfr_game(game, event_facts=facts)
    loaded.assert_all_applied()
    assert [(p.play_number, p.result) for p in result.plays] == [(8, "BLACK")]
    assert [(f.play_number, f.unit, f.lost) for f in result.fumbles] == [(7, "passing", False)]
    assert result.diagnostics["reconciled_prepass_fumbles"] == 1
    assert result.diagnostics["unmodeled_prepass_fumbles"] == 1
    assert not result.diagnostics.get("missing_required_gains", 0)
    assert not result.diagnostics.get("unknown_fumble_recoveries", 0)
    assert not result.event_counts.get("FOX", {}).get("sacks", 0)
    assert facts[7].to_dict() == record
    assert game == _prepass_game()


@pytest.mark.parametrize(
    "mutation",
    ["missing", "hash", "nonadjacent", "quarter", "down", "distance", "location",
     "actor", "complete", "fumble_again", "nullified_pass", "sacked", "overlap", "not_bare",
     "not_bare_no_period", "unknown_quarter", "unknown_actor_name"],
)
def test_split_prepass_facts_require_one_unambiguous_bound_snap(
    tmp_path: Path, mutation: str
) -> None:
    game = _prepass_game()
    first, following = game.plays
    if mutation == "quarter":
        following = replace(following, quarter=3)
    elif mutation == "down":
        following = replace(following, down=3)
    elif mutation == "distance":
        following = replace(following, yards_to_go=4)
    elif mutation == "location":
        following = replace(following, location="FOX 31")
    elif mutation == "actor":
        following = replace(following, player_ids=("other-passer",))
    elif mutation == "complete":
        following = replace(following, detail="Pat Quarterback pass complete for 7 yards")
    elif mutation == "fumble_again":
        following = replace(following, detail=following.detail + ". Pat Quarterback fumbles")
    elif mutation == "nullified_pass":
        following = replace(following, detail=following.detail + " (no play)")
    elif mutation == "sacked":
        following = replace(following, detail="Pat Quarterback sacked by Unknown Defender")
    elif mutation == "not_bare":
        first = replace(first, detail="Pat Quarterback scrambles for 5 yards. Pat Quarterback fumbles")
    elif mutation == "not_bare_no_period":
        first = replace(first, detail="Pat Quarterback scrambles for 5 yards and fumbles")
    elif mutation == "unknown_quarter":
        first = replace(first, quarter=None)
        following = replace(following, quarter=None)
    elif mutation == "unknown_actor_name":
        first = replace(first, detail="Mystery Actor fumbles")
    game = replace(game, plays=(first, following))
    path, record = _prepass_sidecar(tmp_path, game)
    events = [record]
    if mutation == "hash":
        record["continuation_play_sha256"] = "0" * 64
    elif mutation == "missing":
        game = replace(game, plays=(first,))
    elif mutation == "nonadjacent":
        game = replace(game, plays=(first, replace(first, number=9), following))
    elif mutation == "overlap":
        another = dict(record, play_number=8, raw_play_sha256=_play_hash(following))
        events.append(another)
    path.write_text(json.dumps({"schema_version": 2, "events": events}))
    with pytest.raises(ValueError):
        _load(path).for_game(game, record["raw_game_sha256"])


def test_unreviewed_split_rows_keep_missing_gain_visible() -> None:
    result = classify_pfr_game(_prepass_game())
    assert result.diagnostics["missing_required_gains"] == 1
    assert result.fumbles[0].unit == "rushing"
    assert result.fumbles[0].lost is None
    assert [p.result for p in result.plays] == ["BLACK"]


@pytest.mark.parametrize(
    "detail,expected",
    [
        ("Pat Quarterback rushes for -3 yards", "-3"),
        ("Pat Quarterback for no gain. Pat Quarterback fumbles", "F"),
        ("Pat Quarterback for -3 yards. Pat Quarterback fumbles", "F - 3"),
        ("Pat Quarterback rushes for 5 yards. Pat Quarterback fumbles", "F + 5"),
    ],
)
def test_quarterback_position_alone_does_not_turn_a_rush_into_qt(
    detail: str, expected: str
) -> None:
    result = classify_pfr_game(_game(detail))
    assert [(p.chart, p.result) for p in result.plays] == [("line_plunge", expected)]
    assert result.diagnostics["heuristic_quarterback_run_family"] == 1
    assert not result.event_counts.get("FOX", {}).get("sacks", 0)
    if "fumbles" in detail:
        assert result.fumbles[0].unit == "rushing"


@pytest.mark.parametrize(
    "detail,expected_chart",
    [
        ("Pat Quarterback scrambles for 5 yards", "qb_time"),
        ("Pat Quarterback left end for 5 yards", "end_run"),
        ("Pat Quarterback on a draw for 5 yards", "draw"),
    ],
)
def test_explicit_quarterback_play_families_remain_distinct(
    detail: str, expected_chart: str
) -> None:
    result = classify_pfr_game(_game(detail))
    assert result.plays[0].chart == expected_chart
    assert not result.diagnostics.get("heuristic_quarterback_run_family", 0)
