import React, { useEffect, useMemo } from 'react';
import { useGameStore } from '../../store/gameStore';

const PlayModifiers = ({ selectedPlay, onModifierChange, disabled = false }) => {
  const { 
    noHuddleMode, 
    toggleNoHuddleMode,
    selectedModifier,
    setModifier,
    down,
    playerOffense,
    homeTimeouts,
    awayTimeouts,
    humanIsHome
  } = useGameStore();

  const isHumanOffense = playerOffense;
  const humanTimeouts = humanIsHome ? homeTimeouts : awayTimeouts;
  const timeoutHelp = humanTimeouts <= 0
    ? 'No timeouts remaining. A timeout cannot be requested.'
    : `Request a timeout after ${isHumanOffense ? 'your next play' : "the opponent's next play"}. Uses one timeout only when the engine can stop a running clock. Shortcut: T.`;

  // Memoize spike disabled state to avoid stale closures in keyboard handler
  const spikeDisabled = useMemo(() => {
    if (!isHumanOffense) return true;
    if (down >= 3) return true; // 3rd or 4th down
    // Disable for special plays (punt, field goal, kneel)
    const specialPlays = ['P', 'F', 'K', 'S'];
    if (selectedPlay && specialPlays.includes(selectedPlay.toUpperCase())) return true;
    return false;
  }, [isHumanOffense, down, selectedPlay]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (disabled) return;
      // Radio focus must not suppress shortcuts, but typing must remain untouched.
      if ((event.target.tagName === 'INPUT' && event.target.type !== 'radio') ||
          event.target.tagName === 'TEXTAREA' || event.target.isContentEditable) return;
      
      const key = event.key.toUpperCase();
      
      if (key === 'N' && isHumanOffense) {
        toggleNoHuddleMode();
      } else if (key === 'T' && humanTimeouts > 0) {
        setModifier('T');
        onModifierChange && onModifierChange('T');
      } else if (key === 'O' && isHumanOffense) {
        setModifier('+');
        onModifierChange && onModifierChange('+');
      } else if (key === 'S' && isHumanOffense && !spikeDisabled) {
        setModifier('S');
        onModifierChange && onModifierChange('S');
      } else if (key === '0') {
        setModifier(null);
        onModifierChange && onModifierChange(null);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [disabled, humanTimeouts, isHumanOffense, spikeDisabled, toggleNoHuddleMode, setModifier, onModifierChange]);

  return (
    <fieldset disabled={disabled} className="bg-gray-800 rounded px-2 py-1 min-w-0" data-testid="play-modifiers" title="Modifiers apply to the next play only. No Huddle persists until possession changes.">
      <div className="flex flex-wrap gap-2 items-center text-xs">
        {/* No-Huddle Toggle */}
        {isHumanOffense && <div className="flex items-center gap-1">
          <span className="text-gray-400">No Huddle:</span>
          <button
            onClick={toggleNoHuddleMode}
            title="Use no huddle to reduce eligible running-clock plays from 40 to 20 seconds. May cause a no-huddle penalty. Stays on until possession changes or you turn it off. Shortcut: N."
            className={`px-2 py-1 rounded font-bold text-xs ${
              noHuddleMode 
                ? 'bg-red-600 text-white hover:bg-red-700' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {noHuddleMode ? 'ON' : 'OFF'} [N]
          </button>
        </div>}

        {/* Modifier Radio Buttons */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="text-gray-400">Modifier:</span>
          <label className="flex items-center gap-0.5 cursor-pointer" title="Clear the next-play modifier. This does not turn off No Huddle. Shortcut: 0.">
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
            <span className="text-gray-300">None [0]</span>
          </label>
          
          <label className="flex items-center gap-0.5 cursor-pointer" title={timeoutHelp}>
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
              Timeout ({humanTimeouts} left) [T]
            </span>
          </label>
          
          {isHumanOffense && <>
          <label className="flex items-center gap-0.5 cursor-pointer" title="Request out of bounds on the next play: eligible plays in the final minutes take ten seconds and cost five yards. The engine decides whether the result qualifies. Shortcut: O.">
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
            <span className="text-gray-300">Out of bounds [O]</span>
          </label>
          
          <label className="flex items-center gap-0.5 cursor-pointer" title="Request a spike after your next play to stop a running clock. Uses an extra down and caps eligible play-plus-spike time at 20 seconds. Available on first or second down for regular offensive plays. Shortcut: S.">
            <input
              type="radio"
              name="modifier"
              checked={selectedModifier === 'S'}
              onChange={() => {
                setModifier('S');
                onModifierChange && onModifierChange('S');
              }}
              disabled={spikeDisabled}
              className="w-3 h-3 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className={spikeDisabled ? 'text-gray-600' : 'text-gray-300'}>
              Spike [S]
            </span>
          </label>
          </>}
        </div>
      </div>
    </fieldset>
  );
};

export default PlayModifiers;
