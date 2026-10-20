import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import PenaltyDecisionPanel from '../components/Game/PenaltyDecisionPanel'
import { useGameStore } from '../store/gameStore.js'

const home = { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' }
const away = { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' }

// Engine-shaped kickoff return-penalty choice: the receiving team (MCT) fouled,
// so the kicking team (HBI, the human here) chooses. The receiver is "offense".
const kickoffChoice = {
  offended_team: 'defense',
  offsetting: false,
  kick_phase: 'return',
  play_result_preview: 'Return to MCT 35',
  reroll_log: [],
  penalty_options: [{
    penalty_type: 'OFF', raw_result: 'OFF 15', yards: 15,
    description: 'OFF 15 on the return (receiving team foul)',
    auto_first_down: false, is_pass_interference: false,
    result_preview: '1st and 10 at MCT 20',
  }],
}
const pendingKickoffResult = {
  result: 'off_penalty', yards: 0, description: 'PENALTY on kickoff return: OFF 15 (receiving team foul).',
  turnover: false, scoring: false, touchdown: false, new_ball_position: 35, new_down: 1, new_yards_to_go: 10,
  new_score_home: 0, new_score_away: 0, possession_changed: false, game_over: false,
  pending_penalty_decision: true, penalty_choice: kickoffChoice, play_type: 'kickoff',
}
const state = (overrides = {}) => ({
  home_team: home, away_team: away, home_score: 0, away_score: 0, quarter: 1, time_remaining: 900,
  possession: 'home', ball_position: 35, field_position: 'HBI 35', down: 1, yards_to_go: 10,
  home_timeouts: 3, away_timeouts: 3, player_offense: true, human_is_home: true,
  game_over: false, pending_pat: false, is_kickoff: true, halftime_pending: false, ...overrides,
})

beforeEach(() => {
  useGameStore.getState().reset()
  useGameStore.setState({ gamePhase: 'playing', gameId: 'synthetic-game', homeTeam: home, awayTeam: away, humanIsHome: true })
})

afterEach(() => {
  cleanup()
  useGameStore.getState().reset()
  vi.unstubAllGlobals()
})

describe('kickoff return-penalty choice (RULE-013)', () => {
  it('panel names the kicking and receiving sides and shows the engine previews', () => {
    render(<PenaltyDecisionPanel penaltyData={pendingKickoffResult} onDecision={vi.fn()} cpuIsOnDefense={false} />)
    expect(screen.getByText(/RECEIVING TEAM committed penalty/i)).toBeInTheDocument()
    expect(screen.getByText(/Your choice \(Kicking team\)/i)).toBeInTheDocument()
    const accept = screen.getByRole('button', { name: /\[2\]/ })
    expect(accept).toHaveTextContent('1st and 10 at MCT 20')
    expect(accept).toBeEnabled()
    const decline = screen.getByRole('button', { name: /\[1\]/ })
    expect(decline).toHaveTextContent('Return to MCT 35')
    expect(decline).toBeEnabled()
  })

  it('hides the KICK OFF button while the human kicker decides, then applies the decision', async () => {
    const fetchMock = vi.fn(async (url) => {
      if (String(url).endsWith('/api/game/kickoff')) {
        return { ok: true, json: async () => ({
          player_play: 'KICKOFF', cpu_play: 'KICKOFF', dice_roll_offense: 24, dice_roll_defense: 31,
          dice_details: { offense: { black: 2, white1: 4, white2: 0, total: 24 }, defense: { red: 3, green: 1, total: 31 } },
          result: pendingKickoffResult, game_state: state({ is_kickoff: false }),
        }) }
      }
      if (String(url).endsWith('/api/game/penalty-decision')) {
        return { ok: true, json: async () => ({
          player_play: 'PENALTY', cpu_play: 'CPU', dice_roll_offense: 0, dice_roll_defense: 0,
          result: { ...pendingKickoffResult, pending_penalty_decision: false, penalty_choice: null,
            description: 'Kickoff 60 yards. OFF 15 on the return accepted, ball at MCT 20.', yards: 20, new_ball_position: 20 },
          game_state: state({ is_kickoff: false, possession: 'away', player_offense: false, ball_position: 20, field_position: 'MCT 20' }),
        }) }
      }
      return { ok: true, json: async () => ({ status: 'ok' }) }
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    act(() => useGameStore.getState().updateGameState(state()))
    fireEvent.click(screen.getByRole('button', { name: 'KICK OFF', exact: true }))
    expect(await screen.findByText('PENALTY ON THE PLAY!', { exact: true }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'KICK OFF', exact: true })).not.toBeInTheDocument()
    const accept = screen.getByRole('button', { name: /\[2\]/ })
    expect(accept).toBeEnabled()
    fireEvent.click(accept)
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/api/game/penalty-decision'))).toBe(true))
    const decisionCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/api/game/penalty-decision'))
    expect(JSON.parse(decisionCall[1].body)).toMatchObject({ accept_penalty: true, penalty_index: 0 })
    await waitFor(() => expect(useGameStore.getState().ballPosition).toBe(20))
    expect(useGameStore.getState().isKickoff).toBe(false)
    expect(screen.queryByText('PENALTY ON THE PLAY!', { exact: true })).not.toBeInTheDocument()
  })
})
