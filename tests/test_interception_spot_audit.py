"""Spot support is play-specific and separate from interception returns."""
from fractions import Fraction

import pytest

from paydirt import chart_audit
from paydirt.chart_tactics_audit import controlled_offense


def audit(charts):
    function = getattr(chart_audit, "interception_spot_audit", None)
    assert callable(function), "Audit must retain exact play-specific spot probability mass"
    return function(charts)


def test_spots_use_physical_weights_and_priority_not_return_gains():
    chart = controlled_offense("0")
    chart.offense.screen[10] = "INT 44"
    chart.offense.long_pass = dict.fromkeys(range(10, 40), "INT 30")
    chart.special_teams.interception_return = dict.fromkeys(range(10, 40), "70")
    chart.defense.modifiers = {(letter, row): dict.fromkeys(range(1, 10), "0")
                               for letter in "ABCDEF" for row in range(1, 6)}
    chart.defense.modifiers[("A", 1)][5] = "INT 5"
    report = audit([chart])
    team = report["teams"]["Synthetic"]
    assert team["offense"]["screen"] == {"44": {"mass": "1/108", "probability": pytest.approx(1 / 108)}}
    assert team["offense"]["short_pass"] == {}
    assert team["offense"]["long_pass"] == {"30": {"mass": "1", "probability": 1}}
    expected = {"5": Fraction(1, 3), "44": Fraction(2, 3 * 108)}
    actual = team["reachable"]["screen/A"]["spots"]
    assert {spot: Fraction(value["mass"]) for spot, value in actual.items()} == expected
    assert team["reachable"]["screen/A"]["interception_probability"] == pytest.approx(float(sum(expected.values())))
    assert team["reachable"]["screen/B"]["spots"] == team["offense"]["screen"]
    assert "70" not in str(team["reachable"])
    assert report["source_fidelity_checked"] is False


def test_shorter_competing_spot_and_penalty_override_remain_reachable():
    chart = controlled_offense("INT 12")
    chart.defense.modifiers = {(letter, row): dict.fromkeys(range(1, 10), "INT 5")
                               for letter in "ABCDEF" for row in range(1, 6)}
    chart.defense.modifiers[("B", 1)][5] = "OFF 5"
    team = audit([chart])["teams"]["Synthetic"]
    assert team["reachable"]["screen/A"]["spots"] == {"5": {"mass": "1", "probability": 1}}
    assert team["reachable"]["screen/B"]["spots"]["5"]["mass"] == "2/3"
    assert team["defense"]["screen/B"]["5"]["mass"] == "2/3"


def test_uniform_opponents_preserve_each_offenses_identity():
    first = controlled_offense("INT 12")
    second = controlled_offense("0")
    second.peripheral.team_name = "Other"
    for chart in (first, second):
        chart.defense.modifiers = {(letter, row): dict.fromkeys(range(1, 10), "0")
                                   for letter in "ABCDEF" for row in range(1, 6)}
    teams = audit([first, second])["teams"]
    assert teams["Synthetic"]["reachable"]["screen/A"]["spots"]["12"]["mass"] == "1"
    assert teams["Other"]["reachable"]["screen/A"]["spots"] == {}


def test_equivalent_integer_labels_accumulate_physical_mass():
    chart = controlled_offense("0")
    chart.offense.screen[10] = "INT 05"
    chart.offense.screen[11] = "INT 5"
    chart.defense.modifiers = {(letter, row): dict.fromkeys(range(1, 10), "0")
                               for letter in "ABCDEF" for row in range(1, 6)}
    team = audit([chart])["teams"]["Synthetic"]
    assert team["offense"]["screen"]["5"]["mass"] == team["reachable"]["screen/A"]["spots"]["5"]["mass"]
    assert "05" not in team["offense"]["screen"]
