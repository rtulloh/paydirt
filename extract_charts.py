#!/usr/bin/env python3
"""
Extract chart data from Excel files and generate CSV files.
Identifies BLACK cells (incomplete passes) from cell background colors.

NOTE: xlrd 1.2.0 cannot evaluate Excel formulas.
If a cell contains a formula (e.g., ="(1)"), it will show as empty.
Teams with formula cells (Redskins, Eagles) need manual fix or .xlsx conversion.
"""

import xlrd
import os
import csv
import argparse

BASE_DIR = "/Users/rtulloh/Downloads/1972teams"
OUTPUT_DIR = "/Users/rtulloh/Downloads/1972"

TEAM_MAPPING = {
    'FortyNiners': '49ers',
    'NYGiants': 'Giants',
    'NYJets ': 'Jets',
}

parser = argparse.ArgumentParser(description='Extract chart data from Excel files')
parser.add_argument('-i', '--input', default=BASE_DIR, help='Input directory with .xls files')
parser.add_argument('-o', '--output', default=OUTPUT_DIR, help='Output directory for CSV files')
parser.add_argument('-t', '--team', help='Process specific team file (e.g., 197249ers.xls)')

args = parser.parse_args()


def format_cell_value(value, ctype):
    """Format cell value - read as string, convert floats to ints if whole numbers."""
    if value is None:
        return ''
    if ctype == 2:
        try:
            f = float(value)
            if f == int(f):
                return str(int(f))
            return str(f)
        except Exception:
            pass
    return str(value).strip()


def is_black_cell(workbook, cell):
    """Check if a cell has BLACK background (incomplete pass)."""
    try:
        xf = workbook.xf_list[cell.xf_index]
        bg = xf.background
        fill = bg.fill_pattern
        fg_color_idx = bg.pattern_colour_index
        # BLACK cell = solid fill with black foreground
        return fill == 1 and fg_color_idx == 8
    except Exception:
        return False


def has_paren_format(workbook, cell):
    """Check if a cell has parentheses number format (displays values like (2))."""
    try:
        xf = workbook.xf_list[cell.xf_index]
        fmt_key = xf.format_key
        if fmt_key in workbook.format_map:
            fmt_str = workbook.format_map[fmt_key].format_str
            return '\\(0\\)' in fmt_str
        return False
    except Exception:
        return False


def extract_fumble_ranges(file_path):
    """Extract fumble recovery ranges from column Q of offense sheet."""
    workbook = xlrd.open_workbook(file_path, formatting_info=True)
    sheet = workbook.sheet_by_name('OFFENSE')
    
    fumble_rec_range = None  # (start, end)
    fumble_lost_range = None  # (start, end)
    
    # Look in column Q (index 16) for fumble range info
    for row_idx in range(min(40, sheet.nrows)):
        cell = sheet.cell(row_idx, 16)
        if cell.value and isinstance(cell.value, str):
            val = str(cell.value).strip()
            if 'Fumble Recovered' in val:
                # Format: "Fumble Recovered 10-29; Lost Ball 30-39"
                import re
                rec_match = re.search(r'Fumble Recovered (\d+)-(\d+)', val)
                lost_match = re.search(r'Lost Ball (\d+)-(\d+)', val)
                if rec_match:
                    fumble_rec_range = (int(rec_match.group(1)), int(rec_match.group(2)))
                if lost_match:
                    fumble_lost_range = (int(lost_match.group(1)), int(lost_match.group(2)))
                break
    
    return fumble_rec_range, fumble_lost_range


def extract_offense_chart(file_path):
    """Extract offense chart from Excel file."""
    workbook = xlrd.open_workbook(file_path, formatting_info=True)
    sheet = workbook.sheet_by_name('OFFENSE')
    
    # Find the header row with dice values (1-9)
    # Typically row 1 or row 2
    dice_row = None
    for row_idx in range(5):
        row_vals = [sheet.cell(row_idx, c).value for c in range(15)]
        if '1.0' in row_vals or '1' in str(row_vals):
            # Check if this looks like dice headers
            dice_vals = []
            for c in range(2, 12):
                v = sheet.cell(row_idx, c).value
                try:
                    if v and float(v) == int(float(v)):
                        dice_vals.append(int(float(v)))
                except Exception:
                    pass
            if sorted(dice_vals) == list(range(1, 10)):
                dice_row = row_idx
                break
    
    if dice_row is None:
        dice_row = 2  # Default fallback
    
    # Extract fumble ranges from column Q
    fumble_rec_range, fumble_lost_range = extract_fumble_ranges(file_path)
    
    # Find dice rows (starting from dice_row + 1, looking for dice values 10-39)
    chart_data = {}  # {dice_value: {col_name: value}}
    
    col_names = ['Line Plunge', 'Off Tackle', 'End Run', 'Draw', 'Screen', 
                 'Short', 'Med', 'Long', 'T/E S/L']
    special_cols = [(13, 'B'), (14, 'QT'), (15, 'Fumble')]
    
    for row_idx in range(dice_row + 1, min(dice_row + 40, sheet.nrows)):
        dice_cell = sheet.cell(row_idx, 1)
        if not dice_cell.value:
            continue
        try:
            # Handle both int and float
            dice_val = int(float(dice_cell.value))
        except Exception:
            continue
        
        if not (10 <= dice_val <= 39):
            continue
            
        row_data = {}
        
        # Main columns (2-10)
        for col_idx, col_name in enumerate(col_names, start=2):
            cell = sheet.cell(row_idx, col_idx)
            cell_value = format_cell_value(cell.value, cell.ctype)
            
            # Check if BLACK cell
            is_black = is_black_cell(workbook, cell)
            
            if is_black and not cell_value:
                cell_value = 'BLACK'
            
            if cell_value:
                row_data[col_name] = cell_value
            elif is_black:
                row_data[col_name] = 'BLACK'
        
        # Special columns B, QT, Fumble
        for col_idx, col_name in special_cols:
            cell = sheet.cell(row_idx, col_idx)
            cell_value = format_cell_value(cell.value, cell.ctype)
            
            is_black = is_black_cell(workbook, cell)
            
            if is_black and not cell_value:
                cell_value = 'BLACK'
            
            # For Fumble column, use R/L based on ranges from column Q
            if col_name == 'Fumble':
                if fumble_rec_range and fumble_rec_range[0] <= dice_val <= fumble_rec_range[1]:
                    cell_value = 'R'
                elif fumble_lost_range and fumble_lost_range[0] <= dice_val <= fumble_lost_range[1]:
                    cell_value = 'L'
            
            if cell_value:
                row_data[col_name] = cell_value
            elif is_black:
                row_data[col_name] = 'BLACK'
        
        if row_data:
            chart_data[dice_val] = row_data
    
    return chart_data

def extract_defense_chart(file_path):
    """Extract defense and special teams charts from Excel file."""
    workbook = xlrd.open_workbook(file_path, formatting_info=True)
    sheet = workbook.sheet_by_name('DEFENSE')
    
    # Find header row with dice values 1-9
    dice_row = None
    dice_col_map = {}  # {dice_num: col_index}
    
    for row_idx in range(5):
        for col_idx in range(12):
            v = sheet.cell(row_idx, col_idx).value
            if v:
                try:
                    val = float(v)
                    if 1 <= val <= 9 and val == int(val):
                        dice_col_map[int(val)] = col_idx
                except (ValueError, TypeError):
                    pass
        if len(dice_col_map) >= 3:  # If we found at least 3 dice columns
            dice_row = row_idx
            break
    
    if not dice_row:
        dice_row = 1
    
    if not dice_col_map:
        dice_col_map = {1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 11}
    
    # Parse the defense chart
    chart_data = {}  # {(formation, sub_row): {dice: value}}
    
    current_formation = None
    
    for row_idx in range(dice_row + 1, sheet.nrows):
        formation = None
        sub_row = None
        
        # Check columns 0-2 for formation letter
        for col in range(3):
            cell_val = sheet.cell(row_idx, col).value
            if cell_val and isinstance(cell_val, str):
                cell_val = str(cell_val).strip()
                if cell_val in ['A', 'B', 'C', 'D', 'E', 'F']:
                    formation = cell_val
                    current_formation = formation
                    break
        
        if not formation and current_formation:
            formation = current_formation
        
        if not formation:
            continue
        
        # Find sub-row number by looking for a number 1-5 in columns 0-3
        for col in range(4):
            cell_val = sheet.cell(row_idx, col).value
            if cell_val:
                try:
                    val = float(cell_val)
                    if val == int(val) and 1 <= int(val) <= 5:
                        sub_row = int(val)
                        break
                except (ValueError, TypeError):
                    pass
        
        if not sub_row:
            continue
        
        # Get dice values using the dice_col_map
        for dice_num, col_idx in dice_col_map.items():
            cell = sheet.cell(row_idx, col_idx)
            
            # Check if BLACK cell
            is_black = is_black_cell(workbook, cell)
            
            # Check if cell has parentheses format
            use_parens = has_paren_format(workbook, cell)
            
            # Get cell value based on type
            if cell.ctype == 2:  # numeric
                float_val = cell.value
                if float_val == int(float_val):
                    cell_value = str(int(float_val))
                else:
                    cell_value = str(float_val)
                if use_parens:
                    cell_value = f'({cell_value})'
            elif cell.ctype == 1:  # text
                cell_value = str(cell.value).strip()
            else:
                cell_value = ''
            
            if is_black and not cell_value:
                cell_value = 'BLACK'
            
            key = (formation, sub_row)
            if key not in chart_data:
                chart_data[key] = {}
            
            if cell_value and cell_value not in ['', 'None']:
                chart_data[key][dice_num] = cell_value
            elif is_black:
                chart_data[key][dice_num] = 'BLACK'
    
    # Extract special teams data from columns N-S and V (13-18, 21)
    # Columns: N=Kickoff, O=Kickoff Return, P=Punt, Q=Punt Return, R=Int. Return, S=Field Goal, V=Extra Point
    special_col_names = ['Kickoff', 'Kickoff Return', 'Punt', 'Punt Return', 'Int. Return', 'Field Goal', 'Extra Point']
    special_col_map = {
        'Kickoff': 13,
        'Kickoff Return': 14,
        'Punt': 15,
        'Punt Return': 16,
        'Int. Return': 17,
        'Field Goal': 18,
        'Extra Point': 21
    }
    
    special_data = {}  # {dice_val: {col_name: value}}
    
    for row_idx in range(dice_row + 1, sheet.nrows):
        # Stop when we hit empty rows (end of first special teams block)
        dice_cell = sheet.cell(row_idx, 19)
        if not dice_cell.value:
            break  # Stop at first empty row
        
        # Get dice value from column 19 (index 19) for special teams
        try:
            dice_val = int(float(dice_cell.value))
        except Exception:
            continue
        
        if not (10 <= dice_val <= 39):
            continue
        
        row_data = {}
        for col_name, col_idx in special_col_map.items():
            cell = sheet.cell(row_idx, col_idx)
            cell_value = format_cell_value(cell.value, cell.ctype)
            
            is_black = is_black_cell(workbook, cell)
            
            if is_black and not cell_value:
                cell_value = 'BLACK'
            
            if cell_value:
                row_data[col_name] = cell_value
            elif is_black:
                row_data[col_name] = 'BLACK'
        
        if row_data:
            special_data[dice_val] = row_data
    
    return chart_data, special_data

def write_offense_csv(chart_data, output_path):
    """Write offense chart to CSV."""
    col_names = ['#', 'Line Plunge', 'Off Tackle', 'End Run', 'Draw', 'Screen', 
                 'Short', 'Med', 'Long', 'T/E S/L', 'B', 'QT', 'Fumble']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        
        for dice_val in sorted(chart_data.keys()):
            row = [dice_val]
            row_data = chart_data[dice_val]
            for col_name in col_names[1:]:
                row.append(row_data.get(col_name, ''))
            writer.writerow(row)

def write_defense_csv(chart_data, output_path):
    """Write defense chart to CSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['#', 'Formation', 'Sub', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
        
        for (formation, sub_row) in sorted(chart_data.keys()):
            row = [f'{formation}-{sub_row}', formation, sub_row]
            row_data = chart_data[(formation, sub_row)]
            for dice in range(1, 10):
                row.append(row_data.get(dice, ''))
            writer.writerow(row)

def write_special_csv(chart_data, output_path):
    """Write special teams chart to CSV."""
    col_names = ['#', 'Kickoff', 'Kickoff Return', 'Punt', 'Punt Return', 'Int. Return', 'Field Goal', 'Extra Point']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        
        for dice_val in sorted(chart_data.keys()):
            row = [dice_val]
            row_data = chart_data[dice_val]
            for col_name in col_names[1:]:
                row.append(row_data.get(col_name, ''))
            writer.writerow(row)

def process_team(excel_file):
    """Process a single team's Excel file."""
    # Extract team name - handle both 1983 and 1972 file naming conventions
    team_name = excel_file.replace('.xls', '').replace('1983', '').replace('1972', '')
    team_folder = TEAM_MAPPING.get(team_name, team_name)
    
    # Additional mappings for 1972 files
    if team_folder == '197249ers':
        team_folder = '49ers'
    elif team_folder == '1972Giants':
        team_folder = 'Giants'
    elif team_folder == '1972Jets':
        team_folder = 'Jets'
    
    file_path = os.path.join(args.input, excel_file)
    output_folder = os.path.join(args.output, team_folder)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Processing {team_name} -> {team_folder}")
    
    # Extract offense (includes fumble R/L per dice roll from column Q)
    offense_data = extract_offense_chart(file_path)
    offense_path = os.path.join(output_folder, 'offense.csv')
    write_offense_csv(offense_data, offense_path)
    print(f"  Wrote {len(offense_data)} offense rows")
    
    # Extract defense and special teams
    defense_data, special_data = extract_defense_chart(file_path)
    defense_path = os.path.join(output_folder, 'defense.csv')
    write_defense_csv(defense_data, defense_path)
    print(f"  Wrote {len(defense_data)} defense rows")
    
    # Write special teams
    special_path = os.path.join(output_folder, 'special.csv')
    write_special_csv(special_data, special_path)
    print(f"  Wrote {len(special_data)} special teams rows")

def main():
    # Get all Excel files
    if args.team:
        excel_files = [args.team]
    else:
        excel_files = sorted([f for f in os.listdir(args.input) if f.endswith('.xls')])
    
    print(f"Found {len(excel_files)} teams")
    
    for excel_file in excel_files:
        try:
            process_team(excel_file)
        except Exception as e:
            print(f"ERROR processing {excel_file}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()
