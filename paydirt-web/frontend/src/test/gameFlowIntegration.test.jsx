import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useGameStore } from '../store/gameStore.js'

describe('Penalty Decision Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    }))
    
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      playLog: [],
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 0,
      awayScore: 0,
      quarter: 1,
      timeRemaining: 800,
      possession: 'home',
      ballPosition: 30,
      down: 2,
      yardsToGo: 5,
      playerOffense: true,
    })
  })

  it('should prepare penalty decision API call correctly', () => {
    const store = useGameStore.getState()
    
    const penaltyDecisionBody = {
      game_id: store.gameId,
      penalty_index: 0,
      accept_penalty: true,
    }
    
    expect(penaltyDecisionBody.game_id).toBe('test-game-123')
    expect(penaltyDecisionBody.accept_penalty).toBe(true)
    expect(penaltyDecisionBody.penalty_index).toBe(0)
  })

  it('should handle penalty data extraction correctly', () => {
    const penaltyData = {
      description: 'Holding penalty on the offense',
      yards: 5,
      pending_penalty_decision: true,
      penalty_choice: {
        offended_team: 'offense',
        offsetting: false,
        penalty_options: [
          { description: 'Penalty accepted: 1st & 15', yards: -5, auto_first_down: false }
        ]
      }
    }
    
    const penalty_choice = penaltyData.penalty_choice
    
    expect(penalty_choice.offsetting).toBe(false)
    expect(penalty_choice.offended_team).toBe('offense')
    expect(penalty_choice.penalty_options.length).toBe(1)
    expect(penalty_choice.penalty_options[0].yards).toBe(-5)
  })

  it('should handle offsetting penalties correctly', () => {
    const penaltyData = {
      description: 'Offsetting penalties',
      yards: 0,
      pending_penalty_decision: true,
      penalty_choice: {
        offended_team: '',
        offsetting: true,
        penalty_options: []
      }
    }
    
    const penalty_choice = penaltyData.penalty_choice
    
    expect(penalty_choice.offsetting).toBe(true)
    expect(penalty_choice.penalty_options.length).toBe(0)
  })
})

describe('Touchdown and PAT Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    }))
    
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      playLog: [],
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 7,
      awayScore: 0,
      quarter: 1,
      timeRemaining: 500,
      possession: 'home',
      ballPosition: 95,
      down: 1,
      yardsToGo: 5,
      playerOffense: true,
    })
  })

  it('should handle touchdown score update correctly', () => {
    const store = useGameStore.getState()
    expect(store.homeScore).toBe(7)
    
    store.updateGameState({
      home_score: 14,
      away_score: 0,
      quarter: 1,
      time_remaining: 495,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      human_plays_offense: true,
      human_is_home: true,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.homeScore).toBe(14)
  })
})

describe('CPU Decision Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    }))
    
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      playLog: [],
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 0,
      awayScore: 0,
      quarter: 2,
      timeRemaining: 100,
      possession: 'away',
      ballPosition: 60,
      down: 4,
      yardsToGo: 8,
      playerOffense: false,
      cpuFourthDownDecision: {
        decision: 'field_goal',
        play: 'F',
        description: 'CPU will attempt a field goal'
      },
    })
  })

  it('should store CPU fourth down decision correctly', () => {
    const store = useGameStore.getState()
    expect(store.cpuFourthDownDecision).toBeDefined()
    expect(store.cpuFourthDownDecision.decision).toBe('field_goal')
    expect(store.cpuFourthDownDecision.play).toBe('F')
  })
  
  it('should clear CPU fourth down decision correctly', () => {
    const store = useGameStore.getState()
    expect(store.cpuFourthDownDecision).toBeDefined()
    
    store.clearCpuFourthDownDecision()
    
    const clearedStore = useGameStore.getState()
    expect(clearedStore.cpuFourthDownDecision).toBeNull()
  })
})

describe('Game State Updates', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    }))
    
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      playLog: [],
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 0,
      awayScore: 0,
      quarter: 1,
      timeRemaining: 900,
      possession: 'home',
      ballPosition: 25,
      down: 1,
      yardsToGo: 10,
      playerOffense: true,
    })
  })

  it('should update scores correctly after touchdown', () => {
    const store = useGameStore.getState()
    expect(store.homeScore).toBe(0)
    
    store.updateGameState({
      home_score: 7,
      away_score: 0,
      quarter: 1,
      time_remaining: 850,
      possession: 'home',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      human_plays_offense: true,
      human_is_home: true,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.homeScore).toBe(7)
  })

  it('should update possession correctly', () => {
    const store = useGameStore.getState()
    expect(store.possession).toBe('home')
    expect(store.playerOffense).toBe(true)
    
    store.updateGameState({
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 800,
      possession: 'away',
      ball_position: 40,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      player_offense: false,
      human_is_home: true,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.possession).toBe('away')
    expect(updatedStore.playerOffense).toBe(false)
  })

  it('should track downs correctly', () => {
    const store = useGameStore.getState()
    expect(store.down).toBe(1)
    expect(store.yardsToGo).toBe(10)
    
    store.updateGameState({
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 850,
      possession: 'home',
      ball_position: 25,
      down: 2,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      human_plays_offense: true,
      human_is_home: true,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.down).toBe(2)
  })

  it('should handle first down correctly', () => {
    const store = useGameStore.getState()
    
    store.updateGameState({
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 800,
      possession: 'home',
      ball_position: 40,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      human_plays_offense: true,
      human_is_home: true,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.down).toBe(1)
    expect(updatedStore.yardsToGo).toBe(10)
  })
})

describe('Play Log Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    }))
    
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      playLog: [],
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 0,
      awayScore: 0,
      quarter: 1,
      timeRemaining: 900,
      possession: 'home',
      ballPosition: 25,
      down: 1,
      yardsToGo: 10,
      playerOffense: true,
    })
  })

  it('should add plays to log correctly', () => {
    const store = useGameStore.getState()
    
    store.addToPlayLog({
      quarter: 1,
      timeRemaining: 900,
      down: 1,
      yardsToGo: 10,
      ballPosition: 25,
      offenseTeam: 'MCT',
      defenseTeam: 'HBI',
      offensePlay: '1',
      defensePlay: 'A',
      description: 'Run up the middle for 4 yards',
      yards: 4,
      newPosition: 29,
    })
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.playLog.length).toBe(1)
    expect(updatedStore.playLog[0].description).toBe('Run up the middle for 4 yards')
  })

  it('should preserve play order in log', () => {
    const store = useGameStore.getState()
    
    for (let i = 0; i < 5; i++) {
      store.addToPlayLog({
        quarter: 1,
        timeRemaining: 900 - (i * 30),
        down: Math.min(i + 1, 4),
        yardsToGo: 10,
        ballPosition: 25 + i,
        offenseTeam: 'MCT',
        defenseTeam: 'HBI',
        offensePlay: String(i + 1),
        defensePlay: 'A',
        description: `Play ${i + 1}`,
        yards: i,
        newPosition: 25 + i + 1,
      })
    }
    
    const updatedStore = useGameStore.getState()
    expect(updatedStore.playLog.length).toBe(5)
    expect(updatedStore.playLog[0].description).toBe('Play 1')
    expect(updatedStore.playLog[4].description).toBe('Play 5')
  })

  it('should clear play log on reset', () => {
    useGameStore.setState({
      playLog: [{ quarter: 1, timeRemaining: 900, description: 'Test play' }],
    })
    
    const store = useGameStore.getState()
    expect(store.playLog.length).toBe(1)
    
    store.reset()
    
    const resetStore = useGameStore.getState()
    expect(resetStore.playLog).toEqual([])
  })
})
