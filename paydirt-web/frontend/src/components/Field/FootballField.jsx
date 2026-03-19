import { useMemo } from 'react'

const YARD_LINES = [
  { yard: 50, label: '50' },
  { yard: 40, label: '40' },
  { yard: 30, label: '30' },
  { yard: 20, label: '20' },
  { yard: 10, label: '10' },
  { yard: 0, label: 'END' },
  { yard: 10, label: '10' },
  { yard: 20, label: '20' },
  { yard: 30, label: '30' },
  { yard: 40, label: '40' },
  { yard: 50, label: '50' },
]

export function FootballField({ 
  ballPosition = 35, 
  possession = 'home', 
  homeEndzoneColor = '#8B0000', 
  awayEndzoneColor = '#1E3A8A',
  homeTeamName = 'HOME',
  awayTeamName = 'AWAY',
}) {
  const ballStyle = useMemo(() => {
    const percentage = (ballPosition / 100) * 100
    return {
      left: `${percentage}%`,
      transform: 'translateX(-50%)',
    }
  }, [ballPosition])

  const directionArrow = possession === 'home' ? '→' : '←'

  return (
    <div className="relative w-full" data-testid="football-field">
      <div 
        className="relative h-32 overflow-hidden rounded-lg border-4 border-white shadow-xl"
        style={{ backgroundColor: 'var(--field-green)' }}
      >
        <div 
          className="absolute inset-0"
          style={{
            backgroundImage: `repeating-linear-gradient(
              90deg,
              transparent,
              transparent 9.5%,
              var(--field-stripe) 9.5%,
              var(--field-stripe) 10%
            )`,
          }}
        />

        <div 
          className="absolute top-0 bottom-0 flex items-center justify-center font-bold text-white text-sm border-2 border-white"
          style={{ 
            left: '0%', 
            width: '5%', 
            backgroundColor: homeEndzoneColor,
            writingMode: 'vertical-rl',
            textOrientation: 'mixed',
          }}
        >
          <span className="transform rotate-180">{homeTeamName}</span>
        </div>

        <div 
          className="absolute top-0 bottom-0 flex items-center justify-center font-bold text-white text-sm border-2 border-white"
          style={{ 
            right: '0%', 
            width: '5%', 
            backgroundColor: awayEndzoneColor,
            writingMode: 'vertical-rl',
          }}
        >
          <span>{awayTeamName}</span>
        </div>

        <div className="absolute inset-0 flex items-center" style={{ left: '5%', right: '5%' }}>
          {YARD_LINES.map((line, index) => (
            <div
              key={index}
              className="absolute flex flex-col items-center"
              style={{ left: `${(index / (YARD_LINES.length - 1)) * 100}%` }}
            >
              <div 
                className="w-0.5 bg-white h-full"
                data-testid={`yard-line-${line.yard}`}
              />
              <span className="absolute top-1 text-white text-xs font-bold px-1 rounded bg-black/30">
                {line.label}
              </span>
            </div>
          ))}
        </div>

        <div className="absolute inset-0 flex items-center" style={{ left: '5%', right: '5%' }}>
          {[5, 15, 25, 35, 45, 55, 65, 75, 85, 95].map((x) => (
            <div
              key={x}
              className="absolute w-0.5 h-2 bg-white"
              style={{ left: `${x}%`, opacity: 0.5 }}
            />
          ))}
        </div>

        <div
          className="absolute top-1/2 transform -translate-y-1/2 z-10"
          style={ballStyle}
          data-testid="ball-marker"
        >
          <div className="relative">
            <div 
              className="w-6 h-4 bg-amber-600 rounded-full border-2 border-amber-800 shadow-lg"
              style={{
                boxShadow: '0 2px 4px rgba(0,0,0,0.3), inset 0 -2px 4px rgba(0,0,0,0.2)',
              }}
            >
              <div className="absolute inset-x-1 top-1/2 transform -translate-y-1/2 h-0.5 bg-white opacity-70" />
            </div>
            <div 
              className="absolute -right-2 top-1/2 transform -translate-y-1/2 text-base font-bold text-white drop-shadow-lg"
              style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.8)' }}
            >
              {directionArrow}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-1 flex justify-center gap-4 text-xs">
        <span className="text-gray-400">
          Ball at yard line {ballPosition}
        </span>
        <span className="text-gray-500">|</span>
        <span className="text-gray-400">
          {possession === 'home' ? 'Home' : 'Away'} possession
        </span>
      </div>
    </div>
  )
}

export default FootballField
