interface Team {
  id?: string;
  name?: string;
  short_name?: string;
  abbreviation?: string;
  team_color?: string;
}

interface ScoreboardProps {
  homeTeam?: Team | null;
  awayTeam?: Team | null;
  homeScore?: number;
  awayScore?: number;
  quarter?: number;
  timeRemaining?: number;
  down?: number;
  yardsToGo?: number;
  homeTimeouts?: number;
  awayTimeouts?: number;
  possession?: 'home' | 'away';
  ballPosition?: number;
  fieldPosition?: string;
  humanIsHome?: boolean;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
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
  homeTimeouts = 3,
  awayTimeouts = 3,
  possession = 'home',
  ballPosition = 35,
  fieldPosition = '',
  humanIsHome = true,
}: ScoreboardProps) {
  const homeAbbr = homeTeam?.abbreviation || homeTeam?.short_name || 'HOME'
  const awayAbbr = awayTeam?.abbreviation || awayTeam?.short_name || 'AWAY'
  const homeName = homeTeam?.name || 'Home'
  const awayName = awayTeam?.name || 'Away'
  const homeHasBall = possession === 'home'
  const ordinals = ['1st', '2nd', '3rd', '4th']
  const ordinal = ordinals[down - 1] || `${down}th`

  return (
    <div className="bg-gray-800 px-6 py-3" data-testid="scoreboard">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-8">
          <div className="text-center">
            <div className={`text-sm font-bold ${homeHasBall ? 'text-white' : 'text-gray-500'}`}>
              {homeAbbr}
            </div>
            <div className="text-xs text-gray-500 mb-1">{homeName}</div>
            <div className={`text-2xl font-bold ${homeHasBall ? 'text-yellow-400' : 'text-gray-600'}`}>
              {homeScore}
            </div>
          </div>
          
          <div className="text-center">
            <div className={`text-sm font-bold ${!homeHasBall ? 'text-white' : 'text-gray-500'}`}>
              {awayAbbr}
            </div>
            <div className="text-xs text-gray-500 mb-1">{awayName}</div>
            <div className={`text-2xl font-bold ${!homeHasBall ? 'text-yellow-400' : 'text-gray-600'}`}>
              {awayScore}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-8">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">TIME</div>
            <div className="text-lg font-bold text-cyan-400">
              {formatTime(timeRemaining)}
            </div>
          </div>

          <div className="text-center px-4 border-l border-gray-700">
            <div className="text-xs text-gray-500 mb-1">QUARTER</div>
            <div className="text-lg font-bold text-white">Q{quarter}</div>
          </div>

          <div className="text-center px-4 border-l border-gray-700">
            <div className="text-xs text-gray-500 mb-1">DOWN & DIST</div>
            <div className="text-lg font-bold text-white">
              {ordinal} & {yardsToGo >= (100 - ballPosition) ? 'Goal' : yardsToGo}
            </div>
          </div>

          <div className="text-center px-4 border-l border-gray-700">
            <div className="text-xs text-gray-500 mb-1">POS</div>
            <div className="text-lg font-bold text-yellow-400">
              {fieldPosition}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">TIMEOUTS</div>
            <div className="text-sm font-bold text-gray-400">
              {homeTimeouts} - {awayTimeouts}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Scoreboard
