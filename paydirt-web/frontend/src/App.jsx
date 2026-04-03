import React, { useState, useEffect } from 'react';
import { useGameStore } from './store/gameStore';
import MenuPhase from './components/Game/MenuPhase';
import TeamSelectPhase from './components/Game/TeamSelectPhase';
import CoinToss from './components/Game/CoinToss';
import PlayingPhase from './components/Game/PlayingPhase';
import Halftime from './components/Game/Halftime';
import GameOver from './components/Game/GameOver';
import HelpGuide from './components/Game/HelpGuide';
import { API_BASE } from './config';

function App() {
  const { gamePhase, setGamePhase, reset } = useGameStore();
  const [backendStatus, setBackendStatus] = useState('checking');

  // Check backend health on load
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('Backend not available');
      })
      .then(() => setBackendStatus('connected'))
      .catch(() => setBackendStatus('disconnected'));
  }, []);

  // Route to appropriate phase component
  switch (gamePhase) {
    case 'menu':
      return <MenuPhase onNewGame={handleNewGame} onOpenGuide={handleOpenGuide} />;
    case 'guide':
      return <HelpGuide onBackToMenu={handleBackToMenu} />;
    case 'teamSelect':
      return <TeamSelectPhase 
        onTeamSelected={handleTeamSelection} 
        onBackToMenu={handleBackToMenu} 
      />;
    case 'coinToss':
      return <CoinToss 
        homeTeam={useGameStore.getState().homeTeam} 
        awayTeam={useGameStore.getState().awayTeam}
        onComplete={handleCoinTossComplete} 
      />;
    case 'playing':
      return <PlayingPhase 
        onNewGame={handleNewGame} 
        onReturnToMenu={handleReturnToMenu} 
        onSaveGame={handleSaveGame} 
      />;
    case 'halftime':
      return <Halftime 
        homeTeam={useGameStore.getState().homeTeam} 
        awayTeam={useGameStore.getState().awayTeam} 
        homeScore={useGameStore.getState().homeScore} 
        awayScore={useGameStore.getState().awayScore} 
        quarter={useGameStore.getState().quarter}
        onContinue={handleHalftimeContinue} 
        onNewGame={handleNewGame} 
      />;
    case 'gameOver':
      return <GameOver 
        homeTeam={useGameStore.getState().homeTeam} 
        awayTeam={useGameStore.getState().awayTeam} 
        homeScore={useGameStore.getState().homeScore} 
        awayScore={useGameStore.getState().awayScore} 
        onNewGame={handleNewGame} 
      />;
    default:
      return <MenuPhase onNewGame={handleNewGame} />;
  }
}

// Handler functions - these would be moved to hooks or store actions
const handleNewGame = () => {
  // Reset game state
  const { reset } = useGameStore.getState();
  reset();
  // Set phase to team select
  const { setGamePhase } = useGameStore.getState();
  setGamePhase('teamSelect');
};

const handleTeamSelection = (selection) => {
  // The game was already created in TeamSelectPhase via API call
  // Now transition to coin toss
  const { setGamePhase, setIsKickoff } = useGameStore.getState();
  setIsKickoff(true);
  setGamePhase('coinToss');
};

const handleBackToMenu = () => {
  const { setGamePhase, reset } = useGameStore.getState();
  reset();
  setGamePhase('menu');
};

const handleOpenGuide = () => {
  const { setGamePhase } = useGameStore.getState();
  setGamePhase('guide');
};

const handleCoinTossComplete = async (coinData) => {
  // Process coin toss result
  const { updateGameState, setGamePhase, setIsKickoff, setPlayerOffense, setPossession, gameId } = useGameStore.getState();
  
  try {
    const res = await fetch(`${API_BASE}/api/game/coin-toss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        player_won: coinData.playerWonToss,
        player_kicks: !coinData.playerReceives,
        human_plays_offense: coinData.playerReceives,
      })
    });
    
    if (res.ok) {
      const data = await res.json();
      setPossession(data.possession);
      setPlayerOffense(data.player_offense);
    }
  } catch (err) {
    console.error('Failed to process coin toss:', err);
  }
  
  // Transition to playing phase with kickoff
  setIsKickoff(true);
  setGamePhase('playing');
};

const handleHalftimeContinue = () => {
  const { setGamePhase } = useGameStore.getState();
  setGamePhase('playing');
};

const handleSaveGame = () => {
  const { saveGame } = useGameStore.getState();
  const state = useGameStore.getState();
  const success = saveGame({
    gameId: state.gameId,
    homeTeam: state.homeTeam,
    awayTeam: state.awayTeam,
    homeScore: state.homeScore,
    awayScore: state.awayScore,
    quarter: state.quarter,
    timeRemaining: state.timeRemaining,
    possession: state.possession,
    ballPosition: state.ballPosition,
    down: state.down,
    yardsToGo: state.yardsToGo,
    homeTimeouts: state.homeTimeouts,
    awayTimeouts: state.awayTimeouts,
    humanPlaysOffense: state.humanPlaysOffense,
    humanTeamId: state.humanTeamId,
    cpuTeamId: state.cpuTeamId,
    playLog: state.playLog,
    pendingPat: state.pendingPat,
    currentSeason: state.currentSeason,
  });
  
};

const handleReturnToMenu = () => {
  const { reset, setGamePhase } = useGameStore.getState();
  reset();
  setGamePhase('menu');
};

export default App;