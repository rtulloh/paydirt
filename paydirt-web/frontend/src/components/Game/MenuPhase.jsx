import React, { useState, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';

const MenuPhase = ({ onNewGame }) => {
  const [hasSavedGame, setHasSavedGame] = useState(false);
  const [hasSavedReplay, setHasSavedReplay] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { reset, loadGame, loadReplay, clearReplay, setGamePhase, gamePhase } = useGameStore();
  
  // If gamePhase is not 'menu', don't render MenuPhase
  if (gamePhase !== 'menu' && !isLoading) {
    return null;
  }
  
  useEffect(() => {
    try {
      setHasSavedGame(localStorage.getItem('paydirt_save') !== null);
      setHasSavedReplay(localStorage.getItem('paydirt_replay') !== null);
    } catch {
      setHasSavedGame(false);
      setHasSavedReplay(false);
    }
  }, []);
  
  const handleNewGame = () => {
    reset();
    onNewGame();
  };
  
  const handleLoadGame = () => {
    const success = loadGame();
    if (!success) {
      console.error('Failed to load saved game');
    }
  };
  
  const handleLoadReplay = () => {
    setIsLoading(true);
    loadReplay()
      .then(() => {
        // State is already updated in store, App will re-render
      })
      .catch(err => {
        console.error('Failed to load replay:', err.message || err);
        alert('Failed to load replay: ' + (err.message || 'Unknown error') + '. Check console for details.');
        setIsLoading(false);
      });
  };
  
  const handleClearReplay = () => {
    clearReplay();
    setHasSavedReplay(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-white mb-4 tracking-wider">
          PAYDIRT
        </h1>
        <p className="text-gray-400 text-xl mb-12">
          Classic Football Board Game
        </p>
        <div className="space-y-4">
          <button
            onClick={handleNewGame}
            className="w-64 px-8 py-4 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all transform hover:scale-105 text-xl"
          >
            NEW GAME
          </button>
          {hasSavedGame && (
            <button
              onClick={handleLoadGame}
              className="w-64 px-8 py-4 bg-green-600 text-white rounded-lg font-bold hover:bg-green-700 transition-all transform hover:scale-105 text-xl"
            >
              LOAD GAME
            </button>
          )}
          {hasSavedReplay && (
            <div className="space-y-2">
              <button
                onClick={handleLoadReplay}
                className="w-64 px-8 py-4 bg-purple-600 text-white rounded-lg font-bold hover:bg-purple-700 transition-all transform hover:scale-105 text-xl"
              >
                LOAD REPLAY
              </button>
              <button
                onClick={handleClearReplay}
                className="w-64 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-all text-sm"
              >
                Clear Saved Replay
              </button>
            </div>
          )}
        </div>
        <p className="text-gray-500 text-sm mt-8">
          Tip: Save Replay during gameplay to capture the exact state for debugging
        </p>
      </div>
    </div>
  );
};

export default MenuPhase;
