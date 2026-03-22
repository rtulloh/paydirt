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
  const [phase, setPhase] = useState('choice')  // 'choice', 'rolling', 'result'
  const [isRolling, setIsRolling] = useState(false)
  const [diceResult, setDiceResult] = useState(null)
  const [kickoffResult, setKickoffResult] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isOnside, setIsOnside] = useState(false)

  const performKickoff = async (onside = false) => {
    setIsOnside(onside)
    setPhase('rolling')
    setIsRolling(true)
    setLoading(true)
    setError(null)

    await new Promise(resolve => setTimeout(resolve, 1500))
    
    try {
      const res = await fetch(`${API_BASE}/api/game/kickoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          kickoff_spot: isOnside ? 35 : 35,  // Onside kick still from 35
          onside: onside,
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
      setIsRolling(false)
      setLoading(false)
      setPhase('result')
    } catch (err) {
      console.error('Failed to fetch kickoff:', err)
      setError(err.message)
      setLoading(false)
      setIsRolling(false)
    }
  }

  const handleContinue = () => {
    onComplete(gameState)
  }

  const kickingTeam = playerOffense ? homeTeam : awayTeam
  const receivingTeam = playerOffense ? awayTeam : homeTeam

  return (
    <div className="board-panel p-6 text-center">
      <h2 className="text-2xl font-heading font-bold mb-4 text-gray-800">
        {isOnside ? 'ONSIDE KICK' : 'KICKOFF'}
      </h2>
      
      <p className="text-lg text-gray-700 mb-4">
        {(kickingTeam?.short_name || kickingTeam?.name || 'Team')} kicks off to {(receivingTeam?.short_name || receivingTeam?.name || 'Team')}
      </p>

      {/* Choice phase - let player choose kickoff type */}
      {phase === 'choice' && (
        <div className="mb-6">
          <div className="flex justify-center gap-4">
            <button
              onClick={() => performKickoff(false)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
            >
              KICKOFF
            </button>
            <button
              onClick={() => performKickoff(true)}
              className="px-6 py-3 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-all"
              title="Risky - recover on roll 13-20"
            >
              ONSIDE KICK
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Onside kick: Low chance to recover (13-20 on dice)
          </p>
        </div>
      )}

      {/* Rolling phase - show dice animation */}
      {phase === 'rolling' && (
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
      )}

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

      {/* Result phase */}
      {phase === 'result' && kickoffResult && (
        <div className="animate-fade-in">
          <div className="bg-gray-100 rounded-lg p-4 mb-4">
            <p className="text-gray-800 whitespace-pre-wrap">{kickoffResult.description}</p>
          </div>
          
          <p className="text-base text-gray-600 mb-4">
            {kickoffResult.touchdown 
              ? 'TOUCHDOWN!'
              : kickoffResult.turnover 
                ? 'ONSIDE KICK RECOVERED!'
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
    </div>
  )
}

export default KickoffPlay
