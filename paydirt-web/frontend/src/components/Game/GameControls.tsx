import React from 'react';

interface GameControlsProps {
  isRolling: boolean;
  lastResult: any; // We'll refine this later
  showPatChoice: boolean;
  showPenaltyChoice: boolean;
  executing: boolean;
  onKickoff: () => void;
  onContinue: () => void;
}

const GameControls = ({ isRolling, lastResult, showPatChoice, showPenaltyChoice, executing, onKickoff, onContinue }: GameControlsProps) => {
  return (
    <>
      {!isRolling && lastResult && !showPatChoice && !showPenaltyChoice && (
        <button
          onClick={onContinue}
          className="play-button text-base px-6 py-3"
        >
          CONTINUE
        </button>
      )}
      
      {!isRolling && !lastResult && !executing && !showPatChoice && (
        <button
          onClick={onKickoff}
          className="play-button text-base px-6 py-3"
        >
          KICK OFF
        </button>
      )}
    </>
  );
};

export default GameControls;