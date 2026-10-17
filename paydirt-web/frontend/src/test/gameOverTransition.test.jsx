import { act, cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { useGameStore } from '../store/gameStore.js'

const home = { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' }
const away = { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' }
const responseState = (overrides = {}) => ({
  home_team: home, away_team: away,
  home_score: 14, away_score: 7, quarter: 4, time_remaining: 0,
  possession: 'home', ball_position: 40, field_position: 'HBI 40',
  down: 2, yards_to_go: 8, home_timeouts: 2, away_timeouts: 1,
  player_offense: true, human_is_home: true,
  game_over: true, pending_pat: false, is_kickoff: false, ...overrides,
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

describe('authoritative final state reaches GameOver from any API path', () => {
  it.each([
    [14, 7, 4], [7, 14, 4], [14, 14, 5],
  ])('shows final %i–%i in period %i after an update', async (homeScore, awayScore, quarter) => {
    render(<App />)
    act(() => useGameStore.getState().updateGameState(responseState({
      home_score: homeScore, away_score: awayScore, quarter,
    })))
    const final = await screen.findByTestId('game-over')
    expect(within(final).getByTestId('home-score')).toHaveTextContent(String(homeScore))
    expect(within(final).getByTestId('away-score')).toHaveTextContent(String(awayScore))
    expect(screen.queryByTestId('offense-plays')).not.toBeInTheDocument()
  })

  it('also handles an already-final state when playing mounts', async () => {
    useGameStore.getState().updateGameState(responseState())
    render(<App />)
    expect(await screen.findByTestId('game-over')).toBeInTheDocument()
  })

  it('does not show final before the engine ends the game', () => {
    useGameStore.getState().updateGameState(responseState({ game_over: false, time_remaining: 1 }))
    render(<App />)
    expect(screen.queryByTestId('game-over')).not.toBeInTheDocument()
    expect(screen.getByTestId('offense-plays')).toBeInTheDocument()
  })

  it('waits for the pending final-play PAT before showing final', async () => {
    useGameStore.getState().updateGameState(responseState({ pending_pat: true }))
    render(<App />)
    expect(screen.queryByTestId('game-over')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'KICK XP (1 PT)' })).toBeInTheDocument()
    act(() => useGameStore.getState().updateGameState(responseState({ home_score: 15 })))
    expect(await screen.findByTestId('game-over')).toBeInTheDocument()
  })
})
