import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { useGameStore } from '../store/gameStore.js'

const home = { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' }
const away = { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' }
const responseState = (overrides = {}) => ({
  home_team: home, away_team: away,
  home_score: 7, away_score: 0, quarter: 3, time_remaining: 900,
  possession: 'away', ball_position: 35, field_position: 'MCT 35',
  down: 1, yards_to_go: 10, home_timeouts: 3, away_timeouts: 3,
  player_offense: false, human_is_home: true,
  game_over: false, pending_pat: false, is_kickoff: true, halftime_pending: true, ...overrides,
})

beforeEach(() => {
  useGameStore.getState().reset()
  useGameStore.setState({ gamePhase: 'playing', gameId: 'synthetic-game', homeTeam: home, awayTeam: away })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) }))
})

afterEach(() => {
  cleanup()
  useGameStore.getState().reset()
  vi.unstubAllGlobals()
})

describe('halftime comes from the engine, not from one API path', () => {
  it('shows halftime once when the engine reports it pending, then the kickoff', async () => {
    render(<App />)
    act(() => useGameStore.getState().updateGameState(responseState()))
    expect(await screen.findByTestId('halftime')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('continue-button'))
    expect(screen.queryByTestId('halftime')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'KICK OFF', exact: true })).toBeInTheDocument()
    // A later state refresh with the flag still set must not re-open the screen.
    act(() => useGameStore.getState().updateGameState(responseState({ time_remaining: 900 })))
    expect(screen.queryByTestId('halftime')).not.toBeInTheDocument()
  })

  it('waits for an outstanding try before showing halftime', async () => {
    render(<App />)
    act(() => useGameStore.getState().updateGameState(responseState({
      pending_pat: true, is_kickoff: false, possession: 'home', player_offense: true,
    })))
    expect(screen.queryByTestId('halftime')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'KICK XP (1 PT)' })).toBeInTheDocument()
    act(() => useGameStore.getState().updateGameState(responseState({ home_score: 7 })))
    expect(await screen.findByTestId('halftime')).toBeInTheDocument()
  })
})
