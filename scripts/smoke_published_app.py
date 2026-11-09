#!/usr/bin/env python3
"""Verify and run a downloaded release application on an isolated native runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

EXPECTED_TEAMS = {"1983": 28, "2024": 32, "2026": 2}


def verify_asset(path: Path, metadata: dict[str, Any]) -> None:
    """Reject a download whose actual bytes differ from release metadata."""
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != metadata["size"] or digest != metadata.get("digest"):
        raise ValueError(f"Published asset identity mismatch: {path.name}")


def request_json(base: str, path: str, payload: dict | None = None) -> dict:
    """Request actual packaged API data without importing application code."""
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(base + path, data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def check_api(base: str, version: str) -> dict:
    """Require the installed models, every bundled team list and chart books."""
    if request_json(base, "/openapi.json")["info"]["version"] != version:
        raise ValueError("Packaged API version differs from requested release")
    if set(request_json(base, "/api/seasons")["seasons"]) != set(EXPECTED_TEAMS):
        raise ValueError("Unexpected bundled seasons or non-isolated user data")
    counts = {year: len(request_json(base, f"/api/teams?season={year}")["teams"])
              for year in EXPECTED_TEAMS}
    if counts != EXPECTED_TEAMS:
        raise ValueError(f"Incomplete team lists: {counts}")
    game = request_json(base, "/api/game/new", {
        "season": "2026", "player_team": "Ironclads", "opponent_team": "Thunderhawks",
        "difficulty": "hard", "play_as_home": True,
    })
    state = game["game_state"]
    if any(state.get(key) != value for key, value in {
            "quarter": 1, "home_score": 0, "away_score": 0, "time_remaining": 900}.items()):
        raise ValueError("New packaged game has invalid initial state")
    game_id = game["game_id"]
    if not isinstance(game_id, str) or not game_id:
        raise ValueError("New game has no identifier")
    charts = {}
    for side in ["home", "away"]:
        book = request_json(base, f"/api/game/charts/{game_id}?side={side}")
        if any(not book.get(key, {}).get("rows") or not book.get(key, {}).get("columns")
               for key in ["offense", "defense", "special_teams"]):
            raise ValueError(f"Incomplete {side} chart book")
        charts[side] = True
    return {"version": version, "team_counts": counts, "game_id": game_id, "charts": charts}


def check_ui(base: str, output: Path) -> dict:
    """Exercise the rendered bundled UI using a browser outside application code."""
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import sync_playwright

    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: errors.append(f"Failed request: {request.url}"))
            page.on("response", lambda response: errors.append(f"{response.status} {response.url}")
                    if response.url.startswith(base) and response.status >= 400 else None)
            page.goto(base)
            page.get_by_role("button", name="NEW GAME", exact=True).click()
            for season, count in EXPECTED_TEAMS.items():
                page.get_by_role("button", name=season, exact=True).click()
                page.wait_for_function("expected => document.querySelectorAll('div.grid > button').length === expected", arg=count)
            page.get_by_role("button").filter(has_text="Harbor Bay Ironclads").click()
            page.get_by_role("button").filter(has_text="Metro City Thunderhawks").click()
            page.get_by_role("button", name="START GAME", exact=True).click()
            page.get_by_test_id("coin-toss").wait_for()
            page.screenshot(path=str(output / "browser.png"), full_page=True)
            if errors:
                raise RuntimeError(f"Packaged browser errors: {errors}")
            return {"team_grids": EXPECTED_TEAMS, "new_game_screen": True, "errors": errors}
        except BrowserError as error:
            raise RuntimeError(f"Packaged UI verification failed: {error}") from error
        finally:
            browser.close()


def prepare(asset: Path, kind: str, output: Path, assets: list[dict]) -> tuple[Path, str, Path | None]:
    """Install/extract the published bytes, preserving a normal application entry."""
    if kind == "windows-installer":
        install = output / "installed"
        subprocess.run([str(asset), "/S", f"/D={install}"], check=True, timeout=90)
        executable = install / "paydirt.exe"
        verify_asset(executable, next(item for item in assets if item["name"] == "paydirt.exe"))
        return executable, "NSIS silent install, installed executable", None
    if kind == "windows-portable":
        return asset, "published portable executable", None
    if kind == "linux":
        asset.chmod(asset.stat().st_mode | 0o111)
        subprocess.run([str(asset), "--appimage-extract"], cwd=output,
                       check=True, timeout=90, stdout=subprocess.DEVNULL)
        return output / "squashfs-root/AppRun", "AppImage extracted; AppRun entry (no FUSE required)", None
    mount = output / "mount"
    mount.mkdir()
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount),
                    str(asset)], check=True, timeout=90)
    try:
        apps = list(mount.glob("*.app"))
        if len(apps) != 1:
            raise ValueError("DMG must contain exactly one application")
        installed = output / apps[0].name
        shutil.copytree(apps[0], installed, symlinks=True)
        return installed / "Contents/MacOS/paydirt", "mounted DMG copied to isolated app", mount
    except BaseException:
        subprocess.run(["hdiutil", "detach", str(mount)], check=False, timeout=30)
        raise


def stop(process: subprocess.Popen, base: str) -> str:
    """Stop only the owned process tree and require its server to disappear."""
    method = "SIGINT to owning application process"
    if process.poll() is None:
        if sys.platform == "win32":
            method = "CTRL_C to isolated application console"
            helper = """import ctypes, sys, time
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.FreeConsole()
if not kernel.AttachConsole(int(sys.argv[1])):
    raise ctypes.WinError(ctypes.get_last_error())
kernel.SetConsoleCtrlHandler(None, True)
if not kernel.GenerateConsoleCtrlEvent(0, 0):
    raise ctypes.WinError(ctypes.get_last_error())
time.sleep(1)
kernel.FreeConsole()
"""
            subprocess.run([sys.executable, "-c", helper, str(process.pid)], check=True, timeout=10)
        else:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               check=False, timeout=15)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
            raise RuntimeError("Application required forced termination")
    for _ in range(20):
        try:
            request_json(base, "/api/health")
        except urllib.error.HTTPError:
            pass
        except OSError:
            return method
        time.sleep(.25)
    raise RuntimeError("Owned packaged server remained after shutdown")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--kind", choices=["windows-installer", "windows-portable", "linux", "macos"], required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"passed": False, "tag": args.tag, "platform": sys.platform,
               "architecture": os.environ.get("RUNNER_ARCH"), "asset": args.asset.name,
               "security_scope": "Functional native runtime; not signing/notarization/browser-quarantine acceptance"}
    process = None
    mount = None
    base = "http://127.0.0.1:8000"
    try:
        release = json.loads(args.release_json.read_text())
        if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.tag) or release["tag_name"] != args.tag or release["draft"]:
            raise ValueError("A matching published stable version tag is required")
        metadata = next(item for item in release["assets"] if item["name"] == args.asset.name)
        verify_asset(args.asset, metadata)
        receipt["digest"] = metadata["digest"]
        with socket.socket() as preflight:
            preflight.bind(("127.0.0.1", 8000))
        executable, method, mount = prepare(args.asset.resolve(), args.kind, output, release["assets"])
        receipt["launch_method"] = method
        env = os.environ.copy()
        for key in ["PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"]:
            env.pop(key, None)
        if sys.platform == "win32":
            env["LOCALAPPDATA"] = str(output / "user-data")
        elif sys.platform != "darwin":
            env["XDG_DATA_HOME"] = str(output / "user-data")
        options = {"creationflags": subprocess.CREATE_NEW_CONSOLE} if sys.platform == "win32" else {"start_new_session": True}
        with (output / "application.log").open("w") as log:
            process = subprocess.Popen([str(executable)], cwd=output, env=env,
                                       stdout=log, stderr=subprocess.STDOUT, **options)
            deadline = time.monotonic() + 90
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Packaged application exited before API readiness")
                try:
                    request_json(base, "/api/health")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Packaged application startup timed out")
                    time.sleep(.5)
            receipt.update(check_api(base, args.tag[1:]))
            receipt["browser"] = check_ui(base, output)
            # The normal entry point also completes its browser-opening startup delay.
            time.sleep(4)
            receipt["shutdown"] = stop(process, base)
            process = None
        text = (output / "application.log").read_text(errors="replace")
        if "Shutting down..." not in text:
            raise RuntimeError("Application normal shutdown handler did not complete")
        errors = [line for line in text.splitlines()
                  if re.search(r"Traceback|PydanticUserError|\bERROR\b", line)]
        receipt["log_errors"] = errors
        if errors:
            raise RuntimeError("Packaged application emitted error logs")
        receipt["passed"] = True
    except (OSError, ValueError, KeyError, TypeError, StopIteration, RuntimeError, subprocess.SubprocessError) as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            try:
                stop(process, base)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                receipt["cleanup_error"] = str(error)
        if mount is not None:
            detached = subprocess.run(["hdiutil", "detach", str(mount)], check=False, timeout=30)
            if detached.returncode:
                receipt["passed"] = False
                receipt["cleanup_error"] = "DMG detach failed"
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
