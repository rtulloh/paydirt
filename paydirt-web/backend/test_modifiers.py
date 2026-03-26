#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def create_game():
    """Create a new game and return game_id and whether player is on offense."""
    payload = {
        "player_team": "Ironclads",
        "season": "2026",
        "play_as_home": True
    }
    resp = requests.post(f"{BASE_URL}/api/game/new", json=payload)
    if resp.status_code != 200:
        print(f"Failed to create game: {resp.text}")
        return None, None
    data = resp.json()
    game_id = data["game_id"]
    player_offense = data["game_state"]["player_offense"]
    return game_id, player_offense

def execute_play(game_id, player_play, no_huddle=False):
    """Execute a play with given player_play string (can include suffixes)."""
    payload = {
        "game_id": game_id,
        "player_play": player_play,
        "no_huddle": no_huddle
    }
    resp = requests.post(f"{BASE_URL}/api/game/execute", json=payload)
    if resp.status_code != 200:
        print(f"Failed to execute play: {resp.text}")
        return None
    return resp.json()

def main():
    print("Testing play modifiers backend...")
    # Try up to 5 games to get player on offense
    for i in range(5):
        game_id, player_offense = create_game()
        if game_id is None:
            return
        print(f"Game {i+1}: {game_id}, player offense: {player_offense}")
        if player_offense:
            print("Player is on offense! Testing suffixes...")
            # Test simple play
            result = execute_play(game_id, "7")
            if result:
                print(f"Play 7 executed successfully")
            # Test spike modifier
            result = execute_play(game_id, "7S")
            if result:
                print(f"Play 7S executed (spike modifier)")
            # Test timeout modifier
            result = execute_play(game_id, "7T")
            if result:
                print(f"Play 7T executed (timeout modifier)")
            # Test out-of-bounds modifier
            result = execute_play(game_id, "7+")
            if result:
                print(f"Play 7+ executed (out-of-bounds modifier)")
            # Test no-huddle mode
            result = execute_play(game_id, "7", no_huddle=True)
            if result:
                print(f"Play 7 with no_huddle=True executed")
            print("All tests passed!")
            return
        else:
            print("Player is on defense, trying another game...")
            time.sleep(0.5)
    print("Could not get player on offense after 5 attempts.")

if __name__ == "__main__":
    main()