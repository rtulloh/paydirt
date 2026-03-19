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
    render(<CoinToss homeTeam={{ name: 'Home' }} awayTeam={{ name: 'Away' }} onComplete={vi.fn()} />)
    expect(screen.getByTestId('coin-toss')).toBeDefined()
    expect(screen.getByText('COIN TOSS')).toBeDefined()
  })

  it('shows flipping animation initially', () => {
    render(<CoinToss homeTeam={{ name: 'Home' }} awayTeam={{ name: 'Away' }} onComplete={vi.fn()} />)
    expect(screen.getByText('Flipping...')).toBeDefined()
  })

  it('reveals result after flip timeout', async () => {
    vi.spyOn(global, 'setTimeout').mockImplementation((callback) => {
      return callback
    })
    
    render(<CoinToss homeTeam={{ name: 'Home' }} awayTeam={{ name: 'Away' }} onComplete={vi.fn()} />)
    
    expect(screen.getByText('Flipping...')).toBeDefined()
  })
})
