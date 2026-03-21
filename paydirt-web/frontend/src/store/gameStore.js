import { create } from 'zustand'

const initialGameState = {
  homeTeam: null,
  awayTeam: null,
  homeScore: 0,
  awayScore: 0,
  quarter: 1,
  timeRemaining: 900,
  possession: 'home',
  ballPosition: 35,
  down: 1,
  yardsToGo: 10,
  homeTimeouts: 3,
  awayTimeouts: 3,
  humanPlaysOffense: true,
  humanIsHome: null,
  humanTeamId: null,
  humanPlaySelected: null,
  cpuPlaySelected: null,
  gameOver: false,
  playResult: null,
  cpuFourthDownDecision: null,
  pendingExtraPoint: null,
  canGoForTwo: false,
  pendingPenalty: null,
  difficulty: 'medium',
  isKickoff: false,
  playLog: [],
}

export const useGameStore = create((set, get) => ({
  gamePhase: 'menu',
  gameId: null,
  ...initialGameState,

  setGamePhase: (phase) => set({ gamePhase: phase }),
  setGameId: (id) => set({ gameId: id }),
  setIsKickoff: (value) => set({ isKickoff: value }),
  setPlayLog: (log) => set({ playLog: log }),
  addToPlayLog: (entry) => set((state) => ({ playLog: [...state.playLog, entry] })),
  
  setHumanPlay: (play) => set({ humanPlaySelected: play }),
  setCpuPlay: (play) => set({ cpuPlaySelected: play }),
  setPlayResult: (result) => set({ playResult: result }),
  setCpuFourthDownDecision: (decision) => set({ cpuFourthDownDecision: decision }),
  clearCpuFourthDownDecision: () => set({ cpuFourthDownDecision: null }),
  setPendingExtraPoint: (data) => set({ pendingExtraPoint: data, canGoForTwo: data?.canGoForTwo || false }),
  clearPendingExtraPoint: () => set({ pendingExtraPoint: null, canGoForTwo: false }),
  setPendingPenalty: (data) => set({ pendingPenalty: data }),
  clearPendingPenalty: () => set({ pendingPenalty: null }),
  
  updateGameState: (state) => {
    const possession = state.possession
    // Backend sends player_offense, not human_plays_offense
    const playerIsOnOffense = state.player_offense !== undefined ? state.player_offense : true
    
    // human_is_home comes from backend
    const human_is_home = state.human_is_home !== undefined ? state.human_is_home : state.humanIsHome
    
    console.log('updateGameState - player_offense from backend:', state.player_offense, 'human_is_home:', human_is_home);
    
    set({
      homeTeam: state.home_team,
      awayTeam: state.away_team,
      homeScore: state.home_score,
      awayScore: state.away_score,
      quarter: state.quarter,
      timeRemaining: state.time_remaining,
      possession: possession,
      ballPosition: state.ball_position,
      down: state.down,
      yardsToGo: state.yards_to_go,
      gameOver: state.game_over,
      homeTimeouts: state.home_timeouts,
      awayTimeouts: state.away_timeouts,
      humanIsHome: human_is_home,
      playerOffense: playerIsOnOffense,
    })
  },
   
  startNewGame: (gameData) => {
    const possession = gameData.possession
    const humanPlaysOffense = gameData.human_plays_offense
    const human_is_home = gameData.home_team?.id === gameData.human_team_id
    
    // humanIsOnOffense depends on possession relative to where the human plays
    // At game start, possession is 'away' (away team receives kickoff)
    let humanControlsOffense = false
    if (human_is_home !== undefined) {
      const possession_at_human_end = (possession === 'home' && human_is_home) || (possession === 'away' && !human_is_home)
      humanControlsOffense = possession_at_human_end ? humanPlaysOffense : !humanPlaysOffense
    }
    
    set({
      gameId: gameData.game_id,
      homeTeam: gameData.home_team,
      awayTeam: gameData.away_team,
      homeScore: gameData.home_score,
      awayScore: gameData.away_score,
      quarter: gameData.quarter,
      timeRemaining: gameData.time_remaining,
      possession: possession,
      ballPosition: gameData.ball_position,
      down: gameData.down,
      yardsToGo: gameData.yards_to_go,
      homeTimeouts: 3,
      awayTimeouts: 3,
      humanPlaysOffense: humanPlaysOffense,
      humanIsOnOffense: humanControlsOffense,
      humanIsHome: human_is_home,
      playerOffense: humanControlsOffense,
      humanTeamId: gameData.human_team_id,
      cpuTeamId: gameData.cpu_team_id,
      humanPlaySelected: null,
      cpuPlaySelected: null,
      playResult: null,
      gameOver: false,
      cpuFourthDownDecision: null,
    })
  },

  resetGameState: () => set(initialGameState),
  
  reset: () => set({ gamePhase: 'menu', gameId: null, playLog: [], ...initialGameState }),
  
  saveGame: (gameData) => {
    const saveData = {
      gameId: gameData.gameId,
      homeTeam: gameData.homeTeam,
      awayTeam: gameData.awayTeam,
      homeScore: gameData.homeScore,
      awayScore: gameData.awayScore,
      quarter: gameData.quarter,
      timeRemaining: gameData.timeRemaining,
      possession: gameData.possession,
      ballPosition: gameData.ballPosition,
      down: gameData.down,
      yardsToGo: gameData.yardsToGo,
      homeTimeouts: gameData.homeTimeouts,
      awayTimeouts: gameData.awayTimeouts,
      humanPlaysOffense: gameData.humanPlaysOffense,
      humanTeamId: gameData.humanTeamId,
      cpuTeamId: gameData.cpuTeamId,
      playLog: gameData.playLog,
      savedAt: new Date().toISOString(),
    };
    
    try {
      localStorage.setItem('paydirt_save', JSON.stringify(saveData));
      console.log('Game saved successfully');
      return true;
    } catch (err) {
      console.error('Failed to save game:', err);
      return false;
    }
  },
  
  loadGame: () => {
    try {
      const savedData = localStorage.getItem('paydirt_save');
      if (savedData) {
        const data = JSON.parse(savedData);
        set({
          gamePhase: 'playing',
          gameId: data.gameId,
          homeTeam: data.homeTeam,
          awayTeam: data.awayTeam,
          homeScore: data.homeScore,
          awayScore: data.awayScore,
          quarter: data.quarter,
          timeRemaining: data.timeRemaining,
          possession: data.possession,
          ballPosition: data.ballPosition,
          down: data.down,
          yardsToGo: data.yardsToGo,
          homeTimeouts: data.homeTimeouts,
          awayTimeouts: data.awayTimeouts,
          humanPlaysOffense: data.humanPlaysOffense,
          humanTeamId: data.humanTeamId,
          cpuTeamId: data.cpuTeamId,
          playLog: data.playLog || [],
          savedAt: data.savedAt,
        });
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to load game:', err);
      return false;
    }
  },
  
  hasSavedGame: () => {
    try {
      return localStorage.getItem('paydirt_save') !== null;
    } catch {
      return false;
    }
  },
  
  hasSavedReplay: () => {
    try {
      return localStorage.getItem('paydirt_replay') !== null;
    } catch {
      return false;
    }
  },
  
  saveReplay: (gameId) => {
    const state = get();
    
    const replayData = {
      replay_id: `replay_${Date.now()}`,
      game_state: {
        game_id: gameId,
        home_team: state.homeTeam,
        away_team: state.awayTeam,
        home_score: state.homeScore,
        away_score: state.awayScore,
        quarter: state.quarter,
        time_remaining: state.timeRemaining,
        possession: state.possession,
        ball_position: state.ballPosition,
        down: state.down,
        yards_to_go: state.yardsToGo,
        game_over: state.gameOver,
        home_timeouts: state.homeTimeouts,
        away_timeouts: state.awayTimeouts,
        player_offense: state.playerOffense,
        human_team_id: state.humanTeamId,
        cpu_team_id: state.cpuTeamId,
        human_is_home: state.humanIsHome,
      },
      play_history: state.playLog,
    };
    
    try {
      localStorage.setItem('paydirt_replay', JSON.stringify({
        replay_data: replayData,
        savedAt: new Date().toISOString(),
      }));
      console.log('Replay saved:', replayData.game_state);
      return Promise.resolve(replayData);
    } catch (err) {
      console.error('Failed to save replay:', err);
      return Promise.reject(err);
    }
  },
  
  loadReplay: () => {
    try {
      const savedReplay = localStorage.getItem('paydirt_replay');
      if (savedReplay) {
        const replay = JSON.parse(savedReplay);
        const replayData = replay.replay_data;
        
        if (!replayData || !replayData.game_state) {
          console.error('Invalid replay data:', replay);
          throw new Error('Invalid replay data structure');
        }
        
        const gameState = replayData.game_state;
        console.log('Loading replay:', gameState.quarter, 'Q, possession:', gameState.possession);
        
        // Call backend to create a new game with saved state
        const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
        console.log('Calling backend:', apiBase + '/api/game/load-replay');
        
        return fetch(`${apiBase}/api/game/load-replay`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ replay_data: replayData }),
        })
          .then(res => {
            console.log('Backend response status:', res.status);
            if (!res.ok) throw new Error('Failed to load replay on backend');
            return res.json();
          })
          .then(data => {
            console.log('Backend response data:', data);
            // Update store with new game from backend
            set({
              gamePhase: 'playing',
              gameId: data.game_id,
              homeTeam: data.game_state.home_team,
              awayTeam: data.game_state.away_team,
              homeScore: data.game_state.home_score,
              awayScore: data.game_state.away_score,
              quarter: data.game_state.quarter,
              timeRemaining: data.game_state.time_remaining,
              possession: data.game_state.possession,
              ballPosition: data.game_state.ball_position,
              down: data.game_state.down,
              yardsToGo: data.game_state.yards_to_go,
              homeTimeouts: data.game_state.home_timeouts,
              awayTimeouts: data.game_state.away_timeouts,
              humanTeamId: data.game_state.human_team_id,
              cpuTeamId: data.game_state.cpu_team_id,
              humanIsHome: data.game_state.human_is_home,
              playerOffense: data.game_state.player_offense,
              playLog: replayData.play_history || [],
              isKickoff: false,
            });
            return data;
          });
      }
      return Promise.reject(new Error('No saved replay found'));
    } catch (err) {
      console.error('Failed to load replay:', err);
      return Promise.reject(err);
    }
  },
  
  clearReplay: () => {
    try {
      localStorage.removeItem('paydirt_replay');
    } catch {
      // Ignore
    }
  },
}))
