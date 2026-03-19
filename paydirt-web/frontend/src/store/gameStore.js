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
  playerOffense: true,
  humanPlaySelected: null,
  cpuPlaySelected: null,
  gameOver: false,
  playResult: null,
}

export const useGameStore = create((set, get) => ({
  gamePhase: 'menu',
  gameId: null,
  ...initialGameState,

  setGamePhase: (phase) => set({ gamePhase: phase }),
  setGameId: (id) => set({ gameId: id }),
  
  setHumanPlay: (play) => set({ humanPlaySelected: play }),
  setCpuPlay: (play) => set({ cpuPlaySelected: play }),
  setPlayResult: (result) => set({ playResult: result }),
  
  updateGameState: (state) => set({
    homeTeam: state.home_team,
    awayTeam: state.away_team,
    homeScore: state.home_score,
    awayScore: state.away_score,
    quarter: state.quarter,
    timeRemaining: state.time_remaining,
    possession: state.possession,
    ballPosition: state.ball_position,
    down: state.down,
    yardsToGo: state.yards_to_go,
    gameOver: state.game_over,
    homeTimeouts: state.home_timeouts,
    awayTimeouts: state.away_timeouts,
    playerOffense: state.player_offense,
    ...state,
  }),
  
  startNewGame: (gameData) => set({
    gameId: gameData.game_id,
    homeTeam: gameData.home_team,
    awayTeam: gameData.away_team,
    homeScore: gameData.home_score,
    awayScore: gameData.away_score,
    quarter: gameData.quarter,
    timeRemaining: gameData.time_remaining,
    possession: gameData.possession,
    ballPosition: gameData.ball_position,
    down: gameData.down,
    yardsToGo: gameData.yards_to_go,
    homeTimeouts: 3,
    awayTimeouts: 3,
    playerOffense: true,
    humanPlaySelected: null,
    cpuPlaySelected: null,
    playResult: null,
    gameOver: false,
  }),

  resetGameState: () => set(initialGameState),
  
  reset: () => set({ gamePhase: 'menu', gameId: null, ...initialGameState }),
}))
