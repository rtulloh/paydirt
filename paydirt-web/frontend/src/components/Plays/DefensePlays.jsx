import { useEffect, useCallback } from 'react'

const DEFENSIVE_FORMATIONS = [
  { key: 'A', name: 'Standard', description: 'Normal Defense' },
  { key: 'B', name: 'Short Yardage', description: 'Short Yardage' },
  { key: 'C', name: 'Spread', description: 'Spread Defense' },
  { key: 'D', name: 'Short Pass', description: 'Short Pass' },
  { key: 'E', name: 'Long Pass', description: 'Long Pass' },
  { key: 'F', name: 'Blitz', description: 'Blitz' },
]

export function DefensePlays({ selectedPlay, onSelectPlay, disabled = false, isHumanTurn = true }) {
  const handleKeyPress = useCallback((event) => {
    // Ignore if disabled, not human's turn, or modifier keys are pressed (Ctrl/Cmd for copy/paste)
    if (disabled || !isHumanTurn || event.ctrlKey || event.metaKey || event.altKey) return
    
    const key = event.key.toUpperCase()
    const formation = DEFENSIVE_FORMATIONS.find(f => f.key === key)
    
    if (formation) {
      onSelectPlay(key)
    }
  }, [disabled, isHumanTurn, onSelectPlay])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [handleKeyPress])

  if (!isHumanTurn) {
    return (
      <div className="board-panel" data-testid="defense-plays">
        <div className="board-panel-header text-center py-1">
          ⚔ DEFENSE ⚔
        </div>
        <div className="p-3 text-center text-gray-500">
          CPU is selecting...
        </div>
      </div>
    )
  }

  return (
    <div className="bg-panel-bg border-2 border-panel-border rounded-lg p-3" data-testid="defense-plays">
      <div className="mb-2 text-center text-sm font-bold text-panel-border">
        YOUR DEFENSE
      </div>
      
      <div className="grid grid-cols-3 gap-x-2 gap-y-3 sm:grid-cols-4">
          {DEFENSIVE_FORMATIONS.map(formation => (
            <button
              key={formation.key}
              onClick={() => onSelectPlay(formation.key)}
              disabled={disabled || !isHumanTurn}
              className={`
                play-button flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 py-2
                ${selectedPlay === formation.key ? 'play-button-selected' : ''}
                ${disabled ? 'cursor-not-allowed saturate-0' : ''}
              `}
              data-testid={`defense-play-${formation.key.toLowerCase()}`}
            >
              <span className="text-lg font-bold leading-none">{formation.key}</span>
              <span className="text-center text-sm leading-tight">{formation.name}</span>
            </button>
          ))}
      </div>
    </div>
  )
}

export default DefensePlays
