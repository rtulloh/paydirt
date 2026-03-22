"""
Tests for AI data persistence (save/load opponent model).
"""
import json
import os
import tempfile

from paydirt.ai_save import get_ai_filepath, save_ai_data, load_ai_data
from paydirt.ai_analysis import OpponentModel


class MockCpuAI:
    """Mock CPU AI for testing."""
    def __init__(self, use_analysis=True):
        self.use_analysis = use_analysis
        self.opponent_model = OpponentModel() if use_analysis else None


class TestGetAIFilepath:
    """Tests for get_ai_filepath function."""
    
    def test_generates_correct_filename(self):
        """Test that filepath is generated correctly from team paths."""
        filepath = get_ai_filepath("seasons/1983/Bears", "seasons/1983/Colts")
        # May include ./ prefix when save_dir is "."
        assert "BEA_COL_ai.json" in filepath
    
    def test_generates_correct_filename_reversed(self):
        """Test that order matters for filename."""
        filepath = get_ai_filepath("seasons/1983/Colts", "seasons/1983/Bears")
        assert "COL_BEA_ai.json" in filepath
    
    def test_includes_save_directory(self):
        """Test that save directory is included in filepath."""
        filepath = get_ai_filepath("seasons/1983/Bears", "seasons/1983/Colts", "/tmp")
        assert filepath == "/tmp/BEA_COL_ai.json"


class TestSaveAIData:
    """Tests for save_ai_data function."""
    
    def test_returns_none_when_no_cpu_ai(self):
        """Test that save returns None when cpu_ai is None."""
        result = save_ai_data(None, "seasons/1983/A", "seasons/1983/B", ".")
        assert result is None
    
    def test_returns_none_when_analysis_disabled(self):
        """Test that save returns None when use_analysis is False."""
        cpu_ai = MockCpuAI(use_analysis=False)
        result = save_ai_data(cpu_ai, "seasons/1983/A", "seasons/1983/B", ".")
        assert result is None
    
    def test_returns_none_when_no_opponent_model(self):
        """Test that save returns None when opponent_model is None."""
        cpu_ai = MockCpuAI(use_analysis=True)
        cpu_ai.opponent_model = None
        result = save_ai_data(cpu_ai, "seasons/1983/A", "seasons/1983/B", ".")
        assert result is None
    
    def test_saves_to_file(self):
        """Test that AI data is saved to file."""
        cpu_ai = MockCpuAI(use_analysis=True)
        cpu_ai.opponent_model.tracker.record_play(1, 10, "RUN", 5)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_ai_data(cpu_ai, "seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            assert result is not None
            assert os.path.exists(result)
            
            # Verify file contents
            with open(result, 'r') as f:
                data = json.load(f)
            
            assert data["version"] == 1
            assert data["metadata"]["away_team_path"] == "seasons/1983/Bears"
            assert data["metadata"]["home_team_path"] == "seasons/1983/Colts"
            assert "opponent_model" in data


class TestLoadAIData:
    """Tests for load_ai_data function."""
    
    def test_returns_none_when_file_not_found(self):
        """Test that load returns None when file doesn't exist."""
        result = load_ai_data("seasons/1983/A", "seasons/1983/B", ".")
        assert result is None
    
    def test_returns_none_when_metadata_mismatch(self):
        """Test that load returns None when team paths don't match."""
        cpu_ai = MockCpuAI(use_analysis=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save with different teams
            save_ai_data(cpu_ai, "seasons/1983/A", "seasons/1983/B", tmpdir)
            
            # Try to load with different teams
            result = load_ai_data("seasons/1983/X", "seasons/1983/Y", tmpdir)
            
            assert result is None
    
    def test_loads_successfully(self):
        """Test that AI data is loaded when metadata matches."""
        cpu_ai = MockCpuAI(use_analysis=True)
        cpu_ai.opponent_model.tracker.record_play(1, 10, "RUN", 5)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save data
            save_ai_data(cpu_ai, "seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            # Load data
            loaded_model = load_ai_data("seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            assert loaded_model is not None
            assert loaded_model.tracker.situation_plays is not None
    
    def test_preserves_tendency_data(self):
        """Test that loaded model has recorded tendency data."""
        cpu_ai = MockCpuAI(use_analysis=True)
        cpu_ai.opponent_model.tracker.record_play(1, 10, "RUN", 5)
        cpu_ai.opponent_model.tracker.record_play(1, 10, "RUN", 3)
        cpu_ai.opponent_model.tracker.record_play(1, 10, "PASS", 10)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_ai_data(cpu_ai, "seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            loaded_model = load_ai_data("seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            # Check tendency data was preserved - just check total plays exist
            tendency = loaded_model.tracker.get_tendency(1, 10)
            assert tendency.total_plays == 3
    
    def test_returns_none_for_version_mismatch(self):
        """Test that load returns None when version doesn't match."""
        cpu_ai = MockCpuAI(use_analysis=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save data normally
            save_ai_data(cpu_ai, "seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            
            # Corrupt version
            filepath = get_ai_filepath("seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            with open(filepath, 'r') as f:
                data = json.load(f)
            data["version"] = 999
            with open(filepath, 'w') as f:
                json.dump(data, f)
            
            # Try to load - should return None
            result = load_ai_data("seasons/1983/Bears", "seasons/1983/Colts", tmpdir)
            assert result is None


class TestRoundTrip:
    """Integration tests for save/load round trip."""
    
    def test_complete_round_trip(self):
        """Test that data survives a complete save/load cycle."""
        cpu_ai = MockCpuAI(use_analysis=True)
        
        # Record some plays
        cpu_ai.opponent_model.tracker.record_play(1, 10, "RUN", 5)
        cpu_ai.opponent_model.tracker.record_play(2, 5, "PASS", 15)
        cpu_ai.opponent_model.tracker.record_play(3, 2, "RUN", 2)
        
        # Set game state
        cpu_ai.opponent_model.score_differential_history = [3, -7, 10]
        cpu_ai.opponent_model.is_protecting_lead = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            filepath = save_ai_data(
                cpu_ai, 
                "seasons/1983/Bears", 
                "seasons/1983/Colts", 
                tmpdir
            )
            assert filepath is not None
            
            # Load
            loaded_model = load_ai_data(
                "seasons/1983/Bears",
                "seasons/1983/Colts",
                tmpdir
            )
            
            assert loaded_model is not None
            
            # Verify game state
            assert loaded_model.score_differential_history == [3, -7, 10]
            assert loaded_model.is_protecting_lead
            
            # Verify tendency data exists
            t1 = loaded_model.tracker.get_tendency(1, 10)
            assert t1.total_plays == 1
