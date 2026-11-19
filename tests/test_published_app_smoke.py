"""Public/synthetic regressions for published application acceptance."""

import hashlib
import importlib.util
from pathlib import Path

import pytest


def smoke_module():
    path = Path(__file__).resolve().parents[1] / "scripts/smoke_published_app.py"
    assert path.is_file(), "Published-asset smoke implementation is required"
    spec = importlib.util.spec_from_file_location("published_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asset_identity_rejects_changed_bytes(tmp_path):
    smoke = smoke_module()
    artifact = tmp_path / "published.bin"
    artifact.write_bytes(b"reviewed public artifact")
    metadata = {
        "size": artifact.stat().st_size,
        "digest": "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    smoke.verify_asset(artifact, metadata)
    artifact.write_bytes(b"changed public artifact!")
    with pytest.raises(ValueError, match="identity"):
        smoke.verify_asset(artifact, metadata)


def api_responses():
    responses = {
        "/openapi.json": {"info": {"version": "1.10.3"}},
        "/api/seasons": {"seasons": ["2026", "2024", "1983"]},
        **{
            f"/api/teams?season={year}": {"teams": [{"id": str(i)} for i in range(count)]}
            for year, count in [(1983, 28), (2024, 32), (2026, 2)]
        },
        "/api/game/new": {
            "game_id": "game_public",
            "game_state": {
                "quarter": 1,
                "home_score": 0,
                "away_score": 0,
                "time_remaining": 900,
                "season": "2026",
                "home_team": {"id": "Ironclads"},
                "away_team": {"id": "Thunderhawks"},
            },
        },
        **{
            f"/api/game/charts/game_public?side={side}": {
                key: {"rows": [{}], "columns": [{}]}
                for key in ["offense", "defense", "special_teams"]
            }
            for side in ["home", "away"]
        },
    }
    for side, team in [("home", "Ironclads"), ("away", "Thunderhawks")]:
        responses[f"/api/game/charts/game_public?side={side}"].update(
            season="2026", team={"id": team}
        )
    return responses


@pytest.mark.parametrize("failure", [None, "version", "teams", "game", "charts", "empty-charts"])
def test_packaged_api_acceptance_checks_all_required_results(monkeypatch, failure):
    smoke = smoke_module()
    responses = api_responses()
    if failure == "version":
        responses["/openapi.json"]["info"]["version"] = "1.10.2"
    if failure == "teams":
        responses["/api/teams?season=2024"]["teams"].pop()
    if failure == "game":
        responses["/api/game/new"]["game_state"]["quarter"] = 2
    if failure == "charts":
        responses["/api/game/charts/game_public?side=away"].pop("offense")
    if failure == "empty-charts":
        responses["/api/game/charts/game_public?side=away"]["offense"]["rows"] = []
    calls = []

    def request(base, path, payload=None):
        calls.append((path, payload))
        return responses[path]

    monkeypatch.setattr(smoke, "request_json", request)
    if failure:
        with pytest.raises(ValueError):
            smoke.check_api("http://synthetic", "1.10.3")
    else:
        result = smoke.check_api("http://synthetic", "1.10.3")
        assert result["team_counts"] == {"1983": 28, "2024": 32, "2026": 2}
        assert result["game_id"] == "game_public"
        assert calls[-1][0].endswith("side=away")
        payload = next(payload for path, payload in calls if path == "/api/game/new")
        assert payload["player_team"] == "Ironclads"
        assert payload["opponent_team"] == "Thunderhawks"


def test_shutdown_rejects_http_error_from_surviving_server(monkeypatch):
    from unittest.mock import Mock
    from urllib.error import HTTPError

    smoke = smoke_module()
    process = Mock()
    process.poll.return_value = 0
    process.returncode = 0

    def responding(*args):
        raise HTTPError("http://synthetic", 500, "still alive", {}, None)

    monkeypatch.setattr(smoke, "request_json", responding)
    monkeypatch.setattr(smoke.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="remained"):
        smoke.stop(process, "http://synthetic")


@pytest.mark.parametrize("succeeds", [True, False])
def test_windows_launch_explicitly_enables_inherited_ctrl_c(succeeds):
    from unittest.mock import Mock

    smoke = smoke_module()
    kernel = Mock()
    kernel.SetConsoleCtrlHandler.return_value = succeeds
    if succeeds:
        smoke.enable_windows_ctrl_c(kernel)
    else:
        with pytest.raises(OSError, match="Ctrl-C"):
            smoke.enable_windows_ctrl_c(kernel)
    kernel.SetConsoleCtrlHandler.assert_called_once_with(None, False)


def test_shutdown_rejects_abnormal_process_exit(monkeypatch):
    from unittest.mock import Mock

    smoke = smoke_module()
    process = Mock()
    process.poll.return_value = 1
    process.returncode = 1

    def disconnected(*args):
        raise ConnectionRefusedError("closed")

    monkeypatch.setattr(smoke, "request_json", disconnected)
    with pytest.raises(RuntimeError, match="exit status"):
        smoke.stop(process, "http://synthetic")


@pytest.mark.parametrize("ignored_exited", [False, True])
def test_console_differential_requires_ignored_negative_control(ignored_exited):
    smoke = smoke_module()
    results = {
        "enabled": {"normal_exit": True},
        "ignored": {"normal_exit": ignored_exited, "required_cleanup": not ignored_exited},
    }
    if ignored_exited:
        with pytest.raises(RuntimeError, match="inconclusive"):
            smoke.validate_console_controls(results)
    else:
        smoke.validate_console_controls(results)


@pytest.mark.parametrize("remaining", [False, True])
def test_shutdown_rejects_surviving_owned_application_process(remaining):
    from unittest.mock import Mock

    smoke = smoke_module()
    inspector = Mock()
    inspector.NoSuchProcess = ProcessLookupError
    child = Mock()
    child.create_time.return_value = 123.0 if remaining else 456.0
    inspector.Process.return_value = child
    if remaining:
        with pytest.raises(RuntimeError, match="surviving owned"):
            smoke.verify_owned_processes_gone({42: 123.0}, inspector)
    else:
        assert smoke.verify_owned_processes_gone({42: 123.0}, inspector) == []


@pytest.mark.parametrize(
    "version, include_1977, count",
    [
        ("1.10.3", False, 3),
        ("1.10.4", False, 3),
        ("1.10.4", True, 4),
        ("1.11.0", True, 4),
        ("1.12.0", True, 4),
    ],
)
def test_explicit_version_aware_season_profile(version, include_1977, count):
    smoke = smoke_module()
    profile = smoke.season_profile(version, include_1977)
    assert len(profile) == count
    assert profile == {"1983": 28, "2024": 32, "2026": 2, **({"1977": 28} if include_1977 else {})}
    assert profile["2026"] == 2
    assert (profile.get("1977") == 28) == include_1977


def test_candidate_1977_profile_cannot_change_immutable_103_acceptance():
    smoke = smoke_module()
    with pytest.raises(ValueError, match="1.10.4"):
        smoke.season_profile("1.10.3", True)


@pytest.mark.parametrize("candidate_count", [28, 27])
def test_candidate_profile_checks_every_synthetic_1977_team(monkeypatch, candidate_count):
    smoke = smoke_module()
    responses = api_responses()
    responses["/openapi.json"]["info"]["version"] = "1.10.4"
    responses["/api/seasons"]["seasons"].append("1977")
    responses["/api/teams?season=1977"] = {
        "teams": [{"id": str(i)} for i in range(candidate_count)]
    }

    def request(base, path, payload=None):
        if path == "/api/game/new" and payload["season"] == "1977":
            return {
                "game_id": "game_candidate",
                "game_state": {
                    "quarter": 1,
                    "home_score": 0,
                    "away_score": 0,
                    "time_remaining": 900,
                    "season": "1977",
                    "home_team": {"id": "0"},
                    "away_team": {"id": "1"},
                },
            }
        if path.startswith("/api/game/charts/game_candidate"):
            side = path.split("=")[-1]
            return {
                **{
                    key: {"rows": [{}], "columns": [{}]}
                    for key in ["offense", "defense", "special_teams"]
                },
                "season": "1977",
                "team": {"id": "0" if side == "home" else "1"},
            }
        return responses[path]

    monkeypatch.setattr(smoke, "request_json", request)
    if candidate_count == 28:
        assert smoke.check_api("http://synthetic", "1.10.4", True)["team_counts"]["1977"] == 28
    else:
        with pytest.raises(ValueError, match="Incomplete team"):
            smoke.check_api("http://synthetic", "1.10.4", True)


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "game",
        "home-chart",
        "away-chart",
        "reused-id",
        "wrong-season",
        "wrong-team",
        "wrong-chart-team",
    ],
)
@pytest.mark.parametrize("version", ["1.10.4", "1.11.0", "1.12.0"])
def test_opt_in_1977_creates_game_and_checks_both_chart_books(monkeypatch, failure, version):
    smoke = smoke_module()
    responses = api_responses()
    responses["/openapi.json"]["info"]["version"] = version
    if version in {"1.11.0", "1.12.0"}:
        responses["/api/teams?season=1983"]["teams"][:3] = [
            {"id": team, "short_name": label} for team, label in {
                "Chargers": "SD '83", "Cardinals": "STL '83", "Raiders": "LA '83",
            }.items()
        ]
    responses["/api/seasons"]["seasons"].append("1977")
    responses["/api/teams?season=1977"] = {"teams": [{"id": f"Synthetic{i}"} for i in range(28)]}
    game_1977 = {
        "game_id": "game_synthetic_1977",
        "game_state": {
            "quarter": 1,
            "home_score": 0,
            "away_score": 0,
            "time_remaining": 900,
            "season": "1977",
            "home_team": {"id": "Synthetic0"},
            "away_team": {"id": "Synthetic1"},
        },
    }
    if failure == "game":
        game_1977["game_state"]["quarter"] = 2
    if failure == "reused-id":
        game_1977["game_id"] = "game_public"
    if failure == "wrong-season":
        game_1977["game_state"]["season"] = "2026"
    if failure == "wrong-team":
        game_1977["game_state"]["home_team"]["id"] = "Ironclads"
    for side in ["home", "away"]:
        responses[f"/api/game/charts/game_synthetic_1977?side={side}"] = {
            key: {"rows": [{}], "columns": [{}]} for key in ["offense", "defense", "special_teams"]
        }
        responses[f"/api/game/charts/game_synthetic_1977?side={side}"].update(
            season="1977", team={"id": "Synthetic0" if side == "home" else "Synthetic1"}
        )
    if failure == "wrong-chart-team":
        responses["/api/game/charts/game_synthetic_1977?side=away"]["team"]["id"] = "Ironclads"
    if failure == "home-chart":
        responses["/api/game/charts/game_synthetic_1977?side=home"].pop("offense")
    if failure == "away-chart":
        responses["/api/game/charts/game_synthetic_1977?side=away"]["defense"]["rows"] = []
    calls = []

    def request(base, path, payload=None):
        calls.append((path, payload))
        if path == "/api/game/new" and payload["season"] == "1977":
            return game_1977
        if (
            failure == "reused-id"
            and path.startswith("/api/game/charts/game_public")
            and any(body and body.get("season") == "1977" for _, body in calls)
        ):
            return responses[path.replace("game_public", "game_synthetic_1977")]
        return responses[path]

    monkeypatch.setattr(smoke, "request_json", request)
    if failure:
        with pytest.raises(ValueError):
            smoke.check_api("http://synthetic", version, True)
    else:
        result = smoke.check_api("http://synthetic", version, True)
        assert result["team_counts"] == {"1983": 28, "2024": 32, "2026": 2, "1977": 28}
        assert sum(result["team_counts"].values()) == 90
        assert result["season_games"]["1977"]["game_id"] == "game_synthetic_1977"
        assert result["season_games"]["2026"]["game_id"] == "game_public"
        created = [payload for path, payload in calls if path == "/api/game/new"]
        assert [
            (item["season"], item["player_team"], item["opponent_team"]) for item in created
        ] == [("2026", "Ironclads", "Thunderhawks"), ("1977", "Synthetic0", "Synthetic1")]
        assert calls[-2][0].endswith("game_synthetic_1977?side=home")
        assert calls[-1][0].endswith("game_synthetic_1977?side=away")


def test_next_reviewed_release_preserves_1977_and_immutable_profiles() -> None:
    smoke = smoke_module()
    assert smoke.season_profile("1.10.5", True) == {
        "1983": 28,
        "2024": 32,
        "2026": 2,
        "1977": 28,
    }
    with pytest.raises(ValueError, match="reviewed"):
        smoke.season_profile("1.10.7", True)
    assert smoke.season_profile("1.10.6", True) == {
        "1983": 28,
        "2024": 32,
        "2026": 2,
        "1977": 28,
    }
    assert smoke.season_profile("1.10.3") == {"1983": 28, "2024": 32, "2026": 2}


@pytest.mark.parametrize(
    "failure", [None, "Chargers", "Cardinals", "Raiders", "missing", "duplicate"]
)
@pytest.mark.parametrize("version", ["1.10.5", "1.10.6", "1.11.0", "1.12.0"])
def test_corrective_release_checks_packaged_1983_identity_labels(
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    version: str,
) -> None:
    smoke = smoke_module()
    responses = api_responses()
    responses["/openapi.json"]["info"]["version"] = version
    teams = responses["/api/teams?season=1983"]["teams"]
    corrected = {"Chargers": "SD '83", "Cardinals": "STL '83", "Raiders": "LA '83"}
    teams[:3] = [{"id": team, "short_name": label} for team, label in corrected.items()]
    if failure in corrected:
        old_labels = {"Chargers": "LAC '83", "Cardinals": "ARI '83", "Raiders": "OAK '83"}
        next(team for team in teams if team["id"] == failure)["short_name"] = old_labels[failure]
    if failure == "missing":
        teams[0] = {"id": "Other", "short_name": "SD '83"}
    if failure == "duplicate":
        teams[3] = {"id": "Chargers", "short_name": "SD '83"}
    monkeypatch.setattr(smoke, "request_json", lambda base, path, payload=None: responses[path])
    if failure:
        with pytest.raises(ValueError, match="1983.*identity"):
            smoke.check_api("http://synthetic", version)
    else:
        result = smoke.check_api("http://synthetic", version)
        assert result["verified_1983_labels"] == corrected


def test_release_automatically_calls_published_install_verification() -> None:
    root = Path(__file__).resolve().parents[1]
    release = (root / ".github/workflows/release.yml").read_text()
    smoke = (root / ".github/workflows/post-release-smoke.yml").read_text()
    assert "  workflow_call:" in smoke
    post_release = release.split("  verify-published-install:", 1)[1]
    assert "needs: [verify-ci, release]" in post_release
    assert "uses: ./.github/workflows/post-release-smoke.yml" in post_release
    assert "release_tag: ${{ needs.verify-ci.outputs.tag }}" in post_release
    assert "include_1977: true" in post_release


@pytest.mark.parametrize("version", ["1.10.7", "1.11.1", "1.13.0", "2.0.0"])
def test_unreviewed_future_native_profiles_are_rejected(version: str) -> None:
    with pytest.raises(ValueError, match="reviewed"):
        smoke_module().season_profile(version, True)


def test_reviewed_season_release_112_preserves_complete_season_profile() -> None:
    assert smoke_module().season_profile('1.12.0', True) == {
        '1977': 28, '1983': 28, '2024': 32, '2026': 2,
    }


@pytest.mark.parametrize("first_year", ["synthetic-older", "2026"])
@pytest.mark.parametrize("browser_error", [False, True])
def test_packaged_ui_sets_both_independent_years(monkeypatch, tmp_path, first_year, browser_error):
    """A year button changes only the active side, as in the rendered selector."""
    import sys
    from types import SimpleNamespace

    smoke = smoke_module()
    years = {"player": first_year, "opponent": first_year}
    expected = dict.fromkeys([first_year, "2026"], 2)
    state = {"side": "player", "selected": [], "grids": [], "closed": False}
    callbacks = {}

    class Control:
        def __init__(self, name):
            self.name = name

        def filter(self, *, has_text):
            return Control(has_text)

        def select_option(self, year):
            side = {"Your chart year": "player", "Opponent chart year": "opponent"}[self.name]
            years[side] = year
            state["side"] = side

        def click(self):
            if self.name in expected:
                years[state["side"]] = self.name
            elif self.name == "Choose your team":
                state["side"] = "player"
            elif self.name in {"Harbor Bay Ironclads", "Metro City Thunderhawks"}:
                assert years[state["side"]] == "2026", "Selected team's edition is unavailable"
                state["selected"].append((state["side"], self.name, "2026"))
                state["side"] = "opponent"
            elif self.name == "START GAME":
                assert len(state["selected"]) == 2

        def wait_for(self):
            assert self.name == "coin-toss"
            assert len(state["selected"]) == 2

    class Page:
        def on(self, event, callback):
            callbacks[event] = callback

        def goto(self, base):
            if browser_error:
                callbacks["pageerror"]("synthetic render failure")

        def get_by_role(self, role, *, name=None, exact=False):
            return Control(name)

        def get_by_test_id(self, name):
            return Control(name)

        def wait_for_function(self, script, *, arg):
            assert arg == expected[years[state["side"]]]
            state["grids"].append(years[state["side"]])

        def screenshot(self, **kwargs):
            pass

    class Browser:
        def new_page(self, **kwargs):
            return Page()

        def close(self):
            state["closed"] = True

    class Playwright:
        chromium = SimpleNamespace(launch=Browser)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = SimpleNamespace(Error=type("BrowserError", (Exception,), {}), sync_playwright=Playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake)
    if browser_error:
        with pytest.raises(RuntimeError, match="synthetic render failure"):
            smoke.check_ui("http://synthetic", tmp_path, expected)
    else:
        result = smoke.check_ui("http://synthetic", tmp_path, expected)
        assert result == {"team_grids": expected, "new_game_screen": True, "errors": []}
    assert state["selected"] == [
        ("player", "Harbor Bay Ironclads", "2026"),
        ("opponent", "Metro City Thunderhawks", "2026"),
    ]
    assert set(expected).issubset(state["grids"])
    assert state["closed"]
