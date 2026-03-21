import React from 'react';

const PlayLogDisplay = ({ plays = [], onPlayClick }) => {
  return (
    <div className="w-full">
      <div className="text-white font-bold mb-2">PLAY LOG</div>
      <div className="h-64 overflow-y-auto border rounded p-2 space-y-1">
        {plays && plays.length > 0 ? plays.map((play, index) => (
          <div
            key={index}
            onClick={() => onPlayClick(play)}
            className="cursor-pointer p-2 rounded hover:bg-gray-700 bg-gray-800/50"
          >
            {/* Header: Quarter, Time, Teams */}
            <div className="flex justify-between items-start mb-1">
              <div className="text-xs text-gray-300">
                <span className="font-bold">Q{play.quarter}</span> {' '}
                {play.timeRemaining}"
              </div>
              <div className="text-xs text-gray-400">
                {play.offenseTeam} vs {play.defenseTeam}
              </div>
            </div>
            
            {/* Down and Distance */}
            <div className="text-xs text-yellow-400 mb-1">
              {play.down && play.yardsToGo ? 
                `${play.down}&${play.yardsToGo} at ${play.homeTeamAbbrev}-${play.awayTeamAbbrev} ${play.lineOfScrimmage || ''}` : 
                '1st & 10'
              }
            </div>
            
            {/* Play Calls */}
            <div className="flex gap-2 text-xs text-gray-300 mb-1">
              <span className={play.playerTeam === play.offenseTeam ? "text-green-400" : "text-red-400"}>
                OFF: {play.offensePlay}
              </span>
              <span className={play.playerTeam === play.offenseTeam ? "text-red-400" : "text-green-400"}>
                DEF: {play.defensePlay}
              </span>
            </div>
            
            {/* Dice Rolls */}
            {play.offenseDice && play.defenseDice && (
              <div className="flex gap-2 text-xs text-gray-500 mb-1">
                <span>Off: {play.offenseDice.black}+{play.offenseDice.white1}+{play.offenseDice.white2}={play.offenseDice.total}</span>
                <span>Def: {play.defenseDice.red}+{play.defenseDice.green}={play.defenseDice.total}</span>
              </div>
            )}
            
            {/* Result */}
            <div className="text-sm text-white font-medium">{play.description || play.headline}</div>
            
            {/* Yards gained/lost */}
            {play.yards !== undefined && play.yards !== 0 && (
              <div className={`text-xs ${play.yards > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {play.yards > 0 ? `+${play.yards} yards` : `${play.yards} yards`}
              </div>
            )}
            
            {/* New Position */}
            {play.newPosition !== undefined && (
              <div className="text-xs text-gray-400">
                New: {play.homeTeamAbbrev}-{play.awayTeamAbbrev} {play.newPosition}
              </div>
            )}
            
            {/* Score Change */}
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
