import { useState, useEffect } from 'react'

export function CoinToss({ homeTeam, awayTeam, onComplete }) {
  const [flipping, setFlipping] = useState(true)
  const [result, setResult] = useState(null)
  const [showResult, setShowResult] = useState(false)

  useEffect(() => {
    const flipDuration = 2000
    const timer = setTimeout(() => {
      setFlipping(false)
      const heads = Math.random() > 0.5
      setResult(heads ? 'heads' : 'tails')
      setShowResult(true)
    }, flipDuration)
    return () => clearTimeout(timer)
  }, [])

  const handleContinue = () => {
    onComplete(result)
  }

  const teamReceiving = result === 'heads' ? 'home' : 'away'
  const receivingTeam = teamReceiving === 'home' ? homeTeam : awayTeam
  const kickingTeam = teamReceiving === 'home' ? awayTeam : homeTeam

  return (
    <div className="board-panel p-6 text-center" data-testid="coin-toss">
      <h2 className="text-2xl font-heading font-bold mb-4 text-gray-800">
        COIN TOSS
      </h2>

      <div className="mb-4">
        <div 
          className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 
            flex items-center justify-center shadow-xl transition-transform duration-500
            ${flipping ? 'animate-spin' : ''}`}
          data-testid="coin"
        >
          <div className="text-4xl font-bold text-yellow-900">
            {flipping ? '?' : result === 'heads' ? 'H' : 'T'}
          </div>
        </div>
      </div>

      {showResult && result && (
        <div className="animate-fade-in">
          <p className="text-lg text-gray-700 mb-2 capitalize">
            It's {result}!
          </p>
          <p className="text-base text-gray-600 mb-2">
            {receivingTeam?.short_name || receivingTeam?.name || 'Receiving Team'} ({teamReceiving === 'home' ? 'HOME' : 'AWAY'}) receives
          </p>
          <p className="text-sm text-gray-500 mb-4">
            {kickingTeam?.short_name || kickingTeam?.name || 'Kicking Team'} ({teamReceiving === 'home' ? 'AWAY' : 'HOME'}) kicks off
          </p>

          <button
            onClick={handleContinue}
            className="play-button text-base px-6 py-3"
            data-testid="coin-toss-continue"
          >
            CONTINUE
          </button>
        </div>
      )}

      {flipping && (
        <p className="text-gray-500 animate-pulse">Flipping...</p>
      )}
    </div>
  )
}

export default CoinToss
