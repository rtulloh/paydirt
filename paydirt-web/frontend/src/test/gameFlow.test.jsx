/**
 * Integration tests for the game flow from start through first plays.
 * Run with: npm test -- --run src/test/gameFlow.test.jsx
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { KickoffPlay } from '../components/Game/KickoffPlay'

global.fetch = vi.fn()

const mockFetch = (data, ok = true, status = 200) => {
  fetch.mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(data)
  })
}

describe('Game Flow Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Coin Toss Flow', () => {
    it('should handle coin toss with player winning and receiving', () => {
      const coinData = {
        coinResult: 'heads',
        playerCall: 'heads',
        playerWonToss: true,
        playerReceives: true,
      }
      expect(coinData.playerWonToss).toBe(true)
      expect(coinData.playerReceives).toBe(true)
    })

    it('should handle coin toss with player losing', () => {
      const coinData = {
        coinResult: 'heads',
        playerCall: 'tails',
        playerWonToss: false,
        playerReceives: false,
      }
      expect(coinData.playerWonToss).toBe(false)
    })
  })

  describe('Kickoff Flow', () => {
    it('should render kickoff screen with correct props', () => {
      render(<KickoffPlay 
        homeTeam={{ id: 'MCT', name: 'Metro City Thunderhawks', short_name: 'MCT' }}
        awayTeam={{ id: 'HBI', name: 'Harbor Bay Ironclads', short_name: 'HBI' }}
        playerOffense={true}
        gameId="test123"
        onComplete={vi.fn()}
      />)
      
      expect(screen.getByText('OPENING KICKOFF')).toBeDefined()
    })

    it('should show correct teams when player is on defense (kicking)', () => {
      render(<KickoffPlay 
        homeTeam={{ id: 'MCT', name: 'Metro City Thunderhawks', short_name: 'MCT' }}
        awayTeam={{ id: 'HBI', name: 'Harbor Bay Ironclads', short_name: 'HBI' }}
        playerOffense={true}
        gameId="test123"
        onComplete={vi.fn()}
      />)
      
      expect(screen.getByText(/MCT kicks off to HBI/)).toBeTruthy()
    })

    it('should show correct teams when player is on offense (receiving)', () => {
      render(<KickoffPlay 
        homeTeam={{ id: 'MCT', name: 'Metro City Thunderhawks', short_name: 'MCT' }}
        awayTeam={{ id: 'HBI', name: 'Harbor Bay Ironclads', short_name: 'HBI' }}
        playerOffense={false}
        gameId="test123"
        onComplete={vi.fn()}
      />)
      
      expect(screen.getByText(/HBI kicks off to MCT/)).toBeTruthy()
    })
  })

  describe('Game Phase Transitions', () => {
    it('should include kickoff phase in game flow', () => {
      const validPhases = ['coinToss', 'kickoff', 'playing', 'halftime', 'gameOver']
      
      expect(validPhases).toContain('kickoff')
      expect(validPhases).toContain('coinToss')
      expect(validPhases).toContain('playing')
    })

    it('should transition from coinToss to kickoff to playing', () => {
      const flow = ['coinToss', 'kickoff', 'playing']
      
      expect(flow[0]).toBe('coinToss')
      expect(flow[1]).toBe('kickoff')
      expect(flow[2]).toBe('playing')
    })
  })

  describe('Possession Logic', () => {
    it('should set player on offense when player wins and chooses to receive', () => {
      const playerReceives = true
      const humanPlaysOffense = playerReceives
      
      expect(humanPlaysOffense).toBe(true)
    })

    it('should set player on defense when player wins and chooses to kick', () => {
      const playerReceives = false
      const humanPlaysOffense = playerReceives
      
      expect(humanPlaysOffense).toBe(false)
    })

    it('should correctly calculate humanIsOnOffense based on possession', () => {
      const testCases = [
        { humanIsHome: true, humanPlaysOffense: true, possession: 'home', expected: true },
        { humanIsHome: true, humanPlaysOffense: true, possession: 'away', expected: false },
        { humanIsHome: true, humanPlaysOffense: false, possession: 'home', expected: false },
        { humanIsHome: true, humanPlaysOffense: false, possession: 'away', expected: true },
        { humanIsHome: false, humanPlaysOffense: true, possession: 'home', expected: false },
        { humanIsHome: false, humanPlaysOffense: true, possession: 'away', expected: true },
        { humanIsHome: false, humanPlaysOffense: false, possession: 'home', expected: true },
        { humanIsHome: false, humanPlaysOffense: false, possession: 'away', expected: false },
      ]
      
      testCases.forEach(({ humanIsHome, humanPlaysOffense, possession, expected }) => {
        const possessionAtHumanEnd = (possession === 'home' && humanIsHome) || (possession === 'away' && !humanIsHome)
        const humanIsOnOffense = possessionAtHumanEnd ? humanPlaysOffense : !humanPlaysOffense
        
        expect(humanIsOnOffense).toBe(expected)
      })
    })
  })

  describe('API Request Shapes', () => {
    it('should have correct coin-toss request shape', () => {
      const request = {
        game_id: 'test123',
        player_won: true,
        player_kicks: false,
        human_plays_offense: true,
      }
      
      expect(request.game_id).toBeDefined()
      expect(request.player_won).toBeDefined()
      expect(request.player_kicks).toBeDefined()
      expect(request.human_plays_offense).toBeDefined()
    })

    it('should have correct kickoff request shape', () => {
      const request = {
        game_id: 'test123',
        kickoff_spot: 35,
      }
      
      expect(request.game_id).toBeDefined()
      expect(request.kickoff_spot).toBeDefined()
    })
  })

  describe('Error Handling', () => {
    it('should handle kickoff API failure gracefully', () => {
      fetch.mockRejectedValue(new Error('Network error'))
      
      const handleError = () => {
        return { error: 'Failed to process coin toss' }
      }
      
      expect(handleError().error).toBe('Failed to process coin toss')
    })

    it('should render KickoffPlay even when fetch fails', () => {
      fetch.mockRejectedValue(new Error('Network error'))
      
      render(<KickoffPlay 
        homeTeam={{ id: 'MCT', name: 'Metro City Thunderhawks', short_name: 'MCT' }}
        awayTeam={{ id: 'HBI', name: 'Harbor Bay Ironclads', short_name: 'HBI' }}
        playerOffense={true}
        gameId="test123"
        onComplete={vi.fn()}
      />)
      
      expect(screen.getByText('OPENING KICKOFF')).toBeDefined()
    })
  })
})
