import { useState, useEffect, useCallback } from 'react'

const DICE_COLORS = {
  black: { bg: 'bg-gray-900', text: 'text-white', border: 'border-gray-700' },
  white: { bg: 'bg-white', text: 'text-gray-900', border: 'border-gray-300' },
  red: { bg: 'bg-red-600', text: 'text-white', border: 'border-red-800' },
  green: { bg: 'bg-green-600', text: 'text-white', border: 'border-green-800' },
}

/**
 * Paydirt uses custom dice with specific number faces, not standard d6 pips.
 * Display numbers instead of dots since dice can show 0, and the faces are:
 * - Black die: 1,2,2,3,3,3
 * - White die 1: 0,0,1,2,3,4
 * - White die 2: 0,1,2,3,4,5
 * - Red die: 1,1,1,2,2,3
 * - Green die: 0,0,0,0,1,2
 */
function Die({ value, color, size = 'md', animate, settled }) {
  const colorClass = DICE_COLORS[color] || DICE_COLORS.white
  const sizeClass = size === 'lg' ? 'w-16 h-16' : size === 'sm' ? 'w-10 h-10' : 'w-12 h-12'
  const textSizeClass = size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-lg' : 'text-2xl'
  
  return (
    <div
      className={`
        relative ${sizeClass} rounded-lg ${colorClass.bg} ${colorClass.border} border-2
        flex items-center justify-center
        ${animate ? 'animate-dice-roll' : 'animate-dice-settle'}
      `}
      data-testid={`die-${color}`}
    >
      <span className={`${textSizeClass} font-bold ${colorClass.text}`}>
        {value}
      </span>
    </div>
  )
}

export function DiceDisplay({ 
  offenseRoll, 
  defenseRoll, 
  result,
  offensePlay,
  defensePlay,
  description,
  onAnimationComplete,
  isRolling = false,
  hideDefenseDice = false,
}) {
  // Simplified: dice are either all visible (settled) or all rolling
  // No staggered animation - prevents jitter
  const settled = !isRolling

  // Don't render if not rolling and no dice data
  if (!isRolling && !offenseRoll && !defenseRoll) {
    return null
  }

  // Use total from backend if available, otherwise calculate
  // For kickoffs, black IS the total (10-39), not a die face
  // For regular plays, black is a die face (1-3) that needs to be multiplied by 10
  const offenseTotal = offenseRoll?.total ?? ((offenseRoll?.black ?? 0) * 10 + (offenseRoll?.white1 ?? 0) + (offenseRoll?.white2 ?? 0))
  const defenseTotal = defenseRoll?.total ?? ((defenseRoll?.red ?? 0) * 10 + (defenseRoll?.green ?? 0))

  return (
    <div className="bg-gray-800 rounded-lg p-4" data-testid="dice-display">
      <div className="flex justify-center gap-8 mb-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-blue-400 w-6">OFF</span>
          <div className="flex gap-2">
            <Die value={offenseRoll?.black ?? 0} color="black" size="md" animate={isRolling} settled={settled} delay={0} />
            <Die value={offenseRoll?.white1 ?? 0} color="white" size="md" animate={isRolling} settled={settled} delay={0} />
            <Die value={offenseRoll?.white2 ?? 0} color="white" size="md" animate={isRolling} settled={settled} delay={0} />
          </div>
          <span className={`text-lg font-bold text-blue-400 w-8 text-center`}>{offenseTotal}</span>
        </div>

        {!hideDefenseDice && (
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-purple-400 w-6">DEF</span>
            <div className="flex gap-2">
              <Die value={defenseRoll?.red ?? 0} color="red" size="md" animate={isRolling} settled={settled} delay={0} />
              <Die value={defenseRoll?.green ?? 0} color="green" size="md" animate={isRolling} settled={settled} delay={0} />
            </div>
            <span className={`text-lg font-bold text-purple-400 w-8 text-center`}>{defenseTotal}</span>
          </div>
        )}
      </div>
      
      {description && (
        <div className="text-center text-white text-sm mt-2 pt-2 border-t border-gray-700">
          {description}
        </div>
      )}
    </div>
  )
}

// Standard Paydirt dice faces
// Reference: https://wizardofvegas.com/forum/off-topic/general/16854-pay-dirt-dice-percentages/
const BLACK_DIE = [1, 2, 2, 3, 3, 3]      // 1 appears 1/6, 2 appears 2/6, 3 appears 3/6
const WHITE_DIE_1 = [0, 0, 1, 2, 3, 4]    // First white die
const WHITE_DIE_2 = [0, 1, 2, 3, 4, 5]    // Second white die
const RED_DIE = [1, 1, 1, 2, 2, 3]
const GREEN_DIE = [0, 0, 0, 0, 1, 2]

const randomFrom = (arr) => arr[Math.floor(Math.random() * arr.length)]

export function DiceRoller({ onComplete }) {
  const [rolling, setRolling] = useState(true)
  const [values, setValues] = useState({
    black: 1,
    white1: 0,
    white2: 0,
    red: 1,
    green: 0,
  })

  useEffect(() => {
    const interval = setInterval(() => {
      setValues({
        black: randomFrom(BLACK_DIE),
        white1: randomFrom(WHITE_DIE_1),
        white2: randomFrom(WHITE_DIE_2),
        red: randomFrom(RED_DIE),
        green: randomFrom(GREEN_DIE),
      })
    }, 100)

    setTimeout(() => {
      clearInterval(interval)
      setRolling(false)
      if (onComplete) onComplete()
    }, 1500)

    return () => clearInterval(interval)
  }, [onComplete])

  return (
    <div className="flex justify-center gap-4">
      <Die value={values.black} color="black" size="lg" animate={rolling} settled={!rolling} delay={0} />
      <Die value={values.white1} color="white" size="lg" animate={rolling} settled={!rolling} delay={100} />
      <Die value={values.white2} color="white" size="lg" animate={rolling} settled={!rolling} delay={200} />
    </div>
  )
}

export default DiceDisplay
