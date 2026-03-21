import { useState, useEffect } from 'react'

export function CoinToss({ homeTeam, awayTeam, onComplete }) {
  const [phase, setPhase] = useState('flip') // 'flip' -> 'call' -> 'result'
  const [flipping, setFlipping] = useState(true)
  const [coinResult, setCoinResult] = useState(null) // 'heads' or 'tails' (hidden until call is made)
  const [playerCall, setPlayerCall] = useState(null) // 'heads' or 'tails'
  const [playerChoice, setPlayerChoice] = useState(null) // 'receive' or 'kick'
  const [showResult, setShowResult] = useState(false)

  // Start flipping the coin on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setFlipping(false)
      // Generate the result but don't show it yet
      setCoinResult(Math.random() > 0.5 ? 'heads' : 'tails')
      setPhase('call')
    }, 1500)
    return () => clearTimeout(timer)
  }, [])

  const handleCall = (call) => {
    setPlayerCall(call)
    setFlipping(true)
    
    // Now reveal the coin result
    setTimeout(() => {
      setFlipping(false)
      setShowResult(true)
      setPhase('result')
    }, 1000)
  }

  const handleChoice = (choice) => {
    setPlayerChoice(choice)
    
    // Determine possession based on choice
    // If player receives, they get the ball; if they kick, opponent receives
    const playerReceives = choice === 'receive'
    const playerWonToss = playerCall === coinResult
    
    // If player won toss, they get their choice
    // If player lost toss, opponent receives (CPU always chooses to receive)
    // So playerReceives is only true if player won AND chose to receive
    onComplete({
      coinResult,
      playerCall,
      playerWonToss,
      playerReceives: playerWonToss && playerReceives,
    })
  }

  const playerWonToss = playerCall === coinResult

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
            {/* Show ? while flipping, or while waiting for call */}
            {flipping || phase === 'flip' || phase === 'call' ? '?' : (coinResult === 'heads' ? 'H' : 'T')}
          </div>
        </div>
      </div>

      {phase === 'flip' && (
        <p className="text-gray-500 animate-pulse">Flipping coin...</p>
      )}

      {phase === 'call' && (
        <div className="animate-fade-in">
          <p className="text-lg text-gray-700 mb-4">
            The coin is in the air! Call it:
          </p>
          <div className="flex justify-center gap-4">
            <button
              onClick={() => handleCall('heads')}
              className="play-button text-base px-8 py-3 bg-green-600 hover:bg-green-700"
              data-testid="choose-heads"
            >
              HEADS
            </button>
            <button
              onClick={() => handleCall('tails')}
              className="play-button text-base px-8 py-3 bg-blue-600 hover:bg-blue-700"
              data-testid="choose-tails"
            >
              TAILS
            </button>
          </div>
        </div>
      )}

      {phase === 'result' && (
        <div className="animate-fade-in">
          <p className="text-lg text-gray-700 mb-2 capitalize">
            It's {coinResult}!
          </p>
          <p className={`text-base mb-4 font-bold ${playerWonToss ? 'text-green-600' : 'text-red-600'}`}>
            {playerWonToss ? 'You won the toss!' : 'You lost the toss'}
          </p>
          
          {playerWonToss ? (
            <div>
              <p className="text-base text-gray-700 mb-2">
                Choose what to do:
              </p>
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => handleChoice('receive')}
                  className="play-button text-base px-6 py-3 bg-green-600 hover:bg-green-700"
                  data-testid="choose-receive"
                >
                  RECEIVE
                </button>
                <button
                  onClick={() => handleChoice('kick')}
                  className="play-button text-base px-6 py-3 bg-blue-600 hover:bg-blue-700"
                  data-testid="choose-kick"
                >
                  KICK OFF
                </button>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-base text-gray-600 mb-2">
                {homeTeam?.short_name || 'OPPONENT'} elects to receive.
              </p>
              <button
                onClick={() => handleChoice('kick')}
                className="play-button text-base px-6 py-3"
                data-testid="coin-toss-continue"
              >
                CONTINUE
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default CoinToss
