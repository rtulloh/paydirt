import { useState, useEffect, useCallback, useRef } from 'react'
import { useGameStore } from './store/gameStore'
import { FootballField } from './components/Field/FootballField'
import { Scoreboard } from './components/Scoreboard/Scoreboard'
import { OffensePlays } from './components/Plays/OffensePlays'
import { DefensePlays } from './components/Plays/DefensePlays'
import { CoinToss } from './components/Game/CoinToss'
import { GameOver } from './components/Game/GameOver'
import { Halftime } from './components/Game/Halftime'
import { DiceDisplay } from './components/Dice/DiceDisplay'
import { PlayLog, logPlay } from './components/PlayLog/PlayLog'
import { saveGame, loadGame, getSavedGameInfo, hasSavedGame, deleteSavedGame } from './utils/saveGame'

const API_BASE = ''

const BLACK_DIE = [1, 1, 2, 2, 3, 3]
const WHITE_DIE = [0, 1, 2, 3, 4, 5]
const RED_DIE = [1, 1, 1, 2, 2, 3]
const GREEN_DIE = [0, 0, 0, 0, 1, 2]

const randomFrom = (arr) => arr[Math.floor(Math.random() * arr.length)]

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

        {(gamePhase === 'coinToss' || gamePhase === 'kickoff' || gamePhase === 'playing' || gamePhase === 'halftime' || gamePhase === 'gameOver') && (
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
  const [difficulty, setDifficulty] = useState('medium')
  const [loading, setLoading] = useState(true)
  const [savedGameInfo, setSavedGameInfo] = useState(null)

  useEffect(() => {
    setSavedGameInfo(getSavedGameInfo())
  }, [])

  const handleLoadGame = async () => {
    const saved = loadGame()
    if (!saved || !saved.gameState) {
      alert('No saved game found')
      return
    }
    
    const { gameState } = saved
    
    if (!gameState.humanTeamId) {
      alert('Saved game is missing humanTeamId. Please start a new game.')
      deleteSavedGame()
      return
    }
    
    if (!gameState.cpuTeamId) {
      alert('Saved game is missing cpuTeamId. Please start a new game.')
      deleteSavedGame()
      return
    }
    
    // Create a new game with the saved teams
    const requestBody = { 
      player_team: gameState.humanTeamId,
      season: '2026',
      play_as_home: gameState.homeTeam?.id === gameState.humanTeamId,
      opponent_team: gameState.cpuTeamId,
    }
    
    fetch(`${API_BASE}/api/game/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    })
      .then(res => {
        if (!res.ok) {
          return res.text().then(text => {
            throw new Error(`Server error: ${res.status} - ${text}`)
          })
        }
        return res.json()
      })
      .then(data => {
        setGameId(data.game_id)
        
        // Update with saved game state (minus what's overridden by new game)
        updateGameState({
          ...data.game_state,
          homeScore: gameState.homeScore,
          awayScore: gameState.awayScore,
          quarter: gameState.quarter,
          time_remaining: gameState.timeRemaining,
          possession: gameState.possession,
          ball_position: gameState.ballPosition,
          down: gameState.down,
          yards_to_go: gameState.yardsToGo,
          home_timeouts: gameState.homeTimeouts,
          away_timeouts: gameState.awayTimeouts,
          human_plays_offense: gameState.humanPlaysOffense,
        })
        
        // Restore play log
        if (gameState.playLog && Array.isArray(gameState.playLog)) {
          setPlayLog(gameState.playLog)
        }
        
        setGamePhase('playing')
        deleteSavedGame()
      })
      .catch(err => {
        console.error('Failed to load game:', err)
        alert('Failed to load game: ' + err.message)
      })
  }

  const handleDeleteSavedGame = () => {
    deleteSavedGame()
    setSavedGameInfo(null)
  }

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
          difficulty: difficulty,
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

      {savedGameInfo && (
        <div className="mb-6 p-4 bg-blue-100 border-2 border-blue-400 rounded-lg">
          <div className="flex justify-between items-center">
            <div>
              <div className="text-sm font-bold text-blue-800 mb-1">SAVED GAME</div>
              <div className="text-sm text-blue-700">
                {savedGameInfo.homeTeam} {savedGameInfo.homeScore} - {savedGameInfo.awayTeam} {savedGameInfo.awayScore}
                <span className="ml-2">Q{savedGameInfo.quarter}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleLoadGame}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700"
              >
                Load
              </button>
              <button
                onClick={handleDeleteSavedGame}
                className="px-4 py-2 bg-gray-400 text-white rounded-lg font-bold hover:bg-gray-500"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

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

      {canStart && (
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-4 bg-gray-100 rounded-lg px-6 py-3">
            <span className="font-bold text-gray-700">CPU DIFFICULTY:</span>
            <div className="flex gap-2">
              <button
                onClick={() => setDifficulty('easy')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  difficulty === 'easy'
                    ? 'bg-green-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-200'
                }`}
              >
                Easy
              </button>
              <button
                onClick={() => setDifficulty('medium')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  difficulty === 'medium'
                    ? 'bg-yellow-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-200'
                }`}
              >
                Medium
              </button>
              <button
                onClick={() => setDifficulty('hard')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  difficulty === 'hard'
                    ? 'bg-red-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-200'
                }`}
              >
                Hard
              </button>
            </div>
          </div>
        </div>
      )}

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
    cpuFourthDownDecision,
    setCpuFourthDownDecision,
    clearCpuFourthDownDecision,
  } = useGameStore()

  const [executing, setExecuting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [cpuPlay, setCpuPlay] = useState(null)
  const [showCpuPlay, setShowCpuPlay] = useState(false)
  const [halftimeShown, setHalftimeShown] = useState(false)
  const [isRolling, setIsRolling] = useState(false)
  const [diceResult, setDiceResult] = useState(null)
  const [playLog, setPlayLog] = useState([])
  const [showSaveConfirm, setShowSaveConfirm] = useState(false)
  const [showCpuDecision, setShowCpuDecision] = useState(false)
  const [cpuDecisionPending, setCpuDecisionPending] = useState(false)
  const [pendingDefensePlay, setPendingDefensePlay] = useState(null)
  const [showPatChoice, setShowPatChoice] = useState(false)
  const [patResult, setPatResult] = useState(null)
  const [pendingKickoff, setPendingKickoff] = useState(false)
  const [canGoForTwo, setCanGoForTwo] = useState(false)
  const [cpuShouldGoForTwo, setCpuShouldGoForTwo] = useState(false)
  const [showPenaltyChoice, setShowPenaltyChoice] = useState(false)
  const [pendingPenaltyData, setPendingPenaltyData] = useState(null)

  const handleSaveGame = () => {
    const state = useGameStore.getState()
    saveGame({
      gameId: state.gameId,
      homeTeam: state.homeTeam,
      awayTeam: state.awayTeam,
      homeScore: state.homeScore,
      awayScore: state.awayScore,
      quarter: state.quarter,
      timeRemaining: state.timeRemaining,
      possession: state.possession,
      ballPosition: state.ballPosition,
      down: state.down,
      yardsToGo: state.yardsToGo,
      homeTimeouts: state.homeTimeouts,
      awayTimeouts: state.awayTimeouts,
      humanPlaysOffense: state.humanPlaysOffense,
      humanTeamId: state.humanTeamId,
      cpuTeamId: state.cpuTeamId,
      playLog: playLog,
    })
    setShowSaveConfirm(true)
    setTimeout(() => setShowSaveConfirm(false), 2000)
  }

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

  useEffect(() => {
    const handleBeforeUnload = () => {
      const state = useGameStore.getState()
      if (state.gameId && state.gamePhase === 'playing') {
        try {
          saveGame({
            gameId: state.gameId,
            homeTeam: state.homeTeam,
            awayTeam: state.awayTeam,
            homeScore: state.homeScore,
            awayScore: state.awayScore,
            quarter: state.quarter,
            timeRemaining: state.timeRemaining,
            possession: state.possession,
            ballPosition: state.ballPosition,
            down: state.down,
            yardsToGo: state.yardsToGo,
            homeTimeouts: state.homeTimeouts,
            awayTimeouts: state.awayTimeouts,
            playerOffense: state.playerOffense,
            playerTeamId: state.homeTeam?.id,
            cpuTeamId: state.awayTeam?.id,
          })
        } catch (e) {
          console.error('Auto-save failed:', e)
        }
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [])

  const handleCoinTossComplete = async (coinData) => {
    // coinData contains: { coinResult, playerCall, playerWonToss, playerReceives }
    // Send the result to the backend to set up possession
    try {
      const res = await fetch(`${API_BASE}/api/game/coin-toss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_won: coinData.playerWonToss,
          player_kicks: !coinData.playerReceives,
          human_plays_offense: coinData.playerReceives,  // Player is on offense if they chose to receive
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        // Update game state with new possession and humanPlaysOffense
        updateGameState({
          possession: data.possession,
          human_plays_offense: coinData.playerReceives,
          human_is_home: useGameStore.getState().humanIsHome,
          home_score: useGameStore.getState().homeScore,
          away_score: useGameStore.getState().awayScore,
          quarter: 1,
          time_remaining: 900,
          ball_position: 35,
          down: 1,
          yards_to_go: 10,
          game_over: false,
          home_timeouts: 3,
          away_timeouts: 3,
        })
      }
    } catch (err) {
      console.error('Failed to process coin toss:', err)
    }
    
    // Trigger kickoff
    setGamePhase('kickoff')
  }

  const executePlay = async (play) => {
    if (!gameId || executing) return
    
    if (!playerOffense && down === 4 && !cpuFourthDownDecision && !cpuDecisionPending) {
      await handleCpuFourthDownDecision()
      return
    }
    
    if (cpuFourthDownDecision && cpuFourthDownDecision.decision === 'go_for_it') {
      await executeCpuSpecialPlay(cpuFourthDownDecision, play)
      return
    }
    
    setExecuting(true)
    setHumanPlay(play)
    setShowCpuPlay(false)
    setCpuPlay(null)
    setLastResult(null)
    setDiceResult(null)
    setIsRolling(false)
    
    let cpuPlayValue = null
    
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
        cpuPlayValue = cpuData.cpu_play
        setCpuPlay(cpuData.cpu_play)
      }
      
      await new Promise(resolve => setTimeout(resolve, 300))
      setShowCpuPlay(true)
      
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setIsRolling(true)
      setDiceResult({
        offenseRoll: {
          black: randomFrom(BLACK_DIE),
          white1: randomFrom(WHITE_DIE),
          white2: randomFrom(WHITE_DIE),
        },
        defenseRoll: {
          red: randomFrom(RED_DIE),
          green: randomFrom(GREEN_DIE),
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
          cpu_play: cpuPlayValue,
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        setLastResult(data.result)
        updateGameState(data.game_state)
        setIsRolling(false)
        
        const scoreChange = data.result.scoring ? 
          `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}` : null
        const offenseTeam = playerOffense ? 
          (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME') : 
          (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY')
        const defenseTeam = playerOffense ? 
          (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY') : 
          (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME')
        
        const logEntry = logPlay({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: data.game_state.down,
          yardsToGo: data.game_state.yards_to_go,
          ballPosition: data.game_state.ball_position,
          offenseTeam,
          defenseTeam,
          playerTeam: playerOffense ? offenseTeam : defenseTeam,
          offensePlay: playerOffense ? play : cpuPlayValue,
          defensePlay: playerOffense ? cpuPlayValue : play,
          description: data.result.description,
          yards: data.result.yards,
          scoreChange,
          turnover: data.result.turnover,
        })
        setPlayLog(prev => [...prev, logEntry])
        
        if (data.result.pending_penalty_decision && data.result.penalty_choice) {
          setPendingPenaltyData(data.result)
          setShowPenaltyChoice(true)
          setExecuting(false)
          setHumanPlay(null)
          return
        }
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver')
        } else if (data.result.half_changed && !halftimeShown) {
          setHalftimeShown(true)
          setGamePhase('halftime')
        } else if (data.result.touchdown) {
          const patRes = await fetch(`${API_BASE}/api/game/pat-choice/${gameId}`)
          if (patRes.ok) {
            const patData = await patRes.json()
            setCanGoForTwo(patData.can_go_for_two)
            setCpuShouldGoForTwo(patData.cpu_should_go_for_two)
            
            if (patData.scoring_team_is_player) {
              setShowPatChoice(true)
            } else {
              if (patData.cpu_should_go_for_two && patData.can_go_for_two) {
                await handleCpuTwoPoint()
              } else {
                await handleCpuPat()
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to execute play:', err)
    } finally {
      if (!showPenaltyChoice) {
        setExecuting(false)
        setHumanPlay(null)
      }
    }
  }

  const handlePenaltyDecision = async (acceptPenalty, penaltyIndex = 0) => {
    setShowPenaltyChoice(false)
    setExecuting(true)
    
    try {
      const res = await fetch(`${API_BASE}/api/game/penalty-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          penalty_index: penaltyIndex,
          accept_penalty: acceptPenalty,
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        setLastResult(data.result)
        updateGameState(data.game_state)
        
        const logEntry = logPlay({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: data.game_state.down,
          yardsToGo: data.game_state.yards_to_go,
          ballPosition: data.game_state.ball_position,
          offenseTeam: playerOffense ? 
            (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME') : 
            (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY'),
          defenseTeam: playerOffense ? 
            (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY') : 
            (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME'),
          playerTeam: playerOffense ? 
            (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME') : 
            (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY'),
          offensePlay: '-',
          defensePlay: '-',
          description: data.result.description,
          yards: data.result.yards,
          scoreChange: data.result.scoring ? 
            `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}` : null,
          turnover: data.result.turnover,
        })
        setPlayLog(prev => [...prev, logEntry])
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver')
        } else if (data.result.touchdown) {
          const patRes = await fetch(`${API_BASE}/api/game/pat-choice/${gameId}`)
          if (patRes.ok) {
            const patData = await patRes.json()
            setCanGoForTwo(patData.can_go_for_two)
            setCpuShouldGoForTwo(patData.cpu_should_go_for_two)
            
            if (patData.scoring_team_is_player) {
              setShowPatChoice(true)
            } else {
              if (patData.cpu_should_go_for_two && patData.can_go_for_two) {
                await handleCpuTwoPoint()
              } else {
                await handleCpuPat()
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to apply penalty decision:', err)
    } finally {
      setPendingPenaltyData(null)
      setExecuting(false)
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

  const isCpuOffenseFourthDown = () => {
    return !playerOffense && down === 4
  }

  const executeCpuSpecialPlay = async (cpuDecision, defensePlay = 'A') => {
    if (!gameId || executing) return
    
    setExecuting(true)
    setCpuPlay(cpuDecision.play)
    setShowCpuPlay(true)
    setCpuDecisionPending(false)
    setShowCpuDecision(false)
    setLastResult(null)
    setDiceResult(null)
    setIsRolling(false)
    setPendingDefensePlay(null)
    
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setIsRolling(true)
      setDiceResult({
        offenseRoll: {
          black: randomFrom(BLACK_DIE),
          white1: randomFrom(WHITE_DIE),
          white2: randomFrom(WHITE_DIE),
        },
        defenseRoll: {
          red: randomFrom(RED_DIE),
          green: randomFrom(GREEN_DIE),
        },
        result: 0,
      })
      
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const res = await fetch(`${API_BASE}/api/game/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: defensePlay,
          cpu_play: cpuDecision.play,
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        setLastResult(data.result)
        updateGameState(data.game_state)
        setIsRolling(false)
        
        const scoreChange = data.result.scoring ? 
          `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}` : null
        const offenseTeam = playerOffense ? 
          (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME') : 
          (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY')
        const defenseTeam = playerOffense ? 
          (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY') : 
          (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME')
        
        const logEntry = logPlay({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: data.game_state.down,
          yardsToGo: data.game_state.yards_to_go,
          ballPosition: data.game_state.ball_position,
          offenseTeam,
          defenseTeam,
          playerTeam: playerOffense ? offenseTeam : defenseTeam,
          offensePlay: cpuDecision.play,
          defensePlay: defensePlay,
          description: data.result.description,
          yards: data.result.yards,
          scoreChange,
          turnover: data.result.turnover,
        })
        setPlayLog(prev => [...prev, logEntry])
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver')
        } else if (data.result.half_changed && !halftimeShown) {
          setHalftimeShown(true)
          setGamePhase('halftime')
        } else if (data.result.touchdown) {
          const patRes = await fetch(`${API_BASE}/api/game/pat-choice/${gameId}`)
          if (patRes.ok) {
            const patData = await patRes.json()
            setCanGoForTwo(patData.can_go_for_two)
            setCpuShouldGoForTwo(patData.cpu_should_go_for_two)
            
            if (patData.scoring_team_is_player) {
              setShowPatChoice(true)
            } else {
              if (patData.cpu_should_go_for_two && patData.can_go_for_two) {
                await handleCpuTwoPoint()
              } else {
                await handleCpuPat()
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to execute CPU special play:', err)
    } finally {
      setExecuting(false)
      clearCpuFourthDownDecision()
    }
  }

  const handleCpuFourthDownDecision = async () => {
    console.log('handleCpuFourthDownDecision called', { gameId, cpuDecisionPending, playerOffense, down })
    if (!gameId) {
      console.log('No gameId')
      return
    }
    if (cpuDecisionPending) {
      console.log('Already pending')
      return
    }
    
    setCpuDecisionPending(true)
    
    try {
      const res = await fetch(`${API_BASE}/api/game/cpu-4th-down-decision/${gameId}`)
      console.log('API response status:', res.status)
      if (res.ok) {
        const data = await res.json()
        console.log('API response data:', data)
        
        if (data.decision === 'none') {
          console.log('Decision is none')
          setCpuDecisionPending(false)
          return
        }
        
        setCpuFourthDownDecision(data)
        setShowCpuDecision(true)
        
        await new Promise(resolve => setTimeout(resolve, 2500))
        
        if (data.decision !== 'go_for_it') {
          await executeCpuSpecialPlay(data)
        } else {
          setShowCpuDecision(false)
          setCpuDecisionPending(false)
        }
      } else {
        console.error('API error:', res.status)
      }
    } catch (err) {
      console.error('Failed to get CPU 4th down decision:', err)
      setCpuDecisionPending(false)
    }
  }

  const handlePatKick = async () => {
    setShowPatChoice(false)
    try {
      const res = await fetch(`${API_BASE}/api/game/extra-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: 'K',
        })
      })
      if (res.ok) {
        const data = await res.json()
        setPatResult({
          type: 'kick',
          success: data.success,
          description: data.description,
        })
        updateGameState({
          ...useGameStore.getState(),
          homeScore: data.new_score_home,
          awayScore: data.new_score_away,
        })
        await new Promise(r => setTimeout(r, 2000))
        setPatResult(null)
        // Trigger kickoff
        await handleKickoff()
      }
    } catch (err) {
      console.error('Failed to attempt extra point:', err)
    }
  }

  const handlePatTwoPoint = async (offensePlay) => {
    setShowPatChoice(false)
    try {
      const res = await fetch(`${API_BASE}/api/game/two-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          offense_play: offensePlay || '1',
          defense_play: 'A',
        })
      })
      if (res.ok) {
        const data = await res.json()
        setPatResult({
          type: 'two_point',
          success: data.result.description.includes('GOOD'),
          description: data.result.description,
        })
        updateGameState(data.game_state)
        await new Promise(r => setTimeout(r, 2000))
        setPatResult(null)
        // Trigger kickoff
        await handleKickoff()
      }
    } catch (err) {
      console.error('Failed to attempt two-point conversion:', err)
    }
  }

  const handleCpuPat = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/game/extra-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: 'K',
        })
      })
      if (res.ok) {
        const data = await res.json()
        setPatResult({
          type: 'kick',
          isCpu: true,
          success: data.success,
          description: data.description,
        })
        updateGameState({
          ...useGameStore.getState(),
          homeScore: data.new_score_home,
          awayScore: data.new_score_away,
        })
        await new Promise(r => setTimeout(r, 2000))
        setPatResult(null)
        // Trigger kickoff
        await handleKickoff()
      }
    } catch (err) {
      console.error('Failed to attempt extra point:', err)
    }
  }

  const handleCpuTwoPoint = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/game/two-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          offense_play: '1',
          defense_play: 'A',
        })
      })
      if (res.ok) {
        const data = await res.json()
        setPatResult({
          type: 'two_point',
          isCpu: true,
          success: data.result.description.includes('GOOD'),
          description: data.result.description,
        })
        updateGameState(data.game_state)
        await new Promise(r => setTimeout(r, 2000))
        setPatResult(null)
        // Trigger kickoff
        await handleKickoff()
      }
    } catch (err) {
      console.error('Failed to attempt two-point conversion:', err)
    }
  }

  const handleKickoff = async () => {
    setExecuting(true)
    setLastResult(null)
    setDiceResult(null)
    setIsRolling(false)
    
    try {
      // Show dice rolling animation
      await new Promise(resolve => setTimeout(resolve, 500))
      setIsRolling(true)
      setDiceResult({
        offenseRoll: {
          black: randomFrom(BLACK_DIE),
          white1: randomFrom(WHITE_DIE),
          white2: randomFrom(WHITE_DIE),
        },
        defenseRoll: {
          red: randomFrom(RED_DIE),
          green: randomFrom(GREEN_DIE),
        },
        result: 0,
      })
      
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const res = await fetch(`${API_BASE}/api/game/kickoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          kickoff_spot: 35,
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        setLastResult(data.result)
        updateGameState(data.game_state)
        setIsRolling(false)
        
        const scoring = data.result.touchdown || data.result.safety
        const scoreChange = scoring ? 
          `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}` : null
        
        // Log the kickoff
        const kickingTeam = data.game_state.possession === 'home' 
          ? (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME') 
          : (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY')
        const receivingTeam = data.game_state.possession === 'home' 
          ? (data.game_state.away_team?.short_name || data.game_state.away_team?.name || 'AWAY') 
          : (data.game_state.home_team?.short_name || data.game_state.home_team?.name || 'HOME')
        
        const logEntry = logPlay({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: data.game_state.down,
          yardsToGo: data.game_state.yards_to_go,
          ballPosition: data.game_state.ball_position,
          offenseTeam: kickingTeam,
          defenseTeam: receivingTeam,
          playerTeam: playerOffense ? kickingTeam : receivingTeam,
          offensePlay: 'KO',
          defensePlay: 'KR',
          description: data.result.description,
          yards: data.result.yards,
          scoreChange,
          turnover: data.result.turnover,
        })
        setPlayLog(prev => [...prev, logEntry])
        
        if (data.result.pending_penalty_decision && data.result.penalty_choice) {
          setPendingPenaltyData(data.result)
          setShowPenaltyChoice(true)
          setExecuting(false)
          return
        }
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver')
        } else if (data.result.touchdown) {
          // Handle touchdown - show PAT choice
          const patRes = await fetch(`${API_BASE}/api/game/pat-choice/${gameId}`)
          if (patRes.ok) {
            const patData = await patRes.json()
            setCanGoForTwo(patData.can_go_for_two)
            setCpuShouldGoForTwo(false) // CPU doesn't score on kickoff return TD
            
            if (patData.scoring_team_is_player) {
              setShowPatChoice(true)
            } else {
              // CPU scored, auto-handle PAT
              await handleCpuPat()
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to perform kickoff:', err)
    } finally {
      if (!showPatChoice && !showPenaltyChoice) {
        setExecuting(false)
      }
    }
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
    setPlayLog([])
    setGamePhase('teamSelect')
    clearCpuFourthDownDecision()
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
    setPlayLog([])
    setGamePhase('teamSelect')
    clearCpuFourthDownDecision()
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

  if (gamePhase === 'kickoff') {
    // Auto-trigger kickoff when entering this phase (only once)
    const kickoffTriggeredRef = useRef(false)
    useEffect(() => {
      if (!kickoffTriggeredRef.current && !executing && !lastResult) {
        kickoffTriggeredRef.current = true
        handleKickoff()
      }
      return () => {
        kickoffTriggeredRef.current = false
      }
    }, [])
    
    const kickingTeam = playerOffense ? 
      (homeTeam?.short_name || homeTeam?.name || 'HOME') : 
      (awayTeam?.short_name || awayTeam?.name || 'AWAY')
    const receivingTeam = playerOffense ? 
      (awayTeam?.short_name || awayTeam?.name || 'AWAY') : 
      (homeTeam?.short_name || homeTeam?.name || 'HOME')
    
    return (
      <div className="board-panel p-6 text-center">
        <h2 className="text-2xl font-heading font-bold mb-4 text-gray-800">
          KICKOFF
        </h2>
        
        <p className="text-lg text-gray-700 mb-4">
          {kickingTeam} kicks off to {receivingTeam}
        </p>
        
        {isRolling && (
          <div className="flex justify-center gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-4 w-20 h-20 flex items-center justify-center">
              <span className="text-4xl font-bold text-white animate-pulse">
                ?
              </span>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 w-20 h-20 flex items-center justify-center">
              <span className="text-4xl font-bold text-white animate-pulse">
                ?
              </span>
            </div>
          </div>
        )}
        
        {!isRolling && lastResult && !showPatChoice && !showPenaltyChoice && (
          <div className="bg-gray-100 rounded-lg p-4 mb-4">
            <p className="text-gray-800">{lastResult.description}</p>
            {lastResult.touchdown && (
              <p className="text-green-600 font-bold mt-2">TOUCHDOWN!</p>
            )}
          </div>
        )}
        
        {!isRolling && !lastResult && !executing && !showPatChoice && (
          <button
            onClick={() => handleKickoff()}
            className="play-button text-base px-6 py-3"
          >
            KICK OFF
          </button>
        )}
        
        {!isRolling && lastResult && !showPatChoice && !showPenaltyChoice && (
          <button
            onClick={() => {
              setExecuting(false)
              setLastResult(null)
              setDiceResult(null)
              setGamePhase('playing')
            }}
            className="play-button text-base px-6 py-3"
          >
            CONTINUE
          </button>
        )}
      </div>
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
    <div className="flex flex-col h-screen bg-gray-900">
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

      <div className="flex-shrink-0 px-4 py-4">
        <FootballField 
          ballPosition={ballPosition} 
          possession={possession}
          homeEndzoneColor={homeTeam?.team_color || '#8B0000'}
          homeTeamName={homeTeam?.name || homeTeam?.abbreviation || 'HOME'}
          yardsToGo={yardsToGo}
        />
      </div>

      {(isRolling || diceResult) && (
        <div className="px-4 pb-2">
          <DiceDisplay
            offenseRoll={diceResult?.offenseRoll}
            defenseRoll={diceResult?.defenseRoll}
            result={diceResult?.result}
            isRolling={isRolling}
            onAnimationComplete={() => {}}
          />
        </div>
      )}

      {lastResult && (
        <div className="px-4 pb-2">
          <div className={`rounded-lg px-4 py-2 text-center ${
            lastResult.big_play_factor >= 3 ? 'bg-red-700' :
            lastResult.big_play_factor >= 2 ? 'bg-orange-700' :
            lastResult.big_play_factor >= 1 ? 'bg-yellow-700' :
            'bg-gray-800'
          }`}>
            <div className="text-white font-bold text-lg">{lastResult.headline || lastResult.description}</div>
            {lastResult.commentary && (
              <div className="text-white/80 text-sm mt-1">{lastResult.commentary}</div>
            )}
          </div>
        </div>
      )}

      {showCpuDecision && cpuFourthDownDecision && (
        <div className="px-4 pb-2">
          <div className="bg-yellow-600 rounded-lg px-4 py-4 text-center animate-pulse">
            <div className="text-lg font-bold text-white mb-1">CPU 4TH DOWN DECISION</div>
            <div className="text-2xl font-bold text-white">
              {cpuFourthDownDecision.decision === 'go_for_it' 
                ? 'GO FOR IT!' 
                : cpuFourthDownDecision.decision === 'field_goal'
                ? 'KICKING A FIELD GOAL'
                : 'PUNTING'}
            </div>
          </div>
        </div>
      )}

      {showPatChoice && (
        <div className="px-4 pb-2">
          <div className="bg-green-700 rounded-lg px-4 py-4 text-center border-2 border-green-500">
            <div className="text-xl font-bold text-white mb-3">EXTRA POINT!</div>
            <div className="flex justify-center gap-4">
              <button
                onClick={handlePatKick}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
              >
                KICK XP (1 PT)
              </button>
              {canGoForTwo && (
                <button
                  onClick={() => handlePatTwoPoint('1')}
                  className="px-6 py-3 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-all"
                >
                  GO FOR 2!
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {patResult && (
        <div className="px-4 pb-2">
          <div className={`rounded-lg px-4 py-4 text-center ${patResult.success ? 'bg-green-700' : 'bg-red-700'}`}>
            <div className="text-xl font-bold text-white">
              {patResult.type === 'two_point' ? 'TWO-POINT CONVERSION' : 'EXTRA POINT'}
            </div>
            <div className="text-2xl font-bold text-white mt-2">
              {patResult.success ? 'GOOD!' : 'NO GOOD!'}
            </div>
            <div className="text-white mt-1">{patResult.description}</div>
          </div>
        </div>
      )}

      {showPenaltyChoice && pendingPenaltyData && (
        <div className="px-4 pb-2">
          <div className="bg-yellow-700 rounded-lg px-4 py-4 text-center border-2 border-yellow-500">
            <div className="text-xl font-bold text-white mb-3">PENALTY ON THE PLAY!</div>
            
            {pendingPenaltyData.penalty_choice.offsetting ? (
              <div className="text-white mb-4">
                <div className="text-lg font-bold mb-2">OFFSETTING PENALTIES</div>
                <div className="text-yellow-200">Down will be replayed</div>
                <div className="flex justify-center mt-4">
                  <button
                    onClick={() => handlePenaltyDecision(false, 0)}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
                  >
                    CONTINUE
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="text-yellow-200 text-sm mb-4">
                  {pendingPenaltyData.penalty_choice.offended_team.toUpperCase()} is offended - choose one:
                </div>
                
                {/* Play Result Option */}
                <div className="bg-gray-800 rounded-lg p-3 mb-4">
                  <div className="text-white text-sm mb-1">PLAY RESULT:</div>
                  <div className="text-white font-bold">
                    {pendingPenaltyData.yards > 0 ? `+${pendingPenaltyData.yards} yards` : 
                     pendingPenaltyData.yards < 0 ? `${pendingPenaltyData.yards} yards` : 
                     'No gain'}
                  </div>
                  {pendingPenaltyData.turnover && (
                    <div className="text-red-400 text-sm">TURNOVER</div>
                  )}
                  {pendingPenaltyData.touchdown && (
                    <div className="text-green-400 text-sm">TOUCHDOWN!</div>
                  )}
                  <div className="text-gray-400 text-xs mt-1">
                    Down counts if accepted
                  </div>
                </div>
                
                {/* Penalty Options */}
                {pendingPenaltyData.penalty_choice.penalty_options && 
                 pendingPenaltyData.penalty_choice.penalty_options.length > 0 && (
                  <div className="mb-4">
                    <div className="text-white text-sm mb-2">PENALTY OPTIONS:</div>
                    <div className="flex flex-col gap-2">
                      {pendingPenaltyData.penalty_choice.penalty_options.map((opt, idx) => (
                        <button
                          key={idx}
                          onClick={() => handlePenaltyDecision(false, idx)}
                          className="px-4 py-3 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-all text-left"
                        >
                          <div className="flex justify-between items-center">
                            <span>{opt.description}</span>
                            <span className="text-sm">
                              {opt.auto_first_down && (
                                <span className="text-yellow-300 ml-2">+AUTO 1ST</span>
                              )}
                            </span>
                          </div>
                          <div className="text-red-200 text-xs">
                            Down replayed if accepted
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Take Play Result Button */}
                <button
                  onClick={() => handlePenaltyDecision(true, 0)}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
                >
                  TAKE PLAY RESULT (DOWN COUNTS)
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          {playerOffense ? (
            <OffensePlays
              selectedPlay={humanPlaySelected}
              onSelectPlay={handleOffensePlay}
              isHumanTurn={true}
              disabled={executing}
            />
          ) : (
            <>
              {down === 4 && !cpuFourthDownDecision && !cpuDecisionPending && (
                <div className="col-span-2 bg-blue-900 rounded-lg p-6 text-center border-2 border-blue-500">
                  <div className="text-xl font-bold text-white mb-2">4TH DOWN - CPU OFFENSE</div>
                  <div className="text-blue-200 mb-4">CPU is deciding what to do...</div>
                  <button
                    onClick={handleCpuFourthDownDecision}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
                  >
                    REVEAL CPU DECISION
                  </button>
                </div>
              )}
              {cpuDecisionPending && (
                <div className="col-span-2 bg-gray-800 rounded-lg p-6 text-center">
                  <div className="text-xl font-bold text-white mb-2">CPU IS DECIDING...</div>
                  <div className="text-gray-400">Please wait</div>
                </div>
              )}
              {cpuFourthDownDecision && cpuFourthDownDecision.decision === 'go_for_it' && (
                <DefensePlays
                  selectedPlay={humanPlaySelected}
                  onSelectPlay={handleDefensePlay}
                  isHumanTurn={true}
                  disabled={executing}
                />
              )}
              {down !== 4 && !cpuFourthDownDecision && !cpuDecisionPending && !executing && (
                <DefensePlays
                  selectedPlay={humanPlaySelected}
                  onSelectPlay={handleDefensePlay}
                  isHumanTurn={true}
                  disabled={executing}
                />
              )}
            </>
          )}

          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-sm text-gray-400 mb-2">
              {playerOffense ? 'CPU DEFENSE' : 'CPU OFFENSE'}
            </div>
            <div className="text-gray-500">
              {executing ? (
                <span className="text-gray-600">Selecting...</span>
              ) : showCpuPlay && cpuPlay ? (
                <span className="text-yellow-400 font-bold text-xl">{cpuPlay}</span>
              ) : (
                <span className="text-gray-600">-</span>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex justify-center gap-6 text-sm text-gray-500">
          <button onClick={handleSaveGame} className="hover:text-white transition-colors">
            {showSaveConfirm ? '✓ Saved' : 'Save Game'}
          </button>
          <span>|</span>
          <button onClick={handleReturnToMenu} className="hover:text-white transition-colors">
            Return to Menu
          </button>
        </div>
      </div>

      <PlayLog entries={playLog} />
    </div>
  )
}

export default App
