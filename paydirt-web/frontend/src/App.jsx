import { useNativeLibrary } from './runtime/useNativeLibrary';
import { gameFetch, browserMode } from './runtime/gameFetch';
import React, { useState, useEffect } from 'react';
import { useGameStore } from './store/gameStore';
import MenuPhase from './components/Game/MenuPhase';
import SeasonDesk from './components/Game/SeasonDesk';
import SavedGames from './components/Game/SavedGames';
import { sessionPersistence } from './runtime/sessionPersistence';
import { saveCurrentSession } from './runtime/gameFetch';
import TeamSelectPhase from './components/Game/TeamSelectPhase';
import CoinToss from './components/Game/CoinToss';
import PlayingPhase from './components/Game/PlayingPhase';
import Halftime from './components/Game/Halftime';
import GameOver from './components/Game/GameOver';
import HelpGuide from './components/Game/HelpGuide';
import { DetachedCharts } from './components/Game/ChartViewer';
import { API_BASE } from './config';

function App() {
  const params = new URLSearchParams(window.location.search);
  if (params.has('charts')) {
    return <DetachedCharts gameId={params.get('charts')} initialSide={params.get('side')} initialChart={params.get('view')} />;
  }
  return <><PersistenceStatus />{browserMode ? <BrowserGameApp /> : <GameApp />}</>;
}

function BrowserGameApp() {
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    const runtimeError = event => { setError(event.detail); setStatus('failed'); };
    window.addEventListener('paydirt-runtime-error', runtimeError);
    gameFetch('/api/health').then(async response => {
      if (!response.ok) throw new Error('The browser game engine could not start.');
      if (active) setStatus('ready');
    }).catch(failure => { if (active) { setError(failure.message); setStatus('failed'); } });
    return () => { active = false; window.removeEventListener('paydirt-runtime-error', runtimeError); };
  }, []);
  return <>
    <aside className="bg-amber-100 text-gray-900 px-4 py-3 text-center">Browser prototype · Public seasons: 1977, 1983, 2024 and 2026 sample teams. Saved games and seasons stay in this browser. Export backups to keep a portable copy. Offline engine loading is unavailable.</aside>
    {status === 'loading' && <main className="p-8 text-white"><p role="status">Loading the Python game engine… The first download may take a moment.</p></main>}
    {status === 'failed' && <main className="p-8 text-white"><p role="alert">{error}</p><button type="button" onClick={() => window.location.reload()}>Reload browser prototype</button></main>}
    {status === 'ready' && <GameApp />}
  </>;
}

function GameApp() {
  const { gamePhase, setGamePhase, reset } = useGameStore();
  const [backendStatus, setBackendStatus] = useState('checking');
  const [coinError, setCoinError] = useState('');
  const [coinBusy, setCoinBusy] = useState(false);

  async function completeCoinToss(coinData) {
    if (coinBusy) return;
    setCoinBusy(true);
    setCoinError('');
    try { await handleCoinTossComplete(coinData); }
    catch (error) { setCoinError(error.message); }
    finally { setCoinBusy(false); }
  }

  // Check backend health on load
  useEffect(() => {
    gameFetch(`${API_BASE}/api/health`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('Backend not available');
      })
      .then(() => setBackendStatus('connected'))
      .catch(() => setBackendStatus('disconnected'));
  }, []);

  // Route to appropriate phase component
  switch (gamePhase) {
    case 'seasons':
      return <SeasonDesk onMenu={handleBackToMenu} onSaves={() => setGamePhase('saves')} onPlay={data => {
        useGameStore.getState().restoreSession({...data,game_phase:'coinToss'});
      }} />;
    case 'saves':
      return <SavedGames onMenu={handleBackToMenu} onResume={(data,metadata)=>useGameStore.getState().restoreSession(data,metadata)} />;
    case 'menu':
      return <MenuPhase onNewGame={handleNewGame} onOpenGuide={handleOpenGuide} onOpenSeasons={() => setGamePhase('seasons')} onOpenSaves={() => setGamePhase('saves')} />;
    case 'guide':
      return <HelpGuide onBackToMenu={handleBackToMenu} />;
    case 'teamSelect':
      return <TeamSelectPhase 
        onTeamSelected={handleTeamSelection} 
        onBackToMenu={handleBackToMenu} 
      />;
    case 'coinToss':
      return <>
        {coinError && <p role="alert">{coinError}</p>}
        <fieldset disabled={coinBusy}>
          <CoinToss
            homeTeam={useGameStore.getState().homeTeam}
            awayTeam={useGameStore.getState().awayTeam}
            onComplete={completeCoinToss}
          />
        </fieldset>
      </>;
    case 'playing':
      return <PlayingPhase key={useGameStore.getState().gameId}
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
  
  const res = await gameFetch(`${API_BASE}/api/game/coin-toss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({game_id: gameId, player_won: coinData.playerWonToss,
      player_kicks: !coinData.playerReceives, human_plays_offense: coinData.playerReceives})
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Could not process the coin toss.');
  setPossession(data.possession);
  setPlayerOffense(data.player_offense);

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

// Only UI preferences are frontend-owned. Rules and pending game procedures
// remain inside the opaque Python checkpoint.
sessionPersistence.setMetadataFor((gameId,response) => {
 const state=useGameStore.getState(), view=response.game_state||{};
 return {phase:response.ui_phase || (view.game_over?'gameOver':view.halftime_pending?'halftime':state.gamePhase==='coinToss'?'playing':state.gamePhase),noHuddleMode:state.noHuddleMode,selectedModifier:state.selectedModifier};
});
function PersistenceStatus(){
 const [status,setStatus]=useState(null);
 useEffect(()=>{const listener=e=>setStatus(e.detail);window.addEventListener('paydirt-save-status',listener);return()=>window.removeEventListener('paydirt-save-status',listener)},[]);
 if(!status)return null;
 return <aside className="bg-gray-800 text-white px-4 py-2 text-sm" role={status.status==='failed'?'alert':'status'}>
 {status.status==='saving'?'Saving game…':status.status==='saved'?<SavedLocation record={status.record}/>:`Game save failed: ${status.error.message}. Your previous save is retained.`}
 {status.status==='failed'&&<><button className="ml-3 underline" onClick={()=>saveCurrentSession(status.gameId).catch(()=>{})}>Retry save</button><button className="ml-3 underline" onClick={()=>useGameStore.getState().setGamePhase('saves')}>Saved games / export</button></>}
 </aside>;
}

function SavedLocation({record}) {
 const native=useNativeLibrary();
 return <>{native===true?'Saved in this application':native===false?'Saved in this browser':'Saved locally'} · {new Date(record.savedAt).toLocaleTimeString()}</>;
}
