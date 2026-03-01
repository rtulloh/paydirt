import pytest
from pathlib import Path
from paydirt.chart_loader import load_team_chart
from paydirt.game_engine import PaydirtGameEngine

@pytest.fixture
def ironclads_team():
    team_dir = str(Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads"))
    return load_team_chart(team_dir)

@pytest.fixture
def thunderhawks_team():
    team_dir = str(Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks"))
    return load_team_chart(team_dir)


def test_ironclads_metadata(ironclads_team):
    assert ironclads_team.peripheral.team_name == "Ironclads"
    assert ironclads_team.peripheral.short_name == "HBI"
    assert ironclads_team.peripheral.year == 2026
    assert ironclads_team.peripheral.team_nickname == "Ironclads"


def test_thunderhawks_metadata(thunderhawks_team):
    assert thunderhawks_team.peripheral.team_name == "Thunderhawks"
    assert thunderhawks_team.peripheral.short_name == "MCT"
    assert thunderhawks_team.peripheral.year == 2026
    assert thunderhawks_team.peripheral.team_nickname == "Thunderhawks"


def test_ironclads_roster(ironclads_team):
    # Roster is loaded separately from roster.json
    roster_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads/roster.json")
    assert roster_file.exists()
    
    import json
    with open(roster_file) as f:
        roster = json.load(f)
    
    assert roster["qb"] == ["Jim McMahon"]
    assert roster["rb"] == ["Walter Payton", "Matt Suhey"]
    assert roster["wr"] == ["Willie Gault", "Dennis McKinnon", "Alvin Garrett", "Lemuel Stinson"]


def test_thunderhawks_roster(thunderhawks_team):
    roster_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks/roster.json")
    assert roster_file.exists()
    
    import json
    with open(roster_file) as f:
        roster = json.load(f)
    
    assert roster["qb"] == ["Joe Montana"]
    assert roster["rb"] == ["Roger Craig", "Lenvil Elliott"]
    assert roster["wr"] == ["Freddie Solomon", "Dwight Clark", "Ricky Patton", "Terrell Buckley"]


def test_ironclads_offense_csv_exists():
    offense_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads/offense.csv")
    assert offense_file.exists()
    with open(offense_file) as f:
        content = f.read()
        assert "BLACK" in content


def test_thunderhawks_offense_csv_exists():
    offense_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks/offense.csv")
    assert offense_file.exists()
    with open(offense_file) as f:
        content = f.read()
        assert "BLACK" in content


def test_ironclads_black_results_in_offense():
    offense_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads/offense.csv")
    with open(offense_file) as f:
        content = f.read()
        
    # Check that BLACK results are properly placed for incomplete passes
    # Looking at the structure, BLACK should appear in passing columns where incomplete passes occur
    lines = content.split('\n')
    # Line 15 should have BLACK results for incomplete passes
    line15 = lines[14] if len(lines) > 14 else ""
    assert "BLACK" in line15
    
    # Line 26 should also have BLACK results
    line26 = lines[25] if len(lines) > 25 else ""
    assert "BLACK" in line26


def test_thunderhawks_black_results_in_offense():
    offense_file = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks/offense.csv")
    with open(offense_file) as f:
        content = f.read()
        
    lines = content.split('\n')
    # Check BLACK results placement - line starting with "22" has BLACK
    line_with_black = lines[13] if len(lines) > 13 else ""
    assert "BLACK" in line_with_black


def test_sample_teams_can_be_loaded():
    ironclads_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads")
    thunderhawks_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks")
    
    assert ironclads_dir.exists()
    assert thunderhawks_dir.exists()
    
    # Test that team charts can be loaded
    ironclads_team = load_team_chart(ironclads_dir)
    thunderhawks_team = load_team_chart(thunderhawks_dir)
    
    assert ironclads_team is not None
    assert thunderhawks_team is not None


def test_game_engine_with_sample_teams():
    ironclads_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads")
    thunderhawks_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks")
    
    ironclads_team = load_team_chart(ironclads_dir)
    thunderhawks_team = load_team_chart(thunderhawks_dir)
    
    # Test that game engine can be created with these teams
    try:
        game = PaydirtGameEngine(ironclads_team, thunderhawks_team)
        assert game is not None
    except Exception as e:
        pytest.fail(f"Failed to create game engine with sample teams: {e}")


def test_team_metadata_consistency():
    ironclads_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Ironclads")
    thunderhawks_dir = Path("/Users/rtulloh/Downloads/paydirt/seasons/2026/Thunderhawks")
    
    ironclads_team = load_team_chart(ironclads_dir)
    thunderhawks_team = load_team_chart(thunderhawks_dir)
    
    # Test that metadata is properly loaded and accessible
    assert hasattr(ironclads_team, 'peripheral')
    assert hasattr(thunderhawks_team, 'peripheral')
    assert hasattr(ironclads_team, 'offense')
    assert hasattr(thunderhawks_team, 'offense')
    assert hasattr(ironclads_team, 'defense')
    assert hasattr(thunderhawks_team, 'defense')
    assert hasattr(ironclads_team, 'special_teams')
    assert hasattr(thunderhawks_team, 'special_teams')
    assert hasattr(ironclads_team, 'team_dir')
    assert hasattr(thunderhawks_team, 'team_dir')
    
    # Test that peripheral data has expected attributes
    assert hasattr(ironclads_team.peripheral, 'team_name')
    assert hasattr(ironclads_team.peripheral, 'short_name')
    assert hasattr(ironclads_team.peripheral, 'year')
    assert hasattr(ironclads_team.peripheral, 'team_nickname')
    
    assert hasattr(thunderhawks_team.peripheral, 'team_name')
    assert hasattr(thunderhawks_team.peripheral, 'short_name')
    assert hasattr(thunderhawks_team.peripheral, 'year')
    assert hasattr(thunderhawks_team.peripheral, 'team_nickname')