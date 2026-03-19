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
})
