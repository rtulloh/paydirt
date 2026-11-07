interface PenaltyOption {
  penalty_type?: string;
  raw_result?: string;
  yards?: number;
  description?: string;
  auto_first_down?: boolean;
  is_pass_interference?: boolean;
  result_preview?: string | null;
}

interface PenaltyChoice {
  penalty_options?: PenaltyOption[];
  offended_team?: string;
  offsetting?: boolean;
  is_pass_interference?: boolean;
  reroll_log?: string[];
  kick_phase?: string;
  play_result_preview?: string | null;
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

  const turnover = penaltyData.turnover || false;
  const isTouchdown = penaltyData.touchdown || false;
  // The engine supplies projected situations. A legacy response can provide
  // a retained description, but cannot supply an unrecorded field position.
  const getPlayResultSummary = (): string =>
    penalty_choice.play_result_preview || penaltyData.description || 'play result';

  const isDefenseChoosing = penalty_choice.offended_team === 'defense';
  const cpuDeciding = isDefenseChoosing && cpuIsOnDefense;
  // Kickoffs: the receiving team is "offense"; a receiving-team foul is the kicking team's choice.
  const isKickoff = penaltyData.play_type === 'kickoff';
  const chooserLabel = isKickoff
    ? (isDefenseChoosing
      ? 'RECEIVING TEAM committed penalty - Your choice (Kicking team)'
      : 'KICKING TEAM committed penalty - Your choice (Receiving team)')
    : (isDefenseChoosing
      ? 'OFFENSE committed penalty - Your choice (Defense)'
      : 'DEFENSE committed penalty - Your choice (Offense)');
  
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
            {cpuDeciding ? 'CPU is deciding...' : chooserLabel}
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
              {penalty_choice.play_result_preview}
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
                Penalty Options:
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
                    {opt.result_preview && (
                      <div className={`text-xs mt-1 ${cpuDeciding ? 'text-gray-500' : 'text-red-200'}`}>
                        {opt.result_preview}
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
