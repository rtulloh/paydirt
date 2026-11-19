import { gameFetch } from '../../runtime/gameFetch';
import React, { useState, useEffect, useRef } from 'react';
import { useGameStore } from '../../store/gameStore';
import { API_BASE } from '../../config';

const TeamSelectPhase = ({ onTeamSelected, onBackToMenu }) => {
  const [seasons, setSeasons] = useState([]);
  const [teams, setTeams] = useState([]);
  const [teamSearch, setTeamSearch] = useState('');
  const [playerSeason, setPlayerSeason] = useState(null);
  const [opponentSeason, setOpponentSeason] = useState(null);
  const [activeSide, setActiveSide] = useState('player');
  const selectedSeason = activeSide === 'player' ? playerSeason : opponentSeason;
  const visibleTeams = teams.filter(team => team.name.toLocaleLowerCase().includes(teamSearch.trim().toLocaleLowerCase()));
  const catalogCache = useRef(new Map());

  useEffect(() => { setTeamSearch(''); }, [selectedSeason, activeSide]);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const [playerTeam, setPlayerTeam] = useState(null);
  const [opponentTeam, setOpponentTeam] = useState(null);
  const [playerIsHome, setPlayerIsHome] = useState(true);
  const [difficulty, setDifficulty] = useState('medium');
  const [loading, setLoading] = useState(true);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [seasonRetry, setSeasonRetry] = useState(0);
  const [teamRetry, setTeamRetry] = useState(0);

  const { setGameId, updateGameState, setIsKickoff, setCurrentSeason } = useGameStore.getState();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);
    gameFetch(`${API_BASE}/api/seasons`)
      .then(res => {
        if (!res.ok) throw new Error('Could not load seasons.');
        return res.json();
      })
      .then(data => {
        if (!active) return;
        setSeasons(data.seasons);
        if (data.seasons.length > 0) {
          setPlayerSeason(data.seasons[0]);
          setOpponentSeason(data.seasons[0]);
        } else {
          setTeamsLoading(false);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setLoadError({ kind: 'seasons', message: 'Could not load seasons. Please retry.' });
        setTeamsLoading(false);
        setLoading(false);
      });
    return () => { active = false; };
  }, [seasonRetry]);

  useEffect(() => {
    let active = true;
    if (selectedSeason) {
      setTeams([]);
      setTeamsLoading(true);
      setLoadError(null);
      if (catalogCache.current.has(selectedSeason)) {
        setTeams(catalogCache.current.get(selectedSeason));
        setTeamsLoading(false);
        return () => { active = false; };
      }
      gameFetch(`${API_BASE}/api/teams?season=${encodeURIComponent(selectedSeason)}`)
        .then(res => {
          if (!res.ok) throw new Error('Could not load teams.');
          return res.json();
        })
        .then(data => {
          if (!active) return;
          catalogCache.current.set(selectedSeason, data.teams || []);
          setTeams(data.teams || []);
          setTeamsLoading(false);
        })
        .catch(() => {
          if (!active) return;
          setLoadError({ kind: 'teams', message: `Could not load teams for ${selectedSeason}. Please retry.` });
          setTeamsLoading(false);
        });
    }
    return () => { active = false; };
  }, [selectedSeason, teamRetry]);

  const changeSeason = (side, season) => {
    setActiveSide(side);
    setStartError('');
    if (side === 'player') {
      if (season !== playerSeason) setPlayerTeam(null);
      setPlayerSeason(season);
    } else {
      if (season !== opponentSeason) setOpponentTeam(null);
      setOpponentSeason(season);
    }
  };

  const sameEdition = (team, edition, season) => team?.id === edition?.id && selectedSeason === season;
  const handleTeamClick = team => {
    if (teamsLoading || loadError || starting) return;
    setStartError('');
    if (activeSide === 'player') {
      if (team.id === opponentTeam?.id && playerSeason === opponentSeason) return;
      setPlayerTeam(team);
      setActiveSide('opponent');
    } else {
      if (team.id === playerTeam?.id && playerSeason === opponentSeason) {
        setActiveSide('player');
        return;
      }
      setOpponentTeam(team);
    }
  };
  const canStart = !teamsLoading && !loadError && !starting && playerTeam && opponentTeam
    && !(playerTeam.id === opponentTeam.id && playerSeason === opponentSeason);
  const rulesSeason = playerIsHome ? playerSeason : opponentSeason;
  const swapTeams = () => {
    setPlayerTeam(opponentTeam); setOpponentTeam(playerTeam);
    setPlayerSeason(opponentSeason); setOpponentSeason(playerSeason);
    setStartError('');
  };

  const handleStartGame = () => {
    if (!canStart) return;
    setStarting(true);
    setStartError('');

    gameFetch(`${API_BASE}/api/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_team: playerTeam.id,
        season: rulesSeason,
        player_season: playerSeason,
        opponent_season: opponentSeason,
        play_as_home: playerIsHome,
        opponent_team: opponentTeam.id,
        difficulty: difficulty,
        // End-zone interception returns are always decided in play: the human
        // is asked after the catch, and the CPU uses its situation policy.
        player_end_zone_interception_policy: 'ask',
        opponent_end_zone_interception_policy: 'auto',
        // Retained for older backends; the policy above is authoritative.
        player_attempt_end_zone_interception_returns: false,
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Could not start this game.');
        return data;
      })
      .then(data => {
        setGameId(data.game_id);
        updateGameState(data.game_state);
        setIsKickoff(true);
        setCurrentSeason(rulesSeason);
        onTeamSelected?.({ playerTeam, opponentTeam, playerIsHome, playerSeason, opponentSeason });
      })
      .catch(err => {
        setStartError(err.message || 'Could not start this game. Please retry.');
        setStarting(false);
      });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div role="status" className="text-white text-xl">Loading teams...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">SELECT TEAMS</h1>
          <p className="text-gray-400">Choose your team, then your opponent. Each can use a different chart year.</p>
        </div>

        {seasons.length > 0 && (
          <div className="mb-6 text-center space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="text-white text-left">Your chart year
                <select aria-label="Your chart year" value={playerSeason || ''} onChange={event => changeSeason('player', event.target.value)} className="block w-full bg-gray-800 rounded-lg p-3 mt-1">
                  {seasons.map(season => <option key={season} value={season}>{season}</option>)}
                </select>
              </label>
              <label className="text-white text-left">Opponent chart year
                <select aria-label="Opponent chart year" value={opponentSeason || ''} onChange={event => changeSeason('opponent', event.target.value)} className="block w-full bg-gray-800 rounded-lg p-3 mt-1">
                  {seasons.map(season => <option key={season} value={season}>{season}</option>)}
                </select>
              </label>
            </div>
            <div className="flex gap-3 justify-center">
              <button aria-pressed={activeSide === 'player'} onClick={() => setActiveSide('player')} className="text-white rounded-lg border border-gray-600 p-3">Choose your team</button>
              <button aria-pressed={activeSide === 'opponent'} onClick={() => setActiveSide('opponent')} className="text-white rounded-lg border border-gray-600 p-3">Choose opponent</button>
            </div>
            <div className="inline-flex flex-wrap justify-center items-center gap-4 bg-gray-800 rounded-lg px-6 py-3">
              <span className="font-bold text-gray-300">{activeSide === 'player' ? 'YOUR TEAM' : 'OPPONENT'} YEAR:</span>
              <div className="flex flex-wrap justify-center gap-2">
                {seasons.map((season) => (
                  <button
                    key={season}
                    onClick={() => {
                      changeSeason(activeSide, season);
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
          <label className="block text-gray-300 mb-3">Search by name within year
            <input type="search" aria-label={`Search teams in ${selectedSeason || 'selected year'}`}
              value={teamSearch} onChange={event => setTeamSearch(event.target.value)}
              disabled={teamsLoading || !!loadError}
              className="block w-full bg-gray-800 rounded-lg p-3 mt-1 text-white" />
          </label>
          {!teamsLoading && !loadError && teams.length > 0 && visibleTeams.length === 0 && (
            <p role="status" className="text-center text-gray-300">No matching teams in {selectedSeason}.</p>
          )}
          {teamsLoading && <p role="status" className="text-center text-gray-300">Loading teams...</p>}
          {loadError && (
            <div role="alert" className="text-center text-red-300 mb-4">
              <p>{loadError.message}</p>
              <button className="mt-2 px-4 py-2 bg-gray-700 rounded-lg text-white" onClick={() => {
                if (loadError.kind === 'seasons') setSeasonRetry(value => value + 1);
                else setTeamRetry(value => value + 1);
              }}>Retry</button>
            </div>
          )}
          {!teamsLoading && !loadError && teams.length === 0 && (
            <p className="text-center text-gray-300">No teams available for this season.</p>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {visibleTeams.map(team => {
              const isPlayer = sameEdition(team, playerTeam, playerSeason);
              const isOpponent = sameEdition(team, opponentTeam, opponentSeason);
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

        <div className="mb-6 text-center text-gray-200 space-y-2" aria-live="polite">
          {playerTeam && <p>Your team: {playerSeason} {playerTeam.name}</p>}
          {opponentTeam && <p>Opponent: {opponentSeason} {opponentTeam.name}</p>}
          {playerTeam && opponentTeam && <>
            <p>Playing under {rulesSeason} rules</p>
            <p className="text-gray-400 text-sm">The home team's chart year governs this exhibition.</p>
            <button onClick={swapTeams} disabled={starting} className="text-white border border-gray-600 px-4 py-2 rounded-lg">Swap teams</button>
          </>}
        </div>
        {playerTeam && opponentTeam && (
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

        {startError && <p role="alert" className="text-red-300 text-center mb-4">{startError}</p>}
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
            {starting ? 'STARTING GAME…' : canStart ? 'START GAME' : 'SELECT BOTH TEAMS'}
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
