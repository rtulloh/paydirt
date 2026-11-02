"""Tests for transforming historical PFR play-by-play into chart outcomes."""

from paydirt.pfr_play_by_play import classify_pfr_game, parse_pfr_boxscore


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


def test_pfr_chart_command_generates_team_and_audit_inputs(tmp_path) -> None:
    import json

    from generate_pfr_charts import main

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
    assert manifest["games"] == 1
    assert manifest["source_rows"] == 1
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
