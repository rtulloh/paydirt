"""Version two role assumptions remain separate from source facts."""
from dataclasses import replace

import pytest

from paydirt.pfr_play_by_play import classify_pfr_game
from tests.test_reported_fumble_gain import game_with

POLICY = "historical_fumble_class_proxy_v2"


@pytest.mark.parametrize("position,yards,kind,basis", [
    ("RB", -3, "rushing", "assumed_known_running_back"),
    ("FB", 2, "rushing", "assumed_known_running_back"),
    ("C", -2, "rushing", "assumed_center_snap"),
    ("WR", 3, "receiving", "assumed_known_receiver"),
    ("TE", 0, "receiving", "assumed_known_receiver"),
    ("QB", 2, "rushing", "assumed_qb_rush"),
    ("QB", 3, "rushing", "assumed_qb_rush"),
    ("QB", 14, "rushing", "assumed_qb_rush"),
])
def test_v2_known_positions(position: str, yards: int, kind: str, basis: str) -> None:
    game = game_with(f"Pat Passer for {yards} yards. Pat Passer fumbles, recovered by Lee Runner at FOX39")
    game = replace(game, player_positions={**game.player_positions, "pat": position})
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert not result.unsupported_fields
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == kind
    assert projection.modeled_class_basis == basis
    assert projection.source_facts.reported_kind is None
    assert projection.source_facts.credited_kind is None
    assert projection.modeled_initial_yards == yards
    assert projection.policy == POLICY


def test_v2_missing_gain_cannot_borrow_recovery_return() -> None:
    game = game_with("Pat Passer fumbles, recovered by Lee Runner at FOX35 and returned for 9 yards")
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert result.unsupported_fields and not result.fumble_gain_projections
    assert len(result.fumbles) == 1


@pytest.mark.parametrize("detail", [
    "Pat Passer sacked by, recovered by Pat Passer at FOX14 Sam Defender for 6 yards. Pat Passer fumbles (forced by Sam Defender)",
    "Pat Passer sacked by Sam Defender. Pat Passer fumbles (forced by Sam Defender for 6 yards, recovered by Lee Runner at FOX34)",
])
def test_v2_reordered_sack_loss_is_source_bound(detail: str) -> None:
    game = game_with(detail)
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert not result.unsupported_fields
    projection, = result.fumble_gain_projections
    assert projection.originating_kind == "sack"
    assert projection.modeled_initial_yards == -6
    assert projection.modeled_class_basis == "reordered_source_sack"
    assert projection.source_facts.reported_kind == "sack"
    assert projection.source_facts.physical_initial_yards is None


@pytest.mark.parametrize("detail", [
    "Pat Passer sacked by Sam Defender. Lee Runner fumbles, recovered by Pat Passer at FOX34 for 6 yards",
    "Pat Passer sacked by Sam Defender. Pat Passer fumbles, recovered by Lee Runner at FOX34 and returned for 6 yards",
])
def test_v2_reordered_sack_rejects_actor_and_return_ambiguity(detail: str) -> None:
    game = game_with(detail)
    result = classify_pfr_game(game, fumble_gain_policy=POLICY)
    assert result.unsupported_fields and not result.fumble_gain_projections
