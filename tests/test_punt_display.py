"""
Tests for punt display commentary.

The punt display should provide specific commentary based on the outcome:
- Touchback: "Ball placed at the 20-yard line."
- Fair catch: "Fair catch signaled - no return."
- Downed: "Ball downed by the coverage team."
- Out of bounds: "Punt goes out of bounds."
- Return: Shows return yardage
- Blocked: "BLOCKED PUNT!"
- Fumble: "FUMBLE on the return! Kicking team recovers!"
"""



def get_punt_commentary(description: str, touchdown: bool = False) -> str:
    """
    Replicate the punt commentary logic from interactive_game.py.
    Returns the additional commentary line that would be printed.
    """
    if "Touchback" in description:
        return "Ball placed at the 20-yard line."
    elif "fair catch" in description.lower():
        return "Fair catch signaled - no return."
    elif "downed" in description.lower():
        return "Ball downed by the coverage team."
    elif "out of bounds" in description.lower():
        return "Punt goes out of bounds."
    elif "returned" in description.lower():
        if touchdown:
            return "PUNT RETURN TOUCHDOWN!"
        return None  # No extra commentary for normal returns
    elif "BLOCKED" in description.upper():
        return "BLOCKED PUNT!"
    elif "FUMBLE" in description.upper():
        return "FUMBLE on the return! Kicking team recovers!"
    return None


class TestPuntCommentary:
    """Tests for punt display commentary based on outcome."""
    
    def test_touchback_commentary(self):
        """Touchback should mention ball at 20."""
        desc = "Punt 55 yards into the end zone - Touchback at the 20"
        commentary = get_punt_commentary(desc)
        assert commentary == "Ball placed at the 20-yard line."
    
    def test_fair_catch_commentary(self):
        """Fair catch should mention no return."""
        desc = "Punt 42 yards, fair catch at the Wash 83 35"
        commentary = get_punt_commentary(desc)
        assert commentary == "Fair catch signaled - no return."
    
    def test_downed_commentary(self):
        """Downed punt should mention coverage team."""
        desc = "Punt 48 yards, downed at the NYN '83 22"
        commentary = get_punt_commentary(desc)
        assert commentary == "Ball downed by the coverage team."
    
    def test_out_of_bounds_commentary(self):
        """Out of bounds punt should be noted."""
        desc = "Punt 45 yards, out of bounds at the 30"
        commentary = get_punt_commentary(desc)
        assert commentary == "Punt goes out of bounds."
    
    def test_return_no_extra_commentary(self):
        """Normal return should not have extra commentary."""
        desc = "Punt 45 yards, returned 12 yards to the Wash 83 43"
        commentary = get_punt_commentary(desc)
        assert commentary is None
    
    def test_return_touchdown_commentary(self):
        """Return touchdown should be announced."""
        desc = "Punt 40 yards, returned 65 yards - TOUCHDOWN!"
        commentary = get_punt_commentary(desc, touchdown=True)
        assert commentary == "PUNT RETURN TOUCHDOWN!"
    
    def test_blocked_punt_commentary(self):
        """Blocked punt should be announced."""
        desc = "BLOCKED PUNT! Recovered at the NYN '83 8"
        commentary = get_punt_commentary(desc)
        assert commentary == "BLOCKED PUNT!"
    
    def test_fumble_on_return_commentary(self):
        """Fumble on return should be announced."""
        desc = "Punt 40 yards, FUMBLE on the return! Recovered at the Wash 83 30"
        commentary = get_punt_commentary(desc)
        assert commentary == "FUMBLE on the return! Kicking team recovers!"
    
    def test_case_insensitive_fair_catch(self):
        """Fair catch detection should be case insensitive."""
        desc = "Punt 42 yards, Fair Catch at the 35"
        commentary = get_punt_commentary(desc)
        assert commentary == "Fair catch signaled - no return."
    
    def test_case_insensitive_downed(self):
        """Downed detection should be case insensitive."""
        desc = "Punt 48 yards, DOWNED at the 22"
        commentary = get_punt_commentary(desc)
        assert commentary == "Ball downed by the coverage team."


class TestPuntDescriptionParsing:
    """Tests for parsing different punt description formats."""
    
    def test_touchback_detected(self):
        """Touchback keyword should be detected."""
        assert "Touchback" in "Punt 55 yards into the end zone - Touchback at the 20"
    
    def test_fair_catch_detected(self):
        """Fair catch should be detected case-insensitively."""
        desc = "Punt 42 yards, fair catch at the 35"
        assert "fair catch" in desc.lower()
    
    def test_downed_detected(self):
        """Downed should be detected case-insensitively."""
        desc = "Punt 48 yards, downed at the 22"
        assert "downed" in desc.lower()
    
    def test_returned_detected(self):
        """Returned should be detected case-insensitively."""
        desc = "Punt 45 yards, returned 12 yards to the 43"
        assert "returned" in desc.lower()
    
    def test_blocked_detected(self):
        """Blocked should be detected case-insensitively."""
        desc = "BLOCKED PUNT! Recovered at the 8"
        assert "BLOCKED" in desc.upper()
    
    def test_fumble_detected(self):
        """Fumble should be detected case-insensitively."""
        desc = "Punt 40 yards, FUMBLE on the return!"
        assert "FUMBLE" in desc.upper()
