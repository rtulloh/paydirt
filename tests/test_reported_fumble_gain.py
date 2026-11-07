"""Reported primary gains are model inputs, never invented official credits."""
from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path

import pytest

from paydirt.pfr_play_by_play import PfrGame, PfrPlay, classify_pfr_game
from tests.test_fumble_source_projection import (
    PHYSICAL,
    PROXY,
    _reload_reviewed_fumble,
    fact_values,
)

REPORTED = "source_reported_gain_proxy_v1"


def game_with(detail: str, *, names: dict[str, str] | None = None) -> PfrGame:
    return PfrGame(
        "synthetic-2026", "FOX", "OWL",
        {"pat": "FOX", "lee": "FOX", "sam": "OWL", "alex": "FOX"},
        {"pat": "QB", "lee": "RB", "sam": "LB", "alex": "C"},
        names or {"pat passer": "pat", "lee runner": "lee", "sam defender": "sam", "alex center": "alex"},
        (PfrPlay("synthetic-2026", 7, 1, "10:00", 1, 10, "FOX 40", 0, 0,
                 detail, ("pat", "lee", "sam")),),
    )


def projection_facts(**changes):
    module = importlib.import_module("paydirt.fumble_source")
    return module, module.FumbleGainFacts(**fact_values(**{
        "credited_kind": None, "credited_yards": None, "reported_kind": "rushing",
        "reported_yards": 3, "reported_scope": "primary_before_fumble",
        "reported_actor": "lee", "reported_team": "FOX", "recovery_basis": "reported_identity",
        **changes,
    }))


def test_reported_projection_preserves_unknown_credit_and_physical_facts() -> None:
    module, facts = projection_facts()
    projection = module.project_fumble_gain(facts, policy=REPORTED)
    assert projection.modeled_initial_yards == 3
    assert projection.modeled_gain_basis == "source_reported_proxy"
    assert projection.originating_kind == "rushing"
    assert projection.source_facts.credited_yards is None
    assert projection.source_facts.credited_kind is None
    assert projection.source_facts.physical_initial_yards is None
    assert projection.to_dict()["source_facts"]["reported_yards"] == 3


@pytest.mark.parametrize("fields,expected,basis", [
    ({"credited_kind": "rushing", "credited_yards": 0}, 0, "credited_proxy"),
    ({"credited_kind": "rushing", "credited_yards": 0, "physical_initial_yards": -2}, -2, "physical"),
    ({"physical_initial_yards": 0}, 0, "physical"),
])
def test_reported_policy_prefers_supported_physical_then_reviewed_credit(
    fields: dict, expected: int, basis: str,
) -> None:
    module, facts = projection_facts(**fields)
    projected = module.project_fumble_gain(facts, policy=REPORTED)
    assert (projected.modeled_initial_yards, projected.modeled_gain_basis) == (expected, basis)
    assert projected.source_facts.reported_yards == 3


@pytest.mark.parametrize("fields", [
    {"reported_kind": None}, {"reported_kind": "quarterback"},
    {"reported_yards": None}, {"reported_yards": True}, {"reported_yards": 1.5},
    {"reported_scope": "return"}, {"reported_actor": ""}, {"reported_team": None},
    {"lost": None}, {"reported_kind": "sack", "reported_yards": 3},
])
def test_reported_projection_requires_typed_scope_class_actor_and_recovery(fields: dict) -> None:
    module, facts = projection_facts(**fields)
    with pytest.raises(ValueError):
        module.project_fumble_gain(facts, policy=REPORTED)


@pytest.mark.parametrize("policy", [PROXY, PHYSICAL])
def test_existing_strict_policies_do_not_accept_reported_only_facts(policy: str) -> None:
    module, facts = projection_facts()
    with pytest.raises(ValueError):
        module.project_fumble_gain(facts, policy=policy)


@pytest.mark.parametrize("detail,kind,yards,results", [
    ("Lee Runner left end for 7 yards. Lee Runner fumbles, recovered by Sam Defender at FOX47",
     "rushing", 7, ["F + 7"]),
    ("Pat Passer scrambles for -2 yards. Pat Passer fumbles, recovered by Lee Runner at FOX38",
     "rushing", -2, ["F - 2"]),
    ("Lee Runner middle for no gain. Lee Runner fumbles, recovered by Lee Runner at FOX40",
     "rushing", 0, ["F"]),
    ("Pat Passer pass complete to Lee Runner for 9 yards. Lee Runner fumbles, recovered by Sam Defender at FOX49 and returned for 12 yards",
     "receiving", 9, ["F + 9"]),
    ("Pat Passer sacked by Sam Defender for 6 yards. Pat Passer fumbles, recovered by Lee Runner at FOX34",
     "sack", -6, ["QT", "F - 6"]),
])
def test_pfr_reported_policy_associates_primary_number_with_its_actor_and_class(
    detail: str, kind: str, yards: int, results: list[str],
) -> None:
    game = game_with(detail)
    before = game.plays[0]
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.unsupported_fields
    assert [p.result for p in result.plays] == results
    gain, = result.fumble_gain_projections
    assert gain.originating_kind == kind
    assert gain.modeled_initial_yards == yards
    assert gain.source_facts.reported_yards == yards
    assert gain.source_facts.reported_actor == ("lee" if kind == "receiving" or detail.startswith("Lee") else "pat")
    assert gain.source_facts.reported_team == "FOX"
    assert gain.source_facts.credited_kind is None
    assert gain.source_facts.credited_yards is None
    assert gain.source_facts.physical_initial_yards is None
    assert result.fumbles[0].unit == ("rushing" if kind == "rushing" else "passing")
    assert before == game.plays[0]


@pytest.mark.parametrize("detail", [
    "Pat Passer for -3 yards. Pat Passer fumbles, recovered by Lee Runner at FOX37",
    "Alex Center fumbles, recovered by Pat Passer at FOX40 and returned for 7 yards",
    "Pat Passer pass incomplete. Pat Passer fumbles, recovered by Pat Passer at FOX35",
    "Pat Passer pass complete to Lee Runner for 8 yards, lateral to Alex Center for 2 yards. Alex Center fumbles, recovered by Sam Defender",
    "Lee Runner left end for 7 yards. Alex Center fumbles, recovered by Sam Defender",
    "Pat Passer sacked by, recovered by Lee Runner at FOX34 Sam Defender for 6 yards. Pat Passer fumbles",
    "Pat Passer pass complete, recovered by Pat Passer at FOX35 to Lee Runner for -5 yards. Lee Runner fumbles",
    "Lee Runner left end. Lee Runner fumbles, recovered by Sam Defender and returned for 7 yards",
    "Lee Runner left end for 7 yards. Lee Runner fumbles. Sam Defender fumbles, recovered by Lee Runner",
    "Lee Runner left end for 7 yards. Lee Runner fumbles, recovered by Mystery Person",
])
def test_pfr_ambiguous_primary_or_recovery_support_remains_rejected(detail: str) -> None:
    result = classify_pfr_game(game_with(detail), fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert any(x["field"] == "fumble_gain_projection" for x in result.unsupported_fields)


def test_reported_actor_team_is_checked_without_qb_position_inference() -> None:
    game = game_with("Lee Runner left end for 7 yards. Lee Runner fumbles, recovered by Sam Defender")
    changed = replace(game, player_teams={**game.player_teams, "lee": "OWL"})
    result = classify_pfr_game(changed, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_known_correction_wins_and_reported_disagreement_stays_visible(tmp_path: Path) -> None:
    game, facts = _reload_reviewed_fumble(
        tmp_path,
        detail="Pat Quarterback scrambles for -3 yards. Pat Quarterback fumbles, recovered by Pat Quarterback",
        credited_yards=0, initial_gain=None,
    )
    result = classify_pfr_game(game, event_facts=facts, fumble_gain_policy=REPORTED)
    gain, = result.fumble_gain_projections
    assert [p.result for p in result.plays] == ["F"]
    assert gain.source_facts.reported_yards == -3
    assert gain.source_facts.credited_yards == 0
    assert gain.source_facts.physical_initial_yards is None
    assert gain.modeled_gain_basis == "credited_proxy"


@pytest.mark.parametrize("direction,yards", [("left end", 6), ("middle", 2), ("right end", 3), ("left", 1)])
def test_explicit_primary_touchdown_annotation_preserves_scoped_fumble_gain(
    direction: str, yards: int,
) -> None:
    game = game_with(f"Lee Runner {direction} for {yards} yards, touchdown. "
                     "Lee Runner fumbles, recovered by Lee Runner at OWL0, touchdown")
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert projection.modeled_initial_yards == yards
    assert projection.source_facts.reported_yards == yards
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.credited_yards is None
    assert [p.result for p in result.plays] == [f"F + {yards}"]


@pytest.mark.parametrize("detail", [
    "Lee Runner left end, touchdown. Lee Runner fumbles, recovered by Lee Runner",
    "Lee Runner left end for 6 yards, touchdown. Pat Passer fumbles, recovered by Lee Runner",
])
def test_touchdown_annotation_cannot_supply_missing_gain_or_actor(detail: str) -> None:
    result = classify_pfr_game(game_with(detail), fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_source_loss_constraint_is_explicit_recovery_evidence() -> None:
    game = game_with("Lee Runner left end for 7 yards. Lee Runner fumbles")
    game = replace(game, fumble_box={"FOX": (1, 0), "OWL": (0, 0)})
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    gain, = result.fumble_gain_projections
    assert gain.source_facts.lost is False
    assert gain.source_facts.recovery_basis == "unique_team_loss_constraint"
    assert result.fumble_reconciliations[0]["method"] == "unique-team-fumble-loss-constraint"


def test_lateral_residual_is_not_a_reported_primary_gain() -> None:
    game = game_with("Pat Passer pass complete to Lee Runner for 5 yards, lateral to Alex Center for 1 yard. Alex Center fumbles, recovered by Sam Defender")
    result = classify_pfr_game(game, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields


def test_pfr_cli_accepts_explicit_reported_policy_before_classification(tmp_path: Path, monkeypatch) -> None:
    import generate_pfr_charts as command

    class ReachedClassification(Exception):
        pass

    mapping = tmp_path / "teams.json"
    mapping.write_text('{"FOX": "Foxes"}')

    def classify(*args, **kwargs):
        assert kwargs["fumble_gain_policy"] == REPORTED
        raise ReachedClassification

    monkeypatch.setattr(command, "_classify_directory", classify)
    with pytest.raises(ReachedClassification):
        command.main(["--html-dir", str(tmp_path), "--stats-dir", str(tmp_path),
                      "--template-season", str(tmp_path), "--team-map", str(mapping),
                      "--output", str(tmp_path / "out"), "--audit-dir", str(tmp_path / "audit"),
                      "--fumble-gain-policy", REPORTED])


def test_legacy_classification_remains_a_passing_control() -> None:
    game = game_with("Lee Runner left end for 7 yards. Lee Runner fumbles, recovered by Sam Defender")
    assert [p.result for p in classify_pfr_game(game).plays] == ["F + 7"]


@pytest.mark.parametrize("direction", ["left", "right", "middle", "up the middle"])
def test_explicit_scramble_direction_keeps_actor_bound_primary_gain(direction: str) -> None:
    source = game_with(
        f"Pat Passer scrambles {direction} for -2 yards. Pat Passer fumbles, "
        "recovered by Lee Runner at FOX38")
    result = classify_pfr_game(source, fumble_gain_policy=REPORTED)
    projection, = result.fumble_gain_projections
    assert not result.unsupported_fields
    assert projection.originating_kind == "rushing"
    assert projection.modeled_initial_yards == -2
    assert projection.source_facts.reported_actor == "pat"
    assert projection.source_facts.physical_initial_yards is None
    assert projection.source_facts.credited_yards is None


@pytest.mark.parametrize("direction", ["towards Lee Runner", "backwards", "left pass"])
def test_unrecognized_scramble_clause_stays_unsupported(direction: str) -> None:
    source = game_with(
        f"Pat Passer scrambles {direction} for -2 yards. Pat Passer fumbles, "
        "recovered by Lee Runner at FOX38")
    result = classify_pfr_game(source, fumble_gain_policy=REPORTED)
    assert not result.fumble_gain_projections
    assert result.unsupported_fields
