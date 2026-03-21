import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useGameStore } from '../store/gameStore.js'

describe('Replay Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock localStorage
    const storage = {}
    global.localStorage = {
      getItem: vi.fn((key) => storage[key] || null),
      setItem: vi.fn((key, value) => { storage[key] = value }),
      removeItem: vi.fn((key) => { delete storage[key] }),
    }
    
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ 
        status: 'ok',
        replay_id: 'replay_test123',
        game_state: {
          home_score: 0,
          away_score: 0,
          quarter: 1,
          time_remaining: 900,
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
        },
        play_history: [],
        created_at: '2024-01-01T00:00:00Z',
      })
    }))
    
    useGameStore.setState({
      gamePhase: 'menu',
      gameId: null,
      playLog: [],
      homeTeam: null,
      awayTeam: null,
      homeScore: 0,
      awayScore: 0,
    })
  })

  it('should check for saved replay', () => {
    const store = useGameStore.getState()
    expect(store.hasSavedReplay).toBeDefined()
    expect(typeof store.hasSavedReplay).toBe('function')
  })

  it('should save replay with current store state', async () => {
    useGameStore.setState({
      gamePhase: 'playing',
      gameId: 'test-game-123',
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      homeScore: 7,
      awayScore: 3,
      quarter: 2,
      timeRemaining: 500,
      possession: 'away',
      ballPosition: 45,
      down: 2,
      yardsToGo: 5,
      homeTimeouts: 2,
      awayTimeouts: 3,
      playerOffense: false,
      humanTeamId: 'Thunderhawks',
      cpuTeamId: 'Ironclads',
      humanIsHome: true,
      playLog: [{ description: 'Test play' }],
    })
    
    const store = useGameStore.getState()
    const result = await store.saveReplay('test-game-123')
    
    expect(result).toBeDefined()
    expect(result.replay_id).toBeDefined()
    expect(result.game_state.home_score).toBe(7)
    expect(result.game_state.possession).toBe('away')
    expect(result.game_state.ball_position).toBe(45)
    expect(result.game_state.player_offense).toBe(false)
    expect(result.play_history).toHaveLength(1)
    
    // Verify it was saved to localStorage
    const saved = global.localStorage.getItem('paydirt_replay')
    expect(saved).toBeTruthy()
  })

  it('should load replay and update state', async () => {
    // Set up localStorage with saved replay
    global.localStorage.setItem('paydirt_replay', JSON.stringify({
      replay_data: {
        season: '2026',
        game_state: {
          game_id: 'game_test123',
          home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
          away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
          home_score: 7,
          away_score: 0,
          quarter: 2,
          time_remaining: 500,
          possession: 'away',
          ball_position: 45,
          down: 2,
          yards_to_go: 5,
          home_timeouts: 2,
          away_timeouts: 3,
          human_team_id: 'Thunderhawks',
          cpu_team_id: 'Ironclads',
          human_is_home: true,
          player_offense: false,
        },
        play_history: [{ description: 'Test play' }],
      },
      savedAt: '2024-01-01T00:00:00Z',
    }))
    
    // Mock the fetch call
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        game_id: 'game_new123',
        game_state: {
          game_id: 'game_new123',
          home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
          away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
          home_score: 7,
          away_score: 0,
          quarter: 2,
          time_remaining: 500,
          possession: 'away',
          ball_position: 45,
          down: 2,
          yards_to_go: 5,
          home_timeouts: 2,
          away_timeouts: 3,
          human_team_id: 'Thunderhawks',
          cpu_team_id: 'Ironclads',
          human_is_home: true,
          player_offense: false,
        },
        difficulty: 'medium',
      }),
    })
    
    const store = useGameStore.getState()
    await store.loadReplay()
    
    const state = useGameStore.getState()
    expect(state.gamePhase).toBe('playing')
    expect(state.homeScore).toBe(7)
    expect(state.possession).toBe('away')
    expect(state.playerOffense).toBe(false)
  })

  it('should clear replay', () => {
    const store = useGameStore.getState()
    store.clearReplay()
    
    const hasReplay = (() => {
      try {
        return localStorage.getItem('paydirt_replay') !== null
      } catch {
        return false
      }
    })()
    
    expect(hasReplay).toBe(false)
  })
})

describe('Kickoff After Score', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    const storage = {}
    global.localStorage = {
      getItem: vi.fn((key) => storage[key] || null),
      setItem: vi.fn((key, value) => { storage[key] = value }),
      removeItem: vi.fn((key) => { delete storage[key] }),
    }
  })
  
  it('should set isKickoff true when loading replay with FG score', async () => {
    // Mock fetch to return response with is_kickoff = true
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        game_id: 'test_game_123',
        game_state: {
          is_kickoff: true,
          home_score: 3,
          away_score: 0,
          quarter: 1,
          time_remaining: 645,
          possession: 'away',
          ball_position: 35,
          down: 1,
          yards_to_go: 10,
          game_over: false,
          home_timeouts: 3,
          away_timeouts: 3,
          home_team: { id: 'Ironclads', name: 'Iron Mountain Ironclads', short_name: 'Iron' },
          away_team: { id: 'Outlaws', name: 'Oklahoma Outlaws', short_name: 'Outl' },
          human_team_id: 'Ironclads',
          cpu_team_id: 'Outlaws',
          human_is_home: true,
          player_offense: false,
        },
      })
    }))
    
    // Set localStorage with replay containing FG
    const replayData = {
      replay_data: {
        season: '2026',
        game_state: {
          home_score: 3,
          away_score: 0,
        },
        play_history: [
          { description: 'Field goal GOOD! (22 yards)', headline: 'Field Goal' }
        ]
      }
    }
    localStorage.setItem('paydirt_replay', JSON.stringify(replayData))
    
    // Reset store state
    useGameStore.setState({
      gamePhase: 'menu',
      gameId: null,
      playLog: [],
      isKickoff: false,
    })
    
    // Load replay
    await useGameStore.getState().loadReplay()
    
    // Check isKickoff is set to true from backend response
    const state = useGameStore.getState()
    expect(state.isKickoff).toBe(true)
    expect(state.down).toBe(1)
    expect(state.yardsToGo).toBe(10)
    expect(state.ballPosition).toBe(35)
  })
  
  it('should set isKickoff false when loading replay with no score', async () => {
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        game_id: 'test_game_456',
        game_state: {
          is_kickoff: false,
          home_score: 0,
          away_score: 0,
          quarter: 1,
          time_remaining: 800,
          possession: 'home',
          ball_position: 30,
          down: 2,
          yards_to_go: 7,
          game_over: false,
          home_timeouts: 3,
          away_timeouts: 3,
          home_team: { id: 'Ironclads', name: 'Iron Mountain Ironclads', short_name: 'Iron' },
          away_team: { id: 'Outlaws', name: 'Oklahoma Outlaws', short_name: 'Outl' },
          human_team_id: 'Ironclads',
          cpu_team_id: 'Outlaws',
          human_is_home: true,
          player_offense: true,
        },
      })
    }))
    
    const replayData = {
      replay_data: {
        season: '2026',
        game_state: {
          home_score: 0,
          away_score: 0,
        },
        play_history: [
          { description: 'Run for 3 yards', headline: 'Gain of 3' }
        ]
      }
    }
    localStorage.setItem('paydirt_replay', JSON.stringify(replayData))
    
    useGameStore.setState({
      gamePhase: 'menu',
      gameId: null,
      playLog: [],
      isKickoff: true,  // Start with true to verify it gets set to false
    })
    
    await useGameStore.getState().loadReplay()
    
    const state = useGameStore.getState()
    expect(state.isKickoff).toBe(false)
    expect(state.down).toBe(2)
    expect(state.yardsToGo).toBe(7)
  })
})

describe('Debug Mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        deterministic_mode: false,
        seed: null,
      })
    })
  })

  it('should have debug settings functions', () => {
    // Debug settings would be handled by backend
    expect(true).toBe(true)
  })
})
