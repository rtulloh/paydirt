import React, { useState } from 'react';

const PuntOptionsPanel = ({ ballPosition, onSelect, onCancel }) => {
  const [coffinYards, setCoffinYards] = useState(10);
  const [showCoffinInput, setShowCoffinInput] = useState(false);
  
  const isShortDropMandatory = ballPosition >= 95;
  const isShortDropAvailable = ballPosition >= 95;
  
  const handleNormalPunt = () => {
    onSelect({ short_drop: false, coffin_corner_yards: 0 });
  };
  
  const handleShortDrop = () => {
    onSelect({ short_drop: true, coffin_corner_yards: 0 });
  };
  
  const handleCoffinCorner = () => {
    setShowCoffinInput(true);
  };
  
  const handleCoffinConfirm = () => {
    onSelect({ short_drop: false, coffin_corner_yards: coffinYards });
  };
  
  if (isShortDropMandatory) {
    return (
      <div className="bg-yellow-700 rounded-lg px-4 py-4 text-center">
        <div className="text-xl font-bold text-white mb-2">PUNT OPTIONS</div>
        <div className="text-yellow-200 text-sm mb-4">
          Short-Drop Punt is mandatory inside opponent's 5-yard line
        </div>
        <div className="text-white text-sm mb-4">
          Defenders will get Free All-Out Kick Rush
        </div>
        <div className="flex gap-2 justify-center">
          <button
            onClick={handleShortDrop}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700"
          >
            SHORT-DROP PUNT
          </button>
          <button
            onClick={onCancel}
            className="px-6 py-3 bg-gray-600 text-white rounded-lg font-bold hover:bg-gray-700"
          >
            CANCEL
          </button>
        </div>
      </div>
    );
  }
  
  if (showCoffinInput) {
    return (
      <div className="bg-yellow-700 rounded-lg px-4 py-4 text-center">
        <div className="text-xl font-bold text-white mb-2">COFFIN-CORNER PUNT</div>
        <div className="text-yellow-200 text-sm mb-4">
          Subtract yards from your punt distance
        </div>
        <div className="mb-4">
          <label className="text-white text-sm block mb-2">Yards to subtract (0-25):</label>
          <input
            type="number"
            min="0"
            max="25"
            value={coffinYards}
            onChange={(e) => setCoffinYards(Math.max(0, Math.min(25, parseInt(e.target.value) || 0)))}
            className="w-20 px-3 py-2 rounded-lg text-center text-lg font-bold bg-gray-800 text-white border-2 border-yellow-500"
          />
        </div>
        {coffinYards >= 15 && (
          <div className="text-green-300 text-sm mb-4">
            Automatic out of bounds (no return)
          </div>
        )}
        <div className="flex gap-2 justify-center">
          <button
            onClick={handleCoffinConfirm}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700"
          >
            CONFIRM
          </button>
          <button
            onClick={() => setShowCoffinInput(false)}
            className="px-6 py-3 bg-gray-600 text-white rounded-lg font-bold hover:bg-gray-700"
          >
            BACK
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-yellow-700 rounded-lg px-4 py-4 text-center">
      <div className="text-xl font-bold text-white mb-3">PUNT OPTIONS</div>
      <div className="text-gray-300 text-sm mb-4">
        Ball at position {ballPosition}
      </div>
      
      <div className="flex flex-col gap-2">
        <button
          onClick={handleNormalPunt}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700"
        >
          NORMAL PUNT
        </button>
        
        {isShortDropAvailable && (
          <button
            onClick={handleShortDrop}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg font-bold hover:bg-purple-700"
          >
            SHORT-DROP PUNT
            <span className="block text-xs font-normal mt-1">
              Defenders get Free All-Out Kick Rush
            </span>
          </button>
        )}
        
        {!isShortDropAvailable && (
          <button
            onClick={handleCoffinCorner}
            className="px-6 py-3 bg-orange-600 text-white rounded-lg font-bold hover:bg-orange-700"
          >
            COFFIN-CORNER PUNT
            <span className="block text-xs font-normal mt-1">
              Specify yards to subtract
            </span>
          </button>
        )}
        
        <button
          onClick={onCancel}
          className="px-6 py-3 bg-gray-600 text-white rounded-lg font-bold hover:bg-gray-700"
        >
          CANCEL
        </button>
      </div>
    </div>
  );
};

export default PuntOptionsPanel;
