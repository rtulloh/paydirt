import { useState } from 'react';
import PlayLogDisplay from './PlayLogDisplay.tsx';

const panelClass = 'min-w-0 rounded-lg border border-slate-600 bg-slate-800 p-3 text-white';

export default function GamePlayArea({ children, modifiers, plays }) {
  const [showHistory, setShowHistory] = useState(false);

  return (
    <div className="grid grid-cols-1 gap-3 px-4 pb-3 lg:grid-cols-[5fr_4fr_3fr]">
      <section aria-labelledby="play-selection-heading" className={panelClass}>
        <h2 id="play-selection-heading" className="mb-3 font-bold">Play selection</h2>
        {children}
      </section>
      <section aria-labelledby="play-log-heading" className={panelClass}>
        <h2 id="play-log-heading" className="mb-3 font-bold">Play log</h2>
        <div id="game-play-log">
          <PlayLogDisplay plays={showHistory ? plays : plays.slice(-1)} showHeading={false} />
        </div>
      </section>
      <section aria-labelledby="game-controls-heading" className={panelClass}>
        <h2 id="game-controls-heading" className="mb-3 font-bold">Game controls</h2>
        {modifiers}
        <button
          type="button"
          className="play-button mt-3 px-3 py-2 text-sm"
          aria-controls="game-play-log"
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory ? 'Show latest play' : 'Show complete history'}
        </button>
      </section>
    </div>
  );
}
