#!/usr/bin/env python3
"""Fix Extra Point column in special.csv files for 1969-1972 era rules.

In 1969-1972, PAT only fails on a roll of 12 (Boxcars).
Since we map 2d6 rolls to chart positions by adding 8:
- Dice 10-19 (rolls 2-11) = Success
- Dice 20 (roll 12) = Failure

This script sets Extra Point = 0 for dice roll 20 in all special.csv files.
"""

import csv
import os
from pathlib import Path


def fix_extra_point_column(base_dir: str, dry_run: bool = True):
    """Set Extra Point value to 0 for dice roll 20 in special.csv files."""
    
    base_path = Path(base_dir)
    updated_count = 0
    
    for team_dir in sorted(base_path.iterdir()):
        if not team_dir.is_dir():
            continue
            
        special_file = team_dir / "special.csv"
        if not special_file.exists():
            continue
        
        # Read the file
        with open(special_file, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        
        # Find and update the row where first column is 20
        updated = False
        for i, row in enumerate(rows):
            if row and row[0].strip() == '20':
                # Extra Point column is index 7 (column 8)
                if len(row) > 7:
                    old_value = row[7]
                    row[7] = '0'
                    updated = True
                    print(f"  {team_dir.name}: dice 20, Extra Point '{old_value}' → '0'")
                break
        
        if updated:
            updated_count += 1
            if not dry_run:
                with open(special_file, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(rows)
    
    action = "Would update" if dry_run else "Updated"
    print(f"\n{action} {updated_count} team files")
    
    if dry_run:
        print("\nRun with --write to actually apply changes")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Extra Point column in special.csv files')
    parser.add_argument('season', help='Season directory (e.g., seasons/1972)')
    parser.add_argument('--write', action='store_true', help='Write changes dry-run (default is)')
    
    args = parser.parse_args()
    
    print(f"Processing: {args.season}")
    fix_extra_point_column(args.season, dry_run=not args.write)


if __name__ == '__main__':
    main()
