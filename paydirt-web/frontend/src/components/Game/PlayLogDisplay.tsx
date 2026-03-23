import { useRef, useEffect } from 'react';

interface DiceRoll {
  black?: number;
  white1?: number;
  white2?: number;
  total?: number;
  red?: number;
  green?: number;
}

interface PlayLogEntry {
  quarter?: number;
  timeRemaining?: number;
  down?: number;
  yardsToGo?: number;
  ballPosition?: number;
  lineOfScrimmage?: number;
  fieldPosition?: string;  // Pre-calculated by backend
  newFieldPosition?: string;  // Post-play position pre-calculated by backend
  offenseTeam?: string;
  defenseTeam?: string;
  homeTeamAbbrev?: string;
  awayTeamAbbrev?: string;
  playerTeam?: string;
  offensePlay?: string;
  defensePlay?: string;
  offenseDice?: DiceRoll;
  defenseDice?: DiceRoll;
  description?: string;
  headline?: string;
  yards?: number;
  newPosition?: number;
  scoreChange?: string;
  humanIsHome?: boolean;
  possession?: 'home' | 'away';
}

function formatFieldPosition(pos: number | undefined, possession: 'home' | 'away' | undefined, homeAbbrev: string, awayAbbrev: string, humanIsHome: boolean | undefined): string {
  if (pos === undefined || pos === null) return '';
  
  const hasBall = possession === 'home';
  
  if (hasBall) {
    // Home team has the ball
    if (pos <= 50) {
      return `${homeAbbrev} ${pos}`;
    } else {
      return `${homeAbbrev} ${100 - pos}`;
    }
  } else {
    // Away team has the ball
    if (pos <= 50) {
      // Ball on home side - away team at opponent's yard line
      return `${awayAbbrev} ${100 - pos}`;
    } else {
      // Ball on away side - away team at their own yard line
      return `${awayAbbrev} ${pos}`;
    }
  }
}

interface PlayLogDisplayProps {
  plays?: PlayLogEntry[];
  onPlayClick?: (play: PlayLogEntry) => void;
}

const PlayLogDisplay = ({ plays = [], onPlayClick }: PlayLogDisplayProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(plays?.length || 0);
  const initialScrollDone = useRef(false);
  
  // Scroll to bottom when:
  // 1. Component first mounts with existing plays (loading from save)
  // 2. New plays are added
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    
    const currentLength = plays?.length || 0;
    
    // Scroll on initial load OR when plays are added
    if ((currentLength > 0 && !initialScrollDone.current) || 
        (currentLength > prevLengthRef.current)) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      });
      initialScrollDone.current = true;
    }
    
    prevLengthRef.current = currentLength;
  }, [plays?.length]);
  
  return (
    <div className="w-full">
      <div className="text-white font-bold mb-2">PLAY LOG</div>
      <div ref={scrollRef} className="h-64 overflow-y-auto border rounded p-2 space-y-1">
        {plays && plays.length > 0 ? plays.map((play, index) => (
          <div
            key={index}
            onClick={() => onPlayClick?.(play)}
            className="cursor-pointer p-2 rounded hover:bg-gray-700 bg-gray-800/50"
          >
            <div className="flex justify-between items-start mb-1">
              <div className="text-xs text-gray-300">
                <span className="font-bold">Q{play.quarter}</span> {' '}
                {play.timeRemaining}"
              </div>
              <div className="text-xs text-gray-400">
                {play.offenseTeam} vs {play.defenseTeam}
              </div>
            </div>
            
            <div className="text-xs text-yellow-400 mb-1">
              {play.down && play.yardsToGo ? 
                `${play.down}&${play.yardsToGo} at ${play.fieldPosition || formatFieldPosition(play.lineOfScrimmage, play.possession, play.homeTeamAbbrev || '', play.awayTeamAbbrev || '', play.humanIsHome)}` : 
                '1st & 10'
              }
            </div>
            
            <div className="flex gap-2 text-xs text-gray-300 mb-1">
              <span className={play.playerTeam === play.offenseTeam ? "text-green-400" : "text-red-400"}>
                OFF: {play.offensePlay}
              </span>
              <span className={play.playerTeam === play.offenseTeam ? "text-red-400" : "text-green-400"}>
                DEF: {play.defensePlay}
              </span>
            </div>
            
            {play.offenseDice && play.defenseDice && (
              <div className="flex gap-2 text-xs text-gray-500 mb-1">
                <span>Off: {play.offenseDice.black}+{play.offenseDice.white1}+{play.offenseDice.white2}={play.offenseDice.total}</span>
                <span>Def: {play.defenseDice.red}+{play.defenseDice.green}={play.defenseDice.total}</span>
              </div>
            )}
            
            <div className="text-sm text-white font-medium">{play.description || play.headline}</div>
            
            {play.yards !== undefined && play.yards !== 0 && play.description && (
              <div className={`text-xs ${play.yards > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {play.description.toLowerCase().includes('punt') ? 
                  `Punt: ${Math.abs(play.yards)} yards` : 
                  play.yards > 0 ? `+${play.yards} yards` : `${play.yards} yards`}
              </div>
            )}
            
            {play.newPosition !== undefined && (
              <div className="text-xs text-gray-400">
                New: {play.newFieldPosition || formatFieldPosition(play.newPosition, play.possession, play.homeTeamAbbrev || '', play.awayTeamAbbrev || '', play.humanIsHome)}
              </div>
            )}
            
            {play.scoreChange && (
              <div className="text-xs font-bold text-yellow-400 mt-1">
                {play.scoreChange}
              </div>
            )}
          </div>
        )) : (
          <div className="text-gray-400 text-sm">No plays yet</div>
        )}
      </div>
    </div>
  );
};

export default PlayLogDisplay;
