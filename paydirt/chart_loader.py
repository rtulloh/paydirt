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
    fumble_recovered_range: tuple[int, int] = (10, 31)  # dice roll range for recovered
    fumble_lost_range: tuple[int, int] = (32, 39)  # dice roll range for lost
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
        return self.peripheral.short_name or f"{self.peripheral.team_nickname[:3].upper()} '{str(self.peripheral.year)[2:]}"


def parse_peripheral_data(filepath: str) -> PeripheralData:
    """Parse the PERIPHERAL DATA CSV file."""
    with open(filepath, 'r', encoding='utf-8') as f:
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
        pr_match = re.match(r'(\d+)\s*[±+-]\s*(\d+)', data_row[4])
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
        yf_match = re.match(r'(\d+)\s*/\s*(\d+)', data_row[5])
        if yf_match:
            base_yf = int(yf_match.group(1))
            reduced_yf = int(yf_match.group(2))
    
    # Parse fumble ranges
    if len(data_row) > 6 and data_row[6]:
        fr_match = re.match(r'(\d+)-(\d+)', data_row[6])
        if fr_match:
            fumble_rec = (int(fr_match.group(1)), int(fr_match.group(2)))
    
    if len(data_row) > 7 and data_row[7]:
        fl_match = re.match(r'(\d+)-(\d+)', data_row[7])
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


def parse_offense_chart(filepath: str) -> OffenseChart:
    """Parse the OFFENSE CSV file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    chart = OffenseChart()
    
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
    
    return chart


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
    with open(filepath, 'r', encoding='utf-8') as f:
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
            # Use same data for fumble returns (no separate column in CSV)
            special.fumble_return[dice_roll] = int_return_val
        if fg_val:
            special.field_goal[dice_roll] = fg_val
        
        special_teams_roll += 1
    
    return defense, special


def load_team_chart(team_dir: str) -> TeamChart:
    """
    Load a complete team chart from a directory containing the CSV files.
    
    Args:
        team_dir: Path to directory containing OFFENSE-Table 1.csv, 
                  DEFENSE-Table 1.csv, and PERIPHERAL DATA-Table 1.csv
    
    Returns:
        TeamChart with all parsed data
    """
    team_path = Path(team_dir)
    
    # Find the CSV files
    offense_file = team_path / "OFFENSE-Table 1.csv"
    defense_file = team_path / "DEFENSE-Table 1.csv"
    peripheral_file = team_path / "PERIPHERAL DATA-Table 1.csv"
    
    if not offense_file.exists():
        raise FileNotFoundError(f"Offense chart not found: {offense_file}")
    if not defense_file.exists():
        raise FileNotFoundError(f"Defense chart not found: {defense_file}")
    if not peripheral_file.exists():
        raise FileNotFoundError(f"Peripheral data not found: {peripheral_file}")
    
    peripheral = parse_peripheral_data(str(peripheral_file))
    offense = parse_offense_chart(str(offense_file))
    defense, special_teams = parse_defense_chart(str(defense_file))
    
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
        
        try:
            year = year_dir.name
        except ValueError:
            continue
        
        for team_dir in year_dir.iterdir():
            if not team_dir.is_dir():
                continue
            
            # Check if this directory has the required CSV files
            if (team_dir / "OFFENSE-Table 1.csv").exists():
                charts.append((year, team_dir.name, str(team_dir)))
    
    return sorted(charts)
