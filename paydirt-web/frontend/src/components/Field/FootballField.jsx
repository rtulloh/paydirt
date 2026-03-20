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
  const ballStyle = useMemo(() => {
    const percentage = (ballPosition / 100) * 100
    return { left: `${percentage}%`, transform: 'translateX(-50%)' }
  }, [ballPosition])

  const firstDownStyle = useMemo(() => {
    const firstDownPos = Math.min(100, Math.max(0, ballPosition + yardsToGo))
    const percentage = (firstDownPos / 100) * 100
    return { left: `${percentage}%` }
  }, [ballPosition, yardsToGo])

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

  return (
    <div className="relative w-full h-48 rounded-lg overflow-hidden shadow-xl border-2 border-white bg-green-700" data-testid="football-field">
      
      <div className="absolute left-0 top-0 bottom-0 w-12 flex items-center justify-center" style={{ backgroundColor: homeEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl' }}>{homeTeamName}</span>
      </div>
      <div className="absolute right-0 top-0 bottom-0 w-12 flex items-center justify-center" style={{ backgroundColor: homeEndzoneColor }}>
        <span className="text-white text-xs font-bold" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>{homeTeamName}</span>
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
