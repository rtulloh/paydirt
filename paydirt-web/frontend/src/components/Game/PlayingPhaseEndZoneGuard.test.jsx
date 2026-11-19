// These UI tests exercise engine responses; persistence/leases have dedicated integration suites.
vi.mock('../../runtime/gameFetch', async () => { const actual = await vi.importActual('../../runtime/gameFetch'); return { ...actual, gameFetch: actual.rawGameFetch }; });
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PlayingPhase from './PlayingPhase'
import { useGameStore } from '../../store/gameStore'

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }))
vi.mock('../Field/FootballField', () => ({ default: () => null }))
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }))

const initialState = useGameStore.getState()

const pendingEndZone = {
  pending_end_zone_interception_return_decision: true,
  int_catch_depth: 4,
  int_catch_field_position: 'own 4-yard line',
  interception_return_situation: 'AWAY caught it at the own 4-yard line | HOME 0 - AWAY 0 | Q1 14:00',
  int_return_team: 'AWAY',
  description: 'INTERCEPTION in the end zone at the own 4-yard line - choose touchback or attempt return',
  turnover: false,
}

// FLOW-026: while the engine waits for the end-zone return choice, nothing may
// start another play or coaching query. Real timers keep the engine-driven
// delays faithful; this file drives one short execute.
describe('Pending end-zone choice blocks a new play', () => {
  let fetchMock
  let executeCalls
  let decisionCalls

  beforeEach(() => {
    executeCalls = 0
    decisionCalls = 0
    useGameStore.setState({
      ...initialState, gameId: 'end-zone-guard', gamePhase: 'playing',
      playerOffense: false, humanIsHome: true, down: 4, ballPosition: 39,
      yardsToGo: 7, quarter: 1, timeRemaining: 416,
      homeTeam: { short_name: 'HOME' }, awayTeam: { short_name: 'AWAY' }, playLog: [],
    }, true)
    fetchMock = vi.fn(async url => {
      const target = String(url)
      if (target.includes('/cpu-4th-down-decision/')) {
        decisionCalls += 1
        // The CPU goes for it, so the human defence click executes a play that
        // then pauses on the end-zone return choice while still on fourth down.
        return { ok: true, json: async () => ({ decision: 'go_for_it' }) }
      }
      if (target.endsWith('/cpu-play')) {
        return { ok: true, json: async () => ({ cpu_play: '1' }) }
      }
      if (target.endsWith('/execute')) {
        executeCalls += 1
        return { ok: true, json: async () => ({ result: pendingEndZone, dice_details: {} }) }
      }
      throw new Error('Unexpected request: ' + target)
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    useGameStore.setState(initialState, true)
  })

  it('shows the choice, asks for no new coaching decision and ignores further play clicks', async () => {
    render(<PlayingPhase />)
    await waitFor(() => expect(decisionCalls).toBe(1))
    fireEvent.click(screen.getByTestId('defense-play-a'))
    expect(await screen.findByText('END-ZONE INTERCEPTION!', {}, { timeout: 6000 })).toBeInTheDocument()
    expect(executeCalls).toBe(1)
    // Exactly one request was made, before the choice appeared.
    expect(decisionCalls).toBe(1)

    fireEvent.click(screen.getByTestId('defense-play-a'))
    await new Promise(resolve => setTimeout(resolve, 300))
    expect(executeCalls).toBe(1)
    expect(decisionCalls).toBe(1)
    expect(screen.queryByRole('button', { name: 'EXECUTE PLAY' })).not.toBeInTheDocument()
  })

  it('withholds a restored kickoff control while the choice is open', async () => {
    // A pending decision takes precedence over a retained kickoff display flag.
    // Normal snaps during an owed kickoff are independently rejected by the UI.
    useGameStore.getState().restoreSession({
      game_id: 'end-zone-guard',
      game_state: { home_team: {}, away_team: {}, is_kickoff: true, down: 2 },
      pending_result: pendingEndZone,
    })
    render(<PlayingPhase />)
    expect(screen.getByText('END-ZONE INTERCEPTION!')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /KICK OFF/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Call timeout/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /SAVE GAME/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /SAVE REPLAY/i })).toBeDisabled()
    expect(executeCalls).toBe(0)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('withdraws visible try controls while the choice is open', async () => {
    useGameStore.setState({
      playerOffense: true, pendingPat: true, canGoForTwo: true, down: 2,
    })
    render(<PlayingPhase />)
    expect(await screen.findByRole('button', { name: /KICK XP/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /GO FOR 2/i })).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('offense-play-1'))
    await screen.findByText('END-ZONE INTERCEPTION!', {}, { timeout: 6000 })

    expect(screen.queryByRole('button', { name: /KICK XP/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /GO FOR 2/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Call timeout/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /SAVE GAME/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /SAVE REPLAY/i })).toBeDisabled()
    expect(executeCalls).toBe(1)
  })

})
