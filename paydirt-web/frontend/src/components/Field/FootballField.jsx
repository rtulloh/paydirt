import { useMemo } from 'react'

export function FootballField({
  ballPosition = 35,
  possession = 'home',
  quarter = 1,
  homeEndzoneColor = '#8B0000',
  awayEndzoneColor = '#1E3A8A',
  homeTeamName = 'HOME',
  awayTeamName = 'AWAY',
  yardsToGo = 10,
}) {
  // Single coordinate system for all field elements.
  // Each yard = 0.84% of the container (100 yards = 84%).
  // Each end zone = 10 yards = 8.4% of the container.
  const END_ZONE = 8.4
  const YARD = 0.84
  const toPct = (yard) => END_ZONE + yard * YARD

  // Track which endzone each team is attacking based on quarter
  // Q1-Q2: HOME endzone on LEFT, AWAY endzone on RIGHT
  // Q3-Q4: AWAY endzone on LEFT, HOME endzone on RIGHT (teams swap at halftime)
  const homeOnLeft = quarter < 3

  // Determine attack direction: RIGHT if possession matches homeOnLeft
  // HOME in Q1-Q2: RIGHT (homeOnLeft=true, home=true → match → RIGHT)
  // HOME in Q3-Q4: LEFT (homeOnLeft=false, home=true → no match → LEFT)
  // AWAY in Q1-Q2: LEFT (homeOnLeft=true, home=false → no match → LEFT)
  // AWAY in Q3-Q4: RIGHT (homeOnLeft=false, home=false → match → RIGHT)
  const isHomePossession = possession === 'home'
  const attackingRight = homeOnLeft === isHomePossession

  // Convert ball position from "yards from own goal" to field coordinates
  // ball_position is always measured from the possessing team's own goal
  // We need to convert to distance from the LEFT endzone
  const fieldBallPosition = isHomePossession
    ? (homeOnLeft ? ballPosition : 100 - ballPosition)  // HOME goal on LEFT: use directly; on RIGHT: flip
    : (homeOnLeft ? 100 - ballPosition : ballPosition)  // AWAY goal on RIGHT: flip; on LEFT: use directly
  const ballPct = toPct(fieldBallPosition)

  const ballStyle = useMemo(() => ({
    left: `${ballPct}%`,
    // The SVG ellipse tip is 2 px from the right edge of the 40 px container
    // (cx=20 + rx=18 = 38). 
    // When attacking RIGHT: shift left so right tip sits on yard line
    // When attacking LEFT: flip horizontally, then shift so left tip sits on yard line
    transform: attackingRight
      ? 'translateX(calc(-100% + 2px))'
      : 'scaleX(-1)',
    // Smooth animation for ball movement
    transition: 'left 0.6s ease-out',
  }), [ballPct, attackingRight])

  // Convert first down yard line from "yards from own goal" to field coordinates
  const firstDownYard = ballPosition + yardsToGo
  const fieldFirstDownYard = possession === 'home'
    ? (homeOnLeft ? firstDownYard : 100 - firstDownYard)
    : (homeOnLeft ? 100 - firstDownYard : firstDownYard)
  const firstDownPct = toPct(fieldFirstDownYard)

  const firstDownStyle = useMemo(() => ({
    left: `${firstDownPct}%`,
    // Smooth animation for first-down marker movement
    transition: 'left 0.6s ease-out',
  }), [firstDownPct])

  const yardLines = [
    { yard: 10, label: '10' },
    { yard: 20, label: '20' },
    { yard: 30, label: '30' },
    { yard: 40, label: '40' },
    { yard: 50, label: '50' },
    { yard: 60, label: '40' },
    { yard: 70, label: '30' },
    { yard: 80, label: '20' },
    { yard: 90, label: '10' },
  ]

  // Endzones swap at halftime based on quarter
  const leftEndzoneTeam = homeOnLeft ? homeTeamName : awayTeamName
  const rightEndzoneTeam = homeOnLeft ? awayTeamName : homeTeamName
  const leftEndzoneColor = homeOnLeft ? homeEndzoneColor : awayEndzoneColor
  const rightEndzoneColor = homeOnLeft ? awayEndzoneColor : homeEndzoneColor

  // First-down marker is hidden on goal-to-go
  const isGoalToGo = yardsToGo >= (100 - ballPosition)

  return (
    <div className="relative w-full h-48 rounded-lg overflow-hidden shadow-xl border-2 border-white bg-green-700" data-testid="football-field">

      {/* Left end zone (offense) */}
      <div className="absolute left-0 top-0 bottom-0 flex items-center justify-center" style={{ width: `${END_ZONE}%`, backgroundColor: leftEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl' }}>{leftEndzoneTeam}</span>
      </div>

      {/* Right end zone (defense) */}
      <div className="absolute right-0 top-0 bottom-0 flex items-center justify-center" style={{ width: `${END_ZONE}%`, backgroundColor: rightEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>{rightEndzoneTeam}</span>
      </div>

      {/* Yard lines – all positioned in the same coordinate system as the ball */}
      {yardLines.map(({ yard, label }) => (
        <div key={yard} className="absolute top-0 bottom-0" style={{ left: `${toPct(yard)}%` }}>
          <div className="w-0.5 h-full bg-white" />
          <div className="absolute top-1 left-1/2 -translate-x-1/2 text-white text-[10px] font-bold bg-black/30 px-0.5 rounded">
            {label}
          </div>
        </div>
      ))}

      {/* First-down marker */}
      {!isGoalToGo && (
        <div
          className="absolute z-20"
          style={{ left: firstDownStyle.left, top: 0, bottom: 0 }}
        >
          <div className="absolute left-1/2 -translate-x-1/2 top-2 w-1 h-full bg-yellow-400 shadow-md rounded-full" />
          <div className="absolute left-1/2 -translate-x-1/2 -top-1 w-3 h-3 bg-yellow-400 rounded-full shadow-lg border-2 border-yellow-500" />
          <div className="absolute left-1/2 -translate-x-1/2 -top-5 text-yellow-400 text-[9px] font-bold whitespace-nowrap bg-black/70 px-1 py-0.5 rounded">
            1ST
          </div>
        </div>
      )}

      {/* Football */}
      <div
        className="absolute top-1/2 -translate-y-1/2 z-30"
        style={ballStyle}
        data-testid="ball-marker"
      >
        <div className="relative w-10 h-6">
          <svg viewBox="0 0 40 24" className="w-full h-full">
            <ellipse cx="20" cy="12" rx="18" ry="10" fill="#8B4513" />
            <ellipse cx="20" cy="12" rx="16" ry="8" fill="#A0522D" />
            <path d="M8 12 L32 12" stroke="white" strokeWidth="1.5" />
            <path d="M10 10 L10 14 M14 9 L14 15 M18 8.5 L18 15.5 M22 8.5 L22 15.5 M26 9 L26 15 M30 10 L30 14" stroke="white" strokeWidth="1" />
          </svg>
        </div>
      </div>
    </div>
  )
}

export default FootballField
