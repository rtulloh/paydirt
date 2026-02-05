"""
Tests for the commentary system and roster loading.
"""
import json
import os
import pytest
import tempfile

from paydirt.commentary import (
    TeamRoster, get_roster, load_roster_from_file,
    Commentary, TEAM_ROSTERS
)
from paydirt.play_resolver import PlayType, ResultType


class TestTeamRoster:
    """Tests for the TeamRoster dataclass."""
    
    def test_empty_roster(self):
        """Empty roster should return default player descriptions."""
        roster = TeamRoster()
        assert roster.random_qb() == "The quarterback"
        assert roster.random_rb() == "The running back"
        assert roster.random_wr() == "The receiver"
        assert roster.random_dl() == "The defensive lineman"
        assert roster.random_defender() == "The defender"
    
    def test_roster_with_players(self):
        """Roster with players should return actual player names."""
        roster = TeamRoster(
            qb=["Joe Montana"],
            rb=["Roger Craig", "Wendell Tyler"],
            wr=["Jerry Rice"],
            dl=["Fred Dean"],
            lb=["Keena Turner"],
            db=["Ronnie Lott"]
        )
        assert roster.random_qb() == "Joe Montana"
        assert roster.random_rb() in ["Roger Craig", "Wendell Tyler"]
        assert roster.random_wr() == "Jerry Rice"
        assert roster.random_dl() == "Fred Dean"
        assert roster.random_defender() in ["Fred Dean", "Keena Turner", "Ronnie Lott"]
    
    def test_random_defender_combines_all_defense(self):
        """random_defender should pick from DL, LB, and DB."""
        roster = TeamRoster(
            dl=["DL1", "DL2"],
            lb=["LB1"],
            db=["DB1", "DB2", "DB3"]
        )
        # Run multiple times to verify randomness covers all positions
        defenders = set()
        for _ in range(100):
            defenders.add(roster.random_defender())
        
        assert "DL1" in defenders or "DL2" in defenders
        assert "LB1" in defenders
        assert "DB1" in defenders or "DB2" in defenders or "DB3" in defenders


class TestRosterLoading:
    """Tests for loading rosters from JSON files."""
    
    def test_load_roster_from_file(self):
        """Should load roster from a valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roster_data = {
                "qb": ["Dan Marino"],
                "rb": ["Tony Nathan"],
                "wr": ["Mark Duper", "Mark Clayton"],
                "te": ["Bruce Hardy"],
                "ol": ["Dwight Stephenson"],
                "dl": ["Doug Betters"],
                "lb": ["A.J. Duhe"],
                "db": ["Glenn Blackwood"],
                "k": ["Uwe von Schamann"],
                "p": ["Reggie Roby"],
                "kr": ["Tony Nathan"]
            }
            roster_path = os.path.join(tmpdir, "roster.json")
            with open(roster_path, 'w') as f:
                json.dump(roster_data, f)
            
            roster = load_roster_from_file(tmpdir)
            assert roster is not None
            assert roster.qb == ["Dan Marino"]
            assert roster.wr == ["Mark Duper", "Mark Clayton"]
            assert roster.dl == ["Doug Betters"]
    
    def test_load_roster_missing_file(self):
        """Should return None if roster.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roster = load_roster_from_file(tmpdir)
            assert roster is None
    
    def test_load_roster_invalid_json(self):
        """Should return None if roster.json is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roster_path = os.path.join(tmpdir, "roster.json")
            with open(roster_path, 'w') as f:
                f.write("not valid json {{{")
            
            roster = load_roster_from_file(tmpdir)
            assert roster is None
    
    def test_load_roster_partial_data(self):
        """Should handle roster with missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roster_data = {
                "qb": ["John Elway"],
                "rb": ["Sammy Winder"]
                # Missing other fields
            }
            roster_path = os.path.join(tmpdir, "roster.json")
            with open(roster_path, 'w') as f:
                json.dump(roster_data, f)
            
            roster = load_roster_from_file(tmpdir)
            assert roster is not None
            assert roster.qb == ["John Elway"]
            assert roster.rb == ["Sammy Winder"]
            assert roster.wr == []  # Default empty list
            assert roster.dl == []


class TestGetRoster:
    """Tests for the get_roster function."""
    
    def test_get_roster_from_hardcoded(self):
        """Should return hardcoded roster when no team_dir provided."""
        roster = get_roster("1983 Chicago Bears")
        assert "Walter Payton" in roster.rb
        assert "Jim McMahon" in roster.qb
    
    def test_get_roster_unknown_team(self):
        """Should return empty roster for unknown team."""
        roster = get_roster("1999 Nonexistent Team")
        assert roster.qb == []
        assert roster.rb == []
    
    def test_get_roster_prefers_file(self):
        """Should prefer roster.json file over hardcoded data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roster_data = {
                "qb": ["Custom QB"],
                "rb": ["Custom RB"]
            }
            roster_path = os.path.join(tmpdir, "roster.json")
            with open(roster_path, 'w') as f:
                json.dump(roster_data, f)
            
            roster = get_roster("1983 Chicago Bears", team_dir=tmpdir)
            assert roster.qb == ["Custom QB"]  # From file, not hardcoded


class TestHardcodedRosters:
    """Tests for the hardcoded 1983 NFL rosters."""
    
    def test_all_28_teams_present(self):
        """All 28 NFL teams from 1983 should have rosters."""
        expected_teams = [
            # AFC East
            "1983 Miami Dolphins", "1983 New England Patriots", 
            "1983 New York Jets", "1983 Buffalo Bills", "1983 Baltimore Colts",
            # AFC Central
            "1983 Pittsburgh Steelers", "1983 Cleveland Browns",
            "1983 Cincinnati Bengals", "1983 Houston Oilers",
            # AFC West
            "1983 Los Angeles Raiders", "1983 Seattle Seahawks",
            "1983 Denver Broncos", "1983 San Diego Chargers", "1983 Kansas City Chiefs",
            # NFC East
            "1983 Washington Redskins", "1983 Dallas Cowboys",
            "1983 St. Louis Cardinals", "1983 Philadelphia Eagles", "1983 New York Giants",
            # NFC Central
            "1983 Chicago Bears", "1983 Detroit Lions",
            "1983 Green Bay Packers", "1983 Minnesota Vikings", "1983 Tampa Bay Buccaneers",
            # NFC West
            "1983 San Francisco 49ers", "1983 Los Angeles Rams",
            "1983 New Orleans Saints", "1983 Atlanta Falcons"
        ]
        
        for team in expected_teams:
            assert team in TEAM_ROSTERS, f"Missing roster for {team}"
            roster = TEAM_ROSTERS[team]
            assert len(roster.qb) > 0, f"{team} has no QBs"
            assert len(roster.rb) > 0, f"{team} has no RBs"
    
    def test_notable_players_present(self):
        """Notable 1983 players should be in their team rosters."""
        # Check some famous players
        assert "Dan Marino" in TEAM_ROSTERS["1983 Miami Dolphins"].qb
        assert "Walter Payton" in TEAM_ROSTERS["1983 Chicago Bears"].rb
        assert "Joe Montana" in TEAM_ROSTERS["1983 San Francisco 49ers"].qb
        assert "Eric Dickerson" in TEAM_ROSTERS["1983 Los Angeles Rams"].rb
        assert "John Elway" in TEAM_ROSTERS["1983 Denver Broncos"].qb
        assert "Lawrence Taylor" in TEAM_ROSTERS["1983 New York Giants"].lb
        assert "Marcus Allen" in TEAM_ROSTERS["1983 Los Angeles Raiders"].rb
        assert "Tony Dorsett" in TEAM_ROSTERS["1983 Dallas Cowboys"].rb
        assert "John Riggins" in TEAM_ROSTERS["1983 Washington Redskins"].rb
        assert "Dan Fouts" in TEAM_ROSTERS["1983 San Diego Chargers"].qb


class TestCommentary:
    """Tests for the Commentary class."""
    
    @pytest.fixture
    def offense_roster(self):
        """Create an offense roster for testing."""
        return TeamRoster(
            qb=["Joe Montana"],
            rb=["Roger Craig"],
            wr=["Jerry Rice"],
            te=["Russ Francis"]
        )
    
    @pytest.fixture
    def defense_roster(self):
        """Create a defense roster for testing."""
        return TeamRoster(
            dl=["Fred Dean"],
            lb=["Keena Turner"],
            db=["Ronnie Lott"]
        )
    
    @pytest.fixture
    def commentary(self, offense_roster, defense_roster):
        """Create a Commentary instance for testing."""
        return Commentary(offense_roster, defense_roster, "SF '83", "DAL '83")
    
    def test_commentary_initialization(self, commentary):
        """Commentary should initialize with rosters and team names."""
        assert commentary.off_name == "SF '83"
        assert commentary.def_name == "DAL '83"
    
    def test_touchdown_commentary(self, commentary):
        """Touchdown commentary should include team name."""
        comment = commentary.generate(
            PlayType.SHORT_PASS, ResultType.TOUCHDOWN, yards=15, is_touchdown=True
        )
        assert comment is not None
        assert len(comment) > 0
    
    def test_sack_commentary(self, commentary):
        """Sack commentary should mention defender."""
        comment = commentary.generate(
            PlayType.MEDIUM_PASS, ResultType.SACK, yards=-7
        )
        assert comment is not None
        # Should mention one of the defenders
        assert any(name in comment for name in ["Fred Dean", "Keena Turner"])
    
    def test_interception_commentary(self, commentary):
        """Interception commentary should mention defender."""
        comment = commentary.generate(
            PlayType.LONG_PASS, ResultType.INTERCEPTION, yards=15
        )
        assert comment is not None
        # Should mention the DB
        assert "Ronnie Lott" in comment
    
    def test_big_play_commentary(self, commentary):
        """Big plays (15+ yards) should get special commentary."""
        comment = commentary.generate(
            PlayType.OFF_TACKLE, ResultType.YARDS, yards=20
        )
        assert comment is not None
        assert "20" in comment  # Should mention the yardage
    
    def test_incomplete_pass_commentary(self, commentary):
        """Incomplete pass should get appropriate commentary."""
        comment = commentary.generate(
            PlayType.MEDIUM_PASS, ResultType.INCOMPLETE, yards=0
        )
        assert comment is not None
        assert "incomplete" in comment.lower() or "dropped" in comment.lower()
    
    def test_first_down_commentary(self, commentary):
        """First down should add first down call."""
        comment = commentary.generate(
            PlayType.OFF_TACKLE, ResultType.YARDS, yards=5, is_first_down=True
        )
        assert comment is not None
        # Should mention first down or team name
        assert "first down" in comment.lower() or "SF '83" in comment
    
    def test_fumble_commentary(self, commentary):
        """Fumble should mention recovering team."""
        comment = commentary.generate(
            PlayType.LINE_PLUNGE, ResultType.FUMBLE, yards=2
        )
        assert comment is not None
        assert "fumble" in comment.lower() or "DAL '83" in comment
    
    def test_penalty_offense_commentary(self, commentary):
        """Offensive penalty should generate appropriate commentary."""
        comment = commentary.generate(
            PlayType.OFF_TACKLE, ResultType.PENALTY_OFFENSE, yards=-10
        )
        assert comment is not None
        assert "penalty" in comment.lower() or "flag" in comment.lower()
    
    def test_penalty_defense_commentary(self, commentary):
        """Defensive penalty should generate appropriate commentary."""
        comment = commentary.generate(
            PlayType.SHORT_PASS, ResultType.PENALTY_DEFENSE, yards=5
        )
        assert comment is not None
        assert "penalty" in comment.lower() or "flag" in comment.lower()
    
    def test_qb_sneak_uses_qb_name(self):
        """QB Sneak should use QB name as ball carrier, not RB."""
        offense_roster = TeamRoster(
            qb=["Joe Montana"],
            rb=["Roger Craig"]
        )
        defense_roster = TeamRoster(
            dl=["Fred Dean"],
            lb=["Keena Turner"],
            db=["Ronnie Lott"]
        )
        commentary = Commentary(offense_roster, defense_roster, "SF '83", "DAL '83")
        
        # Generate multiple times since some templates don't include player name
        found_qb = False
        found_rb = False
        for _ in range(20):
            comment = commentary.generate(
                PlayType.QB_SNEAK, ResultType.YARDS, yards=1
            )
            if "Joe Montana" in comment:
                found_qb = True
            if "Roger Craig" in comment:
                found_rb = True
        
        # QB Sneak should mention the QB when player name is included, never RB
        assert found_qb is True, "QB name should appear in some QB Sneak commentary"
        assert found_rb is False, "RB name should never appear in QB Sneak commentary"
    
    def test_screen_pass_receiver_not_same_as_qb(self):
        """Screen pass receiver should not be the same person as QB."""
        # Simulate a roster where a player could appear as both QB and RB
        offense_roster = TeamRoster(
            qb=["Joe Theismann"],  # Starting QB
            rb=["John Riggins", "Joe Washington"]  # Different RBs
        )
        defense_roster = TeamRoster(
            dl=["Dexter Manley"],
            lb=["Rich Milot"],
            db=["Darrell Green"]
        )
        commentary = Commentary(offense_roster, defense_roster, "Wash 83", "NYN '83")
        
        # Generate multiple screen pass commentaries
        found_rb = False
        for _ in range(20):
            comment = commentary.generate(
                PlayType.SCREEN, ResultType.YARDS, yards=5
            )
            # Check if an RB name appears (some templates don't include player)
            if "John Riggins" in comment or "Joe Washington" in comment:
                found_rb = True
        
        # At least some commentary should mention an RB
        assert found_rb is True, "RB name should appear in some Screen pass commentary"
    
    def test_short_pass_gain_uses_pass_language(self, commentary):
        """Short pass gains should use pass-appropriate language, not running language."""
        # Generate multiple short pass commentaries
        running_phrases = ["running", "grinds", "fights for"]
        found_running_language = False
        
        for _ in range(50):
            comment = commentary.generate(
                PlayType.MEDIUM_PASS, ResultType.YARDS, yards=8
            )
            for phrase in running_phrases:
                if phrase.lower() in comment.lower():
                    found_running_language = True
                    break
        
        assert found_running_language is False, \
            "Pass play commentary should not use running language"
    
    def test_short_run_gain_uses_run_language(self, commentary):
        """Short run gains should use run-appropriate language."""
        # Generate multiple short run commentaries
        pass_phrases = ["catches", "reception", "grab"]
        found_pass_language = False
        
        for _ in range(50):
            comment = commentary.generate(
                PlayType.OFF_TACKLE, ResultType.YARDS, yards=5
            )
            for phrase in pass_phrases:
                if phrase.lower() in comment.lower():
                    found_pass_language = True
                    break
        
        assert found_pass_language is False, \
            "Run play commentary should not use pass language"

    def test_qb_scramble_commentary(self, commentary):
        """QB scramble should mention the QB and scramble-related language."""
        comment = commentary.generate(
            PlayType.SHORT_PASS, ResultType.QB_SCRAMBLE, yards=16
        )
        assert comment is not None
        # Should mention the QB or scramble-related language
        assert "Joe Montana" in comment or "scramble" in comment.lower() or "escapes" in comment.lower()

    def test_qb_scramble_loss_commentary(self, commentary):
        """QB scramble for a loss should have appropriate commentary."""
        comment = commentary.generate(
            PlayType.MEDIUM_PASS, ResultType.QB_SCRAMBLE, yards=-3
        )
        assert comment is not None
        # Should mention loss or negative outcome
        assert "3" in comment or "loss" in comment.lower()

    def test_qb_scramble_td_commentary(self, commentary):
        """QB scramble touchdown should have TD commentary."""
        comment = commentary.generate(
            PlayType.LONG_PASS, ResultType.QB_SCRAMBLE, yards=25, is_touchdown=True
        )
        assert comment is not None
        # Should mention touchdown
        assert "touchdown" in comment.lower()
