import { useMemo } from 'react'

export function FootballField({ 
  ballPosition = 35, 
  possession = 'home',
  homeEndzoneColor = '#8B0000',
  awayEndzoneColor = '#1E3A8A',
  homeTeamName = 'HOME',
  awayTeamName = 'AWAY',
  yardsToGo = 10,
}) {
  // When possession is 'home', offense is home team, they drive LEFT to RIGHT
  // When possession is 'away', offense is away team, they drive LEFT to RIGHT
  // Ball position is always from offense perspective: 0 = own EZ, 100 = opponent's EZ
  // So when home has possession: ball at 35 means 35 yards from home's end zone
  // So when away has possession: ball at 35 means 35 yards from away's end zone
  
  // The field view should always show offense driving left-to-right
  // Left end zone = offense's end zone, Right end zone = defense's end zone
  
  const isHomePossession = possession === 'home'
  
  // Ball position: 0 = left end zone, 100 = right end zone
  // The playing field starts at ~8% (after 48px left end zone) and ends at ~92%
  // So ballPosition 1 should be just past 8%, ballPosition 99 should be just before 92%
  const FIELD_LEFT = 8;   // Left edge of playing field (% from left)
  const FIELD_RIGHT = 92; // Right edge of playing field (% from left)
  const FIELD_WIDTH = FIELD_RIGHT - FIELD_LEFT;
  
  // Scale ball position to fit within the playing field
  const visualPosition = FIELD_LEFT + ((ballPosition / 100) * FIELD_WIDTH);
  
  const ballStyle = useMemo(() => {
    return { left: `${visualPosition}%`, transform: 'translateX(-50%)' }
  }, [visualPosition])

  // First down marker
  const firstDownPos = FIELD_LEFT + (((ballPosition + yardsToGo) / 100) * FIELD_WIDTH);
  
  const firstDownStyle = useMemo(() => {
    return { left: `${firstDownPos}%` }
  }, [firstDownPos])

  // Yard lines: 10, 20, 30, 40, 50 in middle, then mirrored on right side
  // Left side (near offense): 10, 20, 30, 40, 50
  // Right side (near defense): 50, 40, 30, 20, 10
  const yardLines = [
    { pos: 10, label: '10' },
    { pos: 20, label: '20' },
    { pos: 30, label: '30' },
    { pos: 40, label: '40' },
    { pos: 50, label: '50' },
    { pos: 60, label: '40' },
    { pos: 70, label: '30' },
    { pos: 80, label: '20' },
    { pos: 90, label: '10' },
  ]

  // End zones: left is offense's EZ, right is defense's EZ
  // When home has ball: left end zone = home, right = away
  // When away has ball: left end zone = away, right = home
  const leftEndzoneTeam = isHomePossession ? homeTeamName : awayTeamName
  const rightEndzoneTeam = isHomePossession ? awayTeamName : homeTeamName
  const leftEndzoneColor = isHomePossession ? homeEndzoneColor : awayEndzoneColor
  const rightEndzoneColor = isHomePossession ? awayEndzoneColor : homeEndzoneColor

  return (
    <div className="relative w-full h-48 rounded-lg overflow-hidden shadow-xl border-2 border-white bg-green-700" data-testid="football-field">
      
      {/* Left end zone (offense's end zone) */}
      <div className="absolute left-0 top-0 bottom-0 w-12 flex items-center justify-center" style={{ backgroundColor: leftEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl' }}>{leftEndzoneTeam}</span>
      </div>
      
      {/* Right end zone (defense's end zone) */}
      <div className="absolute right-0 top-0 bottom-0 w-12 flex items-center justify-center" style={{ backgroundColor: rightEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>{rightEndzoneTeam}</span>
      </div>

      <div className="absolute inset-0" style={{ left: '48px', right: '48px' }}>
        {yardLines.map(({ pos, label }) => (
          <div key={pos} className="absolute top-0 bottom-0" style={{ left: `${pos}%` }}>
            <div className="w-0.5 h-full bg-white" />
            <div className="absolute top-1 left-1/2 -translate-x-1/2 text-white text-[10px] font-bold bg-black/30 px-0.5 rounded">
              {label}
            </div>
          </div>
        ))}
        
        {/* Hide first down marker when it's goal to go (yardsToGo >= ballPosition means at or past goal line) */}
        {yardsToGo < ballPosition && (
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
      </div>

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
