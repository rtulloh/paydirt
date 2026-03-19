const QUARTERS = ['I', 'II', 'III', 'IV', 'OT']

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function TimeoutDots({ remaining, total = 3 }) {
  return (
    <div className="flex gap-1" data-testid="timeout-dots">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`w-3 h-3 rounded-full ${
            i < remaining ? 'bg-led-red' : 'bg-led-off'
          }`}
          data-testid={`timeout-dot-${i}`}
        />
      ))}
    </div>
  )
}

function ScoreDisplay({ score, label }) {
  return (
    <div className="text-center" data-testid={`score-${label.toLowerCase()}`}>
      <div 
        className="text-xs text-gray-400 uppercase tracking-wider"
        data-testid={`score-${label.toLowerCase()}-label`}
      >
        {label}
      </div>
      <div 
        className="led-score text-3xl"
        data-testid={`score-${label.toLowerCase()}-value`}
      >
        {score}
      </div>
    </div>
  )
}

function ClockDisplay({ time, quarter }) {
  return (
    <div className="text-center" data-testid="clock-display">
      <div className="text-xs text-gray-400">TIME</div>
      <div 
        className="led-clock text-2xl"
        data-testid="clock-value"
      >
        {formatTime(time)}
      </div>
      <div>
        <span className="text-xs text-gray-300">
          Q{QUARTERS[quarter - 1] || quarter}
        </span>
      </div>
    </div>
  )
}

function DownDistance({ down, yardsToGo, fieldPosition, teamAbbr }) {
  const ordinals = ['1st', '2nd', '3rd', '4th']
  const ordinal = ordinals[down - 1] || `${down}th`
  
  return (
    <div className="text-center" data-testid="down-distance">
      <div className="text-xs text-gray-400">DOWN & DIST</div>
      <div 
        className="text-lg font-bold text-white"
        data-testid="down-distance-value"
      >
        {ordinal} & {yardsToGo}
      </div>
      <div className="text-xs text-gray-400" data-testid="field-position">
        at {teamAbbr} {fieldPosition}
      </div>
    </div>
  )
}

export function Scoreboard({ 
  homeTeam, 
  awayTeam, 
  homeScore = 0, 
  awayScore = 0, 
  quarter = 1, 
  timeRemaining = 900,
  down = 1,
  yardsToGo = 10,
  ballPosition = 35,
  possession = 'home',
  homeTimeouts = 3,
  awayTimeouts = 3,
}) {
  const homeAbbr = homeTeam?.abbreviation || homeTeam?.short_name || 'HOME'
  const awayAbbr = awayTeam?.abbreviation || awayTeam?.short_name || 'AWAY'
  const homeName = homeTeam?.name || 'Home Team'
  const awayName = awayTeam?.name || 'Away Team'
  const homeHasBall = possession === 'home'

  return (
    <div 
      className="board-panel overflow-hidden"
      data-testid="scoreboard"
    >
      <div className="board-panel-header text-center text-lg tracking-widest py-1">
        ⚽ PAYDIRT ⚽
      </div>

      <div className="bg-led-bg p-3">
          <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-center">
              <div 
                className={`text-sm font-bold text-white ${homeHasBall ? 'opacity-100' : 'opacity-60'}`}
                data-testid="home-team"
              >
                {homeAbbr} {homeHasBall && <span className="text-led-red">●</span>}
              </div>
              <div className="text-xs font-bold text-gray-300">{homeName}</div>
              <div className="mt-1">
                <TimeoutDots remaining={homeTimeouts} />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <ScoreDisplay score={homeScore} label={homeAbbr} />
            
            <div className="text-2xl text-gray-500 font-bold">:</div>
            
            <ScoreDisplay score={awayScore} label={awayAbbr} />
          </div>

          <div className="flex items-center gap-3">
            <div className="text-center">
              <div 
                className={`text-sm font-bold text-white ${!homeHasBall ? 'opacity-100' : 'opacity-60'}`}
                data-testid="away-team"
              >
                {awayAbbr} {!homeHasBall && <span className="text-led-red">●</span>}
              </div>
              <div className="text-xs font-bold text-gray-300">{awayName}</div>
              <div className="mt-1">
                <TimeoutDots remaining={awayTimeouts} />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-700 flex justify-between items-center">
          <ClockDisplay time={timeRemaining} quarter={quarter} />
          
          <div className="flex-1 flex justify-center">
            <DownDistance 
              down={down} 
              yardsToGo={yardsToGo} 
              fieldPosition={ballPosition}
              teamAbbr={homeHasBall ? homeAbbr : awayAbbr}
            />
          </div>
          
          <div className="text-center min-w-[60px]">
            <div className="text-xs text-gray-400">TO</div>
            <div className="text-led-blue text-sm font-bold">
              {homeTimeouts} / {awayTimeouts}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Scoreboard
