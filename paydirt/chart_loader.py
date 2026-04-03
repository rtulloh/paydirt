"""
Loader for Paydirt team chart CSV files.
Parses the actual team chart format used in the board game.
"""

import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class TeamMetadata:
    """Team metadata loaded from team.yaml file."""

    team_name: str = ""
    short_name: str = ""
    location: str = ""
    nickname: str = ""
    aliases: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


def load_team_metadata(team_dir: str) -> Optional[TeamMetadata]:
    """
    Load team metadata from team.yaml file in the team directory.

    Returns None if the file doesn't exist or can't be parsed.
    """
    yaml_path = os.path.join(team_dir, "team.yaml")
    if not os.path.exists(yaml_path):
        return None

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        return TeamMetadata(
            team_name=data.get("team_name", ""),
            short_name=data.get("short_name", ""),
            location=data.get("location", ""),
            nickname=data.get("nickname", ""),
            aliases=data.get("aliases", []),
            history=data.get("history", []),
        )
    except Exception:
        return None


@dataclass
class PeripheralData:
    """Team peripheral data from the chart."""

    year: int
    team_name: str
    team_nickname: str
    power_rating: int
    power_rating_variance: int = 1
    base_yardage_factor: int = 100
    reduced_yardage_factor: int = 80
    fumble_recovered_range: tuple[int, int] = (0, 0)  # dice roll range for recovered
    fumble_lost_range: tuple[int, int] = (0, 0)  # dice roll range for lost
    special_defense: str = ""
    short_name: str = ""


@dataclass
class OffenseChart:
    """
    Offensive play chart for a team.
    Maps dice rolls (10-39) to outcomes for each play type.
    """

    # Play type columns: dice_roll -> result string
    line_plunge: dict[int, str] = field(default_factory=dict)
    off_tackle: dict[int, str] = field(default_factory=dict)
    end_run: dict[int, str] = field(default_factory=dict)
    draw: dict[int, str] = field(default_factory=dict)
    screen: dict[int, str] = field(default_factory=dict)
    short_pass: dict[int, str] = field(default_factory=dict)
    medium_pass: dict[int, str] = field(default_factory=dict)
    long_pass: dict[int, str] = field(default_factory=dict)
    te_short_long: dict[int, str] = field(default_factory=dict)
    # Breakaway and QB time columns
    breakaway: dict[int, str] = field(default_factory=dict)
    qb_time: dict[int, str] = field(default_factory=dict)


@dataclass
class DefenseChart:
    """
    Defensive chart for a team.
    Maps defense type + sub-row to modifiers for each offensive play type.
    Defense types: A (Standard), B (Short Yardage), C (Spread),
                   D (Short Pass), E (Long Pass), F (Blitz)
    """

    # Format: (defense_letter, sub_row) -> {play_column: modifier}
    modifiers: dict[tuple[str, int], dict[int, str]] = field(default_factory=dict)


@dataclass
class SpecialTeamsChart:
    """Special teams chart data."""

    # dice_roll -> result
    kickoff: dict[int, str] = field(default_factory=dict)
    kickoff_return: dict[int, str] = field(default_factory=dict)
    punt: dict[int, str] = field(default_factory=dict)
    punt_return: dict[int, str] = field(default_factory=dict)
    interception_return: dict[int, str] = field(default_factory=dict)
    fumble_return: dict[int, str] = field(default_factory=dict)
    field_goal: dict[int, str] = field(default_factory=dict)
    extra_point_no_good: list[int] = field(default_factory=list)


@dataclass
class TeamChart:
    """Complete team chart with all data."""

    peripheral: PeripheralData
    offense: OffenseChart
    defense: DefenseChart
    special_teams: SpecialTeamsChart
    team_dir: str = ""  # Path to team directory for loading roster.json

    @property
    def full_name(self) -> str:
        return f"{self.peripheral.year} {self.peripheral.team_name} {self.peripheral.team_nickname}"

    @property
    def short_name(self) -> str:
        return (
            self.peripheral.short_name
            or f"{self.peripheral.team_nickname[:3].upper()} '{str(self.peripheral.year)[2:]}"
        )


def parse_peripheral_data(filepath: str) -> PeripheralData:
    """Parse the PERIPHERAL DATA CSV file."""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Row 2 (index 1) contains the main data
    # Format: ,,1983,,219 ± 1,100 / 80,10-31,32-39,W,30*31*,CIN '83
    data_row = rows[1] if len(rows) > 1 else []

    year = 1983  # default
    power_rating = 50
    power_variance = 1
    base_yf = 100
    reduced_yf = 80
    fumble_rec = (10, 31)
    fumble_lost = (32, 39)
    special_def = ""
    short_name = ""
    team_name = ""
    team_nickname = ""

    # Parse year
    if len(data_row) > 2 and data_row[2]:
        try:
            year = int(data_row[2])
        except ValueError:
            pass

    # Parse power rating (format: "219 ± 1")
    if len(data_row) > 4 and data_row[4]:
        pr_match = re.match(r"(\d+)\s*[±+-]\s*(\d+)", data_row[4])
        if pr_match:
            power_rating = int(pr_match.group(1))
            power_variance = int(pr_match.group(2))
        else:
            try:
                power_rating = int(data_row[4].split()[0])
            except (ValueError, IndexError):
                pass

    # Parse yardage factors (format: "100 / 80")
    if len(data_row) > 5 and data_row[5]:
        yf_match = re.match(r"(\d+)\s*/\s*(\d+)", data_row[5])
        if yf_match:
            base_yf = int(yf_match.group(1))
            reduced_yf = int(yf_match.group(2))

    # Parse fumble ranges
    if len(data_row) > 6 and data_row[6]:
        fr_match = re.match(r"(\d+)-(\d+)", data_row[6])
        if fr_match:
            fumble_rec = (int(fr_match.group(1)), int(fr_match.group(2)))

    if len(data_row) > 7 and data_row[7]:
        fl_match = re.match(r"(\d+)-(\d+)", data_row[7])
        if fl_match:
            fumble_lost = (int(fl_match.group(1)), int(fl_match.group(2)))

    # Parse special defense
    if len(data_row) > 8:
        special_def = data_row[8]

    # Parse short name
    if len(data_row) > 10:
        short_name = data_row[10]

    # Parse team name and nickname from rows 4-5
    if len(rows) > 4:
        # Row 4: Team name:,,,Cincinnati,...
        name_row = rows[3]
        if len(name_row) > 3:
            team_name = name_row[3]

    if len(rows) > 5:
        # Row 5: Team nickname:,,,Bengals,...
        nick_row = rows[4]
        if len(nick_row) > 3:
            team_nickname = nick_row[3]

    return PeripheralData(
        year=year,
        team_name=team_name,
        team_nickname=team_nickname,
        power_rating=power_rating,
        power_rating_variance=power_variance,
        base_yardage_factor=base_yf,
        reduced_yardage_factor=reduced_yf,
        fumble_recovered_range=fumble_rec,
        fumble_lost_range=fumble_lost,
        special_defense=special_def,
        short_name=short_name,
    )


def parse_offense_chart(filepath: str) -> tuple[OffenseChart, PeripheralData]:
    """
    Parse the OFFENSE CSV file.

    Extracts both the offense chart data and peripheral data (team name, year,
    fumble ranges) from the offense chart, eliminating the need for a separate
    PERIPHERAL DATA file.

    Returns:
        Tuple of (OffenseChart, PeripheralData)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    chart = OffenseChart()

    # Extract peripheral data from offense chart
    # Row 1 (index 0): "1983 Chicago                      offense"
    # Row 12 (index 11): Contains "Yardage factors: 100% / 80%" in column 11
    # Row 21 (index 20): Contains "Power rating: 220½ ± 1" in column 11
    # Row 26 (index 25): Contains "Fumble Recovered 10-27; Lost Ball 28-39" in column 15

    year = 1983
    team_name = ""
    team_nickname = ""
    fumble_rec = (10, 31)  # default
    fumble_lost = (32, 39)  # default

    # Parse year and team from row 1 (format: "1983 Chicago                      offense")
    if rows and rows[0]:
        header = rows[0][0].strip() if rows[0][0] else ""
        # Extract year (first 4 digits) and team name
        year_match = re.match(r"(\d{4})\s+(.+?)\s+offense", header, re.IGNORECASE)
        if year_match:
            year = int(year_match.group(1))
            team_name = year_match.group(2).strip()
            # Use team name as nickname too (can be overridden)
            team_nickname = team_name

    # Parse fumble ranges - look for "Fumble Recovered X-Y; Lost Ball Z-W" pattern
    # This is typically on the row for dice roll 26, but search all rows to be safe
    for row in rows:
        row_text = " ".join(str(cell) for cell in row)
        fumble_match = re.search(
            r"Fumble\s+Recovered\s+(\d+)-(\d+);?\s*Lost\s+Ball\s+(\d+)-(\d+)",
            row_text,
            re.IGNORECASE,
        )
        if fumble_match:
            fumble_rec = (int(fumble_match.group(1)), int(fumble_match.group(2)))
            fumble_lost = (int(fumble_match.group(3)), int(fumble_match.group(4)))
            break

    # Generate short name (e.g., "CHI '83")
    # Use team directory name to disambiguate (Giants vs Jets, Raiders vs Rams)
    # The team_name from header may be ambiguous (e.g., "New York", "Los Angeles")
    short_name_map = {
        "Chicago": "CHI",
        "Cincinnati": "CIN",
        "Cleveland": "CLE",
        "Dallas": "DAL",
        "Denver": "DEN",
        "Detroit": "DET",
        "Green Bay": "GB",
        "Houston": "HOU",
        "Indianapolis": "IND",
        "Baltimore": "BAL",
        "Kansas City": "KC",
        "Miami": "MIA",
        "Minnesota": "MIN",
        "New England": "NE",
        "New Orleans": "NO",
        "Philadelphia": "PHI",
        "Pittsburgh": "PIT",
        "San Diego": "SD",
        "San Francisco": "SF",
        "Seattle": "SEA",
        "St. Louis": "STL",
        "Tampa Bay": "TB",
        "Washington": "Wash",
        "Atlanta": "ATL",
        "Buffalo": "BUF",
        # Handle variants without spaces
        "NewYork": "NY",  # Will be disambiguated by directory
        "LosAngeles": "LA",  # Will be disambiguated by directory
    }

    # Try direct lookup first
    abbrev = short_name_map.get(team_name)

    # If not found or ambiguous (NY/LA), we'll fix it in load_team_chart
    # using the directory name
    if not abbrev:
        abbrev = team_name[:3].upper() if team_name else "UNK"

    short_name = abbrev

    peripheral = PeripheralData(
        year=year,
        team_name=team_name,
        team_nickname=team_nickname,
        power_rating=50,  # Not used in game mechanics
        power_rating_variance=0,
        base_yardage_factor=100,
        reduced_yardage_factor=80,
        fumble_recovered_range=fumble_rec,
        fumble_lost_range=fumble_lost,
        special_defense="",
        short_name=short_name,
    )

    # The offense data starts at row 4 (index 3) with dice roll 10
    # Columns: ,#,Line Plunge,Off Tackle,End Run,Draw,Screen,Short,Med,Long,T/E S/L,...,B,QT,#
    # Data rows have format: ,10,-1,B,5,OFF 10,16,7,OFF 15,PI 37,,,,15,10,10

    # Column indices (0-based, after the first empty column):
    # 1=#, 2=Line Plunge, 3=Off Tackle, 4=End Run, 5=Draw, 6=Screen,
    # 7=Short, 8=Med, 9=Long, 10=T/E S/L, ..., 13=B, 14=QT

    for row in rows[3:33]:  # Rows for dice rolls 10-39
        if len(row) < 10:
            continue

        # Get dice roll number from column 1
        try:
            dice_roll = int(row[1]) if row[1] else None
        except ValueError:
            continue

        if dice_roll is None or dice_roll < 10 or dice_roll > 39:
            continue

        # Parse each play type column
        def get_cell(idx):
            return row[idx].strip() if len(row) > idx and row[idx] else ""

        chart.line_plunge[dice_roll] = get_cell(2)
        chart.off_tackle[dice_roll] = get_cell(3)
        chart.end_run[dice_roll] = get_cell(4)
        chart.draw[dice_roll] = get_cell(5)
        chart.screen[dice_roll] = get_cell(6)
        chart.short_pass[dice_roll] = get_cell(7)
        chart.medium_pass[dice_roll] = get_cell(8)
        chart.long_pass[dice_roll] = get_cell(9)
        chart.te_short_long[dice_roll] = get_cell(10)

        # B and QT columns are typically at indices 13 and 14
        if len(row) > 13:
            chart.breakaway[dice_roll] = get_cell(13)
        if len(row) > 14:
            chart.qb_time[dice_roll] = get_cell(14)

    return chart, peripheral


def parse_defense_chart(filepath: str) -> tuple[DefenseChart, SpecialTeamsChart]:
    """
    Parse the DEFENSE CSV file.

    Defense chart structure:
    - Rows 3-32 contain defense data (formations A-F, sub-rows 1-5)
    - Column 1: Formation letter (A-F) or formation name
    - Column 2: Sub-row number (1-5)
    - Columns 3-11: Defensive modifiers for play types 1-9
    - Column 12: Label ("special team")
    - Columns 13-18: Special teams (Kickoff, KO Return, Punt, Punt Return, Int Return, FG)
    - Column 19: Dice roll number for special teams
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    defense = DefenseChart()
    special = SpecialTeamsChart()

    current_formation = ""
    formation_letters = {"A", "B", "C", "D", "E", "F"}

    # Track dice roll for special teams (starts at 10)
    special_teams_roll = 10

    for row_idx, row in enumerate(rows[2:32], start=2):  # Defense data rows (indices 2-31)
        if len(row) < 3:
            continue

        # Check for formation letter in column 1
        col1 = row[1].strip() if len(row) > 1 and row[1] else ""
        if col1 in formation_letters:
            current_formation = col1

        # Get sub-row number from column 2
        try:
            sub_row = int(row[2]) if row[2] else None
        except ValueError:
            sub_row = None

        # Parse defensive modifiers if we have a valid formation and sub-row
        if current_formation and sub_row:
            modifiers = {}
            # Columns 3-11 contain modifiers for play types 1-9
            for col_idx in range(3, 12):
                if len(row) > col_idx and row[col_idx]:
                    cell_value = row[col_idx].strip()
                    if cell_value:
                        modifiers[col_idx - 2] = cell_value  # 1-indexed play columns

            defense.modifiers[(current_formation, sub_row)] = modifiers

        # Parse special teams data (columns 13-18)
        # The dice roll is in column 19, or we can use sequential numbering
        def get_cell(idx):
            return row[idx].strip() if len(row) > idx and row[idx] else ""

        # Try to get dice roll from column 19
        dice_roll = special_teams_roll
        if len(row) > 19 and row[19]:
            try:
                dice_roll = int(row[19])
            except ValueError:
                pass

        # Parse each special teams column (indices 13-18 based on CSV structure)
        # Column 13 = Kickoff, 14 = Kickoff Return, 15 = Punt,
        # 16 = Punt Return, 17 = Int. Return, 18 = Field Goal, 19 = dice roll #
        kickoff_val = get_cell(13)
        ko_return_val = get_cell(14)
        punt_val = get_cell(15)
        punt_return_val = get_cell(16)
        int_return_val = get_cell(17)
        fg_val = get_cell(18)

        if kickoff_val:
            special.kickoff[dice_roll] = kickoff_val
        if ko_return_val:
            special.kickoff_return[dice_roll] = ko_return_val
        if punt_val:
            special.punt[dice_roll] = punt_val
        if punt_return_val:
            special.punt_return[dice_roll] = punt_return_val
        if int_return_val:
            special.interception_return[dice_roll] = int_return_val
            special.fumble_return[dice_roll] = int_return_val
        if fg_val:
            special.field_goal[dice_roll] = fg_val

        # Column 8 = Extra Point (Good/Missed)
        # 1972 format: 1 = Good, 0 = No Good
        # 1983 format: blank = Good, NG = No Good
        extra_point_val = get_cell(8)
        if extra_point_val and extra_point_val.strip() in ("0", "NG"):
            special.extra_point_no_good.append(dice_roll)

        special_teams_roll += 1

    return defense, special


def parse_offense_csv(filepath: str) -> tuple[OffenseChart, PeripheralData]:
    """
    Parse the new format offense.csv file.

    Format:
    #,Line Plunge,Off Tackle,End Run,Draw,Screen,Short,Med,Long,T/E S/L,B,QT
    10,6,5,F - 4,3,-11,PI 5,13,DEF 5,PI 18,17,-3

    Returns:
        Tuple of (OffenseChart, PeripheralData)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    chart = OffenseChart()

    # Extract team info from filename (directory name)
    path = Path(filepath)
    team_dir = path.parent.name

    # Parse year from parent directory
    year_dir = path.parent.parent.name
    try:
        year = int(year_dir)
    except ValueError:
        year = 1983

    peripheral = PeripheralData(
        year=year,
        team_name=team_dir,
        team_nickname=team_dir,
        short_name=f"{team_dir[:3].upper()} '{str(year)[2:]}",
        power_rating=50,
    )

    # Track fumble results to calculate ranges
    fumble_recovered_rolls = []
    fumble_lost_rolls = []

    # Parse dice rolls (10-39)
    for row in rows[1:]:  # Skip header
        if len(row) < 2:
            continue

        # Skip comment rows (starting with #)
        if row[0] and str(row[0]).strip().startswith("#"):
            continue

        try:
            dice_roll = int(row[0])
        except (ValueError, IndexError):
            continue

        if dice_roll < 10 or dice_roll > 39:
            continue

        # Parse fumble column (R = recovered, L = lost)
        if len(row) > 12 and row[12]:
            fumble_val = row[12].strip().upper()
            if fumble_val == "R":
                fumble_recovered_rolls.append(dice_roll)
            elif fumble_val == "L":
                fumble_lost_rolls.append(dice_roll)

        # Map columns to play types
        if len(row) > 1 and row[1]:
            chart.line_plunge[dice_roll] = row[1]
        if len(row) > 2 and row[2]:
            chart.off_tackle[dice_roll] = row[2]
        if len(row) > 3 and row[3]:
            chart.end_run[dice_roll] = row[3]
        if len(row) > 4 and row[4]:
            chart.draw[dice_roll] = row[4]
        if len(row) > 5 and row[5]:
            chart.screen[dice_roll] = row[5]
        if len(row) > 6 and row[6]:
            chart.short_pass[dice_roll] = row[6]
        if len(row) > 7 and row[7]:
            chart.medium_pass[dice_roll] = row[7]
        if len(row) > 8 and row[8]:
            chart.long_pass[dice_roll] = row[8]
        if len(row) > 9 and row[9]:
            chart.te_short_long[dice_roll] = row[9]
        if len(row) > 10 and row[10]:
            chart.breakaway[dice_roll] = row[10]
        if len(row) > 11 and row[11]:
            chart.qb_time[dice_roll] = row[11]

    # Parse fumble ranges from comment lines at the end of file
    for row in rows:
        if not row or len(row) < 2:
            continue
        first_cell = str(row[0]).strip()
        if first_cell == "# Recovered" and len(row) > 1:
            range_str = str(row[1]).strip()
            if "-" in range_str:
                try:
                    parts = range_str.split("-")
                    peripheral.fumble_recovered_range = (int(parts[0]), int(parts[1]))
                except Exception:
                    pass
        elif first_cell == "# Lost" and len(row) > 1:
            range_str = str(row[1]).strip()
            if "-" in range_str:
                try:
                    parts = range_str.split("-")
                    peripheral.fumble_lost_range = (int(parts[0]), int(parts[1]))
                except Exception:
                    pass

    # Set fumble ranges from the data (fallback if comments not found)
    if peripheral.fumble_recovered_range == (0, 0) and fumble_recovered_rolls:
        peripheral.fumble_recovered_range = (
            min(fumble_recovered_rolls),
            max(fumble_recovered_rolls),
        )
    if peripheral.fumble_lost_range == (0, 0) and fumble_lost_rolls:
        peripheral.fumble_lost_range = (min(fumble_lost_rolls), max(fumble_lost_rolls))

    return chart, peripheral


def parse_defense_csv(filepath: str) -> DefenseChart:
    """
    Parse the new format defense.csv file.

    Format:
    #,Formation,Sub,1,2,3,4,5,6,7,8,9
    A-1,A,1,,,,-2.0,(-1),,,-3.0

    Returns:
        DefenseChart
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    defense = DefenseChart()

    # Skip header row
    for row in rows[1:]:
        if len(row) < 3:
            continue

        # Formation is in column 1, Sub is in column 2
        formation = row[1].strip()
        try:
            sub_row = int(row[2])
        except (ValueError, IndexError):
            continue

        # Parse modifiers for each play type (columns 3-11 for dice 1-9)
        modifiers = {}
        for col_idx in range(3, 12):
            if col_idx < len(row) and row[col_idx]:
                cell_value = row[col_idx].strip()
                if cell_value:
                    modifiers[col_idx - 2] = cell_value  # 1-indexed play columns (col 3 -> dice 1)

        if modifiers:
            defense.modifiers[(formation, sub_row)] = modifiers

    return defense


def parse_special_csv(filepath: str) -> SpecialTeamsChart:
    """
    Parse the new format special.csv file.

    Format:
    #,Kickoff,Kickoff Return,Punt,Punt Return,Int. Return,Field Goal,Extra Point
    10,72,28,30*,OFF 15,,NG,

    Returns:
        SpecialTeamsChart
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    special = SpecialTeamsChart()

    # Skip header row
    for row in rows[1:]:
        if len(row) < 2:
            continue

        try:
            dice_roll = int(row[0])
        except (ValueError, IndexError):
            continue

        if dice_roll < 10 or dice_roll > 39:
            continue

        # Parse special teams columns
        if len(row) > 1 and row[1]:
            special.kickoff[dice_roll] = row[1]
        if len(row) > 2 and row[2]:
            special.kickoff_return[dice_roll] = row[2]
        if len(row) > 3 and row[3]:
            special.punt[dice_roll] = row[3]
        if len(row) > 4 and row[4]:
            special.punt_return[dice_roll] = row[4]
        if len(row) > 5 and row[5]:
            special.interception_return[dice_roll] = row[5]
            special.fumble_return[dice_roll] = row[5]
        if len(row) > 6 and row[6]:
            special.field_goal[dice_roll] = row[6]

        # Extra Point: 1972 format: 1 = Good, 0 = No Good; 1983 format: blank = Good, NG = No Good
        if len(row) > 7 and row[7] and row[7].strip() in ("0", "NG"):
            special.extra_point_no_good.append(dice_roll)

    return special


def load_team_chart(team_dir: str) -> TeamChart:
    """
    Load a complete team chart from a directory containing the CSV files.

    Args:
        team_dir: Path to directory containing CSV files.
                  Supports both legacy format (OFFENSE-Table 1.csv, DEFENSE-Table 1.csv)
                  and new format (offense.csv, defense.csv, special.csv)

    Returns:
        TeamChart with all parsed data
    """
    team_path = Path(team_dir)

    # Check for new format CSV files (offense.csv, defense.csv, special.csv)
    offense_csv = team_path / "offense.csv"
    defense_csv = team_path / "defense.csv"
    special_csv = team_path / "special.csv"

    if offense_csv.exists() and defense_csv.exists() and special_csv.exists():
        # New format: offense.csv, defense.csv, special.csv
        offense, peripheral = parse_offense_csv(str(offense_csv))
        defense = parse_defense_csv(str(defense_csv))
        special_teams = parse_special_csv(str(special_csv))
    else:
        raise FileNotFoundError(
            f"Chart files not found in {team_dir}. Expected: offense.csv, defense.csv, special.csv"
        )

    # Load team metadata from team.yaml if available
    metadata = load_team_metadata(str(team_path))
    if metadata and metadata.short_name:
        peripheral.short_name = metadata.short_name

    # Also set team_nickname from directory name for clarity
    if peripheral.team_nickname == peripheral.team_name:
        peripheral.team_nickname = team_path.name

    return TeamChart(
        peripheral=peripheral,
        offense=offense,
        defense=defense,
        special_teams=special_teams,
        team_dir=str(team_path),
    )


def find_team_charts(seasons_dir: str) -> list[tuple[str, str, str]]:
    """
    Find all team chart directories in the seasons folder.

    Returns:
        List of (year, team_name, path) tuples
    """
    seasons_path = Path(seasons_dir)
    charts = []

    if not seasons_path.exists():
        return charts

    for year_dir in seasons_path.iterdir():
        if not year_dir.is_dir():
            continue

        # Only include directories with numeric names (valid season years)
        if not year_dir.name.isdigit():
            continue

        year = year_dir.name

        for team_dir in year_dir.iterdir():
            if not team_dir.is_dir():
                continue

            # Check if this directory has the required CSV files (new format)
            if (
                (team_dir / "offense.csv").exists()
                and (team_dir / "defense.csv").exists()
                and (team_dir / "special.csv").exists()
            ):
                charts.append((year, team_dir.name, str(team_dir)))

    return sorted(charts)
