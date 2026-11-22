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
      // Keep shortcuts available while a control has focus, but leave typing alone.
      if ((event.target.tagName === 'INPUT' && event.target.type !== 'checkbox') ||
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

  const toggleModifier = (modifier) => {
    const nextModifier = selectedModifier === modifier ? null : modifier;
    setModifier(nextModifier);
    onModifierChange?.(nextModifier);
  };

  return (
    <fieldset disabled={disabled} className="bg-gray-800 rounded px-2 py-1 min-w-0" data-testid="play-modifiers" title="Modifiers apply to the next play only. No Huddle persists until possession changes.">
      <div className="space-y-3 text-sm">
        {isHumanOffense && <div className="flex flex-wrap items-center gap-2 border-t border-slate-600 pt-3">
          <h3 className="font-bold text-white">Pace</h3>
          <label className="flex items-center gap-2 text-gray-200" title="Use no huddle to reduce eligible running-clock plays from 40 to 20 seconds. May cause a no-huddle penalty. Stays on until possession changes or you turn it off. Shortcut: N.">
            <input type="checkbox" checked={noHuddleMode} onChange={toggleNoHuddleMode} className="h-4 w-4 shrink-0 accent-blue-600" />
            <span>No Huddle [N]</span>
          </label>
        </div>}
        <div className="space-y-2 border-t border-slate-600 pt-3">
          <h3 className="font-bold text-white">Clock</h3>
          <label className="flex items-center gap-2 text-gray-200" title={timeoutHelp}>
            <input
              type="checkbox"
              checked={selectedModifier === 'T'}
              onChange={() => toggleModifier('T')}
              disabled={humanTimeouts <= 0}
              className="h-4 w-4 shrink-0 accent-blue-600"
            />
            <span>Timeout ({humanTimeouts} left) [T]</span>
          </label>
          {isHumanOffense && (
            <label className="flex items-center gap-2 text-gray-200" title="Request a spike after your next play to stop a running clock. Uses an extra down and caps eligible play-plus-spike time at 20 seconds. Available on first or second down for regular offensive plays. Shortcut: S.">
              <input
                type="checkbox"
                checked={selectedModifier === 'S'}
                onChange={() => toggleModifier('S')}
                disabled={spikeDisabled}
                className="h-4 w-4 shrink-0 accent-blue-600"
              />
              <span>Spike [S]</span>
            </label>
          )}
        </div>
        {isHumanOffense && <div className="space-y-2 border-t border-slate-600 pt-3">
          <h3 className="font-bold text-white">Next-play result</h3>
          <label className="flex items-center gap-2 text-gray-200" title="Request out of bounds on the next play: eligible plays in the final minutes take ten seconds and cost five yards. The engine decides whether the result qualifies. Shortcut: O.">
            <input
              type="checkbox"
              checked={selectedModifier === '+'}
              onChange={() => toggleModifier('+')}
              className="h-4 w-4 shrink-0 accent-blue-600"
            />
            <span>Out of bounds [O]</span>
          </label>
          <label className="flex items-center gap-2 text-gray-200" title="Request that the next eligible play stay in bounds to keep the clock running. The engine applies the yardage cost and determines eligibility.">
            <input
              type="checkbox"
              checked={selectedModifier === '-'}
              onChange={() => toggleModifier('-')}
              className="h-4 w-4 shrink-0 accent-blue-600"
            />
            <span>Keep in bounds</span>
          </label>
        </div>}
      </div>
    </fieldset>
  );
};

export default PlayModifiers;
