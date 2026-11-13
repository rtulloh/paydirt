"""Reviewed modeled scope never rewrites strict historical source facts."""

import hashlib
import importlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt.historical_fumble_proxy import POLICY_V2, fitting_population
from paydirt.pfr_event_reconciliation import play_fingerprint
from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_reported_fumble_gain import game_with


def scope_api():
    return importlib.import_module("paydirt.pfr_source_scope")


def source():
    game = game_with(
        "Pat Quarterback aborted snap",
        names={
            "pat quarterback": "pat",
            "lee runner": "lee",
            "sam defender": "sam",
        },
    )
    classified = classify_pfr_game(game, fumble_gain_policy=POLICY_V2)
    assert classified.unsupported_fields == (
        {
            "game_id": game.game_id,
            "play_number": 7,
            "team": "FOX",
            "unit": "rushing",
            "field": "initial_gain",
        },
    )
    return game, classified


def scope_document(game):
    return {
        "schema_version": 1,
        "policy": "reviewed_historical_source_scope_v1",
        "season": 2026,
        "historical_source_complete": False,
        "excluded_required_events": [
            {
                "game_id": game.game_id,
                "play_number": game.plays[0].number,
                "team": "FOX",
                "unit": "rushing",
                "field": "initial_gain",
                "raw_game_sha256": "a" * 64,
                "raw_play_sha256": play_fingerprint(game.plays[0]),
                "reason": "Aborted snap gain is unavailable; omit only this fitting observation",
                "scope": "fitting_only",
            }
        ],
        "reviewed_diagnostics": [],
        "known_partial_games": [],
    }


def load(tmp_path, document):
    path = tmp_path / "reviewed-scope.json"
    path.write_text(json.dumps(document))
    return scope_api().load_source_scope(path)


def test_aborted_snap_opt_in_removes_only_fitting_blocker_and_retains_strict_record(tmp_path):
    game, classified = source()
    original = deepcopy(classified)
    scope = load(tmp_path, scope_document(game))
    fitted = scope.review_game(game, classified, raw_sha256="a" * 64)
    assert fitted.unsupported_fields == ()
    assert fitted.diagnostics == classified.diagnostics
    assert fitted.plays == classified.plays == ()
    assert fitting_population(game, fitted, raw_sha256="a" * 64) == ((), [])
    assert classified == original and classified.unsupported_fields
    scope.assert_all_applied()
    assert scope.disclosure() == scope_document(game)
    assert scope_api().validate_source_scope_disclosure(scope.disclosure()) == {
        "missing_required_gains": 1
    }


def test_no_opt_in_still_fails_original_fitting_gate():
    game, classified = source()
    with pytest.raises(ValueError, match="unrelated required"):
        fitting_population(game, classified, raw_sha256="a" * 64)


@pytest.mark.parametrize(
    "damage", ["raw_game", "raw_play", "number", "team", "field", "scope", "truth"]
)
def test_scope_rejects_changed_identity_or_truth_claim(tmp_path, damage):
    game, classified = source()
    document = scope_document(game)
    record = document["excluded_required_events"][0]
    if damage == "raw_game":
        record["raw_game_sha256"] = "b" * 64
    elif damage == "raw_play":
        record["raw_play_sha256"] = "b" * 64
    elif damage == "number":
        record["play_number"] = 8
    elif damage == "team":
        record["team"] = "OWL"
    elif damage == "field":
        record["field"] = "fumble_gain_projection"
    elif damage == "scope":
        record["scope"] = "source_truth"
    else:
        document["historical_source_complete"] = True
    with pytest.raises(ValueError):
        load(tmp_path, document).review_game(game, classified, raw_sha256="a" * 64)


def test_scope_cannot_suppress_other_required_gains_or_source_conflicts(tmp_path):
    game, classified = source()
    for changed in [
        replace(game, plays=(replace(game.plays[0], detail="Pat Passer pass complete"),)),
        replace(game, plays=(replace(game.plays[0], detail="Pat Passer fumbles aborted snap"),)),
    ]:
        document = scope_document(changed)
        with pytest.raises(ValueError):
            load(tmp_path, document).review_game(changed, classified, raw_sha256="a" * 64)
    conflicted = replace(classified, source_conflicts=({"reason": "unresolved competing source"},))
    with pytest.raises(ValueError):
        load(tmp_path, scope_document(game)).review_game(game, conflicted, raw_sha256="a" * 64)


def test_reviewed_box_conflict_keeps_diagnostic_and_requires_exact_game_count(tmp_path):
    game, classified = source()
    document = scope_document(game)
    document["reviewed_diagnostics"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "diagnostic": "unreconciled_fumble_box",
            "count": 1,
            "reason": "Raw box and observed inventory disagree; retain both without inventing events",
        }
    ]
    classified = replace(
        classified, diagnostics={**classified.diagnostics, "unreconciled_fumble_box": 1}
    )
    scope = load(tmp_path, document)
    reviewed = scope.review_game(game, classified, raw_sha256="a" * 64)
    assert reviewed.diagnostics["unreconciled_fumble_box"] == 1
    scope.assert_all_applied()
    assert scope_api().validate_source_scope_disclosure(scope.disclosure()) == {
        "missing_required_gains": 1,
        "unreconciled_fumble_box": 1,
    }
    with pytest.raises(ValueError, match="diagnostic"):
        load(tmp_path, document).review_game(
            game, replace(classified, diagnostics={}), raw_sha256="a" * 64
        )


def test_unused_duplicate_or_unsupported_allowances_fail(tmp_path):
    game, _classified = source()
    document = scope_document(game)
    with pytest.raises(ValueError, match="Unused"):
        load(tmp_path, document).assert_all_applied()
    document["excluded_required_events"] *= 2
    with pytest.raises(ValueError, match="Duplicate"):
        load(tmp_path, document)
    document = scope_document(game)
    document["reviewed_diagnostics"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "diagnostic": "unknown_fumble_recoveries",
            "count": 1,
            "reason": "not authorized",
        }
    ]
    with pytest.raises(ValueError):
        load(tmp_path, document)


def test_known_partial_game_is_preserved_and_hash_bound(tmp_path):
    game, classified = source()
    document = scope_document(game)
    document["known_partial_games"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "reason": "Source publisher reports an incomplete stretch; missing plays are not reconstructed",
        }
    ]
    scope = load(tmp_path, document)
    scope.review_game(game, classified, raw_sha256="a" * 64)
    scope.assert_all_applied()
    assert scope.disclosure()["known_partial_games"] == document["known_partial_games"]
    with pytest.raises(ValueError):
        load(tmp_path, document).review_game(game, classified, raw_sha256="b" * 64)


def test_aborted_snap_scope_does_not_hide_other_fields_on_same_event(tmp_path):
    game, classified = source()
    other = {**classified.unsupported_fields[0], "field": "other_required"}
    classified = replace(classified, unsupported_fields=(*classified.unsupported_fields, other))
    fitted = load(tmp_path, scope_document(game)).review_game(game, classified, raw_sha256="a" * 64)
    assert fitted.unsupported_fields == (other,)


def test_generator_uses_reviewed_fitting_copy_but_ledgers_strict_source(tmp_path):
    from generate_pfr_charts import _classify_directory
    from paydirt.historical_fumble_proxy import FITTING_POLICY
    from paydirt.pfr_play_by_play import parse_pfr_boxscore
    from tests.test_pfr_play_by_play import _game_html, _row

    html = _game_html(
        _row(
            7, "4", "1", "PHI 10", '<a href="/players/P/PassPh00.htm">Phil Passer</a> aborted snap'
        )
    )
    # Avoid the unrelated broad surname pass detector in this synthetic source.
    html = html.replace("Phil Passer", "Phil Quarterback").replace("1983.htm", "2026.htm")
    source_dir = tmp_path / "html"
    source_dir.mkdir()
    path = source_dir / "synthetic-2026.html"
    path.write_text(html)
    game = parse_pfr_boxscore(html, path.stem)
    document = scope_document(game)
    record = document["excluded_required_events"][0]
    record.update(team="PHI", raw_game_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="unrelated required"):
        _classify_directory(
            source_dir,
            None,
            8306,
            fumble_gain_policy=POLICY_V2,
            fumble_exclusion_policy=FITTING_POLICY,
        )
    ledger_path = tmp_path / "ledger.json"
    result = _classify_directory(
        source_dir,
        None,
        8306,
        ledger_path,
        fumble_gain_policy=POLICY_V2,
        fumble_exclusion_policy=FITTING_POLICY,
        source_scope=load(tmp_path, document),
    )
    assert result[3]["missing_required_gains"] == 1
    ledger = json.loads(ledger_path.read_text())
    assert ledger["games"][0]["unsupported_required_fields"][0]["field"] == "initial_gain"
    assert ledger["reviewed_source_scope"] == document


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "missing_contract",
        "extra_count",
        "false_truth",
        "wrong_season",
        "missing_input",
        "input_mismatch",
    ],
)
def test_generated_audit_requires_exact_reviewed_scope_opt_in(tmp_path, damage):
    from paydirt.historical_fumble_proxy import FITTING_POLICY, fitting_metadata, policy_metadata
    from paydirt.pfr_play_by_play import FumbleEvent
    from tests.test_generated_source_audit import _audit, _contract, generated_source

    season, stats = generated_source.__wrapped__(tmp_path)
    manifest_path = season / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    game, _classified = source()
    document = scope_document(game)
    document["reviewed_diagnostics"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "diagnostic": "unreconciled_fumble_box",
            "count": 1,
            "reason": "Retain source contradiction",
        }
    ]
    full = [
        FumbleEvent("Ironclads", "rushing", False, "synthetic-2026", 1),
        FumbleEvent("Thunderhawks", "passing", True, "synthetic-2026", 2),
    ]
    fitting = fitting_metadata(FITTING_POLICY, full, full, [])
    manifest.update(
        fumble_gain_policy=POLICY_V2,
        fumble_fitting_policy=fitting,
        reviewed_source_scope=document,
        diagnostics={"missing_required_gains": 1, "unreconciled_fumble_box": 1},
    )
    manifest.update(policy_metadata(POLICY_V2, manifest["diagnostics"]))
    manifest["input_hashes"]["source_scope/reviewed.json"] = "c" * 64
    if damage == "extra_count":
        manifest["diagnostics"]["unreconciled_fumble_box"] = 2
    elif damage == "false_truth":
        document["historical_source_complete"] = True
    elif damage == "wrong_season":
        document["season"] = 2027
    elif damage == "missing_input":
        del manifest["input_hashes"]["source_scope/reviewed.json"]
    input_files = None
    if damage == "input_mismatch":
        different = deepcopy(document)
        different["excluded_required_events"][0]["reason"] = (
            "A different unapproved scope interpretation"
        )
        scope_path = tmp_path / "different-scope.json"
        scope_path.write_text(json.dumps(different))
        manifest["input_hashes"]["source_scope/reviewed.json"] = hashlib.sha256(
            scope_path.read_bytes()
        ).hexdigest()
        input_files = {
            label: stats / Path(label).name
            for label in manifest["input_hashes"]
            if label.startswith("normalized_stats/")
        }
        input_files["source_scope/reviewed.json"] = scope_path
    manifest_path.write_text(json.dumps(manifest))
    contract = _contract(season)
    contract.update(
        fumble_fitting_policy=fitting,
        reviewed_source_scope=deepcopy(document),
        modeled_fumble_assumptions=manifest["modeled_fumble_assumptions"],
    )
    if damage == "missing_contract":
        del contract["reviewed_source_scope"]
    report = _audit(season, validation_contract=contract, input_files=input_files)
    assert report["passed"] is (damage is None), report["errors"]
    if damage is None:
        assert report["checks"]["reviewed_source_scope"] is True
        assert report["checks"]["historical_source_complete"] is False


def test_field_goal_scope_requires_complete_team_attempt_and_make_totals(tmp_path):
    from paydirt.pfr_play_by_play import FieldGoalAttempt

    game, classified = source()
    document = scope_document(game)
    document["reviewed_diagnostics"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "diagnostic": "unreconciled_field_goal_box",
            "count": 1,
            "reason": "Actor labels differ but complete team attempt/make counts match",
        }
    ]
    game = replace(game, field_goal_box={"actual-kicker": ("FOX", 1, 0)})
    classified = replace(
        classified,
        diagnostics={**classified.diagnostics, "unreconciled_field_goal_box": 1},
        field_goals=(FieldGoalAttempt("FOX", 36, False, game.game_id, 8),),
    )
    scope = load(tmp_path, document)
    scope.review_game(game, classified, raw_sha256="a" * 64)
    scope.assert_all_applied()
    for wrong in [None, {"actual-kicker": ("FOX", 2, 0)}, {"actual-kicker": ("FOX", 1, 1)}]:
        with pytest.raises(ValueError, match="field.goal|Field.goal"):
            load(tmp_path, document).review_game(
                replace(game, field_goal_box=wrong), classified, raw_sha256="a" * 64
            )


@pytest.mark.parametrize(
    "damage", [None, "missing_flag", "missing_contract", "wrong_path", "changed_source"]
)
def test_portable_recipe_binds_exact_scope_input_flag_and_contract(tmp_path, monkeypatch, damage):
    from paydirt.historical_fumble_proxy import FITTING_POLICY, fitting_metadata, policy_metadata
    from tests.test_chart_source_bundle import bundle_files, digest, inventory, prepare

    files = bundle_files.__wrapped__(tmp_path)
    bundle, candidate, *_ = files
    game, _ = source()
    document = scope_document(game)
    scope_path = bundle / "inputs/source_scope/reviewed.json"
    scope_path.parent.mkdir()
    scope_path.write_text(json.dumps(document))
    manifest_path = candidate / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    fitting = fitting_metadata(FITTING_POLICY, [], [], [])
    diagnostics = {"modeled_fumble_classes": 0}
    manifest.update(
        fumble_gain_policy=POLICY_V2,
        fumble_fitting_policy=fitting,
        reviewed_source_scope=document,
        diagnostics=diagnostics,
    )
    manifest.update(policy_metadata(POLICY_V2, diagnostics))
    manifest["input_hashes"]["source_scope/reviewed.json"] = digest(scope_path)
    manifest_path.write_text(json.dumps(manifest))
    contract_path = bundle / "contract.json"
    contract = json.loads(contract_path.read_text())
    contract.update(
        input_hashes=manifest["input_hashes"],
        fumble_fitting_policy=fitting,
        modeled_fumble_assumptions=manifest["modeled_fumble_assumptions"],
        reviewed_source_scope=document,
        generation_manifest_sha256=digest(manifest_path),
    )
    if damage == "missing_contract":
        contract.pop("reviewed_source_scope")
    contract_path.write_text(json.dumps(contract))
    recipe_path = bundle / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["generator_script"] = "generate_pfr_charts.py"
    recipe["expected_input_hashes"] = manifest["input_hashes"]
    args = recipe["arguments"]
    index = args.index("--pbp")
    args[index : index + 2] = ["--html-dir", "inputs/play_by_play"]
    args += ["--fumble-gain-policy", POLICY_V2, "--fumble-exclusion-policy", FITTING_POLICY]
    if damage != "missing_flag":
        args += [
            "--source-scope",
            "inputs/source_scope/reviewed.json"
            if damage != "wrong_path"
            else "inputs/team_map/map.json",
        ]
    recipe_path.write_text(json.dumps(recipe))
    inventory(bundle)
    if damage == "changed_source":
        scope_path.write_text("{}")
    result = prepare(files, monkeypatch)
    assert result["passed"] is (damage is None), result["errors"]


def sack_scope_document(game):
    document = scope_document(game)
    document["reviewed_sack_counts"] = [
        {
            "game_id": game.game_id,
            "raw_game_sha256": "a" * 64,
            "team": "FOX",
            "pbp_sacks": 1,
            "box_sacks": 0,
            "reason": "PBP describes a zero-gain sack; box credits none; retain both accounts",
        }
    ]
    return document


def sack_box_html(away="0-0", home="2-10"):
    return (
        '<table id="team_stats"><tr><th data-stat="stat">Sacked-Yards</th>'
        f'<td data-stat="vis_stat">{away}</td><td data-stat="home_stat">{home}</td>'
        "</tr></table>"
    )


@pytest.mark.parametrize("damage", [None, "pbp", "box", "missing", "wrong_raw", "equal_counts"])
def test_sack_scope_binds_both_observed_and_box_counts_without_rewriting_events(tmp_path, damage):
    game, classified = source()
    classified = replace(classified, event_counts={"FOX": {"sacks": 1}})
    document = sack_scope_document(game)
    html = sack_box_html()
    if damage == "pbp":
        document["reviewed_sack_counts"][0]["pbp_sacks"] = 2
    elif damage == "box":
        html = sack_box_html(away="1-8")
    elif damage == "missing":
        html = "<html></html>"
    elif damage == "wrong_raw":
        document["reviewed_sack_counts"][0]["raw_game_sha256"] = "b" * 64
    elif damage == "equal_counts":
        document["reviewed_sack_counts"][0]["box_sacks"] = 1
    if damage:
        with pytest.raises(ValueError):
            load(tmp_path, document).review_game(
                game, classified, raw_sha256="a" * 64, raw_html=html
            )
    else:
        reviewed = load(tmp_path, document).review_game(
            game, classified, raw_sha256="a" * 64, raw_html=html
        )
        assert reviewed.event_counts == classified.event_counts
        assert reviewed.plays == classified.plays
        assert reviewed.diagnostics == classified.diagnostics


@pytest.mark.parametrize(
    "damage", [None, "extra_pbp", "wrong_team", "wrong_box", "missing_scope", "disappeared"]
)
def test_audit_keeps_exact_reviewed_sack_count_difference_as_finding(tmp_path, damage):
    from paydirt.historical_fumble_proxy import FITTING_POLICY, fitting_metadata, policy_metadata
    from paydirt.pfr_play_by_play import FumbleEvent
    from tests.test_generated_source_audit import _audit, _contract, generated_source

    season, _stats = generated_source.__wrapped__(tmp_path)
    path = season / "generation-manifest.json"
    manifest = json.loads(path.read_text())
    game, _ = source()
    document = sack_scope_document(game)
    document["excluded_required_events"] = []
    document["reviewed_sack_counts"][0]["team"] = "IRON"
    full = [
        FumbleEvent("Ironclads", "rushing", False, "synthetic-2026", 1),
        FumbleEvent("Thunderhawks", "passing", True, "synthetic-2026", 2),
    ]
    manifest.update(
        fumble_gain_policy=POLICY_V2,
        fumble_fitting_policy=fitting_metadata(FITTING_POLICY, full, full, []),
        reviewed_source_scope=document,
        diagnostics={"sacks": 1},
    )
    manifest.update(policy_metadata(POLICY_V2, manifest["diagnostics"]))
    manifest["teams"]["Ironclads"]["pfr_team"] = "IRON"
    manifest["teams"]["Thunderhawks"]["pfr_team"] = "THUN"
    manifest["fumble_fitting_policy"]["teams"] = {
        "IRON": manifest["fumble_fitting_policy"]["teams"]["Ironclads"],
        "THUN": manifest["fumble_fitting_policy"]["teams"]["Thunderhawks"],
    }
    manifest["teams"]["Ironclads"]["source_event_counts"]["sacks"] = 1
    manifest["input_hashes"]["source_scope/reviewed.json"] = "c" * 64
    if damage == "extra_pbp":
        manifest["teams"]["Ironclads"]["source_event_counts"]["sacks"] = 2
        manifest["diagnostics"]["sacks"] = 2
    elif damage == "wrong_team":
        document["reviewed_sack_counts"][0]["team"] = "THUN"
    elif damage == "wrong_box":
        document["reviewed_sack_counts"][0].update(pbp_sacks=2, box_sacks=1)
    elif damage == "missing_scope":
        document["reviewed_sack_counts"] = []
    path.write_text(json.dumps(manifest))
    contract = _contract(season)
    contract.update(
        fumble_fitting_policy=manifest["fumble_fitting_policy"],
        modeled_fumble_assumptions=manifest["modeled_fumble_assumptions"],
        reviewed_source_scope=document,
    )
    if damage == "disappeared":
        for team in manifest["teams"].values():
            team["source_event_counts"]["sacks"] = 10
        manifest["diagnostics"]["sacks"] = 20
        path.write_text(json.dumps(manifest))
        for team in contract["teams"].values():
            team["counts"]["sacks"] = 10
            team["rates"]["sack_rate"] = 10 / 110
        contract["league"]["counts"]["sacks"] = 20
        contract["league"]["rates"]["sack_rate"] = 20 / 220
        contract["targets"]["sack_rate"]["value"] = 20 / 220
    report = _audit(season, validation_contract=contract)
    assert report["passed"] is (damage is None), report["errors"]
    if damage is None:
        assert manifest["diagnostics"]["sacks"] == 1
        assert contract["league"]["counts"]["sacks"] == 0
        assert report["checks"]["historical_source_complete"] is False
        assert any(item["code"] == "reviewed-sack-count-discrepancy" for item in report["findings"])
