import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import App from './App.jsx'

global.fetch = vi.fn()

const mockFetch = (data, ok = true) => {
  fetch.mockResolvedValue({
    ok,
    json: () => Promise.resolve(data)
  })
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the title', () => {
    mockFetch({ status: 'healthy', service: 'paydirt-web' })
    render(<App />)
    expect(screen.getByText('PAYDIRT')).toBeDefined()
  })

  it('shows NEW GAME button', () => {
    mockFetch({ status: 'healthy', service: 'paydirt-web' })
    render(<App />)
    expect(screen.getByText('NEW GAME')).toBeDefined()
  })

  it('shows backend status indicator', async () => {
    mockFetch({ status: 'healthy', service: 'paydirt-web' })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Backend: connected')).toBeDefined()
    })
  })

  it('shows disconnected when backend unavailable', async () => {
    fetch.mockRejectedValue(new Error('Backend not available'))
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Backend: disconnected')).toBeDefined()
    })
  })
})

describe('Game Store', () => {
  it('should be importable', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    expect(useGameStore).toBeDefined()
  })

  it('should have initial state', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    const store = useGameStore.getState()
    expect(store.gamePhase).toBe('menu')
    expect(store.gameId).toBe(null)
  })

  it('should update game phase', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    useGameStore.getState().setGamePhase('teamSelect')
    expect(useGameStore.getState().gamePhase).toBe('teamSelect')
  })

  it('should reset state', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    useGameStore.getState().setGamePhase('playing')
    useGameStore.getState().setGameId('test123')
    useGameStore.getState().reset()
    const store = useGameStore.getState()
    expect(store.gamePhase).toBe('menu')
    expect(store.gameId).toBe(null)
  })

  it('should track human and CPU team IDs', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    const store = useGameStore.getState()
    
    // Verify the fields exist
    expect('humanTeamId' in store).toBe(true)
    expect('cpuTeamId' in store).toBe(true)
  })

  it('should track humanPlaysOffense', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    const store = useGameStore.getState()
    
    // Verify the field exists
    expect('humanPlaysOffense' in store).toBe(true)
  })

  it('startNewGame should set humanTeamId and cpuTeamId', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    const mockGameData = {
      game_id: 'test_game_123',
      home_team: { id: 'TeamA', name: 'Team A' },
      away_team: { id: 'TeamB', name: 'Team B' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'home',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'TeamA',
      cpu_team_id: 'TeamB',
    }
    
    useGameStore.getState().startNewGame(mockGameData)
    
    const store = useGameStore.getState()
    expect(store.humanTeamId).toBe('TeamA')
    expect(store.cpuTeamId).toBe('TeamB')
    expect(store.humanPlaysOffense).toBe(true)
  })

  it('startNewGame should calculate humanIsOnOffense correctly', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    // humanPlaysOffense = true means human controls offense
    // humanIsOnOffense should equal humanPlaysOffense regardless of possession
    
    // Human plays offense, possession is home
    const mockGameData1 = {
      game_id: 'test_game_1',
      home_team: { id: 'HumanTeam', name: 'Human' },
      away_team: { id: 'CPU', name: 'CPU' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'home',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData1)
    expect(useGameStore.getState().humanIsOnOffense).toBe(true)
    
    // Human plays defense, possession is home
    const mockGameData2 = {
      game_id: 'test_game_2',
      home_team: { id: 'HumanTeam', name: 'Human' },
      away_team: { id: 'CPU', name: 'CPU' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'home',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: false,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData2)
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
    
    // Human plays offense, possession is away
    const mockGameData3 = {
      game_id: 'test_game_3',
      home_team: { id: 'CPU', name: 'CPU' },
      away_team: { id: 'HumanTeam', name: 'Human' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData3)
    expect(useGameStore.getState().humanIsOnOffense).toBe(true)
    
    // Human plays defense, possession is away
    const mockGameData4 = {
      game_id: 'test_game_4',
      home_team: { id: 'CPU', name: 'CPU' },
      away_team: { id: 'HumanTeam', name: 'Human' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: false,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData4)
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
  })

  it('should set humanIsHome when starting a new game', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    // Human is home team
    const mockGameData1 = {
      game_id: 'test_game',
      home_team: { id: 'HumanTeam', name: 'Human' },
      away_team: { id: 'CPU', name: 'CPU' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData1)
    expect(useGameStore.getState().humanIsHome).toBe(true)
    
    // Human is away team
    const mockGameData2 = {
      game_id: 'test_game2',
      home_team: { id: 'CPU', name: 'CPU' },
      away_team: { id: 'HumanTeam', name: 'Human' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData2)
    expect(useGameStore.getState().humanIsHome).toBe(false)
  })

  it('should correctly track possession after coin toss - human wins and receives', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    // Initial state: human is home, possession is 'away' (away receives kickoff at start)
    const mockGameData = {
      game_id: 'test_game',
      home_team: { id: 'HumanTeam', name: 'Human' },
      away_team: { id: 'CPU', name: 'CPU' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away',
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true, // Human plays offense (controls offense when possession is at their end)
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData)
    
    // At start: possession is 'away', humanIsHome is true
    // So possession is NOT at human's end (human is on defense)
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
    expect(useGameStore.getState().playerOffense).toBe(false)
    
    // Now simulate coin toss result: human wins, chooses to receive
    // After receiving, possession should switch to 'home'
    useGameStore.getState().updateGameState({
      possession: 'home',
      human_plays_offense: true,
      humanIsHome: true,
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
    })
    
    // Now possession is at human's end, human should be on offense
    expect(useGameStore.getState().humanIsOnOffense).toBe(true)
    expect(useGameStore.getState().playerOffense).toBe(true)
  })

  it('should correctly track possession after coin toss - human loses and kicks', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    // Human is away team, human plays defense
    const mockGameData = {
      game_id: 'test_game',
      home_team: { id: 'CPU', name: 'CPU' },
      away_team: { id: 'HumanTeam', name: 'Human' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'away', // Away (human) receives at start
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: false, // Human plays defense
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData)
    
    // Human is away, possession is 'away' (human's end), human plays defense
    // So human is on defense (possession is at human's end but they play defense)
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
    
    // Simulate coin toss: human loses, CPU receives
    // After kickoff, possession will be at human's end (away)
    useGameStore.getState().updateGameState({
      possession: 'away',
      human_plays_offense: false,
      humanIsHome: false,
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      ball_position: 35,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
    })
    
    // Human should be on defense
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
  })

  it('should switch offense/defense correctly during game', async () => {
    const { useGameStore } = await import('./store/gameStore.js')
    
    // Setup: human is home, plays offense
    const mockGameData = {
      game_id: 'test_game',
      home_team: { id: 'HumanTeam', name: 'Human' },
      away_team: { id: 'CPU', name: 'CPU' },
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 900,
      possession: 'home',
      ball_position: 25,
      down: 1,
      yards_to_go: 10,
      human_plays_offense: true,
      human_team_id: 'HumanTeam',
      cpu_team_id: 'CPU',
    }
    
    useGameStore.getState().startNewGame(mockGameData)
    
    // Human is on offense
    expect(useGameStore.getState().humanIsOnOffense).toBe(true)
    expect(useGameStore.getState().playerOffense).toBe(true)
    
    // After turnover/score, possession switches to 'away'
    useGameStore.getState().updateGameState({
      possession: 'away',
      human_plays_offense: true,
      humanIsHome: true,
      home_score: 0,
      away_score: 0,
      quarter: 1,
      time_remaining: 600,
      ball_position: 75,
      down: 1,
      yards_to_go: 10,
      game_over: false,
      home_timeouts: 3,
      away_timeouts: 3,
    })
    
    // Now human is on defense (possession is at opponent's end)
    expect(useGameStore.getState().humanIsOnOffense).toBe(false)
    expect(useGameStore.getState().playerOffense).toBe(false)
  })
})

describe('Save/Load Game Utils', () => {
  beforeEach(() => {
    // Mock localStorage
    let store = {}
    global.localStorage = {
      getItem: vi.fn((key) => store[key] || null),
      setItem: vi.fn((key, value) => { store[key] = value }),
      removeItem: vi.fn((key) => { delete store[key] }),
      clear: vi.fn(() => { store = {} }),
    }
  })

  it('should save and load game state with team IDs', async () => {
    const { saveGame, loadGame } = await import('./utils/saveGame.js')
    
    const gameState = {
      gameId: 'test_game_123',
      homeTeam: { id: 'Thunderhawks', name: 'Metro City Thunderhawks' },
      awayTeam: { id: 'Ironclads', name: 'Harbor Bay Ironclads' },
      homeScore: 21,
      awayScore: 14,
      quarter: 3,
      timeRemaining: 450,
      possession: 'away',
      ballPosition: 65,
      down: 2,
      yardsToGo: 7,
      homeTimeouts: 2,
      awayTimeouts: 3,
      humanPlaysOffense: false,
      humanTeamId: 'Ironclads',
      cpuTeamId: 'Thunderhawks',
    }
    
    saveGame(gameState)
    
    const loaded = loadGame()
    expect(loaded).not.toBeNull()
    expect(loaded.gameState.humanTeamId).toBe('Ironclads')
    expect(loaded.gameState.cpuTeamId).toBe('Thunderhawks')
    expect(loaded.gameState.homeScore).toBe(21)
    expect(loaded.gameState.awayScore).toBe(14)
    expect(loaded.gameState.possession).toBe('away')
    expect(loaded.gameState.humanPlaysOffense).toBe(false)
  })

  it('should preserve which team is human team after load', async () => {
    const { saveGame, loadGame } = await import('./utils/saveGame.js')
    
    // Case 1: Human is home team
    const gameState1 = {
      homeTeam: { id: 'HumanTeam', name: 'Human' },
      awayTeam: { id: 'CPU', name: 'CPU' },
      humanTeamId: 'HumanTeam',
      cpuTeamId: 'CPU',
      possession: 'home',
      humanPlaysOffense: true,
    }
    
    saveGame(gameState1)
    let loaded = loadGame()
    expect(loaded.gameState.homeTeam.id).toBe('HumanTeam')
    expect(loaded.gameState.humanTeamId).toBe('HumanTeam')
    
    // Case 2: Human is away team
    const gameState2 = {
      homeTeam: { id: 'CPU', name: 'CPU' },
      awayTeam: { id: 'HumanTeam', name: 'Human' },
      humanTeamId: 'HumanTeam',
      cpuTeamId: 'CPU',
      possession: 'away',
      humanPlaysOffense: true,
    }
    
    saveGame(gameState2)
    loaded = loadGame()
    expect(loaded.gameState.homeTeam.id).toBe('CPU')
    expect(loaded.gameState.humanTeamId).toBe('HumanTeam')
  })

  it('should detect saved game exists', async () => {
    const { saveGame, hasSavedGame } = await import('./utils/saveGame.js')
    
    localStorage.clear()
    expect(hasSavedGame()).toBe(false)
    
    saveGame({ homeScore: 10 })
    expect(hasSavedGame()).toBe(true)
  })

  it('should delete saved game', async () => {
    const { saveGame, hasSavedGame, deleteSavedGame } = await import('./utils/saveGame.js')
    
    saveGame({ homeScore: 10 })
    expect(hasSavedGame()).toBe(true)
    
    deleteSavedGame()
    expect(hasSavedGame()).toBe(false)
  })
})
