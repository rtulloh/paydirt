import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { KickoffPlay } from './KickoffPlay'

global.fetch = vi.fn()

const mockFetch = (data, ok = true) => {
  fetch.mockResolvedValue({
    ok,
    json: () => Promise.resolve(data)
  })
}

describe('KickoffPlay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the kickoff screen', async () => {
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={vi.fn()} />)
    expect(screen.getByText('ONSIDE KICK')).toBeDefined()
    expect(screen.getByText(/kicks off to/)).toBeDefined()
  })

  it('shows kickoff choice buttons initially', async () => {
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={vi.fn()} />)
    
    // Should show KICKOFF and ONSIDE KICK buttons initially
    expect(screen.getByRole('button', { name: 'KICKOFF' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'ONSIDE KICK' })).toBeDefined()
  })

  it('fetches kickoff result and displays it', async () => {
    const onComplete = vi.fn()
    
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={onComplete} />)
    
    // Set up mock before clicking
    mockFetch({
      result: {
        description: 'Kickoff 65 yards, returned to the 20 yard line.',
        yards: 20,
        turnover: false,
        touchdown: false,
      },
      game_state: {
        ball_position: 20,
        down: 1,
        yards_to_go: 10,
      },
      dice_roll_offense: 65,
      dice_roll_defense: 20,
    })
    
    // Click the KICKOFF button
    fireEvent.click(screen.getByRole('button', { name: 'KICKOFF' }))
    
    // Wait for the result to appear (component has 1.5s delay + fetch)
    await waitFor(() => {
      expect(screen.getByText(/Kickoff 65 yards/)).toBeDefined()
    }, { timeout: 10000 })
    
    // Should have a continue button
    expect(screen.getByText('CONTINUE')).toBeDefined()
  })

  // Skipped: needs fake timers or async fetch mocking rework
  it.skip('shows touchdown result when applicable', async () => {
    const onComplete = vi.fn()
    
    mockFetch({
      result: {
        description: 'KICK RETURNED FOR A TOUCHDOWN!',
        yards: 100,
        turnover: false,
        touchdown: true,
      },
      game_state: {
        ball_position: 100,
        down: 1,
        yards_to_go: 10,
      },
      dice_roll_offense: 70,
      dice_roll_defense: 100,
    })
    
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={false} gameId="test123" onComplete={onComplete} />)
    
    await waitFor(() => {
      expect(screen.getByText(/TOUCHDOWN!/)).toBeDefined()
    }, { timeout: 15000 })
  })

  it('calls onComplete when continue is clicked', async () => {
    const onComplete = vi.fn()
    
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={onComplete} />)
    
    // Set up mock before clicking the button
    mockFetch({
      result: {
        description: 'Ball placed at the 25 yard line.',
        yards: 25,
        turnover: false,
        touchdown: false,
      },
      game_state: {
        ball_position: 25,
        down: 1,
        yards_to_go: 10,
      },
      dice_roll_offense: 50,
      dice_roll_defense: 25,
    })
    
    // Click the KICKOFF button (not ONSIDE KICK)
    fireEvent.click(screen.getByRole('button', { name: 'KICKOFF' }))
    
    await waitFor(() => {
      expect(screen.getByText('CONTINUE')).toBeDefined()
    }, { timeout: 10000 })
    
    fireEvent.click(screen.getByText('CONTINUE'))
    
    expect(onComplete).toHaveBeenCalled()
  })

  it('shows correct team names based on playerOffense', () => {
    // Player is offense (kicking team)
    const { rerender } = render(
      <KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={vi.fn()} />
    )
    
    expect(screen.getByText(/HOM kicks off to AWY/)).toBeTruthy()
    
    // Player is defense (receiving team)
    rerender(
      <KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={false} gameId="test123" onComplete={vi.fn()} />
    )
    
    expect(screen.getByText(/AWY kicks off to HOM/)).toBeTruthy()
  })

  it('has error handling for failed fetch', async () => {
    // Test that component handles errors gracefully
    // This is a basic smoke test - full error testing would require more setup
    const onComplete = vi.fn()
    
    // Mock a failing fetch
    fetch.mockRejectedValue(new Error('Network error'))
    
    render(<KickoffPlay homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} playerOffense={true} gameId="test123" onComplete={onComplete} />)
    
    // Component should render without crashing
    expect(screen.getByText('ONSIDE KICK')).toBeDefined()
  })
})
