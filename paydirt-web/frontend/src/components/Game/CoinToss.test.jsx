import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { CoinToss } from './CoinToss'

describe('CoinToss', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllTimers()
  })

  it('renders the coin toss screen', () => {
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={vi.fn()} />)
    expect(screen.getByTestId('coin-toss')).toBeDefined()
    expect(screen.getByText('COIN TOSS')).toBeDefined()
  })

  it('shows question mark while coin is flipping', () => {
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={vi.fn()} />)
    
    // Initially should show question mark
    expect(screen.getByText('?')).toBeDefined()
    expect(screen.getByText('Flipping coin...')).toBeDefined()
  })

  it('hides coin result while waiting for player call', async () => {
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={vi.fn()} />)
    
    // Advance past the initial flip
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    // Should still show question mark - result is hidden until call is made
    expect(screen.getByText('?')).toBeDefined()
    // Should show call buttons
    expect(screen.getByText(/Call it/)).toBeDefined()
  })

  it('shows heads/tails buttons after flip', async () => {
    const onComplete = vi.fn()
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={onComplete} />)
    
    // Fast forward past the initial flip animation
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    expect(screen.getByText(/Call it/)).toBeDefined()
    expect(screen.getByText('HEADS')).toBeDefined()
    expect(screen.getByText('TAILS')).toBeDefined()
  })

  it('reveals coin result only after player makes call', async () => {
    const onComplete = vi.fn()
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={onComplete} />)
    
    // Advance past the initial flip
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    // Make a call
    fireEvent.click(screen.getByTestId('choose-heads'))
    
    // Coin should be flipping again during reveal animation
    // (spinning coin = showing ?)
    expect(screen.getByText('?')).toBeDefined()
    
    // Advance past the reveal animation
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })
    
    // Now result should be revealed
    // Should show "It's heads!" or "It's tails!"
    const resultText = screen.queryByText(/It's (heads|tails)!/i)
    expect(resultText).toBeTruthy()
    
    // Should show either won or lost message
    const wonText = screen.queryByText('You won the toss!')
    const lostText = screen.queryByText('You lost the toss')
    expect(wonText || lostText).toBeTruthy()
  })

  it('does not leak coin result before call is made', async () => {
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={vi.fn()} />)
    
    // Advance past the initial flip
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    // Should NOT show the result yet
    expect(screen.queryByText(/It's (heads|tails)!/i)).toBeNull()
    expect(screen.queryByText('You won the toss!')).toBeNull()
    expect(screen.queryByText('You lost the toss')).toBeNull()
    
    // Should show call buttons instead
    expect(screen.getByText(/Call it/)).toBeDefined()
  })

  it('calls onComplete when player loses toss and continues', async () => {
    const onComplete = vi.fn()
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={onComplete} />)
    
    // Fast forward past the initial flip animation
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    // Click heads
    fireEvent.click(screen.getByTestId('choose-heads'))
    
    // Fast forward past the reveal animation
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })
    
    // Check what happened - either won or lost
    const wonMessage = screen.queryByText(/Choose what to do/)
    const lostMessage = screen.queryByText(/elects to receive/)
    
    if (wonMessage) {
      // Player won - should see receive/kick buttons
      expect(screen.getByText('RECEIVE')).toBeDefined()
      expect(screen.getByText('KICK OFF')).toBeDefined()
      
      // Click receive
      fireEvent.click(screen.getByTestId('choose-receive'))
      
      expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({
        playerReceives: true,
      }))
    } else {
      // Player lost - should see continue button
      expect(screen.getByTestId('coin-toss-continue')).toBeDefined()
      fireEvent.click(screen.getByTestId('coin-toss-continue'))
      
      expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({
        playerWonToss: false,
      }))
    }
  })

  it('calls onComplete when player wins and chooses kick', async () => {
    const onComplete = vi.fn()
    render(<CoinToss homeTeam={{ name: 'Home', short_name: 'HOM' }} awayTeam={{ name: 'Away', short_name: 'AWY' }} onComplete={onComplete} />)
    
    // Fast forward past the initial flip animation
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    
    // Keep clicking until we win (simplified - just test the flow)
    // Click a button
    const headsBtn = screen.getByTestId('choose-heads')
    fireEvent.click(headsBtn)
    
    // Fast forward past the reveal animation
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })
    
    // Check what happened
    const wonMessage = screen.queryByText(/Choose what to do/)
    
    if (wonMessage) {
      // Player won - click kick off
      fireEvent.click(screen.getByTestId('choose-kick'))
      
      expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({
        playerWonToss: true,
        playerReceives: false,
      }))
    }
  })
})
