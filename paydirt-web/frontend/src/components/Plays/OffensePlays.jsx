import { useEffect, useCallback } from 'react'

const OFFENSIVE_PLAYS = {
  RUNS: [
    { key: '1', name: 'Ln-Plg' },
    { key: '2', name: 'O-Tkl' },
    { key: '3', name: 'End-Rn' },
    { key: '4', name: 'Draw' },
  ],
  PASSES: [
    { key: '5', name: 'Screen' },
    { key: '6', name: 'Shrt' },
    { key: '7', name: 'Med' },
    { key: '8', name: 'Long' },
    { key: '9', name: 'TE/SL' },
  ],
  SPECIAL: [
    { key: 'Q', name: 'Sneak' },
    { key: 'K', name: 'Kneel' },
    { key: 'P', name: 'Punt' },
    { key: 'F', name: 'FG' },
  ],
}

export function OffensePlays({ selectedPlay, onSelectPlay, disabled = false, isHumanTurn = true }) {
  const handleKeyPress = useCallback((event) => {
    // Ignore if disabled, not human's turn, or modifier keys are pressed (Ctrl/Cmd for shortcuts)
    if (disabled || !isHumanTurn || event.ctrlKey || event.metaKey || event.altKey) return
    const key = event.key.toUpperCase()
    const allPlays = [...OFFENSIVE_PLAYS.RUNS, ...OFFENSIVE_PLAYS.PASSES, ...OFFENSIVE_PLAYS.SPECIAL]
    const play = allPlays.find(p => p.key === key)
    if (play) onSelectPlay(key)
  }, [disabled, isHumanTurn, onSelectPlay])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [handleKeyPress])

  const renderPlayButton = (play) => (
    <button
      key={play.key}
      onClick={() => onSelectPlay(play.key)}
      disabled={disabled || !isHumanTurn}
      className={`
        bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed
        rounded-lg p-3 flex flex-col items-center justify-center transition-colors
        ${selectedPlay === play.key ? 'ring-2 ring-yellow-400 bg-gray-600' : ''}
      `}
      data-testid={`offense-play-${play.key.toLowerCase()}`}
    >
      <span className="text-lg font-bold text-white">{play.key}</span>
      <span className="text-xs text-gray-400">{play.name}</span>
    </button>
  )

  if (!isHumanTurn) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 text-center" data-testid="offense-plays">
        <div className="text-gray-500">CPU selecting...</div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4" data-testid="offense-plays">
      <div className="text-sm text-gray-400 mb-3 font-medium">YOUR PLAY</div>
      
      <div className="mb-3">
        <div className="text-[10px] text-gray-600 mb-1 uppercase">RUNS</div>
        <div className="grid grid-cols-4 gap-2">
          {OFFENSIVE_PLAYS.RUNS.map(renderPlayButton)}
        </div>
      </div>

      <div className="mb-3">
        <div className="text-[10px] text-gray-600 mb-1 uppercase">PASSES</div>
        <div className="grid grid-cols-5 gap-1">
          {OFFENSIVE_PLAYS.PASSES.map(renderPlayButton)}
        </div>
      </div>

      <div>
        <div className="text-[10px] text-gray-600 mb-1 uppercase">SPECIAL</div>
        <div className="grid grid-cols-5 gap-1">
          {OFFENSIVE_PLAYS.SPECIAL.map(renderPlayButton)}
        </div>
      </div>
    </div>
  )
}

export default OffensePlays
