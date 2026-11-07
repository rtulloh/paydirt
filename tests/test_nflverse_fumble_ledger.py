"""Ordered source facts remain separate from chart projection and play credit."""

from dataclasses import replace

import pytest

from paydirt import nflverse_play_by_play as source


def row(**changes: object) -> dict[str, object]:
    """Return one synthetic compound play with explicit scoped movements."""
    values: dict[str, object] = {
        "season_type": "REG", "game_id": "synthetic-ledger", "play_id": 12,
        "two_point_attempt": 0, "posteam": "AAA", "defteam": "BBB",
        "play_type": "pass", "pass_attempt": 1, "sack": 1, "fumble": 1,
        "fumble_lost": 1, "yards_gained": -7,
        "fumbled_1_team": "AAA", "fumbled_1_player_id": "carrier",
        "fumbled_1_player_name": "A.Carrier",
        "fumble_recovery_1_team": "AAA", "fumble_recovery_1_player_id": "lineman",
        "fumble_recovery_1_player_name": "L.Lineman", "fumble_recovery_1_yards": -5,
        "fumbled_2_team": "AAA", "fumbled_2_player_id": "lineman",
        "fumbled_2_player_name": "L.Lineman",
        "fumble_recovery_2_team": "BBB", "fumble_recovery_2_player_id": "defender",
        "fumble_recovery_2_player_name": "D.Defender", "fumble_recovery_2_yards": 28,
        "desc": "A.Carrier sacked for -8 yards. FUMBLES, recovered by AAA-L.Lineman at AAA 33. "
                "L.Lineman to AAA 32 for -1 yards. FUMBLES, recovered by BBB-D.Defender at AAA 28. "
                "D.Defender for 28 yards, TOUCHDOWN.",
    }
    values.update(changes)
    return values


def ledger(**changes: object) -> source.FumbleSourceLedger:
    return source.build_fumble_ledger(row(**changes))


def test_ordered_events_preserve_credit_and_all_source_values() -> None:
    raw = row(extra_provider_field="preserved")
    result = source.build_fumble_ledger(raw)
    assert result.source_event_id == "synthetic-ledger:12"
    assert dict(result.raw_values) == raw
    assert result.raw_play_sha256 == source.source_record_hash(raw)
    assert result.origin == "sack" and result.retained
    assert (result.statistical_kind, result.statistical_yards) == ("sack", -7)
    assert [e.source_event_id for e in result.events] == [
        "synthetic-ledger:12:F1", "synthetic-ledger:12:F2"]
    assert [e.fumbling_player_id for e in result.events] == ["carrier", "lineman"]
    assert [e.recovering_team for e in result.events] == ["AAA", "BBB"]
    assert [e.possession_changed for e in result.events] == [False, True]
    assert all(e.individual_lost is None for e in result.events)
    assert all(e.physical_initial_yards is None for e in result.events)
    assert [s.reported_yards for s in result.segments] == [-1, 28]
    assert [s.provider_recovery_yards for s in result.segments] == [-5, 28]
    assert [s.ends_in_fumble for s in result.segments] == [2, None]
    assert not result.unsupported


def test_same_player_second_fumble_requires_an_explicit_recovery_advance() -> None:
    result = ledger(
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        fumble_recovery_2_team="AAA",
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman at AAA 33. "
             "L.Lineman to AAA 34 for 1 yard. FUMBLES, recovered by AAA-D.Defender.",
    )
    assert len(result.events) == 2
    assert result.events[1].fumbling_player_id == "lineman"
    assert result.events[1].identity_basis == "explicit_recovery_advance"
    assert result.segments[0].reported_yards == 1
    missing = ledger(
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman. FUMBLES, recovered by BBB-D.Defender.",
    )
    assert missing.events[1].fumbling_player_id is None
    assert any("second fumbler" in reason for reason in missing.unsupported)


@pytest.mark.parametrize("origin,flags", [
    ("punt_snap", {"play_type": "run", "pass_attempt": 0, "sack": 0, "rush_attempt": 1,
                   "desc": "(Punt formation) A.Carrier Aborted. FUMBLES. FUMBLES."}),
    ("blocked_punt", {"play_type": "punt", "sack": 0, "punt_blocked": 1}),
    ("interception", {"sack": 0, "interception": 1}),
    ("kickoff_return", {"play_type": "kickoff", "sack": 0}),
    ("punt_return", {"play_type": "punt", "sack": 0}),
])
def test_one_origin_is_distinct_from_conditional_fumbles(origin: str, flags: dict) -> None:
    assert ledger(**flags).origin == origin


def test_unknown_blocked_advance_does_not_use_return_zero_or_recovery_slot() -> None:
    result = ledger(
        play_type="punt", sack=0, punt_blocked=1, return_yards=0,
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        fumble_recovery_2_team="", fumble_recovery_2_player_id="",
        fumble_recovery_2_player_name="",
        desc="A.Carrier punt is BLOCKED, recovered by AAA-A.Carrier. "
             "A.Carrier FUMBLES, recovered by AAA-L.Lineman.",
    )
    assert result.segments[0].entry_reason == "blocked_punt"
    assert result.segments[0].reported_yards is None
    assert result.segments[0].provider_recovery_yards is None
    assert result.segments[1].provider_recovery_yards == -5


def test_explicit_blocked_advance_is_scoped_before_fumble() -> None:
    result = ledger(
        play_type="punt", sack=0, punt_blocked=1, return_yards=0,
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        fumble_recovery_2_team="", fumble_recovery_2_player_id="",
        fumble_recovery_2_player_name="",
        desc="A.Carrier punt is BLOCKED, recovered by AAA-A.Carrier at AAA 21. "
             "A.Carrier to AAA 23 for 2 yards. FUMBLES, recovered by AAA-L.Lineman.",
    )
    assert result.segments[0].reported_yards == 2
    assert result.segments[0].ends_in_fumble == 1


def test_replay_and_muff_metadata_do_not_add_credited_occurrences() -> None:
    result = ledger(
        desc="A.Carrier FUMBLES. FUMBLES. The play was REVERSED. "
             "A.Carrier MUFFS the exchange. A.Carrier FUMBLES, recovered by AAA-L.Lineman. "
             "L.Lineman to AAA 34 for 1 yard. FUMBLES, recovered by BBB-D.Defender. "
             "Fumble forced by Defender.",
    )
    assert len(result.events) == 2
    assert result.muff_actions == 1
    assert result.final_description.startswith("A.Carrier MUFFS")
    assert result.raw_description.startswith("A.Carrier FUMBLES")


@pytest.mark.parametrize("flags", [
    {"play_type": "no_play", "fumble": 0, "penalty": 1},
    {"penalty": 1, "desc": "A.Carrier FUMBLES. FUMBLES. Penalties offsetting."},
])
def test_voided_play_retains_evidence_without_retained_credit(flags: dict) -> None:
    result = ledger(**flags)
    assert not result.retained
    assert len(result.events) == 2
    assert all(e.individual_lost is None for e in result.events)


def test_conflicting_recovery_and_missing_actor_remain_explicit() -> None:
    result = ledger(fumble_recovery_1_team="BBB", fumbled_2_player_id="")
    assert any("recovery" in reason for reason in result.unsupported)
    assert any("second fumbler" in reason for reason in result.unsupported)


def test_reviewed_event_losses_bind_hash_order_and_actor() -> None:
    result = ledger()
    review = source.FumbleLossReview(
        raw_play_sha256=result.raw_play_sha256, ordinal=1,
        fumbling_team="AAA", fumbling_player_id="carrier", lost=False,
        evidence_sha256="a" * 64, evidence_page=3,
    )
    reviewed = source.apply_fumble_loss_reviews(result, [review])
    assert [e.individual_lost for e in reviewed.events] == [False, None]
    assert [e.individual_lost for e in result.events] == [None, None]
    for bad in (
        replace(review, raw_play_sha256="b" * 64),
        replace(review, ordinal=2),
        replace(review, fumbling_player_id="wrong"),
        replace(review, evidence_sha256=""),
    ):
        with pytest.raises(ValueError):
            source.apply_fumble_loss_reviews(result, [bad])


def test_classifier_exposes_ledger_without_accepting_compound_fit() -> None:
    result = source.classify_nflverse_rows([row()], fumble_gain_policy="credited_fumble_proxy_v1")
    assert len(result.fumble_ledgers) == 1
    assert len(result.fumble_ledgers[0].events) == 2
    assert not result.fumble_gain_projections
    assert result.unsupported_fields[0]["field"] == "fumble_ownership"


def test_ordinary_single_event_control_uses_known_row_loss() -> None:
    raw = row(
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
        fumble_recovery_1_team="BBB",
        desc="A.Carrier sacked for -8 yards. FUMBLES, recovered by BBB-L.Lineman.",
    )
    result = source.build_fumble_ledger(raw)
    assert len(result.events) == 1
    assert result.events[0].individual_lost is True
    assert source.classify_nflverse_rows([raw]).fumbles[0].lost is True


def test_blocked_play_without_fumble_keeps_explicit_recovery_advance() -> None:
    result = source.build_fumble_ledger({
        "game_id": "synthetic-blocked", "play_id": 9, "posteam": "AAA", "defteam": "BBB",
        "play_type": "punt", "punt_blocked": 1, "fumble": 0, "return_yards": 0,
        "desc": "A.Kicker punt is BLOCKED, recovered by AAA-R.Returner at AAA 20. "
                "R.Returner to AAA 25 for 5 yards.",
    })
    assert result.events == ()
    assert result.segments[0].player_name == "R.Returner"
    assert result.segments[0].team == "AAA"
    assert result.segments[0].reported_yards == 5
    assert result.segments[0].provider_recovery_yards is None


def test_recovery_actor_conflict_cannot_supply_a_scoped_gain() -> None:
    result = ledger(desc="A.Carrier FUMBLES, recovered by AAA-W.Wrong at AAA 33. "
                         "L.Lineman to AAA 32 for -1 yards. FUMBLES, "
                         "recovered by BBB-D.Defender.")
    assert any("recovery actor" in reason for reason in result.unsupported)
    assert result.segments[0].reported_yards is None


def test_conflicting_statistical_classes_are_not_a_first_flag_wins_choice() -> None:
    result = ledger(rush_attempt=1)
    assert result.statistical_kind is None
    assert any("statistical class" in reason for reason in result.unsupported)


def test_event_zero_identity_is_not_replaced_by_fallback() -> None:
    assert source.build_fumble_ledger(row(play_id=0), fallback_number=99).source_event_id.endswith(":0")


def test_midfield_advance_is_scoped_to_the_named_fumbler() -> None:
    result = ledger(
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman at AAA 49. "
             "L.Lineman to 50 for 1 yard. FUMBLES, recovered by BBB-D.Defender.")
    assert result.segments[0].reported_yards == 1
    assert result.segments[0].provider_recovery_yards == -5
    assert result.segments[0].ends_in_fumble == 2


@pytest.mark.parametrize("location", ["49", "51", "midfield"])
def test_bare_unrecognized_advance_location_does_not_supply_a_gain(location: str) -> None:
    result = ledger(
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman. "
             f"L.Lineman to {location} for 1 yard. FUMBLES, recovered by BBB-D.Defender.")
    assert result.segments[0].reported_yards is None


@pytest.mark.parametrize("lost", ["", None, "NA", "unknown"])
def test_unknown_single_event_loss_stays_null(lost: object) -> None:
    result = ledger(
        fumble_lost=lost,
        fumbled_2_team="", fumbled_2_player_id="", fumbled_2_player_name="",
        fumble_recovery_2_team="", fumble_recovery_2_player_id="", fumble_recovery_2_player_name="",
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman.",
    )
    assert result.row_lost is None
    assert result.events[0].individual_lost is None


@pytest.mark.parametrize("field,origin", [
    ("field_goal_result", "blocked_field_goal"),
    ("extra_point_result", "blocked_extra_point"),
])
def test_provider_block_result_fields_are_censused_without_fumble(field: str, origin: str) -> None:
    raw = {"season_type": "REG", "game_id": "synthetic-block", "play_id": 1,
           "play_type": "field_goal", "posteam": "AAA", "defteam": "BBB",
           field: "blocked", "desc": "A.Kicker kick is BLOCKED.", "fumble": 0,
           "return_yards": 0}
    result = source.classify_nflverse_rows([raw])
    assert len(result.fumble_ledgers) == 1
    assert result.fumble_ledgers[0].origin == origin
    assert result.fumble_ledgers[0].segments[0].reported_yards is None


def test_punt_snap_play_credit_can_belong_to_a_different_actor() -> None:
    result = ledger(
        play_type="run", sack=0, pass_attempt=0, rush_attempt=1,
        rusher_player_id="lineman", rusher_player_name="L.Lineman",
        rusher_id="carrier", rusher="A.Carrier", yards_gained=0,
        desc="(Punt formation) A.Carrier Aborted. FUMBLES, recovered by AAA-L.Lineman. "
             "L.Lineman to AAA 34 for 1 yard. FUMBLES, recovered by BBB-D.Defender.",
    )
    assert result.statistical_player_id == "lineman"
    assert result.statistical_player_name == "L.Lineman"
    assert result.events[0].fumbling_player_id == "carrier"
    assert result.statistical_yards == 0
    assert result.events[0].physical_initial_yards is None


def reviewed_ledger(**changes: object) -> source.FumbleSourceLedger:
    result = ledger(**changes)
    reviews = [
        source.FumbleLossReview(result.raw_play_sha256, event.ordinal, event.fumbling_team,
                                event.fumbling_player_id, event.possession_changed or False,
                                "a" * 64, 3)
        for event in result.events
    ]
    return source.apply_fumble_loss_reviews(result, reviews)


def test_joint_diagnostic_has_one_primary_and_one_conditional_fumble() -> None:
    original = reviewed_ledger()
    result = source.project_fumble_ledger(original, policy="source_reported_gain_proxy_v1")
    assert result.complete
    assert [event.exposure for event in result.events] == ["primary", "shared_return"]
    assert [event.chart_result for event in result.events] == ["F - 7", "F - 1"]
    assert [event.modeled_gain_basis for event in result.events] == [
        "play_statistical_credit_proxy", "scoped_reported_advance_proxy"]
    assert len({event.source_event_id for event in result.events}) == 2
    assert all(event.physical_initial_yards is None for event in original.events)


def test_joint_diagnostic_never_uses_raw_recovery_credit_as_missing_gain() -> None:
    original = reviewed_ledger(
        desc="A.Carrier FUMBLES, recovered by AAA-L.Lineman. "
             "FUMBLES, recovered by BBB-D.Defender.",
    )
    result = source.project_fumble_ledger(original, policy="source_reported_gain_proxy_v1")
    assert not result.complete
    assert len(result.events) == 1
    assert any("scoped advance" in reason for reason in result.unsupported)


def test_joint_diagnostic_requires_each_individual_loss_not_global_loss() -> None:
    result = source.project_fumble_ledger(ledger(), policy="source_reported_gain_proxy_v1")
    assert not result.complete
    assert not result.events
    assert sum("individual lost" in reason for reason in result.unsupported) == 2


def test_punt_snap_diagnostic_keeps_credit_actor_distinct_and_one_origin() -> None:
    original = reviewed_ledger(
        play_type="run", sack=0, pass_attempt=0, rush_attempt=1, yards_gained=0,
        rusher_player_id="lineman", rusher_player_name="L.Lineman",
        desc="(Punt formation) A.Carrier Aborted. FUMBLES, recovered by AAA-L.Lineman. "
             "L.Lineman to AAA 34 for 1 yard. FUMBLES, recovered by BBB-D.Defender.",
    )
    result = source.project_fumble_ledger(original, policy="source_reported_gain_proxy_v1")
    assert result.complete and result.origin == "punt_snap"
    assert [event.exposure for event in result.events] == ["primary", "shared_return"]
    assert result.events[0].chart_result == "F"
    assert result.events[0].statistical_player_id == "lineman"
    assert original.events[0].fumbling_player_id == "carrier"


def test_interception_return_fumble_is_allocated_once_in_shared_population() -> None:
    original = source.build_fumble_ledger({
        "game_id": "synthetic-int", "play_id": 4, "posteam": "AAA", "defteam": "BBB",
        "interception": 1, "fumble": 1, "fumble_lost": 0, "play_type": "pass",
        "fumbled_1_team": "BBB", "fumbled_1_player_id": "defender",
        "fumbled_1_player_name": "D.Defender", "fumble_recovery_1_team": "BBB",
        "fumble_recovery_1_player_id": "teammate", "fumble_recovery_1_player_name": "T.Teammate",
        "return_yards": 9, "desc": "Pass INTERCEPTED by BBB-D.Defender. "
        "D.Defender to BBB 29 for 9 yards. FUMBLES, recovered by BBB-T.Teammate.",
    })
    result = source.project_fumble_ledger(original, policy="source_reported_gain_proxy_v1")
    assert result.complete
    assert [(event.exposure, event.chart_result) for event in result.events] == [("shared_return", "F + 9")]


def test_known_physical_policy_cannot_promote_credit_or_reported_gains() -> None:
    result = source.project_fumble_ledger(reviewed_ledger(), policy="known_physical_v1")
    assert not result.complete
    assert not result.events
    assert len(result.unsupported) == 2


def test_voided_diagnostic_has_no_retained_numeric_projection() -> None:
    result = source.project_fumble_ledger(ledger(play_type="no_play", fumble=0),
                                         policy="source_reported_gain_proxy_v1")
    assert not result.complete
    assert not result.events


@pytest.mark.parametrize("changes", [
    {"two_point_attempt": 1},
    {"extra_point_result": "blocked", "play_type": "extra_point"},
])
def test_conversion_and_blocked_extra_point_do_not_supply_ordinary_projection(changes: dict) -> None:
    result = source.project_fumble_ledger(reviewed_ledger(**changes),
                                         policy="source_reported_gain_proxy_v1")
    assert not result.complete
    assert not result.events


def test_known_physical_gain_wins_without_rewriting_source_credit() -> None:
    original = reviewed_ledger()
    physical = replace(original, events=(
        replace(original.events[0], physical_initial_yards=-2), original.events[1]))
    result = source.project_fumble_ledger(physical, policy="source_reported_gain_proxy_v1")
    assert result.complete
    assert [event.chart_result for event in result.events] == ["F - 2", "F - 1"]
    assert result.events[0].modeled_gain_basis == "known_physical"
    assert physical.statistical_yards == -7


def test_spaced_recovery_surname_keeps_actor_scope() -> None:
    result = ledger(
        fumble_recovery_1_player_name="L.Van Lineman",
        fumbled_2_player_name="L.Van Lineman",
        desc="A.Carrier FUMBLES, recovered by AAA-L.Van Lineman at AAA 33. "
             "L.Van Lineman to AAA 34 for 1 yard. FUMBLES, recovered by BBB-D.Defender.",
    )
    assert not result.unsupported
    assert result.segments[0].reported_yards == 1
