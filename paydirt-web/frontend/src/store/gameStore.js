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
  cpuTeamId: null,
  humanPlaySelected: null,
  cpuPlaySelected: null,
  gameOver: false,
  playResult: null,
  cpuFourthDownDecision: null,
  pendingExtraPoint: null,
  canGoForTwo: false,
  pendingPenalty: null,
  difficulty: 'medium',
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
  setCpuFourthDownDecision: (decision) => set({ cpuFourthDownDecision: decision }),
  clearCpuFourthDownDecision: () => set({ cpuFourthDownDecision: null }),
  setPendingExtraPoint: (data) => set({ pendingExtraPoint: data, canGoForTwo: data?.canGoForTwo || false }),
  clearPendingExtraPoint: () => set({ pendingExtraPoint: null, canGoForTwo: false }),
  setPendingPenalty: (data) => set({ pendingPenalty: data }),
  clearPendingPenalty: () => set({ pendingPenalty: null }),
  
  updateGameState: (state) => {
    const possession = state.possession
    const humanPlaysOffense = state.human_plays_offense
    
    // human_is_home comes from backend as human_is_home, we need to use it
    // If not provided, keep the existing value
    const human_is_home = state.human_is_home !== undefined ? state.human_is_home : state.humanIsHome
    
    // humanIsOnOffense depends on possession relative to where the human plays
    // If possession is at human's end (human is on offense): humanPlaysOffense = true
    // If possession is at opponent's end (human is on defense): humanPlaysOffense = false
    let humanControlsOffense = false
    if (human_is_home !== undefined && human_is_home !== null) {
      // Possession at human's end means human is on offense
      const possession_at_human_end = (possession === 'home' && human_is_home) || (possession === 'away' && !human_is_home)
      humanControlsOffense = possession_at_human_end ? humanPlaysOffense : !humanPlaysOffense
    }
    
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
      humanPlaysOffense: humanPlaysOffense,
      humanIsOnOffense: humanControlsOffense,
      humanIsHome: human_is_home,
      playerOffense: humanControlsOffense,
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
  
  reset: () => set({ gamePhase: 'menu', gameId: null, ...initialGameState }),
}))
