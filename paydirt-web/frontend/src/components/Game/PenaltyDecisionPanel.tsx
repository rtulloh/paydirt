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
}

interface PenaltyDecisionPanelProps {
  penaltyData?: PenaltyData | null;
  onDecision?: (acceptPenalty: boolean, penaltyIndex: number) => void;
}

const PenaltyDecisionPanel = ({ penaltyData, onDecision }: PenaltyDecisionPanelProps) => {
  if (!penaltyData) {
    return null;
  }

  const penalty_choice = penaltyData.penalty_choice;
  
  if (!penalty_choice) {
    return null;
  }

  const yards = penaltyData.yards || 0;
  const turnover = penaltyData.turnover || false;
  const touchdown = penaltyData.touchdown || false;
  const newDown = penaltyData.new_down;
  const newYardsToGo = penaltyData.new_yards_to_go;
  const newBallPosition = penaltyData.new_ball_position;

    const formatFieldPosition = (pos: number): string => {
    if (pos <= 50) return `OWN ${pos}`;
    return `OPP ${100 - pos}`;
  };

  const formatLOS = (pos: number): string => {
    if (pos <= 50) return `OWN ${pos}`;
    return `OPP ${100 - pos}`;
  };

  const formatDown = (down: number): string => {
    if (down === 1) return '1st';
    if (down === 2) return '2nd';
    if (down === 3) return '3rd';
    return `${down}th`;
  };

  const getPlayResultSummary = (): string => {
    if (turnover) {
      return `TURNOVER at ${formatFieldPosition(newBallPosition || 0)}`;
    }
    if (touchdown) {
      return 'TOUCHDOWN!';
    }
    if (yards > 0) {
      return `+${yards} yards → ${formatFieldPosition(newBallPosition || 0)}`;
    }
    return `No gain → ${formatFieldPosition(newBallPosition || 0)}`;
  };
  
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
          <div className="text-yellow-200 text-sm mb-4">
            {penalty_choice.offended_team === 'offense' 
              ? 'DEFENSE committed penalty - Offense may accept or decline' 
              : penalty_choice.offended_team === 'defense'
              ? 'OFFENSE committed penalty - Defense may accept or decline'
              : 'Choose one:'}
          </div>
          
          <div className="bg-gray-800 rounded-lg p-3 mb-4">
            <div className="text-white text-sm mb-1">ACCEPT PLAY RESULT:</div>
            <div className="text-white font-bold text-lg">
              {getPlayResultSummary()}
            </div>
            <div className="text-gray-300 text-sm">
              {formatDown(newDown)} & {newYardsToGo} at {formatLOS(newBallPosition || 0)}
            </div>
            {turnover && (
              <div className="text-red-400 font-bold mt-1">TURNOVER ON DOWNS!</div>
            )}
            {touchdown && (
              <div className="text-green-400 font-bold mt-1">TOUCHDOWN!</div>
            )}
            <div className="text-gray-400 text-xs mt-2">
              Down counts if accepted
            </div>
          </div>
          
          {penalty_choice.penalty_options && 
           penalty_choice.penalty_options.length > 0 && (
            <div className="mb-4">
              <div className="text-white text-sm mb-2">ACCEPT PENALTY:</div>
              <div className="flex flex-col gap-2">
                {penalty_choice.penalty_options.map((opt, idx) => (
                  <button
                    key={idx}
                    onClick={() => onDecision?.(false, idx)}
                    className="px-4 py-3 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-all text-left"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm">{opt.description}</span>
                      <span className="text-sm">
                        {opt.auto_first_down && (
                          <span className="text-yellow-300 ml-2">AUTO 1ST</span>
                        )}
                      </span>
                    </div>
                    {opt.yards !== 0 && (
                      <div className="text-red-200 text-xs mt-1">
                        {opt.yards > 0 ? '+' : ''}{opt.yards} yards
                      </div>
                    )}
                    <div className="text-gray-300 text-xs">
                      Down replayed if accepted
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <div className="mt-4 flex flex-col gap-2">
            <button
              onClick={() => onDecision?.(true, 0)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
            >
              ACCEPT PLAY ({formatDown(newDown)} & {newYardsToGo} at {formatLOS(newBallPosition || 0)})
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default PenaltyDecisionPanel;
