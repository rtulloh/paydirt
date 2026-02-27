from paydirt.models import Team, GameState
from paydirt.game import PaydirtGame

test_team = Team(name="Test", abbreviation="TEST")
print("Testing GameState structure...")
print("GameState attributes:", dir(GameState))

print("\nCreating PaydirtGame...")
game = PaydirtGame(test_team, test_team)
print("PaydirtGame state attributes:", dir(game.state))
print("PaydirtGame state has home_stats:", hasattr(game.state, 'home_stats'))
print("PaydirtGame state has away_stats:", hasattr(game.state, 'away_stats'))