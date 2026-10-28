from __future__ import annotations

import logging
import os
import posixpath
import random
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Handle both development and bundled (PyInstaller) environments
if getattr(sys, "frozen", False):
    # Running as bundled executable
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller
        _base_path = Path(sys._MEIPASS)
    else:
        # cx_Freeze or similar
        _base_path = Path(os.path.dirname(sys.executable))
    sys.path.insert(0, str(_base_path))
else:
    # Running in development
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paydirt.packaging import get_all_season_paths, get_builtin_seasons_path

# For backwards compatibility - SEASONS_DIR points to built-in seasons
SEASONS_DIR = get_builtin_seasons_path()

from paydirt.chart_loader import load_team_chart
from paydirt.computer_ai import cpu_should_accept_penalty, create_computer_ai
from paydirt.game_engine import PaydirtGameEngine
from paydirt.play_resolver import DefenseType, PlayType, is_passing_play
from paydirt.season_rules import load_season_rules

router = APIRouter()

games: dict[str, dict[str, Any]] = {}


@router.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Canonical player topics, assembled for offline reading without a second manual.
GUIDE_PAGES = (
    "installation.md", "web-interface.md", "playing.md", "priority-chart.md", "clock-management.md",
    "ai-difficulty.md", "seasons.md", "chart-generator.md", "saved-games-and-standings.md",
)


def _guide_lines(content: str) -> list[tuple[str, bool]]:
    """Identify fenced code so examples are not rewritten or indexed as headings."""
    lines = []
    fence = ""
    for line in content.split("\n"):
        marker = re.match(r"^ {0,3}(\x60{3,}|~{3,})", line)
        in_code = bool(fence or marker)
        if marker:
            run = marker.group(1)
            if not fence:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not line[marker.end():].strip():
                fence = ""
        lines.append((line, in_code))
    return lines


def _guide_slug(text: str) -> str:
    """Heading slug shared with HelpGuide's Markdown anchor renderer."""
    return re.sub(r"[^\w -]", "", text.lower()).replace(" ", "-")


def _assemble_guide(docs_path: Path) -> str:
    """Join canonical topics and turn their relative links into offline anchors."""
    pages = {page: (docs_path / page).read_text(encoding="utf-8") for page in GUIDE_PAGES}
    anchors = {}
    titles = {}
    used = {"paydirt-user-guide"}
    for page, content in pages.items():
        local_used = set()
        for line, in_code in _guide_lines(content):
            heading = re.match(r"^#{1,6} (.+?)(?: +#+)?$", line) if not in_code else None
            if not heading:
                continue
            title = heading.group(1)
            base = _guide_slug(title)
            local = base
            suffix = 1
            while local in local_used:
                local = f"{base}-{suffix}"
                suffix += 1
            local_used.add(local)
            combined = base
            suffix = 1
            while combined in used:
                combined = f"{base}-{suffix}"
                suffix += 1
            used.add(combined)
            anchors[page, local] = combined
            if page not in titles:
                titles[page] = title
                anchors[page, ""] = combined

    def rewrite_link(match: re.Match, page: str) -> str:
        label, target = match.groups()
        if ":" in target or target.startswith("/"):
            return match.group(0)
        path, _, fragment = target.partition("#")
        target_page = path or page
        if target_page == "README.md":
            anchor = "paydirt-user-guide"
        else:
            anchor = anchors.get((target_page, fragment))
        if anchor is not None:
            return f"[{label}](#{anchor})"
        repo_path = posixpath.normpath(f"docs/{path}") if path else f"docs/{page}"
        url = f"https://github.com/rtulloh/paydirt/blob/main/{repo_path}"
        return f"[{label}]({url}{'#' + fragment if fragment else ''})"

    contents = ["# Paydirt User Guide", ""]
    contents.extend(f"- [{titles[page]}](#{anchors[page, '']})" for page in GUIDE_PAGES)
    for page, content in pages.items():
        contents.extend(["", "---", ""])
        for line, in_code in _guide_lines(content):
            contents.append(line if in_code else re.sub(
                r"(?<!!)\[([^\]]+)\]\(([^)]+)\)",
                lambda match, page=page: rewrite_link(match, page), line,
            ))
    return _filter_readme_for_guide("\n".join(contents))


def _filter_readme_for_guide(content: str) -> str:
    """
    Filter legacy developer sections and rewrite guide image paths.

    Removes:
    - Project Structure section
    - Building Standalone Executables section (includes Code Signing)

    Rewrites:
    - Image paths from docs/images/X.png to /api/docs/images/X.png
    """
    filtered_lines = []
    skip_until_next_h2 = False
    sections_to_skip = ["## Project Structure", "## Building Standalone Executables"]

    for line, in_code in _guide_lines(content):
        if in_code:
            if not skip_until_next_h2:
                filtered_lines.append(line)
            continue
        # Check if we hit a section to skip
        if any(line.startswith(section) for section in sections_to_skip):
            skip_until_next_h2 = True
            continue

        # Check if we hit a new H2 section (stop skipping)
        if skip_until_next_h2 and line.startswith("## "):
            skip_until_next_h2 = False

        # Add line if we're not skipping
        if not skip_until_next_h2:
            # Rewrite image paths to use API endpoint
            line = re.sub(
                r"!\[([^\]]*)\]\((?:docs/)?images/([^)]+)\)",
                r"![\1](/api/docs/images/\2)",
                line,
            )
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


class GuideResponse(BaseModel):
    content: str
    title: str = "Paydirt User Guide"


@router.get("/api/guide", response_model=GuideResponse)
async def get_guide():
    """Return the complete player manual from the bundled canonical topic files."""
    docs_path = _get_docs_path()
    if docs_path is None:
        raise HTTPException(status_code=404, detail="Guide not available")
    try:
        return GuideResponse(content=_assemble_guide(docs_path))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Guide topic not available")
    except Exception as error:
        logging.getLogger(__name__).debug("Operation failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading guide: {error}")


def _get_docs_path() -> Optional[Path]:
    """
    Get the path to the docs directory.

    In bundled mode, docs is in the same directory as other bundled files.
    In development mode, it's in the project root.
    """
    if getattr(sys, "frozen", False):
        # Bundled mode
        if hasattr(sys, "_MEIPASS"):
            docs_path = Path(sys._MEIPASS) / "docs"
        else:
            docs_path = Path(os.path.dirname(sys.executable)) / "docs"
    else:
        # Development mode
        docs_path = Path(__file__).parent.parent.parent / "docs"

    return docs_path if docs_path.exists() else None


@router.get("/api/docs/images/{image_name}")
async def get_doc_image(image_name: str):
    """
    Serve documentation images.

    Returns images from the docs/images directory for use in the guide.
    """
    # Validate image name to prevent path traversal
    if "/" in image_name or "\\" in image_name or ".." in image_name:
        raise HTTPException(status_code=400, detail="Invalid image name")

    # Only allow common image extensions
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    ext = Path(image_name).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image type")

    docs_path = _get_docs_path()
    if docs_path is None:
        raise HTTPException(status_code=404, detail="Documentation not available")

    image_path = docs_path / "images" / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Determine media type
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(image_path, media_type=media_type)


class Team(BaseModel):
    id: str
    name: str
    short_name: Optional[str] = None
    team_color: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PenaltyOptionModel(BaseModel):
    penalty_type: str
    raw_result: str
    yards: int
    description: str
    auto_first_down: bool = False
    is_pass_interference: bool = False
    result_preview: Optional[str] = None


class PenaltyChoiceModel(BaseModel):
    penalty_options: list[PenaltyOptionModel]
    offended_team: str
    offsetting: bool = False
    is_pass_interference: bool = False
    reroll_log: list[str] = []
    kick_phase: str = ""
    play_result_preview: Optional[str] = None


def _penalty_choice_model(choice) -> PenaltyChoiceModel:
    """Serialize the engine's PenaltyChoice, including its state previews."""
    return PenaltyChoiceModel(
        penalty_options=[
            PenaltyOptionModel(
                penalty_type=opt.penalty_type,
                raw_result=opt.raw_result,
                yards=opt.yards,
                description=opt.description,
                auto_first_down=opt.auto_first_down,
                is_pass_interference=getattr(opt, "is_pass_interference", False),
                result_preview=getattr(opt, "result_preview", None),
            )
            for opt in choice.penalty_options
        ],
        offended_team=choice.offended_team,
        offsetting=choice.offsetting,
        is_pass_interference=choice.is_pass_interference,
        reroll_log=choice.reroll_log or [],
        kick_phase=getattr(choice, "kick_phase", ""),
        play_result_preview=getattr(choice, "play_result_preview", None),
    )

class PlayResult(BaseModel):
    result: str
    yards: int
    description: str
    turnover: bool = False
    scoring: bool = False
    touchdown: bool = False
    new_ball_position: int
    new_down: int
    new_yards_to_go: int
    new_score_home: int
    new_score_away: int
    possession_changed: bool = False
    game_over: bool = False
    quarter_changed: bool = False
    half_changed: bool = False
    pending_penalty_decision: bool = False
    penalty_choice: Optional[PenaltyChoiceModel] = None
    play_type: Optional[str] = None
    rule_explanation: Optional[str] = None

    headline: Optional[str] = None
    commentary: Optional[str] = None
    big_play_factor: int = 0
    big_play_type: str = "normal"
    is_gain: bool = False
    is_stuffed: bool = False
    is_big_play: bool = False
    is_explosive: bool = False
    is_interception: bool = False
    is_fumble: bool = False
    is_first_down: bool = False
    is_safety: bool = False
    is_sack: bool = False
    is_breakaway: bool = False


class ExtraPointResponse(BaseModel):
    success: bool
    description: str
    new_score_home: int
    new_score_away: int
    game_state: dict[str, Any]
    is_kickoff: bool = True


class PATChoiceResponse(BaseModel):
    can_go_for_two: bool
    cpu_should_go_for_two: bool
    scoring_team_is_player: bool


class SeasonsResponse(BaseModel):
    seasons: list[str]


class TeamsResponse(BaseModel):
    teams: list[Team]


class NewGameRequest(BaseModel):
    player_team: str
    season: str
    play_as_home: bool = True
    opponent_team: Optional[str] = None
    difficulty: str = "medium"


class GameStateResponse(BaseModel):
    game_id: str
    home_team: Team
    away_team: Team
    home_score: int
    away_score: int
    quarter: int
    time_remaining: int
    possession: str
    ball_position: int
    field_position: str = ""  # Pre-calculated from engine
    down: int
    yards_to_go: int
    game_over: bool
    home_timeouts: int = 3
    away_timeouts: int = 3
    player_offense: bool = True
    difficulty: str = "medium"
    human_team_id: Optional[str] = None
    cpu_team_id: Optional[str] = None
    human_is_home: Optional[bool] = None
    is_kickoff: bool = False
    pending_pat: bool = False
    can_go_for_two: bool = False
    is_overtime: bool = False
    ot_period: int = 0
    home_stats: Optional[dict[str, int]] = None
    away_stats: Optional[dict[str, int]] = None
    season: str = "1983"  # Season year for replay saving
    # Engine-owned: the first half has ended and the second-half kickoff is still owed.
    halftime_pending: bool = False


class NewGameResponse(BaseModel):
    game_id: str
    game_state: GameStateResponse
    difficulty: str = "medium"


class PlayRequest(BaseModel):
    game_id: str
    player_play: str
    cpu_play: Optional[str] = None
    short_drop: bool = False
    coffin_corner_yards: int = 0
    no_huddle: bool = False  # Mode, not a one-play modifier


class GameIdRequest(BaseModel):
    """Simple request model for endpoints that only need game_id."""

    game_id: str


class CPUPlayResponse(BaseModel):
    cpu_play: str


class ExecutePlayResponse(BaseModel):
    player_play: str
    cpu_play: str
    dice_roll_offense: int
    dice_roll_defense: int
    dice_details: Optional[dict[str, Any]] = None  # Full dice breakdown
    result: PlayResult
    game_state: GameStateResponse


def parse_dice_from_description(description: str) -> dict[str, Any]:
    """Parse dice values from play description like 'B1+W4+W3=17 [Off: B1+W1+W4=15, Def: R2+G1=3]'"""
    import re

    dice_info = {
        "offense": {"black": 0, "white1": 0, "white2": 0, "total": 0},
        "defense": {"red": 0, "green": 0, "total": 0},
    }

    offense_match = re.search(r"\[Off:\s*B(\d)\+W(\d)\+W(\d)=(\d+)", description)
    if offense_match:
        dice_info["offense"] = {
            "black": int(offense_match.group(1)),
            "white1": int(offense_match.group(2)),
            "white2": int(offense_match.group(3)),
            "total": int(offense_match.group(4)),
        }

    defense_match = re.search(r"Def:\s*R(\d)\+G(\d)=(\d+)", description)
    if defense_match:
        dice_info["defense"] = {
            "red": int(defense_match.group(1)),
            "green": int(defense_match.group(2)),
            "total": int(defense_match.group(3)),
        }

    return dice_info


def load_team_info(season_dir: Path, team_id: str) -> Team:
    team_dir = season_dir / team_id
    team_info = {"id": team_id, "name": team_id}

    yaml_file = team_dir / "team.yaml"
    if yaml_file.exists():
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            if data:
                team_info["name"] = data.get("team_name", team_id)
                team_info["short_name"] = data.get("short_name")
                team_info["team_color"] = data.get("team_color")
                team_info["city"] = data.get("city")
                team_info["state"] = data.get("state")

    return Team(**team_info)


def _calculate_post_play_state(
    ball_position: int,
    down: int,
    yards_to_go: int,
    play_result,
) -> dict:
    """
    Calculate the post-play down/distance/position for a pending penalty decision.

    When a penalty occurs, the engine state is NOT updated. This function calculates
    what the state WOULD BE if the offended team accepts the play result (declines penalty).
    """
    yards_gained = play_result.yards if hasattr(play_result, "yards") else 0
    turnover = play_result.turnover if hasattr(play_result, "turnover") else False

    # Calculate new ball position
    new_ball_position = ball_position + yards_gained
    if new_ball_position > 100:
        new_ball_position = 100
    elif new_ball_position < 0:
        new_ball_position = 0

    # Check for first down (yards >= yards_to_go)
    if yards_gained >= yards_to_go:
        return {
            "new_ball_position": new_ball_position,
            "new_down": 1,
            "new_yards_to_go": min(10, 100 - new_ball_position),
            "turnover": turnover,
        }
    else:
        return {
            "new_ball_position": new_ball_position,
            "new_down": down + 1,
            "new_yards_to_go": yards_to_go - yards_gained,
            "turnover": turnover,
        }


def _arm_follow_up_state(game: dict[str, Any], engine, outcome) -> tuple:
    """Record pending PAT/kickoff bookkeeping for a FINALIZED engine outcome.

    A pending penalty choice has recorded no score, so it leaves the spot,
    `pending_pat`, and `is_kickoff` untouched. The engine owns scoring; this
    only places the ball for the next engine-driven step.

    Returns:
        (scoring, is_pending_pat, pre_kickoff_ball_position)
    """
    if outcome.pending_penalty_decision:
        game["pending_pat"] = False
        return False, False, None
    scoring = outcome.touchdown or outcome.field_goal_made or outcome.safety
    # Regulation tries are owed even after the clock expires; the engine recomputes
    # game-over after the try (RULE-002).
    is_pending_pat = outcome.touchdown and engine.can_attempt_conversion_after_touchdown()
    game["pending_pat"] = is_pending_pat
    pre_kickoff_ball_position = None
    if is_pending_pat:
        engine.setup_for_pat()
    elif outcome.touchdown:
        engine.setup_for_kickoff()  # Game-ending overtime TD: reset for consistency
    elif scoring and not engine.state.game_over:
        pre_kickoff_ball_position = engine.state.ball_position
        _arm_kickoff(game, engine, from_safety=outcome.safety)
    return scoring, is_pending_pat, pre_kickoff_ball_position


def _arm_kickoff(game: dict[str, Any], engine, *, from_safety: bool = False) -> None:
    """Place the ball for the next kick the engine says is owed.

    A half-ending score is followed by the scheduled second-half kickoff by the
    opening receiver, never by the scoring team's kick.
    """
    if engine.state.game_over:
        # A final try ends the game; nothing is kicked afterwards.
        game["is_kickoff"] = False
        engine.setup_for_kickoff()  # Neutral spot for the final-state display.
        return
    if engine.halftime_pending():
        engine.prepare_second_half_kickoff()
    else:
        # Scoring team keeps possession to kick off; safety free kick is from the 20.
        engine.setup_for_kickoff(from_safety=from_safety)
    game["is_kickoff"] = True

def game_state_to_response(game: dict[str, Any], is_kickoff: Optional[bool] = None) -> GameStateResponse:
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = game["engine"].state.is_home_possession
    player_offense = human_is_home == is_home_possession
    pending_pat = game.get("pending_pat", False)
    # Use stored is_kickoff if not explicitly provided
    if is_kickoff is None:
        is_kickoff = game.get("is_kickoff", False)

    # Get can_go_for_two from season rules if PAT is pending
    can_go_for_two = False
    if pending_pat and hasattr(game["engine"], "season_rules"):
        can_go_for_two = game["engine"].season_rules.two_point_conversion

    # Get team stats if available
    home_stats = None
    away_stats = None
    try:
        engine = game["engine"]
        if hasattr(engine.state, "home_stats") and engine.state.home_stats:
            home_stats = {
                "total_yards": engine.state.home_stats.total_yards,
                "rushing_yards": engine.state.home_stats.rushing_yards,
                "turnovers": engine.state.home_stats.turnovers,
                "penalties": engine.state.home_stats.penalties,
            }
        if hasattr(engine.state, "away_stats") and engine.state.away_stats:
            away_stats = {
                "total_yards": engine.state.away_stats.total_yards,
                "rushing_yards": engine.state.away_stats.rushing_yards,
                "turnovers": engine.state.away_stats.turnovers,
                "penalties": engine.state.away_stats.penalties,
            }
    except Exception:
        logging.getLogger(__name__).debug("Operation failed", exc_info=True)

    response = GameStateResponse(
        game_id=game["game_id"],
        home_team=game["home_team"],
        away_team=game["away_team"],
        home_score=game["engine"].state.home_score,
        away_score=game["engine"].state.away_score,
        quarter=game["engine"].state.quarter,
        time_remaining=int(game["engine"].state.time_remaining * 60),
        possession="home" if is_home_possession else "away",
        ball_position=game["engine"].state.ball_position,
        field_position=game["engine"].state.field_position_str(),
        down=game["engine"].state.down,
        yards_to_go=game["engine"].state.yards_to_go,
        game_over=game["engine"].state.game_over,
        home_timeouts=game["engine"].state.home_timeouts,
        away_timeouts=game["engine"].state.away_timeouts,
        player_offense=player_offense,
        human_team_id=game.get("player_team_id"),
        cpu_team_id=game.get("cpu_team_id"),
        human_is_home=human_is_home,
        is_kickoff=is_kickoff,
        pending_pat=pending_pat,
        can_go_for_two=can_go_for_two,
        is_overtime=game["engine"].state.is_overtime,
        halftime_pending=game["engine"].halftime_pending(),
        ot_period=game["engine"].state.ot_period,
        home_stats=home_stats,
        away_stats=away_stats,
        season=game.get("season", "1983"),
    )
    return response


def get_play_type_from_key(key: str) -> PlayType:
    play_map = {
        "1": PlayType.LINE_PLUNGE,
        "2": PlayType.OFF_TACKLE,
        "3": PlayType.END_RUN,
        "4": PlayType.DRAW,
        "5": PlayType.SCREEN,
        "6": PlayType.SHORT_PASS,
        "7": PlayType.MEDIUM_PASS,
        "8": PlayType.LONG_PASS,
        "9": PlayType.TE_SHORT_LONG,
        "Q": PlayType.QB_SNEAK,
        "K": PlayType.QB_KNEEL,
        "P": PlayType.PUNT,
        "F": PlayType.FIELD_GOAL,
        "S": PlayType.SPIKE_BALL,
    }
    return play_map.get(key.upper(), PlayType.LINE_PLUNGE)


def get_defense_type_from_key(key: str) -> DefenseType:
    defense_map = {
        "A": DefenseType.STANDARD,
        "B": DefenseType.SHORT_YARDAGE,
        "C": DefenseType.SPREAD,
        "D": DefenseType.SHORT_PASS,
        "E": DefenseType.LONG_PASS,
    }
    return defense_map.get(key.upper(), DefenseType.STANDARD)


def parse_play_with_modifiers(play_string: str) -> tuple[PlayType, dict]:
    """
    Parse play string with modifiers (e.g., '7S' -> PlayType.MEDIUM_PASS with spike modifier).

    Modifiers:
        + : out-of-bounds designation
        - : in-bounds designation
        T : timeout after play
        S : spike after play

    Returns:
        Tuple of (PlayType, dict with modifier flags)
    """
    # Extract base play (first character)
    if not play_string:
        raise ValueError("Play string cannot be empty")

    base_play = play_string[0].upper()
    modifiers = play_string[1:].upper()

    # Parse modifiers (only from suffix, not from base play)
    out_of_bounds = "+" in modifiers
    in_bounds = "-" in modifiers
    call_timeout = "T" in modifiers
    call_spike = "S" in modifiers

    # Base play is the first character (could be 'S' for spike ball play)
    play_char = base_play

    play_type = get_play_type_from_key(play_char)

    return play_type, {
        "call_spike": call_spike,
        "call_timeout": call_timeout,
        "out_of_bounds": out_of_bounds,
        "in_bounds": in_bounds,
    }


def _find_season_dir(season: str) -> Optional[Path]:
    """
    Find the directory for a season across all season paths.

    User seasons take precedence over built-in seasons.

    Args:
        season: Season year (e.g., "2026")

    Returns:
        Path to season directory, or None if not found
    """
    for seasons_path in get_all_season_paths():
        season_dir = seasons_path / season
        if season_dir.exists() and season_dir.is_dir():
            return season_dir
    return None


@router.get("/api/seasons", response_model=SeasonsResponse)
async def get_seasons():
    # Collect seasons from all paths (user seasons + built-in)
    # Use a set to avoid duplicates, user paths come first so they take precedence
    seasons_set = set()

    for seasons_path in get_all_season_paths():
        if seasons_path.exists():
            for d in seasons_path.iterdir():
                # Only include directories with numeric names (valid season years)
                if d.is_dir() and d.name.isdigit():
                    seasons_set.add(d.name)

    seasons = sorted(seasons_set, reverse=True)
    return {"seasons": seasons}


@router.get("/api/teams", response_model=TeamsResponse)
async def get_teams(season: str):
    season_dir = _find_season_dir(season)
    if season_dir is None:
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")

    teams = []
    for team_dir in sorted(season_dir.iterdir()):
        if team_dir.is_dir():
            teams.append(load_team_info(season_dir, team_dir.name))

    return {"teams": teams}


@router.get("/api/season-rules")
async def get_season_rules(season: str):
    """
    Get season rules for a specific season.

    Args:
        season: Season year (e.g., "1972", "2026")
    """
    season_dir = _find_season_dir(season)
    if season_dir is None:
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")

    try:
        rules = load_season_rules(season_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return rules.to_dict()


def _extract_team_name(team_id: str, season: str) -> str:
    """Extract team name from 'season/team' format or return as-is."""
    if "/" in team_id:
        parts = team_id.split("/")
        if len(parts) == 2 and parts[0] == season:
            return parts[1]
    return team_id


@router.post("/api/game/new", response_model=NewGameResponse)
async def new_game(request: NewGameRequest):
    # Extract team names from 'season/team' format if present
    player_team = _extract_team_name(request.player_team, request.season)
    opponent_team = (
        _extract_team_name(request.opponent_team, request.season) if request.opponent_team else None
    )

    season_dir = _find_season_dir(request.season)
    if season_dir is None:
        raise HTTPException(status_code=404, detail=f"Season '{request.season}' not found")

    available_teams = [d.name for d in season_dir.iterdir() if d.is_dir()]
    if player_team not in available_teams:
        raise HTTPException(
            status_code=404, detail=f"Team '{player_team}' not found in season '{request.season}'"
        )

    if opponent_team:
        if opponent_team not in available_teams:
            raise HTTPException(
                status_code=404, detail=f"Opponent team '{opponent_team}' not found"
            )
        if opponent_team == player_team:
            raise HTTPException(
                status_code=400, detail="Player team and opponent team cannot be the same"
            )
        player_team_id = player_team
        cpu_team_id = opponent_team
        player_is_home = request.play_as_home
        human_plays_offense = random.choice([True, False])
        if player_is_home:
            home_id = player_team_id
            away_id = cpu_team_id
        else:
            home_id = cpu_team_id
            away_id = player_team_id
    else:
        cpu_teams = [t for t in available_teams if t != player_team]
        cpu_team = random.choice(cpu_teams) if cpu_teams else player_team
        player_is_home = request.play_as_home
        human_plays_offense = random.choice([True, False])
        if player_is_home:
            player_team_id = player_team
            cpu_team_id = cpu_team
            home_id = player_team_id
            away_id = cpu_team_id
        else:
            player_team_id = cpu_team
            cpu_team_id = player_team
            home_id = cpu_team_id
            away_id = player_team_id

    home_team = load_team_info(season_dir, home_id)
    away_team = load_team_info(season_dir, away_id)

    home_chart = load_team_chart(str(season_dir / home_team.id))
    away_chart = load_team_chart(str(season_dir / away_team.id))

    game_id = f"game_{uuid.uuid4().hex[:8]}"

    engine = PaydirtGameEngine(home_chart, away_chart)

    difficulty = request.difficulty.lower() if request.difficulty else "medium"

    game = {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "human_plays_offense": human_plays_offense,
        "player_team_id": player_team_id,
        "cpu_team_id": cpu_team_id,
        "engine": engine,
        "ai": create_computer_ai(difficulty, engine, cpu_is_home=home_team.id == cpu_team_id),
        "created_at": datetime.now(),
        "season": request.season,
        "difficulty": difficulty,
    }


    games[game_id] = game

    return NewGameResponse(
        game_id=game_id,
        game_state=game_state_to_response(game),
        difficulty=difficulty,
    )


@router.get("/api/game/state/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    return game_state_to_response(games[game_id])


class CoinTossRequest(BaseModel):
    game_id: str
    player_won: bool
    player_kicks: bool
    human_plays_offense: Optional[bool] = True


@router.post("/api/game/coin-toss")
async def process_coin_toss(request: CoinTossRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    # Update human's role based on coin toss choice
    if request.human_plays_offense is not None:
        game["human_plays_offense"] = request.human_plays_offense

    # Set possession based on coin toss result
    # player_kicks = True means player kicks (they have possession to kick)
    # player_kicks = False means player receives (opponent has possession to kick)
    # Extract team ID from home_chart.team_dir (e.g., "seasons/2026/TeamName" -> "TeamName")
    home_team_id = engine.state.home_chart.team_dir.split("/")[-1]
    human_is_home = home_team_id == game["player_team_id"]

    if request.player_kicks:
        # Player kicks - player has possession to kick
        engine.state.is_home_possession = human_is_home
    else:
        # Player receives - opponent has possession to kick
        engine.state.is_home_possession = not human_is_home

    # Calculate player_offense for frontend
    # If human is at home AND home has possession, OR human is away AND away has possession
    player_offense = human_is_home == engine.state.is_home_possession

    return {
        "status": "ok",
        "possession": "home" if engine.state.is_home_possession else "away",
        "player_offense": player_offense,
        "human_is_home": human_is_home,
        "human_team_id": game["player_team_id"],
        "cpu_team_id": game["cpu_team_id"],
    }


@router.post("/api/game/cpu-play", response_model=CPUPlayResponse)
async def get_cpu_play(request: GameIdRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]

    if game["engine"].state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    # Calculate player_offense based on actual possession, not stale flag
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = game["engine"].state.is_home_possession
    player_offense = human_is_home == is_home_possession
    cpu_is_offense = not player_offense

    if cpu_is_offense:
        cpu_play_type = game["ai"].select_offense(game["engine"])
        cpu_play = {
            PlayType.LINE_PLUNGE: "1",
            PlayType.OFF_TACKLE: "2",
            PlayType.END_RUN: "3",
            PlayType.DRAW: "4",
            PlayType.SCREEN: "5",
            PlayType.SHORT_PASS: "6",
            PlayType.MEDIUM_PASS: "7",
            PlayType.LONG_PASS: "8",
            PlayType.TE_SHORT_LONG: "9",
            PlayType.QB_SNEAK: "Q",
            PlayType.QB_KNEEL: "K",
            PlayType.PUNT: "P",
            PlayType.FIELD_GOAL: "F",
            PlayType.SPIKE_BALL: "S",
        }.get(cpu_play_type, "1")
    else:
        cpu_defense = game["ai"].select_defense(game["engine"])
        cpu_play = {
            DefenseType.STANDARD: "A",
            DefenseType.SHORT_YARDAGE: "B",
            DefenseType.SPREAD: "C",
            DefenseType.SHORT_PASS: "D",
            DefenseType.LONG_PASS: "E",
        }.get(cpu_defense, "A")

    return CPUPlayResponse(cpu_play=cpu_play)


class CPUFourthDownResponse(BaseModel):
    decision: str
    play: Optional[str] = None


@router.get("/api/game/cpu-4th-down-decision/{game_id}", response_model=CPUFourthDownResponse)
async def get_cpu_4th_down_decision(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    state = game["engine"].state

    # Determine CPU offense status based on current possession
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = state.is_home_possession
    player_is_on_offense = human_is_home == is_home_possession
    cpu_is_offense = not player_is_on_offense

    if not (cpu_is_offense and state.down == 4):
        return CPUFourthDownResponse(decision="none")

    play_map = {
        PlayType.LINE_PLUNGE: "1",
        PlayType.OFF_TACKLE: "2",
        PlayType.END_RUN: "3",
        PlayType.DRAW: "4",
        PlayType.SCREEN: "5",
        PlayType.SHORT_PASS: "6",
        PlayType.MEDIUM_PASS: "7",
        PlayType.LONG_PASS: "8",
        PlayType.TE_SHORT_LONG: "9",
        PlayType.QB_SNEAK: "Q",
        PlayType.QB_KNEEL: "K",
        PlayType.PUNT: "P",
        PlayType.FIELD_GOAL: "F",
        PlayType.SPIKE_BALL: "S",
    }

    play, _, _, _, _, _ = game["ai"].select_offense_with_clock_management(game["engine"])
    play_key = play_map.get(play, "1")

    if play == PlayType.PUNT:
        return CPUFourthDownResponse(decision="punt", play="P")
    elif play == PlayType.FIELD_GOAL:
        return CPUFourthDownResponse(decision="field_goal", play="F")
    else:
        return CPUFourthDownResponse(decision="go_for_it", play=play_key)


@router.post("/api/game/execute", response_model=ExecutePlayResponse)
async def execute_play(request: PlayRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    if engine.state.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    # Check if kickoff is needed - use the is_kickoff flag, not engine state
    # (ball at 35 with 1st-and-10 can happen during normal play after returns/turnovers)
    if game.get("is_kickoff", False):
        raise HTTPException(
            status_code=400, detail="Game is in kickoff position - use /api/game/kickoff endpoint"
        )

    player_play = request.player_play.upper()
    # Determine if player's team is on offense based on CURRENT possession,
    # not the static human_plays_offense flag (which is stale after turnovers/kickoffs)
    human_is_home = game["home_team"].id == game.get("player_team_id")
    is_home_possession = engine.state.is_home_possession
    player_offense = human_is_home == is_home_possession

    cpu_play = request.cpu_play.upper() if request.cpu_play else None

    # Initialize modifier flags
    call_spike = False
    call_timeout = False
    out_of_bounds = False
    in_bounds = False
    no_huddle = request.no_huddle

    if player_offense:
        # Parse player_play for modifiers (e.g., '7S' -> medium pass with spike)
        offense_play, modifiers = parse_play_with_modifiers(player_play)
        call_spike = modifiers["call_spike"]
        call_timeout = modifiers["call_timeout"]
        out_of_bounds = modifiers["out_of_bounds"]
        in_bounds = modifiers["in_bounds"]

        if cpu_play:
            defense_play = get_defense_type_from_key(cpu_play)
        else:
            defense_play = game["ai"].select_defense(engine)
    else:
        # CPU on offense - check for 4th down decision if no cpu_play provided
        if engine.state.down == 4 and not cpu_play:
            play, _, _, _, _, _ = game["ai"].select_offense_with_clock_management(engine)
            play_map = {
                PlayType.LINE_PLUNGE: "1",
                PlayType.OFF_TACKLE: "2",
                PlayType.END_RUN: "3",
                PlayType.DRAW: "4",
                PlayType.SCREEN: "5",
                PlayType.SHORT_PASS: "6",
                PlayType.MEDIUM_PASS: "7",
                PlayType.LONG_PASS: "8",
                PlayType.TE_SHORT_LONG: "9",
                PlayType.QB_SNEAK: "Q",
                PlayType.QB_KNEEL: "K",
                PlayType.PUNT: "P",
                PlayType.FIELD_GOAL: "F",
                PlayType.SPIKE_BALL: "S",
            }
            if play == PlayType.PUNT:
                cpu_play = "P"
            elif play == PlayType.FIELD_GOAL:
                cpu_play = "F"
            else:
                cpu_play = play_map.get(play, "1")

        if cpu_play:
            offense_play = get_play_type_from_key(cpu_play)
        else:
            offense_play = game["ai"].select_offense(engine)
        defense_play = get_defense_type_from_key(player_play)

    home_score_before = engine.state.home_score
    away_score_before = engine.state.away_score
    quarter_before = engine.state.quarter
    down_before = engine.state.down
    distance_before = engine.state.yards_to_go

    # Map play types to display keys for logging
    offense_key_map = {
        PlayType.LINE_PLUNGE: "1",
        PlayType.OFF_TACKLE: "2",
        PlayType.END_RUN: "3",
        PlayType.DRAW: "4",
        PlayType.SCREEN: "5",
        PlayType.SHORT_PASS: "6",
        PlayType.MEDIUM_PASS: "7",
        PlayType.LONG_PASS: "8",
        PlayType.TE_SHORT_LONG: "9",
        PlayType.QB_SNEAK: "Q",
        PlayType.QB_KNEEL: "K",
        PlayType.PUNT: "P",
        PlayType.FIELD_GOAL: "F",
        PlayType.SPIKE_BALL: "S",
        PlayType.KICKOFF: "KO",
    }
    defense_key_map = {
        DefenseType.STANDARD: "A",
        DefenseType.SHORT_YARDAGE: "B",
        DefenseType.SPREAD: "C",
        DefenseType.SHORT_PASS: "D",
        DefenseType.LONG_PASS: "E",
        DefenseType.BLITZ: "F",
    }

    off_key = offense_key_map.get(offense_play, "?")
    def_key = defense_key_map.get(defense_play, "?")

    # Get team abbreviations
    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"

    result = engine.run_play_with_penalty_procedure(
        offense_play,
        defense_play,
        out_of_bounds_designation=out_of_bounds,
        in_bounds_designation=in_bounds,
        no_huddle=no_huddle,
        call_spike=call_spike,
        call_timeout=call_timeout,
        punt_short_drop=request.short_drop,
        punt_coffin_corner_yards=request.coffin_corner_yards,
    )

    if player_offense and game["ai"].opponent_model is not None:
        game["ai"].opponent_model.record_opponent_play(
            down=down_before,
            distance=distance_before,
            play_type=offense_play.value,
            yards_gained=result.yards_gained,
            is_pass=is_passing_play(offense_play),
        )

    # Log play in CLI compact format with teams and field position
    field_pos = engine.state.field_position_str()
    off_team = home_abbrev if engine.state.is_home_possession else away_abbrev
    def_team = away_abbrev if engine.state.is_home_possession else home_abbrev
    pending_str = " [PENDING PENALTY]" if result.pending_penalty_decision else ""
    scoring = result.touchdown or result.field_goal_made or result.safety
    score_str = (
        f" | HOME {engine.state.home_score} - AWAY {engine.state.away_score}" if scoring else ""
    )

    # Include chart values (raw_result = offense chart, defense_modifier = defense chart)
    off_chart_val = getattr(result, "raw_result", "")
    def_chart_val = getattr(result, "defense_modifier", "")
    chart_info = (
        f" [Off: {off_chart_val}, Def: {def_chart_val}]" if off_chart_val or def_chart_val else ""
    )

    print(
        f"[{off_team} vs {def_team}] OFF: {off_key} DEF: {def_key} @ {field_pos} | {result.description}{chart_info}{pending_str}{score_str}"
    )

    # Save result for penalty decision if needed
    if result.pending_penalty_decision:
        engine._last_play_outcome = result

    # Scoring setup must wait for a finalized outcome: a pending penalty choice
    # has recorded no score and must not move the ball before the decision.
    scoring, is_pending_pat, pre_kickoff_ball_position = _arm_follow_up_state(game, engine, result)

    # Determine if human needs to make penalty decision
    # offended_team indicates who is "offended" by the penalty (who benefited)
    # OFFENSE committed penalty (OFF 5, OFF 15) → DEFENSE gets choice → prompt only if human is on DEFENSE
    # DEFENSE committed penalty (DEF 5, DEF 15) → OFFENSE gets choice → prompt only if human is on OFFENSE
    # HUMAN gets prompted if their team is NOT the one that committed the penalty
    # Use player_offense (current possession) instead of stale human_plays_offense flag
    human_is_on_offense = player_offense

    should_prompt_human = False
    pending_penalty = False
    if result.penalty_choice and not result.penalty_choice.offsetting:
        offended_team = result.penalty_choice.offended_team  # "offense" or "defense"

        # The offended team gets to choose (the team that was wronged by the penalty)
        # If offended_team is "offense", offense committed the penalty? NO!
        # offended_team is the team that GETS TO CHOOSE (was wronged)
        # So if offended_team == "offense", the offense was wronged (defense committed penalty)

        # Human should be prompted if human is on the offended team (gets to choose)
        if offended_team == "offense":
            # Defense committed penalty → offense gets choice
            should_prompt_human = human_is_on_offense
        else:
            # Offense committed penalty → defense gets choice
            should_prompt_human = not human_is_on_offense

        pending_penalty = True

    penalty_choice_model = None
    if should_prompt_human:
        # Human decides - save outcome and return pending decision
        penalty_choice_model = _penalty_choice_model(result.penalty_choice)
    elif pending_penalty:
        # CPU decides - apply penalty decision automatically
        human_is_home = game.get("human_is_home", False)
        accept_play, penalty_index = cpu_should_accept_penalty(
            result, is_human_offense=human_is_on_offense, human_is_home=human_is_home
        )
        accept_penalty = not accept_play

        if result.play_type == PlayType.PUNT:
            result = engine.apply_punt_penalty_decision(result, accept_penalty)
        elif result.play_type == PlayType.FIELD_GOAL:
            result = engine.apply_fg_penalty_decision(
                result, accept_play=accept_play, penalty_index=penalty_index
            )
        elif result.play_type == PlayType.KICKOFF:
            result = engine.apply_kickoff_penalty_decision(result, accept_penalty)
        else:
            result = engine.apply_penalty_decision(
                result, accept_play=accept_play, penalty_index=penalty_index
            )

        # Log the CPU decision
        decision_str = "ACCEPT PLAY" if accept_play else "ACCEPT PENALTY"
        home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
        away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"
        field_pos = engine.state.field_position_str()
        off_team = home_abbrev if engine.state.is_home_possession else away_abbrev
        def_team = away_abbrev if engine.state.is_home_possession else home_abbrev
        print(
            f"[{off_team} vs {def_team}] CPU PENALTY DECISION: {decision_str} @ {field_pos} | {result.description}"
        )

        scoring, is_pending_pat, pre_kickoff_ball_position = _arm_follow_up_state(game, engine, result)

        # CPU decided, so no pending decision for human
        pending_penalty = False

    response_game_state = game_state_to_response(game, is_kickoff=scoring and not is_pending_pat)

    # Parse dice from description for frontend display
    dice_details = parse_dice_from_description(result.description)

    # If description didn't have dice pattern, decompose from dice_roll
    # This handles cases like punts where description doesn't include [Off: B1+W4+W3=17, Def: R2+G1=3]
    if (
        dice_details["offense"]["total"] == 0
        and hasattr(result.result, "dice_roll")
        and result.result.dice_roll > 0
    ):
        total = result.result.dice_roll
        black = total // 10  # Tens digit (1, 2, or 3)
        ones = total % 10  # Ones digit (0-9)
        white1 = min(5, ones)
        white2 = ones - white1
        dice_details["offense"] = {
            "black": black,
            "white1": white1,
            "white2": white2,
            "total": total,
        }
        # Defense uses same dice roll
        dice_details["defense"] = {"red": black, "green": white1, "total": total}

    return ExecutePlayResponse(
        player_play=player_play,
        cpu_play="CPU",
        dice_roll_offense=dice_details["offense"]["total"],
        dice_roll_defense=dice_details["defense"]["total"],
        dice_details=dice_details,
        result=PlayResult(
            result=result.result.value if hasattr(result.result, "value") else str(result.result),
            yards=result.yards_gained,
            description=result.description,
            rule_explanation=result.result.rule_explanation,
            turnover=result.turnover,
            scoring=scoring,
            touchdown=result.touchdown,
            new_ball_position=pre_kickoff_ball_position
            if pre_kickoff_ball_position is not None
            else engine.state.ball_position,
            new_down=engine.state.down,
            new_yards_to_go=engine.state.yards_to_go,
            new_score_home=engine.state.home_score,
            new_score_away=engine.state.away_score,
            possession_changed=result.turnover
            or engine.state.home_score != home_score_before
            or engine.state.away_score != away_score_before,
            game_over=engine.state.game_over,
            quarter_changed=engine.state.quarter != quarter_before,
            half_changed=quarter_before == 2 and engine.state.quarter == 3,
            pending_penalty_decision=pending_penalty and result.pending_penalty_decision,
            penalty_choice=penalty_choice_model,
            play_type=result.play_type.value
            if hasattr(result.play_type, "value")
            else str(result.play_type),
        ),
        game_state=response_game_state,
    )


@router.delete("/api/game/{game_id}")
async def delete_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    del games[game_id]
    return {"status": "deleted", "game_id": game_id}


@router.post("/api/game/timeout")
async def call_timeout(request: GameIdRequest):
    """
    Call a timeout for the current team.

    The timeout reduces the play time to ~10 seconds instead of normal play time,
    and is charged to the team calling it.
    """
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]
    human_is_home = game["home_team"].id == game.get("player_team_id")

    # Determine which team is calling the timeout
    is_home_timeout = human_is_home

    # Check if timeout is available
    if is_home_timeout:
        if engine.state.home_timeouts <= 0:
            raise HTTPException(status_code=400, detail="No timeouts remaining")
    else:
        if engine.state.away_timeouts <= 0:
            raise HTTPException(status_code=400, detail="No timeouts remaining")

    # Use the timeout
    success = engine.state.use_timeout(is_home_timeout)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to use timeout")

    # Apply clock adjustment (10 seconds for timeout)
    # The timeout stops the clock, so only ~10 seconds run off
    timeout_seconds = 0.167  # 10 seconds in minutes
    engine.state.time_remaining = max(0, engine.state.time_remaining - timeout_seconds)

    # Log the timeout
    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"
    team_abbrev = home_abbrev if is_home_timeout else away_abbrev
    print(
        f"[{team_abbrev}] TIMEOUT called | Remaining: {engine.state.home_timeouts if is_home_timeout else engine.state.away_timeouts}"
    )

    return {
        "success": True,
        "home_timeouts": engine.state.home_timeouts,
        "away_timeouts": engine.state.away_timeouts,
        "time_remaining": int(engine.state.time_remaining * 60),
        "game_state": game_state_to_response(game).dict(),
    }


@router.post("/api/game/overtime/start")
async def start_overtime(request: GameIdRequest):
    """
    Start overtime period.

    This should be called when the game is tied at the end of regulation.
    The engine will handle the coin toss and set up for kickoff.
    """
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    # Check if game is actually tied
    if engine.state.home_score != engine.state.away_score:
        raise HTTPException(status_code=400, detail="Game is not tied")

    # Check if game is already in overtime
    if engine.state.is_overtime:
        raise HTTPException(status_code=400, detail="Game is already in overtime")

    # Start overtime - coin toss winner receives
    description = engine.start_overtime()

    # Log the overtime start
    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"
    print(f"[{home_abbrev} vs {away_abbrev}] OVERTIME START | {description}")

    return {
        "success": True,
        "description": description,
        "is_overtime": True,
        "ot_period": 1,
        "is_kickoff": True,
        "game_state": game_state_to_response(game, is_kickoff=True).dict(),
    }


@router.get("/api/game/pat-choice/{game_id}", response_model=PATChoiceResponse)
async def get_pat_choice(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]
    engine = game["engine"]

    human_is_home = game["home_team"].id == game["player_team_id"]
    is_home_possession = engine.state.is_home_possession
    scoring_team_is_player = (human_is_home and is_home_possession) or (
        not human_is_home and not is_home_possession
    )

    # Use the CPU decision logic to determine if CPU would go for 2
    # This helps the UI show what the CPU would do
    cpu_should_go_for_two = False
    try:
        from paydirt.computer_ai import cpu_should_go_for_two as cpu_2pt_func

        cpu_should_go_for_two = cpu_2pt_func(engine, try_pending=bool(game.get("pending_pat")))
    except Exception:
        logging.getLogger(__name__).debug("Operation failed", exc_info=True)

    return PATChoiceResponse(
        can_go_for_two=engine.season_rules.two_point_conversion,
        cpu_should_go_for_two=cpu_should_go_for_two,
        scoring_team_is_player=scoring_team_is_player,
    )


@router.post("/api/game/extra-point", response_model=ExtraPointResponse)
async def attempt_extra_point(request: GameIdRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"

    success, description = engine.attempt_extra_point()

    # Log PAT with result
    scoring_abbrev = home_abbrev if engine.state.is_home_possession else away_abbrev
    result_str = "GOOD" if success else "NO GOOD"
    print(
        f"[{scoring_abbrev}] EXTRA POINT: {result_str} | HOME {engine.state.home_score} - AWAY {engine.state.away_score}"
    )

    # After PAT, set up for kickoff using engine method
    # Scoring team keeps possession to kick off — DON'T switch possession here.
    # The engine's kickoff() method handles the receiver getting the ball.
    game["pending_pat"] = False
    _arm_kickoff(game, engine)

    return ExtraPointResponse(
        success=success,
        description=description,
        new_score_home=engine.state.home_score,
        new_score_away=engine.state.away_score,
        game_state=game_state_to_response(game, is_kickoff=game["is_kickoff"]).dict(),
        is_kickoff=game["is_kickoff"],
    )


class KickoffRequest(BaseModel):
    game_id: str
    kickoff_spot: int = 35


@router.post("/api/game/kickoff")
async def perform_kickoff(request: KickoffRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    # Clear the kickoff flag - we're performing the kickoff now
    game["is_kickoff"] = False

    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"

    # The engine decides who kicks: the opening receiver after halftime, otherwise
    # the team holding the ball (the scoring team).
    halftime = engine.halftime_pending()
    kicking_home = engine.second_half_kicking_home() if halftime else engine.state.is_home_possession
    kicking_abbrev = home_abbrev if kicking_home else away_abbrev
    result = engine.kickoff(kicking_home=kicking_home, kickoff_spot=request.kickoff_spot)

    # A penalty on the kick or return is the offended team's choice. Kickoff
    # decisions use the receiving team as "offense" (engine convention).
    penalty_choice_model = None
    if result.pending_penalty_decision and result.penalty_choice:
        human_is_home = game["home_team"].id == game.get("player_team_id")
        human_receives = human_is_home != kicking_home
        human_decides = (result.penalty_choice.offended_team == "offense") == human_receives
        if human_decides:
            engine._last_play_outcome = result
            penalty_choice_model = _penalty_choice_model(result.penalty_choice)
        else:
            accept_play, _ = cpu_should_accept_penalty(
                result, is_human_offense=human_receives, human_is_home=human_is_home
            )
            result = engine.apply_kickoff_penalty_decision(result, accept_penalty=not accept_play)
            print(
                f"[{kicking_abbrev} KO] CPU PENALTY DECISION: "
                f"{'ACCEPT PLAY' if accept_play else 'ACCEPT PENALTY'} | {result.description}"
            )

    # Log kickoff with dice and result details
    receiving_abbrev = home_abbrev if engine.state.is_home_possession else away_abbrev
    field_pos = engine.state.field_position_str()
    print(f"[{kicking_abbrev} KO → {receiving_abbrev}] {result.description} @ {field_pos}")

    scoring = result.touchdown or result.safety
    possession_changed = not result.pending_penalty_decision

    # Get dice roll from result - decompose into display dice
    # Kickoff roll is 10-39, decompose into: black (tens) + white1 + white2 (ones)
    ko_value = result.result.dice_roll if hasattr(result.result, "dice_roll") else 0
    if ko_value > 0:
        black_value = ko_value // 10  # Tens digit (1, 2, or 3)
        ones_digit = ko_value % 10  # Ones digit (0-9)
        # Split ones digit between two white dice (each 0-5)
        white1_value = min(5, ones_digit)
        white2_value = ones_digit - white1_value
    else:
        # Fallback: parse from description
        ko_match = re.search(r"KO:(\d+)", result.description)
        if ko_match:
            ko_value = int(ko_match.group(1))
            black_value = ko_value // 10
            ones_digit = ko_value % 10
            white1_value = min(5, ones_digit)
            white2_value = ones_digit - white1_value
        else:
            ko_value, black_value, white1_value, white2_value = 0, 0, 0, 0

    kickoff_dice = {
        "black": black_value,
        "white1": white1_value,
        "white2": white2_value,
        "total": ko_value,
    }
    # The return is the receiving team's own roll (0 when the kick was not returned).
    rt_value = getattr(result.result, "kickoff_return_dice", 0) or 0
    return_dice = {"red": rt_value // 10, "green": min(5, rt_value % 10), "total": rt_value}

    dice_details = {"offense": kickoff_dice, "defense": return_dice}

    return ExecutePlayResponse(
        player_play="KICKOFF",
        cpu_play="KICKOFF",
        dice_roll_offense=kickoff_dice["total"],
        dice_roll_defense=return_dice["total"],
        dice_details=dice_details,
        result=PlayResult(
            result=result.result.result_type.value
            if hasattr(result.result, "result_type")
            else str(result.result),
            yards=result.yards_gained,
            description=result.description,
            turnover=result.turnover,
            scoring=scoring,
            touchdown=result.touchdown,
            new_ball_position=engine.state.ball_position,
            new_down=engine.state.down,
            new_yards_to_go=engine.state.yards_to_go,
            new_score_home=engine.state.home_score,
            new_score_away=engine.state.away_score,
            possession_changed=possession_changed,
            game_over=engine.state.game_over,
            quarter_changed=False,
            half_changed=halftime,
            pending_penalty_decision=result.pending_penalty_decision,
            penalty_choice=penalty_choice_model,
            play_type="kickoff",
        ),
        game_state=game_state_to_response(game),
    )


class TwoPointRequest(BaseModel):
    game_id: str
    offense_play: str = "1"
    defense_play: str = "A"


@router.post("/api/game/two-point", response_model=ExecutePlayResponse)
async def attempt_two_point(request: TwoPointRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"

    offense_play = get_play_type_from_key(request.offense_play)
    defense_play = get_defense_type_from_key(request.defense_play)

    _success, _defense_points, description = engine.attempt_two_point(offense_play, defense_play)

    # Log two-point conversion
    scoring_abbrev = home_abbrev if engine.state.is_home_possession else away_abbrev
    print(
        f"[{scoring_abbrev}] TWO-POINT: {description} | HOME {engine.state.home_score} - AWAY {engine.state.away_score}"
    )

    # After two-point attempt, set up for kickoff using engine method
    # Scoring team keeps possession to kick off — DON'T switch possession here.
    game["pending_pat"] = False
    _arm_kickoff(game, engine)

    return ExecutePlayResponse(
        player_play=request.offense_play,
        cpu_play=request.defense_play,
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=PlayResult(
            result="two_point_conversion",
            yards=0,
            description=description,
            scoring=True,
            touchdown=False,
            new_ball_position=engine.state.ball_position,
            new_down=engine.state.down,
            new_yards_to_go=engine.state.yards_to_go,
            new_score_home=engine.state.home_score,
            new_score_away=engine.state.away_score,
            possession_changed=True,
            game_over=engine.state.game_over,
        ),
        game_state=game_state_to_response(game, is_kickoff=True),
    )


class PenaltyDecisionRequest(BaseModel):
    game_id: str
    penalty_index: int
    accept_penalty: bool


@router.post("/api/game/penalty-decision", response_model=ExecutePlayResponse)
async def apply_penalty_decision(request: PenaltyDecisionRequest):
    if request.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[request.game_id]
    engine = game["engine"]

    outcome = getattr(engine, "_last_play_outcome", None)
    if not outcome or not outcome.pending_penalty_decision:
        raise HTTPException(status_code=400, detail="No pending penalty decision")

    # Decide from the live possession, never the stale human_plays_offense flag.
    # While a kickoff decision is pending the kicker holds the ball and the
    # receiver is "offense" (engine convention).
    human_is_home = game["home_team"].id == game.get("player_team_id")
    if outcome.play_type == PlayType.KICKOFF:
        player_offense = human_is_home != engine.state.is_home_possession
    else:
        player_offense = human_is_home == engine.state.is_home_possession
    penalty_choice = outcome.penalty_choice
    offended_is_offense = penalty_choice.offended_team == "offense"

    human_decides = (offended_is_offense and player_offense) or (
        not offended_is_offense and not player_offense
    )

    if human_decides:
        accept_penalty = request.accept_penalty
        accept_play = not accept_penalty
        penalty_index = request.penalty_index
    else:
        accept_play, penalty_index = cpu_should_accept_penalty(
            outcome, is_human_offense=player_offense, human_is_home=human_is_home
        )
        accept_penalty = not accept_play

    if outcome.play_type == PlayType.PUNT:
        new_outcome = engine.apply_punt_penalty_decision(outcome, accept_penalty, penalty_index)
    elif outcome.play_type == PlayType.FIELD_GOAL:
        new_outcome = engine.apply_fg_penalty_decision(
            outcome, accept_play=accept_play, penalty_index=penalty_index
        )
    elif outcome.play_type == PlayType.KICKOFF:
        new_outcome = engine.apply_kickoff_penalty_decision(outcome, accept_penalty)
    else:
        new_outcome = engine.apply_penalty_decision(
            outcome, accept_play=accept_play, penalty_index=penalty_index
        )

    # Debug logging for penalty decision
    decision_str = "ACCEPT PENALTY" if not accept_play else "ACCEPT PLAY"
    home_abbrev = game["home_team"].short_name or game["home_team"].id or "HOME"
    away_abbrev = game["away_team"].short_name or game["away_team"].id or "AWAY"
    field_pos = engine.state.field_position_str()
    off_team = home_abbrev if engine.state.is_home_possession else away_abbrev
    def_team = away_abbrev if engine.state.is_home_possession else home_abbrev
    print(
        f"[{off_team} vs {def_team}] PENALTY DECISION: {decision_str} @ {field_pos} | yards_gained={new_outcome.yards_gained} | {new_outcome.description}"
    )

    # The engine alone decides touchdowns; never infer one from the spot here.
    scoring, is_pending_pat, pre_kickoff_ball_position = _arm_follow_up_state(game, engine, new_outcome)

    penalty_choice_model = None
    if new_outcome.penalty_choice:
        penalty_choice_model = _penalty_choice_model(new_outcome.penalty_choice)

    play_result = PlayResult(
        result=new_outcome.result.result_type.value
        if hasattr(new_outcome.result, "result_type")
        else str(new_outcome.result),
        yards=new_outcome.yards_gained,
        description=new_outcome.description,
        turnover=new_outcome.turnover,
        scoring=scoring,
        touchdown=new_outcome.touchdown,
        new_ball_position=pre_kickoff_ball_position
        if pre_kickoff_ball_position is not None
        else engine.state.ball_position,
        new_down=engine.state.down,
        new_yards_to_go=engine.state.yards_to_go,
        new_score_home=engine.state.home_score,
        new_score_away=engine.state.away_score,
        possession_changed=new_outcome.turnover or scoring,
        game_over=engine.state.game_over,
        quarter_changed=False,
        half_changed=engine.halftime_pending(),
        pending_penalty_decision=False,
        penalty_choice=penalty_choice_model,
        play_type=new_outcome.play_type.value
        if hasattr(new_outcome.play_type, "value")
        else str(new_outcome.play_type),
    )

    return ExecutePlayResponse(
        player_play="PENALTY",
        cpu_play="CPU",
        dice_roll_offense=0,
        dice_roll_defense=0,
        result=play_result,
        game_state=game_state_to_response(game, is_kickoff=scoring and not is_pending_pat),
    )


class SaveReplayResponse(BaseModel):
    replay_id: str
    game_state: GameStateResponse
    play_history: list[dict[str, Any]]
    created_at: str
    season: str


class LoadReplayRequest(BaseModel):
    replay_data: dict[str, Any]


@router.post("/api/game/save-replay/{game_id}", response_model=SaveReplayResponse)
async def save_replay(game_id: str):
    """Save current game state and play history for replay."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]

    replay_id = f"replay_{uuid.uuid4().hex[:8]}"

    return SaveReplayResponse(
        replay_id=replay_id,
        game_state=game_state_to_response(game),
        play_history=game.get("play_history", []),
        created_at=datetime.now().isoformat(),
        season=game.get("season", "1983"),
    )


@router.post("/api/game/load-replay")
async def load_replay(request: LoadReplayRequest):
    """Load a saved replay and create a new game from it."""
    replay_data = request.replay_data

    if "game_state" not in replay_data:
        raise HTTPException(status_code=400, detail="Invalid replay data: missing game_state")

    game_state = replay_data["game_state"]

    home_team_id = game_state.get("home_team", {}).get("id")
    away_team_id = game_state.get("away_team", {}).get("id")

    # Also handle case where home_team/away_team is just a string ID
    if not home_team_id:
        home_team_id = (
            game_state.get("home_team") if isinstance(game_state.get("home_team"), str) else None
        )
    if not away_team_id:
        away_team_id = (
            game_state.get("away_team") if isinstance(game_state.get("away_team"), str) else None
        )

    if not home_team_id or not away_team_id:
        raise HTTPException(status_code=400, detail="Invalid replay data: missing team info")

    def find_season_for_teams(home_id, away_id):
        """Find a season that contains BOTH teams (searches all season paths)."""
        for seasons_path in get_all_season_paths():
            if not seasons_path.exists():
                continue
            for season_dir in sorted(seasons_path.iterdir()):
                if (
                    season_dir.is_dir()
                    and (season_dir / home_id).exists()
                    and (season_dir / away_id).exists()
                ):
                    return season_dir.name
        return None

    # Check: replay_data.season (new format) -> game_state.season (legacy format) -> search by team
    season = replay_data.get("season") or game_state.get("season")

    # Validate that the season actually contains BOTH teams, if not, detect from teams
    if season:
        season_dir = _find_season_dir(season)
        if (
            season_dir is None
            or not (season_dir / home_team_id).exists()
            or not (season_dir / away_team_id).exists()
        ):
            season = None  # Invalid season, will detect from teams

    if not season:
        season = find_season_for_teams(home_team_id, away_team_id)
    if not season:
        raise HTTPException(
            status_code=400, detail="Could not determine season for team. Please start a new game."
        )

    season_dir = _find_season_dir(season)
    if season_dir is None:
        raise HTTPException(status_code=404, detail=f"Season '{season}' not found")

    if not (season_dir / home_team_id).exists():
        raise HTTPException(
            status_code=400, detail=f"Team '{home_team_id}' not found in season '{season}'"
        )

    home_team = load_team_info(season_dir, home_team_id)
    away_team = load_team_info(season_dir, away_team_id)

    home_chart = load_team_chart(str(season_dir / home_team.id))
    away_chart = load_team_chart(str(season_dir / away_team.id))

    game_id = f"game_{uuid.uuid4().hex[:8]}"

    engine = PaydirtGameEngine(home_chart, away_chart)

    difficulty = replay_data.get("difficulty", "medium")

    new_game = {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "human_plays_offense": game_state.get("player_offense", True),
        "player_team_id": game_state.get("human_team_id", home_team_id),
        "cpu_team_id": game_state.get("cpu_team_id", away_team_id),
        "engine": engine,
        "ai": create_computer_ai(
            difficulty, engine, cpu_is_home=home_team.id == game_state.get("cpu_team_id", away_team_id)
        ),
        "created_at": datetime.now(),
        "season": season,
        "difficulty": difficulty,
        "play_history": replay_data.get("play_history", []),
    }


    # Restore game state from replay
    state = engine.state
    state.home_score = game_state.get("home_score", 0)
    state.away_score = game_state.get("away_score", 0)
    state.quarter = game_state.get("quarter", 1)
    state.time_remaining = game_state.get("time_remaining", 900) / 60  # Convert seconds to minutes
    state.down = game_state.get("down", 1)
    state.yards_to_go = game_state.get("yards_to_go", 10)
    state.ball_position = game_state.get("ball_position", 20)
    state.home_timeouts = game_state.get("home_timeouts", 3)
    state.away_timeouts = game_state.get("away_timeouts", 3)

    # Set possession correctly
    possession = game_state.get("possession", "home")
    state.is_home_possession = possession == "home"

    # Check if this game needs kickoff transition after a score or halftime
    # If the last play was a TD/FG/safety but game state wasn't set up for kickoff,
    # we need to fix it (this was a bug in the original code)
    play_history = replay_data.get("play_history", [])

    # Check if game is already in kickoff position (no transition needed)
    saved_ball_position = game_state.get("ball_position", 20)
    saved_down = game_state.get("down", 1)
    saved_yards_to_go = game_state.get("yards_to_go", 10)
    saved_quarter = game_state.get("quarter", 1)
    saved_time = game_state.get("time_remaining", 0)
    is_already_in_kickoff_position = (
        saved_ball_position == 35 and saved_down == 1 and saved_yards_to_go == 10
    )

    # Check if this is start of 2nd half (Q3, 15:00, kickoff position)
    is_halftime_kickoff = (
        saved_quarter == 3
        and saved_time == 900
        and saved_ball_position == 35
        and saved_down == 1
        and saved_yards_to_go == 10
    )

    needs_kickoff_transition = is_halftime_kickoff
    # Check for explicit pending_pat flag from frontend save
    explicit_pending_pat = game_state.get("pending_pat", False)
    has_pending_pat = explicit_pending_pat

    if (
        play_history
        and len(play_history) > 0
        and not is_already_in_kickoff_position
        and not explicit_pending_pat
        and not is_halftime_kickoff
    ):
        last_play = play_history[-1]
        if last_play is None:
            last_play = {}
        description = str(last_play.get("description") or "").lower()
        headline = str(last_play.get("headline") or "").lower()

        if any(term in description or term in headline for term in ["field goal good", "safety"]):
            needs_kickoff_transition = True
        elif "touchdown" in description or "touchdown" in headline:
            # Check if a PAT was already attempted after this TD
            last_score_idx = len(play_history) - 1
            pat_found = False
            for i in range(len(play_history) - 1, -1, -1):
                play = play_history[i] or {}
                desc = str(play.get("description") or "").lower()
                head = str(play.get("headline") or "").lower()
                if "touchdown" in desc or "touchdown" in head:
                    last_score_idx = i
                    break
            # Check plays after the TD for a PAT attempt
            for i in range(last_score_idx + 1, len(play_history)):
                play = play_history[i] or {}
                desc = str(play.get("description") or "").lower()
                if "extra point" in desc or "two-point" in desc or "2-point" in desc:
                    pat_found = True
                    break
            if pat_found:
                needs_kickoff_transition = True
            else:
                has_pending_pat = True

    if needs_kickoff_transition:
        state.switch_possession()
        state.ball_position = 35
        state.down = 1
        state.yards_to_go = 10
        possession = "home" if state.is_home_possession else "away"

    games[game_id] = new_game
    new_game["pending_pat"] = has_pending_pat

    # Handle pending penalty decision - we can't reconstruct the PlayOutcome
    # so we check if ball is in end zone (TD) and handle accordingly
    if state.ball_position >= 100:
        # Ball is in end zone - this was a touchdown
        state.ball_position = 100
        has_pending_pat = True
        new_game["pending_pat"] = True

    return NewGameResponse(
        game_id=game_id,
        game_state=game_state_to_response(new_game, is_kickoff=needs_kickoff_transition),
        difficulty=difficulty,
    )


@router.get("/api/debug/settings")
async def get_debug_settings():
    """Get current debug settings."""
    return {
        "deterministic_mode": False,
        "seed": None,
    }


class SetDebugModeRequest(BaseModel):
    deterministic_mode: bool = False
    seed: Optional[int] = None


@router.post("/api/debug/settings")
async def set_debug_settings(request: SetDebugModeRequest):
    """Set debug mode for deterministic dice rolls."""
    return {
        "deterministic_mode": request.deterministic_mode,
        "seed": request.seed,
        "status": "ok",
    }
