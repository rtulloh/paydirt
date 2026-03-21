import React from 'react';

const CpuDecisionPanel = ({ decision, onExecute, onCancel }) => {
  const getDecisionText = () => {
    switch (decision.decision) {
      case 'go_for_it':
        return 'GO FOR IT!';
      case 'field_goal':
        return 'KICKING A FIELD GOAL';
      case 'punt':
        return 'PUNTING';
      default:
        return decision.decision;
    }
  };

  return (
    <div className="bg-yellow-600 rounded-lg px-4 py-4 text-center animate-pulse">
      <div className="text-lg font-bold text-white mb-1">CPU 4TH DOWN DECISION</div>
      <div className="text-2xl font-bold text-white">
        {getDecisionText()}
      </div>
      {decision.decision !== 'go_for_it' && (
        <div className="mt-4">
          <button
            onClick={onExecute}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
          >
            EXECUTE PLAY
          </button>
          <button
            onClick={onCancel}
            className="ml-3 px-6 py-3 bg-gray-600 text-white rounded-lg font-bold hover:bg-gray-700 transition-all"
          >
            CANCEL
          </button>
        </div>
      )}
    </div>
  );
};

export default CpuDecisionPanel;