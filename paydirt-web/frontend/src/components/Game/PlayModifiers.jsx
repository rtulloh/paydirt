import React, { useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';

const PlayModifiers = ({ selectedPlay, onModifierChange }) => {
  const { 
    noHuddleMode, 
    toggleNoHuddleMode,
    selectedModifier,
    setModifier,
    down,
    playerOffense,
    homeTimeouts,
    awayTimeouts,
    possession,
    humanIsHome
  } = useGameStore();

  const isHumanOffense = possession === (humanIsHome ? 'home' : 'away');
  const humanTimeouts = humanIsHome ? homeTimeouts : awayTimeouts;

  // Determine if spike should be disabled
  const isSpikeDisabled = () => {
    if (!isHumanOffense) return true;
    if (down >= 3) return true; // 3rd or 4th down
    // Disable for special plays (punt, field goal, kneel)
    const specialPlays = ['P', 'F', 'K', 'S'];
    if (selectedPlay && specialPlays.includes(selectedPlay.toUpperCase())) return true;
    return false;
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event) => {
      // Ignore if typing in input field
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      
      const key = event.key.toUpperCase();
      
      if (key === 'N') {
        toggleNoHuddleMode();
      } else if (key === 'T' && isHumanOffense) {
        setModifier('T');
        onModifierChange && onModifierChange('T');
      } else if (key === 'O' && isHumanOffense) {
        setModifier('+');
        onModifierChange && onModifierChange('+');
      } else if (key === 'S' && isHumanOffense && !isSpikeDisabled()) {
        setModifier('S');
        onModifierChange && onModifierChange('S');
      } else if (key === '0') {
        setModifier(null);
        onModifierChange && onModifierChange(null);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isHumanOffense, isSpikeDisabled(), toggleNoHuddleMode, setModifier, onModifierChange]);

  // Only show when player is on offense
  if (!isHumanOffense) return null;

  return (
    <div className="bg-gray-800 rounded px-2 py-1" data-testid="play-modifiers" title="Modifiers apply to the next play only. No Huddle persists until possession changes.">
      <div className="flex flex-wrap gap-2 items-center text-xs">
        {/* No-Huddle Toggle */}
        <div className="flex items-center gap-1">
          <span className="text-gray-400">No Huddle:</span>
          <button
            onClick={toggleNoHuddleMode}
            className={`px-2 py-1 rounded font-bold text-xs ${
              noHuddleMode 
                ? 'bg-red-600 text-white hover:bg-red-700' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {noHuddleMode ? 'ON' : 'OFF'}[N]
          </button>
        </div>

        {/* Modifier Radio Buttons */}
        <div className="flex items-center gap-1">
          <span className="text-gray-400">Modifier:</span>
          <label className="flex items-center gap-0.5 cursor-pointer">
            <input
              type="radio"
              name="modifier"
              checked={selectedModifier === null}
              onChange={() => {
                setModifier(null);
                onModifierChange && onModifierChange(null);
              }}
              className="w-3 h-3"
            />
            <span className="text-gray-300">None[0]</span>
          </label>
          
          <label className="flex items-center gap-0.5 cursor-pointer">
            <input
              type="radio"
              name="modifier"
              checked={selectedModifier === 'T'}
              onChange={() => {
                setModifier('T');
                onModifierChange && onModifierChange('T');
              }}
              disabled={humanTimeouts <= 0}
              className="w-3 h-3 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className={humanTimeouts <= 0 ? 'text-gray-600' : 'text-gray-300'}>
              T({humanTimeouts})[T]
            </span>
          </label>
          
          <label className="flex items-center gap-0.5 cursor-pointer">
            <input
              type="radio"
              name="modifier"
              checked={selectedModifier === '+'}
              onChange={() => {
                setModifier('+');
                onModifierChange && onModifierChange('+');
              }}
              className="w-3 h-3"
            />
            <span className="text-gray-300">OOB[O]</span>
          </label>
          
          <label className="flex items-center gap-0.5 cursor-pointer">
            <input
              type="radio"
              name="modifier"
              checked={selectedModifier === 'S'}
              onChange={() => {
                setModifier('S');
                onModifierChange && onModifierChange('S');
              }}
              disabled={isSpikeDisabled()}
              className="w-3 h-3 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className={isSpikeDisabled() ? 'text-gray-600' : 'text-gray-300'}>
              Spike[S]
            </span>
          </label>
        </div>
      </div>
    </div>
  );
};

export default PlayModifiers;