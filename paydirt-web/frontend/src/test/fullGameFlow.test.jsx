import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../App.jsx'
import { useGameStore } from '../store/gameStore.js'

describe('Full Game Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Reset store to known state
    useGameStore.setState({
      gamePhase: 'menu',
      gameId: null,
      playLog: [],
      homeTeam: null,
      awayTeam: null,
      homeScore: 0,
      awayScore: 0,
    })
    
    // Mock fetch
    global.fetch = vi.fn()
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        seasons: ['2026'],
        teams: [
          { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT', team_color: '#0066CC' },
          { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI', team_color: '#8B4513' },
        ]
      })
    })
  })

  it('should render menu with PAYDIRT title', async () => {
    await act(async () => {
      render(<App />)
    })
    
    expect(screen.getByText(/PAYDIRT/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /NEW GAME/i })).toBeInTheDocument()
  })

  it('should have proper default values in store', () => {
    const store = useGameStore.getState()
    
    expect(store.homeTeam).toBeNull()
    expect(store.awayTeam).toBeNull()
    expect(store.homeScore).toBe(0)
    expect(store.awayScore).toBe(0)
    expect(store.quarter).toBe(1)
    expect(store.timeRemaining).toBe(900)
    expect(store.possession).toBe('home')
    expect(store.ballPosition).toBe(35)
    expect(store.down).toBe(1)
    expect(store.yardsToGo).toBe(10)
    expect(store.homeTimeouts).toBe(3)
    expect(store.awayTimeouts).toBe(3)
    expect(store.playLog).toEqual([])
    expect(store.isKickoff).toBe(false)
    expect(store.gamePhase).toBe('menu')
  })

  it('should transition to team select on NEW GAME click', async () => {
    await act(async () => {
      render(<App />)
    })
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /NEW GAME/i }))
    })
    
    await waitFor(() => {
      expect(screen.getByText(/SELECT TEAMS/i)).toBeInTheDocument()
    })
    
    const store = useGameStore.getState()
    expect(store.gamePhase).toBe('teamSelect')
  })

  it('should handle reset properly', async () => {
    useGameStore.setState({
      gameId: 'test',
      homeTeam: { id: 'Test' },
      playLog: [{ description: 'Test play' }],
      homeScore: 21
    })
    
    let store = useGameStore.getState()
    expect(store.gameId).toBe('test')
    expect(store.playLog.length).toBe(1)
    expect(store.homeScore).toBe(21)
    
    useGameStore.getState().reset()
    
    store = useGameStore.getState()
    expect(store.gamePhase).toBe('menu')
    expect(store.gameId).toBeNull()
    expect(store.playLog).toEqual([])
    expect(store.homeScore).toBe(0)
  })

  it('should set and add to play log correctly', () => {
    useGameStore.setState({
      playLog: [{
        quarter: 1,
        description: 'Test play',
        yards: 5
      }]
    })
    
    let store = useGameStore.getState()
    expect(store.playLog.length).toBe(1)
    expect(store.playLog[0].description).toBe('Test play')
    
    store.addToPlayLog({
      quarter: 1,
      description: 'Second play',
      yards: 10
    })
    
    store = useGameStore.getState()
    expect(store.playLog.length).toBe(2)
    expect(store.playLog[1].description).toBe('Second play')
  })

  it('should update game state correctly', () => {
    const newState = {
      home_score: 7,
      away_score: 3,
      quarter: 2,
      time_remaining: 600,
      possession: 'away',
      ball_position: 45,
      down: 2,
      yards_to_go: 7,
      home_timeouts: 2,
      away_timeouts: 3,
      home_team: { id: 'THU', name: 'Thunderhawks' },
      away_team: { id: 'IRO', name: 'Ironclads' },
      possession: 'away',
      human_plays_offense: false,
      human_is_home: true,
    }
    
    useGameStore.getState().updateGameState(newState)
    
    const store = useGameStore.getState()
    expect(store.homeScore).toBe(7)
    expect(store.awayScore).toBe(3)
    expect(store.quarter).toBe(2)
    expect(store.timeRemaining).toBe(600)
    expect(store.possession).toBe('away')
    expect(store.ballPosition).toBe(45)
    expect(store.down).toBe(2)
    expect(store.yardsToGo).toBe(7)
  })

  it('should show kickoff banner when isKickoff is true', async () => {
    useGameStore.setState({
      gamePhase: 'playing',
      isKickoff: true,
      homeTeam: { id: 'THU', name: 'Thunderhawks', short_name: 'THU' },
      awayTeam: { id: 'IRO', name: 'Ironclads', short_name: 'IRO' },
      playerOffense: true,
    })
    
    await act(async () => {
      render(<App />)
    })
    
    expect(screen.getByText(/KICKOFF/i)).toBeInTheDocument()
  })

  it('should simulate a quarter and report final stats', () => {
    // Simulate a quarter of plays by updating game state directly
    const store = useGameStore.getState()
    
    // Setup game state as if we're in the middle of Q1
    store.updateGameState({
      home_team: { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
      away_team: { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
      home_score: 14,
      away_score: 7,
      quarter: 1,
      time_remaining: 450,
      possession: 'home',
      ball_position: 45,
      down: 2,
      yards_to_go: 6,
      human_plays_offense: true,
      human_is_home: true,
      home_timeouts: 2,
      away_timeouts: 3,
      game_over: false,
    })

    // Add some plays to the log with full details
    store.addToPlayLog({
      quarter: 1,
      timeRemaining: 800,
      down: 1,
      yardsToGo: 10,
      ballPosition: 25,
      lineOfScrimmage: 25,
      offenseTeam: 'MCT',
      defenseTeam: 'HBI',
      homeTeamAbbrev: 'MCT',
      awayTeamAbbrev: 'HBI',
      playerTeam: 'MCT',
      offensePlay: '1',
      defensePlay: '1',
      offenseDice: { black: 2, white1: 3, white2: 4, total: 9 },
      defenseDice: { red: 2, green: 1, total: 3 },
      description: 'Run up the middle for 5 yards.',
      headline: '5 YARD RUN',
      yards: 5,
      newPosition: 30,
    })
    
    store.addToPlayLog({
      quarter: 1,
      timeRemaining: 780,
      down: 2,
      yardsToGo: 5,
      ballPosition: 30,
      lineOfScrimmage: 30,
      offenseTeam: 'MCT',
      defenseTeam: 'HBI',
      homeTeamAbbrev: 'MCT',
      awayTeamAbbrev: 'HBI',
      playerTeam: 'MCT',
      offensePlay: '2',
      defensePlay: '2',
      offenseDice: { black: 1, white1: 0, white2: 1, total: 2 },
      defenseDice: { red: 3, green: 2, total: 5 },
      description: 'Pass incomplete.',
      yards: 0,
      newPosition: 30,
    })
    
    store.addToPlayLog({
      quarter: 1,
      timeRemaining: 750,
      down: 3,
      yardsToGo: 5,
      ballPosition: 30,
      lineOfScrimmage: 30,
      offenseTeam: 'MCT',
      defenseTeam: 'HBI',
      homeTeamAbbrev: 'MCT',
      awayTeamAbbrev: 'HBI',
      playerTeam: 'MCT',
      offensePlay: '3',
      defensePlay: '3',
      offenseDice: { black: 3, white1: 5, white2: 4, total: 12 },
      defenseDice: { red: 1, green: 0, total: 1 },
      description: 'Screen pass for 8 yards and a first down!',
      headline: 'FIRST DOWN!',
      yards: 8,
      newPosition: 38,
    })

    // Get final stats
    const finalStore = useGameStore.getState()
    
    console.log('')
    console.log('=== END OF QUARTER 1 SIMULATION ===')
    console.log(`Home Team: ${finalStore.homeTeam?.name || 'Thunderhawks'} (${finalStore.homeTeam?.short_name || 'MCT'})`)
    console.log(`Away Team: ${finalStore.awayTeam?.name || 'Ironclads'} (${finalStore.awayTeam?.short_name || 'HBI'})`)
    console.log(`Home Score: ${finalStore.homeScore}`)
    console.log(`Away Score: ${finalStore.awayScore}`)
    console.log(`Quarter: ${finalStore.quarter}`)
    console.log(`Time Remaining: ${finalStore.timeRemaining}`)
    console.log(`Possession: ${finalStore.possession} (${finalStore.possession === 'home' ? finalStore.homeTeam?.short_name || 'MCT' : finalStore.awayTeam?.short_name || 'HBI'})`)
    console.log(`Ball Position: ${finalStore.ballPosition}`)
    console.log(`Down: ${finalStore.down}`)
    console.log(`Yards to Go: ${finalStore.yardsToGo}`)
    console.log(`Total Plays: ${finalStore.playLog.length}`)
    console.log(`Home Timeouts Remaining: ${finalStore.homeTimeouts}`)
    console.log(`Away Timeouts Remaining: ${finalStore.awayTimeouts}`)
    console.log('====================================')
    console.log('PLAY BY PLAY:')
    finalStore.playLog.forEach((play, i) => {
      const offDice = play.offenseDice ? `${play.offenseDice.black}+${play.offenseDice.white1}+${play.offenseDice.white2}=${play.offenseDice.total}` : 'N/A'
      const defDice = play.defenseDice ? `${play.defenseDice.red}+${play.defenseDice.green}=${play.defenseDice.total}` : 'N/A'
      console.log(`  ${i + 1}. Q${play.quarter} ${play.timeRemaining}" - ${play.offenseTeam} vs ${play.defenseTeam}`)
      console.log(`     ${play.down_name || play.down}&${play.yardsToGo} at ${play.homeTeamAbbrev}-${play.awayTeamAbbrev} ${play.lineOfScrimmage}`)
      console.log(`     OFF: ${play.offensePlay} (${offDice}) | DEF: ${play.defensePlay} (${defDice})`)
      console.log(`     ${play.description}`)
      if (play.yards > 0) console.log(`     +${play.yards} yds -> ${play.homeTeamAbbrev}-${play.awayTeamAbbrev} ${play.newPosition}`)
      if (play.scoreChange) console.log(`     *** ${play.scoreChange} ***`)
    })
    console.log('====================================')
    
    // Assertions
    expect(finalStore.homeScore).toBe(14)
    expect(finalStore.awayScore).toBe(7)
    expect(finalStore.quarter).toBe(1)
    expect(finalStore.timeRemaining).toBe(450)
    expect(finalStore.possession).toBe('home')
    expect(finalStore.playLog.length).toBe(3)
    expect(finalStore.homeTimeouts).toBe(2)
    expect(finalStore.awayTimeouts).toBe(3)
  })
})
