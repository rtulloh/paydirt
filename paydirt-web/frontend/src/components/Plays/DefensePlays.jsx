import { useEffect, useCallback } from 'react'

const DEFENSIVE_FORMATIONS = [
  { key: 'A', name: 'Standard', description: 'Normal Defense' },
  { key: 'B', name: 'Short', description: 'Short Yardage' },
  { key: 'C', name: 'Spread', description: 'Spread Defense' },
  { key: 'D', name: 'Short-P', description: 'Short Pass' },
  { key: 'E', name: 'Long-P', description: 'Long Pass' },
]

export function DefensePlays({ selectedPlay, onSelectPlay, disabled = false, isHumanTurn = true }) {
  const handleKeyPress = useCallback((event) => {
    if (disabled || !isHumanTurn) return
    
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
    <div className="board-panel" data-testid="defense-plays">
      <div className="board-panel-header text-center py-1">
        ⚔ SELECT DEFENSE ⚔
      </div>
      
      <div className="p-3">
        <div className="grid grid-cols-5 gap-1">
          {DEFENSIVE_FORMATIONS.map(formation => (
            <button
              key={formation.key}
              onClick={() => onSelectPlay(formation.key)}
              disabled={disabled || !isHumanTurn}
              className={`
                play-button flex flex-col items-center justify-center w-full py-2
                ${selectedPlay === formation.key ? 'play-button-selected' : ''}
                ${disabled || !isHumanTurn ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              data-testid={`defense-play-${formation.key.toLowerCase()}`}
            >
              <span className="text-sm font-bold">{formation.key}</span>
              <span className="text-xs">{formation.name}</span>
              <span className="text-xs text-gray-600">{formation.description}</span>
            </button>
          ))}
        </div>

        <div className="mt-3 pt-2 border-t border-gray-300 text-center">
          <p className="text-xs text-gray-500">
            Press A, B, C, D, or E
          </p>
        </div>
      </div>
    </div>
  )
}

export default DefensePlays
