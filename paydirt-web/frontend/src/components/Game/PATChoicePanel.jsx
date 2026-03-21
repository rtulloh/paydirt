import React from 'react';

const PATChoicePanel = ({ canGoForTwo, cpuShouldGoForTwo, scoringTeamIsPlayer, onPatKick, onPatTwoPoint, onCpuPat, onCpuTwoPoint }) => {
  if (!scoringTeamIsPlayer) {
    // CPU is handling the PAT, we just show a message or nothing? 
    // In the original code, when CPU scores, it auto-handles the PAT.
    // We might not need to show anything for CPU in this panel.
    return null;
  }

  return (
    <div className="bg-green-700 rounded-lg px-4 py-4 text-center border-2 border-green-500">
      <div className="text-xl font-bold text-white mb-3">EXTRA POINT!</div>
      <div className="flex justify-center gap-4">
        <button
          onClick={onPatKick}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
        >
          KICK XP (1 PT)
        </button>
        {canGoForTwo && (
          <button
            onClick={() => onPatTwoPoint('1')}
            className="px-6 py-3 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-all"
          >
            GO FOR 2!
          </button>
        )}
      </div>
    </div>
  );
};

export default PATChoicePanel;