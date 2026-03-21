import React, { useState, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import { API_BASE } from '../../config';

const TeamSelectPhase = ({ onTeamSelected, onBackToMenu }) => {
  const [seasons, setSeasons] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [playerTeam, setPlayerTeam] = useState(null);
  const [opponentTeam, setOpponentTeam] = useState(null);
  const [playerIsHome, setPlayerIsHome] = useState(true);
  const [difficulty, setDifficulty] = useState('medium');
  const [loading, setLoading] = useState(true);

  const { setGameId, updateGameState, setIsKickoff, setCurrentSeason } = useGameStore.getState();

  useEffect(() => {
    fetch(`${API_BASE}/api/seasons`)
      .then(res => res.json())
      .then(data => {
        setSeasons(data.seasons);
        if (data.seasons.length > 0) {
          setSelectedSeason(data.seasons[0]);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load seasons:', err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (selectedSeason) {
      fetch(`${API_BASE}/api/teams?season=${selectedSeason}`)
        .then(res => res.json())
        .then(data => setTeams(data.teams || []))
        .catch(err => console.error('Failed to load teams:', err));
    }
  }, [selectedSeason]);

  const handleTeamClick = (team) => {
    if (!playerTeam) {
      setPlayerTeam(team);
    } else if (!opponentTeam && team.id !== playerTeam.id) {
      setOpponentTeam(team);
    } else if (playerTeam && team.id === playerTeam.id) {
      setPlayerTeam(null);
    } else if (opponentTeam && team.id === opponentTeam.id) {
      setOpponentTeam(null);
    }
  };

  const canStart = playerTeam && opponentTeam;

  const handleStartGame = () => {
    if (!canStart) return;

    fetch(`${API_BASE}/api/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_team: playerTeam.id,
        season: selectedSeason,
        play_as_home: playerIsHome,
        opponent_team: opponentTeam.id,
        difficulty: difficulty,
      })
    })
      .then(res => res.json())
      .then(data => {
        setGameId(data.game_id);
        updateGameState(data.game_state);
        setIsKickoff(true);
        setCurrentSeason(selectedSeason);
        onTeamSelected({ playerTeam, opponentTeam, playerIsHome });
      })
      .catch(err => {
        console.error('Failed to start game:', err);
      });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading teams...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">SELECT TEAMS</h1>
          <p className="text-gray-400">Click a team to select YOUR team, then click another to select OPPONENT</p>
        </div>

        {seasons.length > 0 && (
          <div className="mb-6 text-center">
            <div className="inline-flex items-center gap-4 bg-gray-800 rounded-lg px-6 py-3">
              <span className="font-bold text-gray-300">SEASON:</span>
              <div className="flex gap-2">
                {seasons.map((season) => (
                  <button
                    key={season}
                    onClick={() => {
                      setSelectedSeason(season);
                      setPlayerTeam(null);
                      setOpponentTeam(null);
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      selectedSeason === season
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {season}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="mb-6">
          <h3 className="text-lg font-bold mb-3 text-gray-300 text-center">
            {selectedSeason ? `TEAMS (${selectedSeason})` : 'TEAMS'}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {teams.map(team => {
              const isPlayer = playerTeam?.id === team.id;
              const isOpponent = opponentTeam?.id === team.id;
              return (
                <button
                  key={team.id}
                  onClick={() => handleTeamClick(team)}
                  className={`p-4 rounded-lg border-4 transition-all relative ${
                    isPlayer
                      ? 'border-green-500 bg-green-900/50'
                      : isOpponent
                      ? 'border-red-500 bg-red-900/50'
                      : 'border-gray-600 bg-gray-800 hover:border-gray-400'
                  }`}
                >
                  {isPlayer && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-green-500 text-white text-xs px-2 py-1 rounded font-bold">
                      YOUR TEAM
                    </div>
                  )}
                  {isOpponent && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-red-500 text-white text-xs px-2 py-1 rounded font-bold">
                      OPPONENT
                    </div>
                  )}
                  <div
                    className="w-16 h-16 mx-auto mb-2 rounded-full flex items-center justify-center text-white font-bold text-xl"
                    style={{ backgroundColor: team.team_color || '#666' }}
                  >
                    {team.short_name?.slice(0, 2) || team.id.slice(0, 2)}
                  </div>
                  <div className="font-bold text-sm text-white">{team.name}</div>
                  <div className="text-xs text-gray-400">{team.short_name}</div>
                </button>
              );
            })}
          </div>
        </div>

        {canStart && (
          <div className="mb-6 text-center">
            <div className="flex flex-col items-center gap-4 bg-gray-800 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-4">
                <span className="font-bold text-gray-300">PLAY AS:</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPlayerIsHome(true)}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      playerIsHome
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    HOME
                  </button>
                  <button
                    onClick={() => setPlayerIsHome(false)}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      !playerIsHome
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    AWAY
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className="font-bold text-gray-300">DIFFICULTY:</span>
                <div className="flex gap-2">
                  {['easy', 'medium', 'hard'].map((diff) => (
                    <button
                      key={diff}
                      onClick={() => setDifficulty(diff)}
                      className={`px-4 py-2 rounded-lg font-medium transition-all capitalize ${
                        difficulty === diff
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {diff}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="text-center">
          <button
            onClick={handleStartGame}
            disabled={!canStart}
            className={`px-8 py-4 rounded-lg font-bold text-xl transition-all ${
              canStart
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-600 text-gray-400 cursor-not-allowed'
            }`}
          >
            {canStart ? 'START GAME' : 'SELECT BOTH TEAMS'}
          </button>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={onBackToMenu}
            className="text-gray-400 hover:text-white transition-colors"
          >
            Back to Menu
          </button>
        </div>
      </div>
    </div>
  );
};

export default TeamSelectPhase;