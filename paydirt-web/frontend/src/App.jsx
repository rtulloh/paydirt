import { useState, useEffect, useCallback } from 'react'
import { useGameStore } from './store/gameStore'
import { FootballField } from './components/Field/FootballField'
import { Scoreboard } from './components/Scoreboard/Scoreboard'
import { OffensePlays } from './components/Plays/OffensePlays'
import { DefensePlays } from './components/Plays/DefensePlays'
import { CoinToss } from './components/Game/CoinToss'
import { GameOver } from './components/Game/GameOver'
import { Halftime } from './components/Game/Halftime'
import { DiceDisplay } from './components/Dice/DiceDisplay'

const API_BASE = ''

function App() {
  const { gamePhase, setGamePhase } = useGameStore()
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => {
        if (res.ok) return res.json()
        throw new Error('Backend not available')
      })
      .then(() => setBackendStatus('connected'))
      .catch(() => setBackendStatus('disconnected'))
  }, [])

  return (
    <div className="min-h-screen p-2">
      <header className="text-center mb-4">
        <h1 className="text-2xl font-heading font-bold text-white mb-1">
          PAYDIRT
        </h1>
        <p className="text-gray-400 text-sm">Classic Football Board Game</p>
        <div className="mt-1">
          <span className={`inline-block px-2 py-0.5 rounded text-xs ${
            backendStatus === 'connected' 
              ? 'bg-green-600 text-white' 
              : backendStatus === 'disconnected'
              ? 'bg-red-600 text-white'
              : 'bg-yellow-600 text-white'
          }`}>
            Backend: {backendStatus}
          </span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto">
        {gamePhase === 'menu' && (
          <div className="board-panel p-4 text-center">
            <h2 className="text-xl font-heading font-bold mb-4 text-gray-800">
              Welcome to Paydirt
            </h2>
            <button
              onClick={() => setGamePhase('teamSelect')}
              className="play-button text-lg px-6 py-3"
            >
              NEW GAME
            </button>
          </div>
        )}

        {gamePhase === 'teamSelect' && (
          <TeamSelect />
        )}

        {(gamePhase === 'coinToss' || gamePhase === 'playing' || gamePhase === 'halftime' || gamePhase === 'gameOver') && (
          <GameContainer />
        )}
      </main>
    </div>
  )
}

function TeamSelect() {
  const { setGamePhase, setGameId, updateGameState } = useGameStore()
  const [seasons, setSeasons] = useState([])
  const [teams, setTeams] = useState([])
  const [selectedSeason, setSelectedSeason] = useState(null)
  const [playerTeam, setPlayerTeam] = useState(null)
  const [opponentTeam, setOpponentTeam] = useState(null)
  const [playerIsHome, setPlayerIsHome] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/api/seasons`)
      .then(res => res.json())
      .then(data => {
        setSeasons(data.seasons)
        if (data.seasons.length > 0) {
          setSelectedSeason(data.seasons[0])
        }
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load seasons:', err)
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    if (selectedSeason) {
      fetch(`${API_BASE}/api/teams?season=${selectedSeason}`)
        .then(res => res.json())
        .then(data => setTeams(data.teams))
        .catch(err => console.error('Failed to load teams:', err))
    }
  }, [selectedSeason])

  const handleTeamClick = (team) => {
    if (!playerTeam) {
      setPlayerTeam(team)
    } else if (!opponentTeam && team.id !== playerTeam.id) {
      setOpponentTeam(team)
    } else if (playerTeam && team.id === playerTeam.id) {
      setPlayerTeam(null)
    } else if (opponentTeam && team.id === opponentTeam.id) {
      setOpponentTeam(null)
    }
  }

  const handleStartGame = () => {
    if (playerTeam && opponentTeam) {
      fetch(`${API_BASE}/api/game/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          player_team: playerTeam.id,
          season: selectedSeason,
          play_as_home: playerIsHome,
          opponent_team: opponentTeam.id,
        })
      })
        .then(res => res.json())
        .then(data => {
          setGameId(data.game_id)
          updateGameState(data.game_state)
          setGamePhase('coinToss')
        })
        .catch(err => console.error('Failed to start game:', err))
    }
  }

  const swapTeams = () => {
    const tempTeam = playerTeam
    const tempHome = playerIsHome
    setPlayerTeam(opponentTeam)
    setOpponentTeam(tempTeam)
    setPlayerIsHome(!playerIsHome)
  }

  if (loading) {
    return <div className="text-center text-white">Loading...</div>
  }

  const canStart = playerTeam && opponentTeam

  return (
    <div className="board-panel p-6">
      <h2 className="text-2xl font-heading font-bold mb-6 text-center text-gray-800">
        SELECT TEAMS
      </h2>

      <div className="mb-6">
        <h3 className="text-lg font-heading font-bold mb-3 text-gray-700">SEASON</h3>
        <div className="flex gap-4 justify-center">
          {seasons.map(season => (
            <button
              key={season}
              onClick={() => {
                setSelectedSeason(season)
                setPlayerTeam(null)
                setOpponentTeam(null)
              }}
              className={`px-6 py-3 rounded-lg font-bold transition-all ${
                selectedSeason === season
                  ? 'bg-board-bg text-panel-bg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {season}
            </button>
          ))}
        </div>
      </div>

      {canStart && (
        <div className="mb-6 p-4 bg-gray-100 rounded-lg max-w-3xl mx-auto">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 text-center">
              <div className="text-sm font-bold text-green-600 mb-1">YOUR TEAM</div>
              <div className="flex items-center justify-center gap-3">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold"
                  style={{ backgroundColor: playerTeam?.team_color || '#666' }}
                >
                  {playerTeam?.short_name?.slice(0, 2) || '?'}
                </div>
                <div>
                  <div className="font-bold text-gray-800">{playerTeam?.name}</div>
                  <div className="text-sm text-gray-500">{playerTeam?.short_name}</div>
                </div>
              </div>
            </div>

            <button
              onClick={swapTeams}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg font-bold hover:bg-blue-600 transition-all"
            >
              SWAP
            </button>

            <div className="flex-1 text-center">
              <div className="text-sm font-bold text-red-600 mb-1">OPPONENT</div>
              <div className="flex items-center justify-center gap-3">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold"
                  style={{ backgroundColor: opponentTeam?.team_color || '#666' }}
                >
                  {opponentTeam?.short_name?.slice(0, 2) || '?'}
                </div>
                <div>
                  <div className="font-bold text-gray-800">{opponentTeam?.name}</div>
                  <div className="text-sm text-gray-500">{opponentTeam?.short_name}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-300 flex justify-center gap-8">
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-2">PLAY AS</div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPlayerIsHome(true)}
                  className={`px-6 py-2 rounded-lg font-bold ${
                    playerIsHome
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-300 text-gray-700'
                  }`}
                >
                  HOME
                </button>
                <button
                  onClick={() => setPlayerIsHome(false)}
                  className={`px-6 py-2 rounded-lg font-bold ${
                    !playerIsHome
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-300 text-gray-700'
                  }`}
                >
                  AWAY
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-heading font-bold mb-3 text-gray-700 text-center">
          {canStart ? 'TEAMS SELECTED - CLICK TO CHANGE' : 'SELECT YOUR TEAM FIRST, THEN OPPONENT'}
        </h3>
        <div className="grid grid-cols-4 gap-4 max-w-2xl mx-auto">
          {teams.map(team => {
            const isPlayer = playerTeam?.id === team.id
            const isOpponent = opponentTeam?.id === team.id
            return (
              <button
                key={team.id}
                onClick={() => handleTeamClick(team)}
                className={`p-4 rounded-lg border-4 transition-all relative ${
                  isPlayer
                    ? 'border-green-500 bg-green-100'
                    : isOpponent
                    ? 'border-red-500 bg-red-100'
                    : 'border-gray-300 bg-white hover:border-gray-400'
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
                  className="w-12 h-12 mx-auto mb-2 rounded-full flex items-center justify-center text-white font-bold text-lg"
                  style={{ backgroundColor: team.team_color || '#666' }}
                >
                  {team.short_name?.slice(0, 2) || team.id.slice(0, 2)}
                </div>
                <div className="font-bold text-sm text-gray-800">{team.name}</div>
                <div className="text-xs text-gray-500">{team.id}</div>
              </button>
            )
          })}
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={handleStartGame}
          disabled={!canStart}
          className={`px-8 py-3 rounded-lg font-bold text-lg transition-all ${
            canStart
              ? 'bg-green-600 text-white hover:bg-green-700'
              : 'bg-gray-400 text-gray-600 cursor-not-allowed'
          }`}
        >
          START GAME
        </button>
      </div>

      <div className="mt-6 text-center">
        <button
          onClick={() => setGamePhase('menu')}
          className="text-gray-600 hover:text-gray-800"
        >
          Back to Menu
        </button>
      </div>
    </div>
  )
}

function GameContainer() {
  const {
    gameId,
    homeTeam,
    awayTeam,
    homeScore,
    awayScore,
    quarter,
    timeRemaining,
    possession,
    ballPosition,
    down,
    yardsToGo,
    homeTimeouts,
    awayTimeouts,
    playerOffense,
    humanPlaySelected,
    setHumanPlay,
    updateGameState,
    reset,
    setGamePhase,
    gamePhase,
  } = useGameStore()

  const [executing, setExecuting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [cpuPlay, setCpuPlay] = useState(null)
  const [showCpuPlay, setShowCpuPlay] = useState(false)
  const [halftimeShown, setHalftimeShown] = useState(false)
  const [isRolling, setIsRolling] = useState(false)
  const [diceResult, setDiceResult] = useState(null)

  const fetchGameState = useCallback(async () => {
    if (!gameId) return
    try {
      const res = await fetch(`${API_BASE}/api/game/state/${gameId}`)
      if (res.ok) {
        const data = await res.json()
        updateGameState(data)
      }
    } catch (err) {
      console.error('Failed to fetch game state:', err)
    }
  }, [gameId, updateGameState])

  useEffect(() => {
    if (useGameStore.getState().gamePhase === 'playing') {
      fetchGameState()
    }
  }, [fetchGameState])

  const handleCoinTossComplete = async (result) => {
    setGamePhase('playing')
    await fetchGameState()
  }

  const executePlay = async (play) => {
    if (!gameId || executing) return
    
    setExecuting(true)
    setHumanPlay(play)
    setShowCpuPlay(false)
    setCpuPlay(null)
    setLastResult(null)
    setDiceResult(null)
    setIsRolling(false)
    
    try {
      const cpuRes = await fetch(`${API_BASE}/api/game/cpu-play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: play,
        })
      })
      
      if (cpuRes.ok) {
        const cpuData = await cpuRes.json()
        setCpuPlay(cpuData.cpu_play)
      }
      
      await new Promise(resolve => setTimeout(resolve, 300))
      setShowCpuPlay(true)
      
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setIsRolling(true)
      setDiceResult({
        offenseRoll: {
          black: Math.floor(Math.random() * 6) + 1,
          white1: Math.floor(Math.random() * 6) + 1,
          white2: Math.floor(Math.random() * 6) + 1,
        },
        defenseRoll: {
          red: Math.floor(Math.random() * 6) + 1,
          green: Math.floor(Math.random() * 6) + 1,
        },
        result: 0,
      })
      
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const res = await fetch(`${API_BASE}/api/game/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: play,
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        setLastResult(data.result)
        updateGameState(data.game_state)
        setIsRolling(false)
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver')
        } else if (data.result.half_changed && !halftimeShown) {
          setHalftimeShown(true)
          setGamePhase('halftime')
        }
      }
    } catch (err) {
      console.error('Failed to execute play:', err)
    } finally {
      setExecuting(false)
      setHumanPlay(null)
    }
  }

  const handleOffensePlay = (play) => {
    executePlay(play)
  }

  const handleDefensePlay = (play) => {
    executePlay(play)
  }

  const handleHalftimeContinue = () => {
    setGamePhase('playing')
  }

  const handleNewGame = async () => {
    if (gameId) {
      try {
        await fetch(`${API_BASE}/api/game/${gameId}`, { method: 'DELETE' })
      } catch (err) {
        console.error('Failed to delete game:', err)
      }
    }
    reset()
    setHalftimeShown(false)
    setGamePhase('teamSelect')
  }

  const handleReturnToMenu = async () => {
    if (gameId) {
      try {
        await fetch(`${API_BASE}/api/game/${gameId}`, { method: 'DELETE' })
      } catch (err) {
        console.error('Failed to delete game:', err)
      }
    }
    reset()
    setHalftimeShown(false)
  }

  if (gamePhase === 'coinToss') {
    return (
      <CoinToss
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        onComplete={handleCoinTossComplete}
      />
    )
  }

  if (gamePhase === 'halftime') {
    return (
      <Halftime
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        quarter={quarter}
        onContinue={handleHalftimeContinue}
      />
    )
  }

  if (gamePhase === 'gameOver') {
    return (
      <GameOver
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        onNewGame={handleNewGame}
      />
    )
  }

  return (
    <div className="space-y-3">
      <Scoreboard
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        quarter={quarter}
        timeRemaining={timeRemaining}
        down={down}
        yardsToGo={yardsToGo}
        ballPosition={ballPosition}
        possession={possession}
        homeTimeouts={homeTimeouts}
        awayTimeouts={awayTimeouts}
      />

      <FootballField
        ballPosition={ballPosition}
        possession={possession}
        homeEndzoneColor={homeTeam?.team_color || '#8B0000'}
        awayEndzoneColor={awayTeam?.team_color || '#1E3A8A'}
        homeTeamName={homeTeam?.short_name || homeTeam?.abbreviation || 'HOME'}
        awayTeamName={awayTeam?.short_name || awayTeam?.abbreviation || 'AWAY'}
      />

      {(isRolling || diceResult) && (
        <DiceDisplay
          offenseRoll={diceResult?.offenseRoll}
          defenseRoll={diceResult?.defenseRoll}
          result={diceResult?.result}
          isRolling={isRolling}
          onAnimationComplete={() => {}}
        />
      )}

      {lastResult && (
        <div className="board-panel p-3 bg-led-bg">
          <div className="text-center">
            <div className="text-lg font-bold mb-1 text-led-red">
              {lastResult.description}
            </div>
            {lastResult.turnover && (
              <div className="text-yellow-400 font-bold animate-pulse text-sm">
                TURNOVER!
              </div>
            )}
            {lastResult.scoring && (
              <div className="text-green-400 font-bold animate-pulse text-sm">
                SCORE!
              </div>
            )}
            <div className="text-gray-400 text-xs mt-1">
              {lastResult.yards > 0 ? `+${lastResult.yards} yards` : 
               lastResult.yards < 0 ? `${lastResult.yards} yards` : 
               'No gain'}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {playerOffense ? (
          <OffensePlays
            selectedPlay={humanPlaySelected}
            onSelectPlay={handleOffensePlay}
            isHumanTurn={true}
            disabled={executing}
          />
        ) : (
          <DefensePlays
            selectedPlay={humanPlaySelected}
            onSelectPlay={handleDefensePlay}
            isHumanTurn={true}
            disabled={executing}
          />
        )}

        <div className="board-panel">
          <div className="board-panel-header text-center py-1">
            {playerOffense ? 'DEFENSE' : 'OFFENSE'}
          </div>
          <div className="p-3 text-center text-gray-500">
            {executing ? 'Rolling dice...' : 
             showCpuPlay && cpuPlay ? (
               <div>
                 <div className="text-base font-bold mb-1">CPU selected:</div>
                 <div className="text-xl font-bold text-yellow-500">
                   {cpuPlay}
                 </div>
               </div>
             ) :
             playerOffense ? 'CPU is selecting defense...' : 'CPU is selecting offense...'}
          </div>
        </div>
      </div>
      
      <div className="text-center">
        <button
          onClick={handleReturnToMenu}
          className="text-white hover:text-gray-300 text-sm"
        >
          Return to Menu
        </button>
      </div>
    </div>
  )
}

export default App
