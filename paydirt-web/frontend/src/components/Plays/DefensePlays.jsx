import { useEffect, useCallback } from 'react'

const DEFENSIVE_FORMATIONS = [
  { key: 'A', name: 'Standard', description: 'Normal Defense' },
  { key: 'B', name: 'Short', description: 'Short Yardage' },
  { key: 'C', name: 'Spread', description: 'Spread Defense' },
  { key: 'D', name: 'Short-P', description: 'Short Pass' },
  { key: 'E', name: 'Long-P', description: 'Long Pass' },
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
    <div className="bg-panel-bg border-2 border-panel-border rounded-lg h-full flex flex-col" data-testid="defense-plays">
      <div className="text-center py-0.5 text-[10px] font-bold text-panel-border">
        YOUR DEFENSE
      </div>
      
      <div className="flex-1 p-0.5">
        <div className="grid grid-cols-6 gap-0.5 h-full">
          {DEFENSIVE_FORMATIONS.map(formation => (
            <button
              key={formation.key}
              onClick={() => onSelectPlay(formation.key)}
              disabled={disabled || !isHumanTurn}
              className={`
                play-button flex flex-col items-center justify-center py-0.5
                ${selectedPlay === formation.key ? 'play-button-selected' : ''}
                ${disabled || !isHumanTurn ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              data-testid={`defense-play-${formation.key.toLowerCase()}`}
            >
              <span className="font-bold text-[10px]">{formation.key}</span>
              <span className="text-[8px]">{formation.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default DefensePlays
