interface PenaltyOption {
  penalty_type?: string;
  raw_result?: string;
  yards?: number;
  description?: string;
  auto_first_down?: boolean;
  is_pass_interference?: boolean;
}

interface PenaltyChoice {
  penalty_options?: PenaltyOption[];
  offended_team?: string;
  offsetting?: boolean;
  is_pass_interference?: boolean;
  reroll_log?: string[];
}

interface PenaltyData {
  description?: string;
  yards?: number;
  turnover?: boolean;
  touchdown?: boolean;
  pending_penalty_decision?: boolean;
  penalty_choice?: PenaltyChoice | null;
  new_down?: number;
  new_yards_to_go?: number;
  new_ball_position?: number;
  play_type?: string;
}

interface PenaltyDecisionPanelProps {
  penaltyData?: PenaltyData | null;
  onDecision?: (acceptPenalty: boolean, penaltyIndex: number) => void;
  cpuIsOnDefense?: boolean;
}

const PenaltyDecisionPanel = ({ penaltyData, onDecision, cpuIsOnDefense = false }: PenaltyDecisionPanelProps) => {
  if (!penaltyData) {
    return null;
  }

  const penalty_choice = penaltyData.penalty_choice;
  
  if (!penalty_choice) {
    return null;
  }

  const yards = penaltyData.yards || 0;
  const turnover = penaltyData.turnover || false;
  const newDown = penaltyData.new_down;
  const newYardsToGo = penaltyData.new_yards_to_go;
  const newBallPosition = penaltyData.new_ball_position;

    // Detect touchdown: engine may not flag TD for small gains near goal line.
    // When pending_penalty_decision, new_ball_position is pre-play; if
    // position + yards >= 100 the play result would score.
    const isTouchdown = penaltyData.touchdown ||
      (!turnover && (newBallPosition || 0) + yards >= 100);

    const formatFieldPosition = (pos: number): string => {
    if (pos <= 50) return `OWN ${pos}`;
    return `OPP ${100 - pos}`;
  };

  const formatDown = (down: number): string => {
    if (down === 1) return '1st';
    if (down === 2) return '2nd';
    if (down === 3) return '3rd';
    return `${down}th`;
  };

  const getPenaltyResult = (opt: PenaltyOption): { down: number; yardsToGo: number; ballPos: number } => {
    const penaltyYards = opt.yards || 0;
    const startingPos = newBallPosition || 50;
    const newPos = Math.max(0, Math.min(100, startingPos - penaltyYards));
    const gained = penaltyYards;
    
    let down = 1;
    let yardsToGo = 10;
    
    if (opt.auto_first_down) {
      down = 1;
      yardsToGo = 10;
    } else if (gained >= (newYardsToGo || 10)) {
      down = 1;
      yardsToGo = 10;
    } else {
      down = (newDown || 1) + 1;
      yardsToGo = (newYardsToGo || 10) - gained;
    }
    
    return { down, yardsToGo: Math.max(1, yardsToGo), ballPos: newPos };
  };

  const formatPenaltyChoice = (opt: PenaltyOption): string => {
    const result = getPenaltyResult(opt);
    return `${formatDown(result.down)} & ${result.yardsToGo} at ${formatFieldPosition(result.ballPos)}`;
  };

  const getPlayResultSummary = (): string => {
    if (turnover) {
      return `TURNOVER at ${formatFieldPosition(newBallPosition || 0)}`;
    }
    if (isTouchdown) {
      return 'TOUCHDOWN!';
    }

    // Special plays: FG, punt, kickoff show play-specific text, not generic yardage
    const playType = penaltyData.play_type || '';
    if (playType === 'field_goal') {
      return penaltyData.description || 'Field Goal attempt';
    }
    if (playType === 'punt') {
      return penaltyData.description || 'Punt';
    }
    if (playType === 'kickoff') {
      return penaltyData.description || 'Kickoff';
    }

    // Calculate the actual new position based on play result
    // newBallPosition is the position AFTER penalty application, but we want position AFTER play
    const playStartPos = penaltyData.line_of_scrimmage || 50;
    const actualNewPos = Math.min(100, playStartPos + yards);

    if (yards > 0) {
      return `+${yards} yards → ${formatFieldPosition(actualNewPos)}`;
    } else if (yards < 0) {
      return `${yards} yards → ${formatFieldPosition(actualNewPos)}`;
    }
    return `No gain → ${formatFieldPosition(playStartPos)}`;
  };
  
  const isDefenseChoosing = penalty_choice.offended_team === 'defense';
  const cpuDeciding = isDefenseChoosing && cpuIsOnDefense;
  
  return (
<div className="bg-yellow-700 rounded-lg px-4 py-4 text-center border-2 border-yellow-500">
      <div className="text-xl font-bold text-white mb-3">PENALTY ON THE PLAY!</div>
      
      {penalty_choice.offsetting ? (
        <div className="text-white mb-4">
          <div className="text-lg font-bold mb-2">OFFSETTING PENALTIES</div>
          <div className="text-yellow-200">Down will be replayed</div>
          <div className="flex justify-center mt-4">
            <button
              onClick={() => onDecision?.(false, 0)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
            >
              CONTINUE
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Choice header - shows who is deciding */}
          <div className="text-yellow-200 text-sm mb-3">
            {cpuDeciding 
              ? 'CPU is deciding...'
              : isDefenseChoosing 
              ? 'OFFENSE committed penalty - Your choice (Defense)'
              : 'DEFENSE committed penalty - Your choice (Offense)'}
          </div>
          
          <div className="bg-gray-800 rounded-lg p-3 mb-4">
            {/* Play Result section */}
            <div className="text-white text-sm mb-2 font-bold">
              {isDefenseChoosing 
                ? 'Play Result (if DECLINED, down counts):' 
                : 'ACCEPT PLAY RESULT:'}
            </div>
            <div className="text-white font-bold text-lg mb-1">
              {penaltyData.description || getPlayResultSummary()}
            </div>
            <div className="text-gray-300 text-sm">
              {formatDown(newDown)} & {newYardsToGo}
            </div>
            {turnover && (
              <div className="text-red-400 font-bold mt-1">TURNOVER!</div>
            )}
            {isTouchdown && (
              <div className="text-green-400 font-bold mt-1">TOUCHDOWN!</div>
            )}
          </div>
          
          {/* Penalty Options */}
          {penalty_choice.penalty_options && 
           penalty_choice.penalty_options.length > 0 && (
            <div className="mb-4">
              <div className="text-yellow-200 text-sm mb-2 font-bold">
                Penalty Options ({penalty_choice.offended_team === 'offense' ? 'DEFENSE' : 'OFFENSE'} is offended):
              </div>
              <div className="flex flex-col gap-2">
                {penalty_choice.penalty_options.map((opt, idx) => (
                  <button
                    key={idx}
                    onClick={() => onDecision?.(true, idx)}
                    disabled={cpuDeciding}
                    className={`px-4 py-3 rounded-lg font-bold text-left ${cpuDeciding ? 'bg-gray-600 text-gray-400 cursor-not-allowed' : 'bg-red-600 text-white hover:bg-red-700 transition-all'}`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm">[{idx + 2}] {opt.description}</span>
                      {opt.auto_first_down && (
                        <span className="text-yellow-300 text-sm ml-2">AUTO 1ST</span>
                      )}
                    </div>
                    {opt.yards !== 0 && (
                      <div className={`text-xs mt-1 ${cpuDeciding ? 'text-gray-500' : 'text-red-200'}`}>
                        {opt.yards > 0 ? '+' : ''}{opt.yards} yards → {formatPenaltyChoice(opt)}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <div className="flex flex-col gap-2">
            {/* When DEFENSE is choosing - show DECLINE option */}
            {isDefenseChoosing && (
              <button
                onClick={() => onDecision?.(false, 0)}
                disabled={cpuDeciding}
                className={`px-6 py-3 rounded-lg font-bold ${cpuDeciding ? 'bg-gray-600 text-gray-400 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700 transition-all'}`}
              >
                [1] REJECT PENALTY - Keep {getPlayResultSummary()}
              </button>
            )}
            {/* When OFFENSE is choosing - show ACCEPT option */}
            {!isDefenseChoosing && (
              <button
                onClick={() => onDecision?.(false, 0)}
                disabled={cpuDeciding}
                className={`px-6 py-3 rounded-lg font-bold ${cpuDeciding ? 'bg-gray-600 text-gray-400 cursor-not-allowed' : 'bg-green-600 text-white hover:bg-green-700 transition-all'}`}
              >
                [1] TAKE YARDAGE - Keep {getPlayResultSummary()}
              </button>
            )}
          </div>
          
          {/* Show reroll log if available */}
          {penalty_choice.reroll_log && penalty_choice.reroll_log.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-700">
              <div className="text-gray-500 text-xs mb-1">Penalty Reroll Log:</div>
              <div className="text-gray-400 text-xs space-y-1">
                {penalty_choice.reroll_log.map((log, idx) => (
                  <div key={idx}>{log}</div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PenaltyDecisionPanel;
