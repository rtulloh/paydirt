import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeamSelectPhase from './TeamSelectPhase'

vi.mock('../../store/gameStore', () => ({
  useGameStore: {
    getState: () => ({
      setGameId: vi.fn(),
      updateGameState: vi.fn(),
      setIsKickoff: vi.fn(),
      setCurrentSeason: vi.fn(),
    }),
  },
}))

const teams = [
  { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
  { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
]

describe('Team selection interception return preferences', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async (url) => ({
      ok: true,
      json: async () => url.endsWith('/api/game/new')
        ? { game_id: 'synthetic-game', game_state: {} }
        : { seasons: ['2026'], teams },
    })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function selectTeams() {
    render(<TeamSelectPhase onTeamSelected={vi.fn()} onBackToMenu={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: /Metro City Thunderhawks/ }))
    fireEvent.click(screen.getByRole('button', { name: /Harbor Bay Ironclads/ }))
  }

  async function submittedRequest() {
    fireEvent.click(screen.getByRole('button', { name: 'START GAME' }))
    await waitFor(() => {
      expect(fetch.mock.calls.some(([url]) => url.endsWith('/api/game/new'))).toBe(true)
    })
    const [, request] = fetch.mock.calls.find(([url]) => url.endsWith('/api/game/new'))
    return JSON.parse(request.body)
  }

  it('retains team and difficulty selection when starting a game', async () => {
    await selectTeams()
    fireEvent.click(screen.getByRole('button', { name: 'hard' }))
    expect(await submittedRequest()).toMatchObject({
      player_team: 'Thunderhawks',
      opponent_team: 'Ironclads',
      season: '2026',
      difficulty: 'hard',
      play_as_home: true,
    })
  })

  it('does not expose a pre-game end-zone choice and always asks in play', async () => {
    await selectTeams()
    expect(screen.queryByLabelText('Your team: end-zone interceptions')).not.toBeInTheDocument()
    expect(screen.queryByText('END-ZONE INTERCEPTIONS')).not.toBeInTheDocument()
    expect(await submittedRequest()).toMatchObject({
      player_end_zone_interception_policy: 'ask',
      opponent_end_zone_interception_policy: 'auto',
      player_attempt_end_zone_interception_returns: false,
    })
  })

  it.each([true, false])('uses the in-play decision regardless of play_as_home is %s', async (isHome) => {
    await selectTeams()
    if (!isHome) fireEvent.click(screen.getByRole('button', { name: 'AWAY' }))
    expect(await submittedRequest()).toMatchObject({
      play_as_home: isHome,
      player_end_zone_interception_policy: 'ask',
      opponent_end_zone_interception_policy: 'auto',
      player_attempt_end_zone_interception_returns: false,
    })
  })
})
