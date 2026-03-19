import { useEffect, useCallback } from 'react'

const OFFENSIVE_PLAYS = {
  RUNS: [
    { key: '1', name: 'Ln-Plg', description: 'Line Plunge' },
    { key: '2', name: 'O-Tkl', description: 'Off Tackle' },
    { key: '3', name: 'End-Rn', description: 'End Run' },
    { key: '4', name: 'Draw', description: 'Draw Play' },
  ],
  PASSES: [
    { key: '5', name: 'Screen', description: 'Screen Pass' },
    { key: '6', name: 'Shrt', description: 'Short Pass' },
    { key: '7', name: 'Med', description: 'Medium Pass' },
    { key: '8', name: 'Long', description: 'Long Pass' },
    { key: '9', name: 'TE/SL', description: 'TE/Sideline' },
  ],
  SPECIAL: [
    { key: 'Q', name: 'Sneak', description: 'QB Sneak' },
    { key: 'K', name: 'Kneel', description: 'Kneel Down' },
    { key: 'P', name: 'Punt', description: 'Punt' },
    { key: 'F', name: 'FG', description: 'Field Goal' },
    { key: 'S', name: 'Spike', description: 'Spike Ball' },
  ],
}

export function OffensePlays({ selectedPlay, onSelectPlay, disabled = false, isHumanTurn = true }) {
  const handleKeyPress = useCallback((event) => {
    if (disabled || !isHumanTurn) return
    
    const key = event.key.toUpperCase()
    const allPlays = [
      ...OFFENSIVE_PLAYS.RUNS,
      ...OFFENSIVE_PLAYS.PASSES,
      ...OFFENSIVE_PLAYS.SPECIAL,
    ]
    const play = allPlays.find(p => p.key === key)
    
    if (play) {
      onSelectPlay(key)
    }
  }, [disabled, isHumanTurn, onSelectPlay])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [handleKeyPress])

  const renderPlayButton = (play, category) => (
    <button
      key={play.key}
      onClick={() => onSelectPlay(play.key)}
      disabled={disabled || !isHumanTurn}
      className={`
        play-button flex flex-col items-center justify-center w-full
        ${selectedPlay === play.key ? 'play-button-selected' : ''}
        ${disabled || !isHumanTurn ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      data-testid={`offense-play-${play.key.toLowerCase()}`}
      data-category={category}
    >
      <span className="text-sm font-bold">{play.key}</span>
      <span className="text-xs">{play.name}</span>
    </button>
  )

  if (!isHumanTurn) {
    return (
      <div className="board-panel" data-testid="offense-plays">
        <div className="board-panel-header text-center">
          ⚈ OFFENSE ⚈
        </div>
        <div className="p-4 text-center text-gray-500">
          CPU is selecting...
        </div>
      </div>
    )
  }

  return (
    <div className="board-panel" data-testid="offense-plays">
      <div className="board-panel-header text-center py-1">
        ⚈ SELECT YOUR PLAY ⚈
      </div>
      
      <div className="p-3">
        <div className="grid grid-cols-4 gap-1 mb-2">
          <div className="col-span-4 font-heading font-bold text-gray-700 text-center mb-1 text-xs">
            RUNS
          </div>
          {OFFENSIVE_PLAYS.RUNS.map(play => renderPlayButton(play, 'runs'))}
        </div>

        <div className="grid grid-cols-5 gap-1 mb-2">
          <div className="col-span-5 font-heading font-bold text-gray-700 text-center mb-1 text-xs">
            PASSES
          </div>
          {OFFENSIVE_PLAYS.PASSES.map(play => renderPlayButton(play, 'passes'))}
        </div>

        <div className="grid grid-cols-5 gap-1">
          <div className="col-span-5 font-heading font-bold text-gray-700 text-center mb-1 text-xs">
            SPECIAL
          </div>
          {OFFENSIVE_PLAYS.SPECIAL.map(play => renderPlayButton(play, 'special'))}
        </div>

        <div className="mt-3 pt-2 border-t border-gray-300 text-center">
          <p className="text-xs text-gray-500">
            Press 1-9, Q, K, P, F, or S
          </p>
        </div>
      </div>
    </div>
  )
}

export default OffensePlays
