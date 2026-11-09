"""Tests for transforming historical PFR play-by-play into chart outcomes."""

import pytest

from paydirt.pfr_play_by_play import classify_pfr_game, parse_pfr_boxscore


def test_nullified_interception_is_penalty_only_even_with_return_language() -> None:
    detail = (
        '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass is intercepted by '
        '<a href="/players/D/DefeDa00.htm">Dan Defender</a> and returned for 9 yards. '
        'Penalty on PHI: Offensive Holding, 10 yards (accepted) (no play)'
    )
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "void-int"))
    assert classified.diagnostics.get("interceptions", 0) == 0
    assert [play.result for play in classified.plays] == ["OFF 10"]


def test_bare_no_play_sack_is_not_an_observed_sack() -> None:
    detail = '<a href="/players/P/PassPh00.htm">Phil Passer</a> sacked by Dan Defender for 8 yards (no play)'
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "void-sack"))
    assert classified.diagnostics.get("sacks", 0) == 0
    assert not classified.plays


def test_sack_with_unknown_yards_keeps_count_without_fabricating_gain() -> None:
    detail = '<a href="/players/P/PassPh00.htm">Phil Passer</a> sacked by'
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "unknown-sack"))
    assert classified.diagnostics["sacks"] == 1
    assert classified.diagnostics["unclassified_sacks"] == 1
    assert not classified.plays  # No invented secondary yardage.


def test_retained_sack_and_end_enforcement_foul_keep_source_occurrence() -> None:
    detail = (
        '<a href="/players/P/PassPh00.htm">Phil Passer</a> sacked by Dan Defender for 8 yards. '
        'Penalty on SFO: Unnecessary Roughness, 15 yards (accepted)'
    )
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "retained-sack"))
    assert classified.diagnostics["sacks"] == 1
    assert classified.diagnostics["sacks_with_retained_penalty"] == 1
    assert classified.event_counts["PHI"]["sacks"] == 1
    assert [play.result for play in classified.plays] == ["DEF 15"]


def test_field_goal_description_requires_official_attempt_credit_when_available() -> None:
    rows = (
        _row(1, "4", "8", "SFO 30", '<a href="/players/R/RushRo00.htm">Ron Runner</a> 47 yard field goal no good')
        + _row(2, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal no good')
    )
    html = _game_html(rows).replace('</body>', '''
      <table id="kicking"><tbody><tr>
        <th data-stat="player" data-append-csv="KickKi00">Ken Kicker</th>
        <td data-stat="team">PHI</td><td data-stat="fga">1</td><td data-stat="fgm">0</td>
      </tr></tbody></table></body>''')
    classified = classify_pfr_game(parse_pfr_boxscore(html, "box-fga"))
    assert len(classified.field_goals) == 1
    assert classified.field_goals[0].play_number == 2
    assert classified.diagnostics["field_goal_descriptions_without_box_credit"] == 1
    assert classified.source_conflicts[0]["play_number"] == 1
    assert classified.source_conflicts[0]["mechanism"] == "unknown"
    assert classified.source_conflicts[0]["official_attempt"] is False


def _with_kicking_box(rows: str, box_rows: str) -> str:
    return _game_html(rows).replace('</body>', f'<table id="kicking"><tbody>{box_rows}</tbody></table></body>')


def _box_credit(player_id: str, attempts: int, made: int) -> str:
    return (
        f'<tr><th data-stat="player" data-append-csv="{player_id}">Actor</th>'
        f'<td data-stat="team">PHI</td><td data-stat="fga">{attempts}</td>'
        f'<td data-stat="fgm">{made}</td></tr>'
    )


def test_nonstandard_actor_with_official_credit_is_a_valid_attempt() -> None:
    rows = _row(1, "4", "8", "SFO 30", '<a href="/players/R/RushRo00.htm">Ron Runner</a> 47 yard field goal good')
    html = _with_kicking_box(rows, _box_credit("RushRo00", 1, 1))
    classified = classify_pfr_game(parse_pfr_boxscore(html, "nonstandard-actor"))
    assert [(attempt.made, attempt.distance) for attempt in classified.field_goals] == [(True, 47)]
    assert not classified.source_conflicts
    assert classified.diagnostics.get("unreconciled_field_goal_box", 0) == 0


def test_blocked_and_penalized_official_attempts_are_preserved() -> None:
    rows = (
        _row(1, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal blocked')
        + _row(2, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal good. Penalty on SFO: Offside, 5 yards (declined)')
    )
    classified = classify_pfr_game(parse_pfr_boxscore(_with_kicking_box(rows, _box_credit("KickKi00", 2, 1)), "valid-fga"))
    assert len(classified.field_goals) == 2
    assert classified.field_goals[0].blocked
    assert classified.field_goals[1].made
    assert any(play.result == "DEF 5" for play in classified.plays)
    assert not classified.source_conflicts


def test_incomplete_box_or_competing_matches_stay_unreconciled() -> None:
    rows = (
        _row(1, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal no good')
        + _row(2, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal no good')
    )
    for attempts, made in [(1, 0), (3, 0), (2, 1)]:
        classified = classify_pfr_game(parse_pfr_boxscore(_with_kicking_box(rows, _box_credit("KickKi00", attempts, made)), "ambiguous"))
        assert len(classified.field_goals) == 2  # Do not choose an event to force a match.
        assert classified.diagnostics["unreconciled_field_goal_box"] == 1


def test_absent_box_or_player_identity_is_unverified_instead_of_zero() -> None:
    rows = _row(1, "4", "8", "SFO 30", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 47 yard field goal no good')
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "missing-box"))
    assert len(classified.field_goals) == 1
    assert classified.diagnostics["unverified_field_goal_box"] == 1
    unknown_actor = _row(1, "4", "8", "SFO 30", 'Unknown Kicker 47 yard field goal no good')
    classified = classify_pfr_game(parse_pfr_boxscore(_with_kicking_box(unknown_actor, _box_credit("KickKi00", 1, 0)), "missing-actor"))
    assert classified.diagnostics["unreconciled_field_goal_box"] == 1


def _game_html(play_rows: str) -> str:
    return f"""
    <html><body>
      <div class="scorebox">
        <div><a href="/teams/phi/1983.htm">Philadelphia Eagles</a></div>
        <div><a href="/teams/sfo/1983.htm">San Francisco 49ers</a></div>
      </div>
      <table id="player_offense"><tbody>
        <tr><th data-append-csv="PassPh00" data-stat="player"><a href="/players/P/PassPh00.htm">Phil Passer</a></th><td data-stat="team">PHI</td><td data-stat="pos">QB</td></tr>
        <tr><th data-append-csv="RushRo00" data-stat="player"><a href="/players/R/RushRo00.htm">Ron Runner</a></th><td data-stat="team">PHI</td><td data-stat="pos">RB</td></tr>
        <tr><th data-append-csv="KickKi00" data-stat="player"><a href="/players/K/KickKi00.htm">Ken Kicker</a></th><td data-stat="team">PHI</td><td data-stat="pos">K</td></tr>
        <tr><th data-append-csv="PuntPa00" data-stat="player"><a href="/players/P/PuntPa00.htm">Pat Punter</a></th><td data-stat="team">PHI</td><td data-stat="pos">P</td></tr>
        <tr><th data-append-csv="RetuRa00" data-stat="player"><a href="/players/R/RetuRa00.htm">Ray Returner</a></th><td data-stat="team">SFO</td><td data-stat="pos">DB</td></tr>
        <tr><th data-append-csv="DefeDa00" data-stat="player"><a href="/players/D/DefeDa00.htm">Dan Defender</a></th><td data-stat="team">SFO</td><td data-stat="pos">DB</td></tr>
      </tbody></table>
      <table id="pbp"><thead><tr>
        <th data-stat="quarter">Quarter</th><th data-stat="qtr_time_remain">Time</th>
        <th data-stat="down">Down</th><th data-stat="yds_to_go">ToGo</th>
        <th data-stat="location">Location</th><th data-stat="pbp_score_aw" aria-label="PHI">PHI</th>
        <th data-stat="pbp_score_hm" aria-label="SFO">SFO</th><th data-stat="detail">Detail</th>
      </tr></thead><tbody>{play_rows}</tbody></table>
    </body></html>
    """


def _row(number: int, down: str, to_go: str, location: str, detail: str) -> str:
    return f"""
      <tr><th data-stat="quarter">1</th><td data-stat="qtr_time_remain">12:00</td>
      <td data-stat="down">{down}</td><td data-stat="yds_to_go">{to_go}</td>
      <td data-stat="location">{location}</td><td data-stat="pbp_score_aw">0</td>
      <td data-stat="pbp_score_hm">0</td><td data-stat="detail"><a name="pbp_{number}.000"></a>{detail}</td></tr>
    """


def test_parse_and_classify_scrimmage_and_special_teams_plays() -> None:
    rows = "".join(
        (
            _row(1, "", "", "PHI 35", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> kicks off 65 yards, touchback.'),
            _row(2, "1", "10", "SFO 20", '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 7 yards (out of bounds)'),
            _row(3, "2", "3", "SFO 27", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner for 14 yards'),
            _row(4, "1", "10", "SFO 41", '<a href="/players/P/PassPh00.htm">Phil Passer</a> sacked by Dan Defender for 6 yards'),
            _row(5, "4", "16", "SFO 35", '<a href="/players/P/PuntPa00.htm">Pat Punter</a> punts 39 yards, returned by <a href="/players/R/RetuRa00.htm">Ray Returner</a> for 9 yards'),
            _row(6, "1", "10", "SFO 35", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass intended for Ron Runner is intercepted by <a href="/players/D/DefeDa00.htm">Dan Defender</a> at PHI45 and returned for 12 yards'),
            _row(7, "4", "5", "SFO 20", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 37 yard field goal good'),
        )
    )

    game = parse_pfr_boxscore(_game_html(rows), game_id="synthetic")
    classified = classify_pfr_game(game, seed=8306)
    outcomes = {(play.team, play.unit, play.chart, play.result) for play in classified.plays}

    assert game.away_team == "PHI"
    assert game.home_team == "SFO"
    assert game.player_teams["PassPh00"] == "PHI"
    assert {play.opponent for play in classified.plays if play.unit == "offense"} == {"SFO"}
    assert ("PHI", "special_teams", "kickoff", "65") in outcomes
    assert ("PHI", "offense", "off_tackle", "7*") in outcomes
    assert any(
        team == "PHI"
        and unit == "offense"
        and chart in {"screen", "short_pass", "medium_pass", "long_pass"}
        and result == "14"
        for team, unit, chart, result in outcomes
    )
    assert any(
        team == "PHI" and unit == "offense" and chart in {"screen", "short_pass", "medium_pass", "long_pass"} and result == "QT"
        for team, unit, chart, result in outcomes
    )
    assert ("PHI", "offense", "qb_time", "-6") in outcomes
    assert ("PHI", "special_teams", "punt", "39") in outcomes
    assert ("SFO", "special_teams", "punt_return", "9") in outcomes
    assert any(
        team == "PHI" and unit == "offense" and result.startswith("INT ")
        for team, unit, _chart, result in outcomes
    )
    assert ("SFO", "special_teams", "interception_return", "12") in outcomes
    assert [(attempt.team, attempt.distance, attempt.made) for attempt in classified.field_goals] == [("PHI", 37, True)]


def test_penalty_classification_preserves_called_and_declined_information() -> None:
    rows = "".join(
        (
            _row(1, "3", "7", "PHI 40", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass incomplete intended for Ron Runner. Penalty on <a href="/players/D/DefeDa00.htm">Dan Defender</a>: Defensive Pass Interference, 12 yards (accepted) (no play)'),
            _row(2, "1", "10", "SFO 48", '<a href="/players/R/RushRo00.htm">Ron Runner</a> right end for 5 yards. Penalty on Dan Defender: Offside, 5 yards (declined)'),
        )
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "penalties"))
    outcomes = [(play.chart, play.result) for play in classified.plays if play.unit == "offense"]

    assert any(result == "PI 12" for _chart, result in outcomes)
    assert ("end_run", "5") in outcomes
    assert classified.diagnostics["accepted_penalties"] == 1
    assert classified.diagnostics["declined_penalties"] == 1


def test_unknown_pass_depth_assignment_is_deterministic() -> None:
    rows = _row(1, "3", "12", "PHI 30", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass incomplete intended for Ron Runner')
    game = parse_pfr_boxscore(_game_html(rows), "depth")

    first = classify_pfr_game(game, seed=44)
    second = classify_pfr_game(game, seed=44)

    assert first.plays == second.plays
    assert len(first.plays) == 1
    assert first.plays[0].chart in {"screen", "short_pass", "medium_pass", "long_pass"}
    assert first.plays[0].result == "BLACK"
    assert first.diagnostics["heuristic_pass_depth"] == 1


def test_parser_reads_pfr_tables_wrapped_in_html_comments() -> None:
    html = _game_html(
        _row(1, "1", "10", "PHI 20", '<a href="/players/R/RushRo00.htm">Ron Runner</a> up the middle for 4 yards')
    )
    commented = html.replace('<table id="player_offense">', '<!--<table id="player_offense">').replace(
        '</tbody></table>\n      <table id="pbp">', '</tbody></table>-->\n      <!--<table id="pbp">', 1
    ).replace('</tbody></table>\n    </body>', '</tbody></table>-->\n    </body>', 1)

    game = parse_pfr_boxscore(commented, "commented")

    assert len(game.plays) == 1
    assert game.player_teams["RushRo00"] == "PHI"


def test_fumble_loss_and_penalty_only_rows_are_retained() -> None:
    rows = "".join(
        (
            _row(1, "1", "10", "PHI 20", '<a href="/players/R/RushRo00.htm">Ron Runner</a> up the middle for 4 yards'),
            _row(2, "2", "6", "PHI 24", 'Penalty on PHI: False Start, 5 yards (accepted)'),
            _row(3, "2", "11", "PHI 19", '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 3 yards. Ron Runner fumbles, recovered by <a href="/players/D/DefeDa00.htm">Dan Defender</a> at PHI22'),
        )
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "fumbles"), seed=8306)

    assert any(play.result == "OFF 5" for play in classified.plays)
    assert any(play.chart == "off_tackle" and play.result == "F + 3" for play in classified.plays)
    assert [(event.team, event.unit, event.lost) for event in classified.fumbles] == [
        ("PHI", "rushing", True)
    ]
    assert classified.diagnostics["unknown_penalty_play_family"] == 1


def test_play_by_play_enriches_fumble_and_field_goal_calibration() -> None:
    from paydirt.chart_generator import TeamSeasonStats
    from paydirt.pfr_play_by_play import calibrate_stats_from_pbp

    stats = TeamSeasonStats.from_dict(
        {
            "season": 2026,
            "team_name": "Foxes",
            "short_name": "FOX",
            "offense": {"rushing": {"attempts": 100}, "passing": {"attempts": 100}},
            "defense": {"rushing": {"attempts": 100}, "passing": {"attempts": 100}},
        }
    )

    rows = "".join(
        (
            _row(1, "1", "10", "PHI 20", '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 3 yards. Ron Runner fumbles, recovered by <a href="/players/D/DefeDa00.htm">Dan Defender</a> at PHI23'),
            _row(2, "4", "5", "SFO 20", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 37 yard field goal good'),
            _row(3, "4", "8", "SFO 31", '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 48 yard field goal no good'),
        )
    )
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "calibration"))

    enriched = calibrate_stats_from_pbp(
        stats,
        team="PHI",
        field_goals=classified.field_goals,
        fumbles=classified.fumbles,
    )

    assert enriched.offense.rushing.fumbles == 1
    assert enriched.offense.rushing.fumbles_lost == 1
    assert enriched.special_teams.field_goal.attempts == 2
    assert enriched.special_teams.field_goal.made == 1
    assert enriched.special_teams.field_goal.long == 37
    assert [(bucket.distance, bucket.attempts, bucket.made) for bucket in enriched.special_teams.field_goal_by_distance] == [
        (37, 1, 1),
        (48, 1, 0),
    ]


def test_pfr_chart_command_generates_team_and_audit_inputs(tmp_path, monkeypatch) -> None:
    import json

    import generate_pfr_charts as command
    from generate_pfr_charts import main

    original_generate = command.generate_team_charts
    pressure_models = []

    def generate_with_shared_pressure(*args, **kwargs):
        assert kwargs.get("neutral_pressure") is not None
        pressure_models.append(kwargs["neutral_pressure"])
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(command, "generate_team_charts", generate_with_shared_pressure)

    html_dir = tmp_path / "html"
    stats_dir = tmp_path / "stats"
    template_dir = tmp_path / "template"
    output_dir = tmp_path / "output"
    audit_dir = tmp_path / "audit"
    html_dir.mkdir()
    stats_dir.mkdir()
    (template_dir / "Foxes").mkdir(parents=True)
    (template_dir / "2026.yaml").write_text("season: 2026\ntwo_point_conversion: true\n", encoding="utf-8")
    (template_dir / "Foxes" / "roster.json").write_text("{}\n", encoding="utf-8")
    (html_dir / "202609010fox.htm").write_text(
        _game_html(
            _row(1, "1", "10", "PHI 20", '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 4 yards')
        ),
        encoding="utf-8",
    )
    stats = {
        "season": 2026,
        "team_name": "Foxes",
        "short_name": "FOX",
        "offense": {"rushing": {"attempts": 100, "yards": 400}, "passing": {"attempts": 100, "completions": 60, "yards": 700}},
        "defense": {"rushing": {"attempts": 100, "yards": 400}, "passing": {"attempts": 100, "completions": 60, "yards": 700}},
    }
    (stats_dir / "Foxes.json").write_text(json.dumps(stats), encoding="utf-8")
    team_map = tmp_path / "team-map.json"
    team_map.write_text(json.dumps({"PHI": "Foxes"}), encoding="utf-8")

    result = main(
        [
            "--html-dir", str(html_dir),
            "--stats-dir", str(stats_dir),
            "--template-season", str(template_dir),
            "--team-map", str(team_map),
            "--output", str(output_dir),
            "--audit-dir", str(audit_dir),
        ]
    )

    assert result == 0
    assert (output_dir / "Foxes" / "offense.csv").exists()
    assert (output_dir / "Foxes" / "roster.json").exists()
    assert (output_dir / "2026.yaml").exists()
    assert (audit_dir / "Foxes.csv").exists()
    manifest = json.loads((output_dir / "generation-manifest.json").read_text())
    assert pressure_models
    assert all(model is pressure_models[0] for model in pressure_models)
    assert manifest["neutral_pressure_model"] == pressure_models[0].evidence
    assert manifest["games"] == 1
    assert all(team.get("primary_layout", {}).get("invariants_passed") is True
               for team in manifest["teams"].values())
    import hashlib
    assert manifest["input_hashes"]["normalized_stats/Foxes.json"] == hashlib.sha256((stats_dir / "Foxes.json").read_bytes()).hexdigest()
    ledger_path = audit_dir / "source-ledger.json"
    assert ledger_path.is_file()
    ledger = json.loads(ledger_path.read_text())
    assert ledger["games"][0]["game_id"] == "202609010fox"
    assert len(ledger["games"][0]["raw_sha256"]) == 64
    assert ledger["games"][0]["representations"][0]["play_number"] == 1
    import hashlib
    assert manifest["classification_ledger"]["sha256"] == hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    assert manifest["source_rows"] == 1
    assert "modeled_missing_features" in manifest["source_feature_coverage"]
    audit = json.loads((output_dir / "chart-audit.json").read_text())
    assert audit["passed"]
    assert audit["team_count"] == 1
    assert manifest["calibration_profile"] == {
        "run_yard_multiplier": 1.0,
        "pass_completion_adjustment": 0.0,
        "pass_interception_adjustment": 0.0,
        "pass_pressure_adjustment": 0.0,
        "pass_yard_multiplier": 1.0,
    }
    assert manifest["teams"]["Foxes"]["empirical_outcomes"] == 1
    assert manifest["teams"]["Foxes"]["generated_empirical_outcomes"] == 0
    assert manifest["teams"]["Foxes"]["fallback_columns"] == 1


def test_observed_gain_does_not_rigidly_define_pass_family() -> None:
    rows = "".join(
        _row(
            number,
            "2",
            "8",
            "PHI 30",
            f'<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner for 2 yards play {number}',
        )
        for number in range(1, 41)
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "pass-family"), seed=8306)
    charts = {play.chart for play in classified.plays}

    assert len(charts) > 1
    assert classified.diagnostics["heuristic_pass_depth"] == 40


def test_nullified_field_goal_is_not_counted_as_an_attempt() -> None:
    rows = _row(
        1,
        "4",
        "5",
        "SFO 20",
        '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 37 yard field goal good '
        'Penalty on PHI: Offensive Holding, 10 yards (accepted) (no play)',
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "nullified-kick"))

    assert classified.field_goals == ()
    assert classified.diagnostics["nullified_field_goals"] == 1


def test_touchdown_results_follow_developer_chart_conventions() -> None:
    """Encode scoring plays the same way as the developer-created charts."""
    rows = "".join(
        (
            _row(
                1,
                "1",
                "2",
                "SFO 2",
                '<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 2 yards, touchdown',
            ),
            _row(
                2,
                "1",
                "10",
                "SFO 35",
                '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner for 35 yards, touchdown',
            ),
            _row(
                3,
                "1",
                "10",
                "SFO 45",
                '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner for 45 yards, touchdown',
            ),
            _row(
                4,
                "4",
                "10",
                "PHI 20",
                '<a href="/players/P/PuntPa00.htm">Pat Punter</a> punts 45 yards, returned by '
                '<a href="/players/R/RetuRa00.htm">Ray Returner</a> for 65 yards, touchdown',
            ),
            _row(
                5,
                "1",
                "10",
                "SFO 35",
                '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass intended for Ron Runner is intercepted by '
                '<a href="/players/D/DefeDa00.htm">Dan Defender</a> at SFO35 and returned for 55 yards, touchdown',
            ),
            _row(
                6,
                "1",
                "10",
                "SFO 35",
                '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass intended for Ron Runner is intercepted by '
                '<a href="/players/D/DefeDa00.htm">Dan Defender</a> at SFO30 and returned for 70 yards, touchdown',
            ),
        )
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "touchdown-results"))
    offense = [play for play in classified.plays if play.unit == "offense"]
    punt_returns = [play for play in classified.plays if play.chart == "punt_return"]
    interception_returns = [
        play for play in classified.plays if play.chart == "interception_return"
    ]

    assert [(play.chart, play.result) for play in offense[:3]] == [
        ("off_tackle", "2"),
        (offense[1].chart, "35"),
        (offense[2].chart, "45"),
    ]
    assert offense[1].chart in {"screen", "short_pass", "medium_pass", "long_pass"}
    assert offense[2].chart == "long_pass"
    assert any(play.result.startswith("INT ") for play in offense)
    assert [(play.team, play.result) for play in punt_returns] == [("SFO", "65")]
    assert [(play.team, play.result) for play in interception_returns] == [
        ("SFO", "55"),
        ("SFO", "70"),
    ]


def test_special_teams_penalties_are_retained_as_chart_results() -> None:
    rows = "".join(
        (
            _row(
                1,
                "",
                "",
                "PHI 35",
                '<a href="/players/K/KickKi00.htm">Ken Kicker</a> kicks off 65 yards, '
                'returned by <a href="/players/R/RetuRa00.htm">Ray Returner</a> for 20 yards. '
                'Penalty on SFO: Holding, 10 yards (declined)',
            ),
            _row(
                2,
                "4",
                "10",
                "PHI 40",
                '<a href="/players/P/PuntPa00.htm">Pat Punter</a> punts 40 yards, '
                'returned by <a href="/players/R/RetuRa00.htm">Ray Returner</a> for 7 yards. '
                'Penalty on PHI: Holding, 10 yards (accepted)',
            ),
            _row(
                3,
                "4",
                "5",
                "SFO 20",
                '<a href="/players/K/KickKi00.htm">Ken Kicker</a> 37 yard field goal good. '
                'Penalty on SFO: Offside, 5 yards (accepted) (no play)',
            ),
            _row(
                4,
                "1",
                "10",
                "SFO 35",
                '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass intended for Ron Runner is intercepted by '
                '<a href="/players/D/DefeDa00.htm">Dan Defender</a> at PHI45 and returned for 18 yards. '
                'Penalty on SFO: Holding, 10 yards (accepted)',
            ),
        )
    )

    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "special-penalties"))

    assert [
        (play.team, play.chart, play.result)
        for play in classified.plays
        if play.unit == "special_teams"
    ] == [
        ("SFO", "kickoff_return", "OFF 10"),
        ("SFO", "punt_return", "DEF 10"),
        ("PHI", "field_goal", "DEF 5"),
        ("SFO", "interception_return", "OFF 10"),
    ]
    assert any(
        play.unit == "offense" and play.result.startswith("INT ")
        for play in classified.plays
    )
    assert classified.diagnostics["special_teams_penalties"] == 4


def test_kickoff_foul_without_return_is_relative_to_kicking_team() -> None:
    rows = _row(1, '', '', 'PHI 35',
        '<a href="/players/K/KickKi00.htm">Ken Kicker</a> kicks off 65 yards. '
        'Penalty on PHI: Offside, 5 yards (accepted) (no play)')
    season = classify_pfr_game(parse_pfr_boxscore(_game_html(rows),'kickoff-foul'))
    assert [(p.team,p.chart,p.result) for p in season.plays] == [('PHI','kickoff','OFF 5')]


def test_return_out_of_bounds_does_not_make_kickoff_illegal() -> None:
    rows = _row(1, '', '', 'PHI 35',
        '<a href="/players/K/KickKi00.htm">Ken Kicker</a> kicks off 65 yards, '
        'returned by <a href="/players/R/RetuRa00.htm">Ray Returner</a> for 20 yards (out of bounds)')
    season = classify_pfr_game(parse_pfr_boxscore(_game_html(rows),'return-oob'))
    assert [(p.chart,p.result) for p in season.plays] == [('kickoff','65'),('kickoff_return','20*')]


def test_half_distance_foul_preserves_nominal_yards_and_first_down() -> None:
    rows = ''.join([
        _row(1, '1', '10', 'PHI 4', '<a href="/players/P/PassPh00.htm">Phil Passer</a> '
             'pass incomplete. Penalty on PHI: False Start, 2 yards (accepted) (no play)'),
        _row(2, '1', '10', 'SFO 6', '<a href="/players/P/PassPh00.htm">Phil Passer</a> '
             'pass incomplete. Penalty on SFO: Defensive Holding, 3 yards (accepted) (no play)'),
    ])
    season = classify_pfr_game(parse_pfr_boxscore(_game_html(rows),'half-distance'))
    assert [p.result for p in season.plays] == ['OFF 5', 'DEF 5X']


def test_kickoff_oob_penalty_uses_the_illegal_kick_procedure() -> None:
    rows = _row(1, '', '', 'PHI 35',
        '<a href="/players/K/KickKi00.htm">Ken Kicker</a> kicks off no gain,. '
        'Penalty on PHI: Kickoff OOB, 5 yards (accepted) (no play)')
    season = classify_pfr_game(parse_pfr_boxscore(_game_html(rows),'kick-out'))
    assert [(p.chart,p.result) for p in season.plays] == [('kickoff','OB')]


def test_qb_run_penalty_is_primary_sample_with_explicit_unknown_call():
    detail = ('<a href="/players/P/PassPh00.htm">Alex Signal</a> scrambles for 4 yards. '
              'Penalty on PHI: Offensive Holding, 10 yards (accepted) (no play)')
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "qb-foul"))
    assert len(classified.plays) == 1
    play = classified.plays[0]
    assert play.result == "OFF 10"
    assert play.chart in {"screen", "short_pass", "medium_pass", "long_pass"}
    assert play.game_id == "qb-foul" and play.play_number == 1 and play.detail
    assert classified.diagnostics["supplemental_penalties_as_primary"] == 1
    assert classified.diagnostics["heuristic_pass_depth"] == 1


@pytest.mark.parametrize("ending,expected_result,expected_sacks", [
    ("sacked by Dan Defender for 5 yards. Penalty on SFO: Unnecessary Roughness, 15 yards (accepted)", "DEF 15", 1),
    ("sacked by Dan Defender for 5 yards. Penalty on PHI: Offensive Holding, 10 yards (accepted) (no play)", "OFF 10", 0),
    ("scrambles for 4 yards. Penalty on PHI: Offensive Holding, 10 yards (declined)", "4", 0),
])
def test_qb_foul_normalization_preserves_retained_nullified_and_declined_semantics(ending, expected_result, expected_sacks):
    detail = '<a href="/players/P/PassPh00.htm">Alex Signal</a> ' + ending
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "qb-foul-controls"))
    assert classified.diagnostics.get("sacks", 0) == expected_sacks
    if "declined" in ending:
        assert any(play.chart == "qb_time" and play.result == expected_result for play in classified.plays)
        assert classified.diagnostics.get("supplemental_penalties_as_primary", 0) == 0
    else:
        assert len(classified.plays) == 1
        assert classified.plays[0].result == expected_result
        assert classified.plays[0].chart in {"screen", "short_pass", "medium_pass", "long_pass"}
        assert classified.diagnostics["supplemental_penalties_as_primary"] == 1


def test_known_qb_run_with_unobserved_design_keeps_unknown_primary_foul_family():
    detail = ('<a href="/players/P/PassPh00.htm">Alex Signal</a> for 4 yards. '
              'Penalty on PHI: Offensive Holding, 10 yards (accepted)')
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "2", "8", "PHI 30", detail)), "unknown-design"))
    assert classified.plays[0].chart in {"line_plunge", "off_tackle", "end_run", "draw",
                                        "screen", "short_pass", "medium_pass", "long_pass"}
    assert classified.diagnostics["unknown_penalty_play_family"] == 1
    assert classified.diagnostics["supplemental_penalties_as_primary"] == 1
    assert not classified.diagnostics.get("heuristic_pass_depth", 0)


@pytest.mark.parametrize("recovery", ["", ", recovered by Unknown Actor at PHI23"])
def test_unknown_pfr_fumble_recovery_is_not_retention(recovery: str) -> None:
    detail = ('<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 3 yards. '
              f'Ron Runner fumbles{recovery}')
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "1", "10", "PHI 20", detail)), "unknown-fumble"))
    assert len(classified.fumbles) == 1
    assert classified.fumbles[0].lost is None
    assert classified.diagnostics["unknown_fumble_recoveries"] == 1


@pytest.mark.parametrize("location", ["PHI23", "PHI 23", "PHIE23", "PHIE 23"])
@pytest.mark.parametrize("actor_id,name,lost", [
    ("RushRo00", "Ron Runner", False), ("DefeDa00", "Dan Defender", True),
])
def test_recovery_ownership_uses_actor_with_long_source_location_codes(location, actor_id, name, lost):
    detail = ('<a href="/players/R/RushRo00.htm">Ron Runner</a> right tackle for 3 yards. '
              f'Ron Runner fumbles, recovered by <a href="/players/{actor_id[0]}/{actor_id}.htm">'
              f'{name}</a> at {location}')
    classified = classify_pfr_game(parse_pfr_boxscore(_game_html(_row(1, "1", "10", "PHI 20", detail)), "recovery-code"))
    assert len(classified.fumbles) == 1
    assert classified.fumbles[0].lost is lost
    assert classified.diagnostics.get("unknown_fumble_recoveries", 0) == 0


def test_unknown_fumble_calibration_cannot_replace_an_official_loss_with_retention() -> None:
    from paydirt.chart_generator import TeamSeasonStats
    from paydirt.pfr_play_by_play import FumbleEvent, calibrate_stats_from_pbp

    stats = TeamSeasonStats.from_dict({
        "season": 2026, "team_name": "Foxes", "short_name": "FOX",
        "offense": {"rushing": {"attempts": 100, "fumbles": 1, "fumbles_lost": 1},
                    "passing": {"attempts": 100}},
        "defense": {"rushing": {"attempts": 100}, "passing": {"attempts": 100}},
    })
    with pytest.raises(ValueError, match="unknown fumble recovery"):
        calibrate_stats_from_pbp(stats, "FOX", [], [FumbleEvent("FOX", "rushing", None, "syn", 1)])
    assert stats.offense.rushing.fumbles_lost == 1


@pytest.mark.parametrize("actor,lost", [("R.J. Runner", False), ("D.J. Defender", True)])
@pytest.mark.parametrize("ending", [" at PHIE 23", " at and returned for 1 yard", ". Next play"])
def test_recovery_actor_initials_and_incomplete_location_preserve_known_identity(
    actor: str, lost: bool, ending: str,
) -> None:
    detail = (
        '<a href="/players/R/RushRo00.htm">R.J. Runner</a> for 2 yards. '
        f'R.J. Runner fumbles, recovered by {actor}{ending}'
    )
    html = _game_html(_row(1, "2", "8", "PHI 30", detail))
    html = html.replace("Ron Runner", "R.J. Runner").replace("Dan Defender", "D.J. Defender")
    classified = classify_pfr_game(parse_pfr_boxscore(html, "initials-recovery"))
    assert len(classified.fumbles) == 1
    assert classified.fumbles[0].lost is lost
    assert classified.diagnostics.get("unknown_fumble_recoveries", 0) == 0


@pytest.mark.parametrize("actor", ["Ron Runner Junior", "Dan Defender Junior", "Mystery Actor"])
def test_recovery_known_name_prefix_does_not_identify_unknown_actor(actor: str) -> None:
    detail = (
        '<a href="/players/R/RushRo00.htm">Ron Runner</a> for 2 yards. '
        f'Ron Runner fumbles, recovered by {actor} at PHI 23'
    )
    classified = classify_pfr_game(parse_pfr_boxscore(
        _game_html(_row(1, "2", "8", "PHI 30", detail)), "unknown-prefix-recovery",
    ))
    assert classified.fumbles[0].lost is None
    assert classified.diagnostics["unknown_fumble_recoveries"] == 1


@pytest.mark.parametrize("unit", ["rushing", "passing"])
@pytest.mark.parametrize("gain", [None, 0, 4])
def test_fumble_initial_gain_is_not_inferred_from_recovery_return(
    unit: str, gain: int | None,
) -> None:
    initial = "" if gain is None else " for no gain" if gain == 0 else f" for {gain} yards"
    start = (
        '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner'
        if unit == "passing" else '<a href="/players/R/RushRo00.htm">Ron Runner</a> left tackle'
    )
    detail = (f'{start}{initial}. Ron Runner fumbles, recovered by Dan Defender at PHI 23 '
              'and returned for 75 yards, touchdown')
    result = classify_pfr_game(parse_pfr_boxscore(
        _game_html(_row(1, "2", "8", "PHI 30", detail)), "initial-before-return",
    ))
    assert len(result.fumbles) == 1
    assert result.fumbles[0].unit == unit
    assert result.fumbles[0].lost is True
    if gain is None:
        assert not result.plays
        assert result.diagnostics["missing_required_gains"] == 1
    else:
        assert [play.result for play in result.plays] == ["F" if gain == 0 else f"F + {gain}"]
        assert result.diagnostics.get("missing_required_gains", 0) == 0


@pytest.mark.parametrize("unit", ["rushing", "passing"])
def test_missing_fumble_gain_still_preserves_known_recovery(unit: str) -> None:
    start = (
        '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner'
        if unit == "passing" else '<a href="/players/R/RushRo00.htm">Ron Runner</a> left tackle'
    )
    detail = start + '. Ron Runner fumbles, recovered by Ron Runner at PHIE 23'
    result = classify_pfr_game(parse_pfr_boxscore(
        _game_html(_row(1, "2", "8", "PHI 30", detail)), "missing-initial-own",
    ))
    assert len(result.fumbles) == 1
    assert result.fumbles[0].unit == unit
    assert result.fumbles[0].lost is False
    assert not result.plays
    assert result.diagnostics["missing_required_gains"] == 1


@pytest.mark.parametrize("marker", ["offset", "offsetting"])
def test_offsetting_penalty_only_rows_are_not_missing_gain_scrimmages(marker: str) -> None:
    rows = (
        _row(1, "3", "1", "SFO 39", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass incomplete (no play)')
        + _row(2, "3", "1", "SFO 39", f'Penalty on <a href="/players/P/PassPh00.htm">Phil Passer</a>: Intentional Grounding ({marker})')
        + _row(3, "3", "1", "SFO 39", f'Penalty on <a href="/players/D/DefeDa00.htm">Dan Defender</a>: Defensive Holding ({marker})')
    )
    result = classify_pfr_game(parse_pfr_boxscore(_game_html(rows), "offset-procedure"))
    assert not result.plays
    assert not result.fumbles
    assert result.diagnostics["offsetting_penalties"] == 2
    assert result.diagnostics.get("missing_required_gains", 0) == 0
    assert not result.unsupported_fields



def _fumble_box(html: str, away: str, home: str = "0-0") -> str:
    return html.replace("</body>", f'''<table id="team_stats"><tr>
      <th data-stat="stat">Fumbles-Lost</th><td data-stat="vis_stat">{away}</td>
      <td data-stat="home_stat">{home}</td></tr></table></body>''')


def _fumble_rows(recoveries: list[str | None]) -> str:
    rows = []
    for number, recovery in enumerate(recoveries, 1):
        detail = '<a href="/players/R/RushRo00.htm">Ron Runner</a> left tackle for 3 yards. Ron Runner fumbles'
        if recovery:
            detail += f', recovered by {recovery} at PHI 23'
        rows.append(_row(number, "2", "8", "PHI 30", detail))
    return "".join(rows)


@pytest.mark.parametrize("recoveries,box,expected", [
    ([None, None], "3-0", [False, False]),
    (["Dan Defender", None], "3-1", [True, False]),
    (["Ron Runner", None], "2-1", [False, True]),
    ([None, None], "2-2", [True, True]),
    ([None, None], "2-1", [None, None]),
    ([None], "2-1", [None]),
])
def test_only_unique_team_box_fumble_loss_constraints_resolve_unknowns(
    recoveries: list[str | None], box: str, expected: list[bool | None],
) -> None:
    game = parse_pfr_boxscore(_fumble_box(_game_html(_fumble_rows(recoveries)), box), "box-fumble")
    result = classify_pfr_game(game)
    assert [f.lost for f in result.fumbles] == expected
    resolved = sum(before is None and after is not None for before, after in zip(recoveries, expected))
    assert result.diagnostics.get("box_reconciled_fumble_recoveries", 0) == resolved
    assert result.diagnostics["unknown_fumble_recoveries"] == sum(x is None for x in expected)
    assert game.fumble_box == {"PHI": tuple(int(x) for x in box.split("-")), "SFO": (0, 0)}
    assert len(result.fumble_reconciliations) == resolved
    for receipt in result.fumble_reconciliations:
        assert receipt["method"] == "unique-team-fumble-loss-constraint"
        assert receipt["box_fumbles"] == int(box.split("-")[0])
        assert receipt["box_lost"] == int(box.split("-")[1])


@pytest.mark.parametrize("away,home", [("", "0-0"), ("1-2", "0-0"), ("1-", "0-0"), ("1-1", "")])
def test_invalid_or_incomplete_fumble_box_does_not_supply_zero(away: str, home: str) -> None:
    game = parse_pfr_boxscore(_fumble_box(_game_html(_fumble_rows([None])), away, home), "bad-fumble-box")
    result = classify_pfr_game(game)
    assert game.fumble_box is None
    assert result.fumbles[0].lost is None
    assert not result.fumble_reconciliations


@pytest.mark.parametrize("recoveries,box", [
    (["Dan Defender", "Dan Defender", None], "3-1"),
    (["Ron Runner", "Ron Runner", None], "3-2"),
    (["Dan Defender", None], "1-1"),
])
def test_inconsistent_team_box_cannot_resolve_a_recovery(recoveries: list[str | None], box: str) -> None:
    result = classify_pfr_game(parse_pfr_boxscore(
        _fumble_box(_game_html(_fumble_rows(recoveries)), box), "conflicting-fumble-box",
    ))
    assert result.fumbles[-1].lost is None
    assert result.diagnostics["unreconciled_fumble_box"] == 1
    assert not result.fumble_reconciliations


def test_duplicate_fumble_box_is_not_trusted() -> None:
    html = _fumble_box(_fumble_box(_game_html(_fumble_rows([None])), "1-0"), "1-1")
    game = parse_pfr_boxscore(html, "duplicate-fumble-box")
    result = classify_pfr_game(game)
    assert game.fumble_box is None
    assert result.fumbles[0].lost is None



def test_fumble_constraints_use_each_team_box_and_preserve_passing_unit() -> None:
    rows = (
        _row(1, "2", "8", "PHI 30", '<a href="/players/P/PassPh00.htm">Phil Passer</a> pass complete to Ron Runner for 3 yards. Ron Runner fumbles')
        + _row(2, "2", "8", "SFO 30", '<a href="/players/R/RetuRa00.htm">Ray Returner</a> left tackle for 3 yards. Ray Returner fumbles')
    )
    result = classify_pfr_game(parse_pfr_boxscore(_fumble_box(_game_html(rows), "1-1", "2-0"), "both-fumble-boxes"))
    assert [(f.team, f.unit, f.lost) for f in result.fumbles] == [("PHI", "passing", True), ("SFO", "rushing", False)]
    assert result.diagnostics["box_reconciled_fumble_recoveries"] == 2


def test_duplicate_source_event_identity_cannot_support_box_inference() -> None:
    from dataclasses import replace
    game = parse_pfr_boxscore(_fumble_box(_game_html(_fumble_rows([None, None])), "2-0"), "duplicate-fumble-key")
    game = replace(game, plays=(game.plays[0], replace(game.plays[1], number=game.plays[0].number)))
    result = classify_pfr_game(game)
    assert [f.lost for f in result.fumbles] == [None, None]
    assert result.diagnostics["unreconciled_fumble_box"] == 1
    assert not result.fumble_reconciliations


@pytest.mark.parametrize("result", ["good", "no good", "blocked"])
def test_quarterback_kicked_extra_point_is_not_a_rushing_attempt(result: str) -> None:
    detail = (
        '<a href="/players/P/PassPh00.htm">Quinn Caller</a> '
        f'kicks extra point {result}'
    )
    game = parse_pfr_boxscore(_game_html(_row(1, "", "", "", detail)), "qb-pat")
    classified = classify_pfr_game(game, fumble_gain_policy="historical_fumble_class_proxy_v2")
    assert not classified.plays
    assert not classified.unsupported_fields
    assert classified.diagnostics["ignored_markers"] == 1
    assert classified.diagnostics.get("heuristic_quarterback_run_family", 0) == 0


@pytest.mark.parametrize("detail", [
    '<a href="/players/P/PassPh00.htm">Quinn Caller</a> right end for 2 yards',
    '<a href="/players/P/PassPh00.htm">Quinn Caller</a> pass complete to Ron Runner for 2 yards',
])
def test_quarterback_scrimmage_controls_still_classify(detail: str) -> None:
    game = parse_pfr_boxscore(_game_html(_row(1, "1", "10", "PHI 30", detail)), "qb-scrimmage")
    classified = classify_pfr_game(game)
    assert len(classified.plays) == 1
    assert classified.plays[0].result == "2"
    assert not classified.unsupported_fields


@pytest.mark.parametrize("runner", [
    "Ron Runner",
    '<a href="/players/R/RushRo00.htm">Ron Runner</a>',
])
def test_known_primary_actor_team_wins_over_linked_defender(runner: str) -> None:
    detail = (
        f'{runner} right guard for 5 yards '
        '(tackle by <a href="/players/D/DefeDa00.htm">Dan Defender</a>)'
    )
    classified = classify_pfr_game(parse_pfr_boxscore(
        _game_html(_row(1, "1", "10", "PHI 30", detail)), "actor-team"))
    assert [(p.team, p.opponent, p.result) for p in classified.plays] == [("PHI", "SFO", "5")]


def test_unlinked_primary_fumbler_is_not_credited_to_linked_recoverer() -> None:
    detail = (
        'Ron Runner right guard for 5 yards. Ron Runner fumbles, recovered by '
        '<a href="/players/D/DefeDa00.htm">Dan Defender</a> at PHI35'
    )
    classified = classify_pfr_game(parse_pfr_boxscore(
        _game_html(_row(1, "1", "10", "PHI 30", detail)), "actor-fumble"))
    assert len(classified.fumbles) == 1
    assert classified.fumbles[0].team == "PHI"
    assert classified.fumbles[0].lost is True


def test_duplicate_display_names_preserve_linked_primary_actor_identity() -> None:
    detail = (
        '<a href="/players/R/RushRo00.htm">Ron Runner</a> right guard for 5 yards '
        '(tackle by <a href="/players/D/DefeDa00.htm">Ron Runner</a>)'
    )
    html = _game_html(_row(1, "1", "10", "PHI 30", detail)).replace("Dan Defender", "Ron Runner")
    game = parse_pfr_boxscore(html, "duplicate-names")
    classified = classify_pfr_game(game)
    assert [(p.team, p.opponent, p.result) for p in classified.plays] == [("PHI", "SFO", "5")]
    assert "ron runner" not in game.player_names  # Ambiguous names cannot supply identity.
