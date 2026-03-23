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
  onCallTimeout?: () => void;
  canCallTimeout?: boolean;
  isOvertime?: boolean;
  otPeriod?: number;
  homeScoreFlash?: boolean;
  awayScoreFlash?: boolean;
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
  onCallTimeout,
  canCallTimeout = false,
  isOvertime = false,
  otPeriod = 0,
  homeScoreFlash = false,
  awayScoreFlash = false,
}: ScoreboardProps) {
  const homeAbbr = homeTeam?.abbreviation || homeTeam?.short_name || 'HOME'
  const awayAbbr = awayTeam?.abbreviation || awayTeam?.short_name || 'AWAY'
  const homeName = homeTeam?.name || 'Home'
  const awayName = awayTeam?.name || 'Away'
  const homeHasBall = possession === 'home'
  const ordinals = ['1st', '2nd', '3rd', '4th']
  const ordinal = ordinals[down - 1] || `${down}th`

  // Determine which team's timeouts to show based on human team
  const humanTimeouts = humanIsHome ? homeTimeouts : awayTimeouts
  const humanAbbr = humanIsHome ? homeAbbr : awayAbbr

  // Determine quarter display
  const quarterDisplay = isOvertime ? `OT${otPeriod}` : `Q${quarter}`

  return (
    <div className={`px-6 py-3 ${isOvertime ? 'bg-yellow-900' : 'bg-gray-800'}`} data-testid="scoreboard">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-8">
          <div className="text-center">
            <div className={`text-sm font-bold ${homeHasBall ? 'text-white' : 'text-gray-500'}`}>
              {homeAbbr}
            </div>
            <div className="text-xs text-gray-500 mb-1">{homeName}</div>
            <div className={`text-2xl font-bold ${homeHasBall ? 'text-yellow-400' : 'text-gray-600'} ${homeScoreFlash ? 'animate-pulse bg-yellow-500/30 rounded px-2' : ''}`}>
              {homeScore}
            </div>
          </div>
          
          <div className="text-center">
            <div className={`text-sm font-bold ${!homeHasBall ? 'text-white' : 'text-gray-500'}`}>
              {awayAbbr}
            </div>
            <div className="text-xs text-gray-500 mb-1">{awayName}</div>
            <div className={`text-2xl font-bold ${!homeHasBall ? 'text-yellow-400' : 'text-gray-600'} ${awayScoreFlash ? 'animate-pulse bg-yellow-500/30 rounded px-2' : ''}`}>
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
            <div className={`text-lg font-bold ${isOvertime ? 'text-yellow-400' : 'text-white'}`}>
              {quarterDisplay}
            </div>
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
            <div className="flex items-center gap-2">
              <div className="text-sm font-bold text-gray-400">
                {humanTimeouts}
              </div>
              {canCallTimeout && humanTimeouts > 0 && (
                <button
                  onClick={onCallTimeout}
                  className="px-2 py-1 bg-yellow-600 text-white text-xs rounded hover:bg-yellow-500 transition-colors"
                  title={`Call ${humanAbbr} timeout`}
                >
                  TO
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Scoreboard
