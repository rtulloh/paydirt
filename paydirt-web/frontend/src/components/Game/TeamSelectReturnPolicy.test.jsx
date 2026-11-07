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

  it('defaults both teams to automatic touchbacks and sends that preference', async () => {
    await selectTeams()
    expect(screen.getByLabelText('Your team: end-zone interceptions')).toHaveValue('touchback')
    expect(screen.getByLabelText('Opponent: end-zone interceptions')).toHaveValue('touchback')
    expect(await submittedRequest()).toMatchObject({
      player_attempt_end_zone_interception_returns: false,
      opponent_attempt_end_zone_interception_returns: false,
    })
  })

  it.each([true, false])('keeps team preferences independent when play_as_home is %s', async (isHome) => {
    await selectTeams()
    if (!isHome) fireEvent.click(screen.getByRole('button', { name: 'AWAY' }))
    fireEvent.change(screen.getByLabelText('Your team: end-zone interceptions'), {
      target: { value: 'return' },
    })
    expect(await submittedRequest()).toMatchObject({
      play_as_home: isHome,
      player_attempt_end_zone_interception_returns: true,
      opponent_attempt_end_zone_interception_returns: false,
    })
  })

  it('allows the opponent to attempt returns while the player elects touchbacks', async () => {
    await selectTeams()
    fireEvent.change(screen.getByLabelText('Opponent: end-zone interceptions'), {
      target: { value: 'return' },
    })
    expect(await submittedRequest()).toMatchObject({
      player_attempt_end_zone_interception_returns: false,
      opponent_attempt_end_zone_interception_returns: true,
    })
  })
})
