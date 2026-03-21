import { useState, useEffect, useCallback } from 'react'

const DICE_COLORS = {
  black: { bg: 'bg-gray-900', text: 'text-white', border: 'border-gray-700' },
  white: { bg: 'bg-white', text: 'text-gray-900', border: 'border-gray-300' },
  red: { bg: 'bg-red-600', text: 'text-white', border: 'border-red-800' },
  green: { bg: 'bg-green-600', text: 'text-white', border: 'border-green-800' },
}

const PIP_PATTERNS = {
  0: [],
  1: [[50, 50]],
  2: [[25, 25], [75, 75]],
  3: [[25, 25], [50, 50], [75, 75]],
  4: [[25, 25], [75, 25], [25, 75], [75, 75]],
  5: [[25, 25], [75, 25], [50, 50], [25, 75], [75, 75]],
}

function Pip({ x, y, color }) {
  const pipColor = color === 'black' || color === 'red' || color === 'green' ? 'bg-white' : 'bg-gray-900'
  return (
    <div
      className={`absolute w-2 h-2 rounded-full ${pipColor}`}
      style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
    />
  )
}

function Die({ value, color, size = 'md', animate, settled, delay = 0 }) {
  const colorClass = DICE_COLORS[color] || DICE_COLORS.white
  const sizeClass = size === 'lg' ? 'w-16 h-16' : size === 'sm' ? 'w-10 h-10' : 'w-12 h-12'
  const pipSizeClass = size === 'lg' ? 'w-3 h-3' : size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'
  
  const pips = PIP_PATTERNS[value] || PIP_PATTERNS[1]
  
  return (
    <div
      className={`
        relative ${sizeClass} rounded-lg ${colorClass.bg} ${colorClass.border} border-2
        flex items-center justify-center
        ${animate && !settled ? 'animate-dice-roll' : ''}
        ${settled ? 'animate-dice-settle' : 'opacity-0'}
        transition-opacity duration-300
      `}
      style={{ 
        animationDelay: settled ? `${delay}ms` : '0ms',
        transitionDelay: settled ? `${delay}ms` : '0ms',
      }}
      data-testid={`die-${color}`}
    >
      <div className={`relative w-full h-full ${pipSizeClass}`}>
        {pips.map(([px, py], index) => (
          <Pip key={index} x={px} y={py} color={color} />
        ))}
      </div>
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
}) {
  const [showOffenseDice, setShowOffenseDice] = useState(false)
  const [showDefenseDice, setShowDefenseDice] = useState(false)
  const [showTotals, setShowTotals] = useState(false)
  const [showResult, setShowResult] = useState(false)
  const [animationStarted, setAnimationStarted] = useState(false)

  const resetAnimation = useCallback(() => {
    setShowOffenseDice(false)
    setShowDefenseDice(false)
    setShowTotals(false)
    setShowResult(false)
    setAnimationStarted(false)
  }, [])

  useEffect(() => {
    if (isRolling && !animationStarted) {
      resetAnimation()
      setAnimationStarted(true)
    }
  }, [isRolling, animationStarted, resetAnimation])

  useEffect(() => {
    if (!animationStarted) return

    const timers = []

    timers.push(setTimeout(() => setShowOffenseDice(true), 200))
    timers.push(setTimeout(() => setShowDefenseDice(true), 600))
    timers.push(setTimeout(() => setShowTotals(true), 1000))
    timers.push(setTimeout(() => setShowResult(true), 1200))
    timers.push(setTimeout(() => {
      if (onAnimationComplete) onAnimationComplete()
    }, 1500))

    return () => timers.forEach(clearTimeout)
  }, [animationStarted, onAnimationComplete])

  if (!isRolling && !showResult && !description) {
    return null
  }

  // Black/Red dice = 10s (B1=10, B2=20, B3=30)
  const offenseTotal = ((offenseRoll?.black || 0) * 10) + (offenseRoll?.white1 || 0) + (offenseRoll?.white2 || 0)
  const defenseTotal = ((defenseRoll?.red || 0) * 10) + (defenseRoll?.green || 0)

  return (
    <div className="bg-gray-800 rounded-lg p-4" data-testid="dice-display">
      <div className="flex justify-center gap-8 mb-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-blue-400 w-6">OFF</span>
          <div className="flex gap-2">
            <Die value={offenseRoll?.black || 1} color="black" size="md" animate={isRolling} settled={showOffenseDice} delay={0} />
            <Die value={offenseRoll?.white1 || 1} color="white" size="md" animate={isRolling} settled={showOffenseDice} delay={100} />
            <Die value={offenseRoll?.white2 || 1} color="white" size="md" animate={isRolling} settled={showOffenseDice} delay={200} />
          </div>
          <span className={`text-lg font-bold ${showTotals ? 'opacity-100' : 'opacity-0'} text-blue-400 w-8 text-center`}>{offenseTotal}</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-purple-400 w-6">DEF</span>
          <div className="flex gap-2">
            <Die value={defenseRoll?.red || 1} color="red" size="md" animate={isRolling} settled={showDefenseDice} delay={400} />
            <Die value={defenseRoll?.green || 1} color="green" size="md" animate={isRolling} settled={showDefenseDice} delay={500} />
          </div>
          <span className={`text-lg font-bold ${showTotals ? 'opacity-100' : 'opacity-0'} text-purple-400 w-8 text-center`}>{defenseTotal}</span>
        </div>
      </div>
      
      {description && (
        <div className="text-center text-white text-sm mt-2 pt-2 border-t border-gray-700">
          {description}
        </div>
      )}
    </div>
  )
}

const BLACK_DIE = [1, 1, 2, 2, 3, 3]
const WHITE_DIE = [0, 1, 2, 3, 4, 5]
const RED_DIE = [1, 1, 1, 2, 2, 3]
const GREEN_DIE = [0, 0, 0, 0, 1, 2]

const randomFrom = (arr) => arr[Math.floor(Math.random() * arr.length)]
const randomFromRange = (min, max) => min + Math.floor(Math.random() * (max - min + 1))

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
        white1: randomFrom(WHITE_DIE),
        white2: randomFrom(WHITE_DIE),
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
