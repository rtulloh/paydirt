import { useState, useEffect } from 'react'

const API_BASE = ''

function formatFieldPosition(position) {
  if (position === null || position === undefined) return ''
  // In Paydirt: 0 = own goal line, 50 = midfield, 100 = opponent's goal line
  if (position <= 50) {
    return position === 0 ? 'Goal Line' : `${position} yard line`
  }
  return `${100 - position} yard line`
}

export function KickoffPlay({ homeTeam, awayTeam, playerOffense, gameId, onComplete }) {
  const [phase, setPhase] = useState('rolling')
  const [isRolling, setIsRolling] = useState(true)
  const [diceResult, setDiceResult] = useState(null)
  const [kickoffResult, setKickoffResult] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const rollTimer = setTimeout(() => {
      setIsRolling(false)
      
      const fetchKickoff = async () => {
        try {
          const res = await fetch(`${API_BASE}/api/game/kickoff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              game_id: gameId,
              kickoff_spot: 35,
            })
          })
          
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`)
          }
          
          const data = await res.json()
          
          setDiceResult({
            offense: data.dice_roll_offense || 0,
            defense: data.dice_roll_defense || 0,
          })
          setKickoffResult(data.result)
          setGameState(data.game_state)
          setPhase('result')
        } catch (err) {
          console.error('Failed to fetch kickoff:', err)
          setError(err.message)
          setLoading(false)
        }
      }
      
      fetchKickoff()
    }, 2000)
    
    return () => clearTimeout(rollTimer)
  }, [gameId])

  const handleContinue = () => {
    onComplete(gameState)
  }

  const kickingTeam = playerOffense ? homeTeam : awayTeam
  const receivingTeam = playerOffense ? awayTeam : homeTeam

  return (
    <div className="board-panel p-6 text-center">
      <h2 className="text-2xl font-heading font-bold mb-4 text-gray-800">
        OPENING KICKOFF
      </h2>
      
      <p className="text-lg text-gray-700 mb-4">
        {(kickingTeam?.short_name || kickingTeam?.name || 'Team')} kicks off to {(receivingTeam?.short_name || receivingTeam?.name || 'Team')}
      </p>

      <div className="flex justify-center gap-4 mb-6">
        <div className="bg-gray-800 rounded-lg p-4 w-20 h-20 flex items-center justify-center">
          <span className={`text-4xl font-bold text-white ${isRolling ? 'animate-pulse' : ''}`}>
            {isRolling ? '?' : (diceResult?.offense || '?')}
          </span>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 w-20 h-20 flex items-center justify-center">
          <span className={`text-4xl font-bold text-white ${isRolling ? 'animate-pulse' : ''}`}>
            {isRolling ? '?' : (diceResult?.defense || '?')}
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 rounded-lg p-4 mb-4">
          <p className="text-red-700">Error: {error}</p>
          <button
            onClick={() => onComplete(null)}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Skip Kickoff
          </button>
        </div>
      )}

      {phase === 'result' && kickoffResult && (
        <div className="animate-fade-in">
          <div className="bg-gray-100 rounded-lg p-4 mb-4">
            <p className="text-gray-800 whitespace-pre-wrap">{kickoffResult.description}</p>
          </div>
          
          <p className="text-base text-gray-600 mb-4">
            {kickoffResult.touchdown 
              ? 'TOUCHDOWN!'
              : kickoffResult.turnover 
                ? 'Turnover!'
                : gameState 
                  ? `Ball placed at the ${formatFieldPosition(gameState.ball_position)}`
                  : kickoffResult.yards > 0 
                    ? `Ball placed at the ${kickoffResult.new_ball_position} yard line`
                    : 'No gain'
            }
          </p>
          
          <button
            onClick={handleContinue}
            className="play-button text-base px-6 py-3"
          >
            CONTINUE
          </button>
        </div>
      )}

      {phase === 'rolling' && !error && (
        <p className="text-gray-500 animate-pulse">
          {loading ? 'Processing...' : 'Rolling...'}
        </p>
      )}
    </div>
  )
}

export default KickoffPlay
