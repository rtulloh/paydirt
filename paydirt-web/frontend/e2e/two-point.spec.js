import { backendURL } from './ports.js'
import { test, expect } from './fixtures.js'

// Public charts and a synthetic saved pending touchdown establish the situation.
// The visible buttons call the real conversion and kickoff APIs without mocks.
for (const home of [true, false]) {
  for (const good of [true, false]) {
    test(`real engine two-point ${good ? 'success' : 'failure'}, human ${home ? 'home' : 'away'}`, async ({ page, request }) => {
      const created = await request.post(backendURL + '/api/game/new', {
        data: { player_team: 'Ironclads', opponent_team: 'Thunderhawks', season: '2026', play_as_home: home },
      })
      const initial = await created.json()
      const state = initial.game_state
      const save = {
        gameId: initial.game_id, homeTeam: state.home_team, awayTeam: state.away_team,
        humanTeamId: state.human_team_id, cpuTeamId: state.cpu_team_id,
        humanPlaysOffense: true, homeScore: home ? 6 : 0, awayScore: home ? 0 : 6,
        quarter: 2, timeRemaining: 20, possession: home ? 'home' : 'away',
        ballPosition: 98, down: 1, yardsToGo: 2, homeTimeouts: 1, awayTimeouts: 2,
        currentSeason: '2026', pendingPat: true, playLog: [],
      }
      await page.addInitScript(save => localStorage.setItem('paydirt_save', JSON.stringify(save)), save)
      await page.goto('/')
      const loading = page.waitForResponse(r => r.url().endsWith('/api/game/load-replay'))
      await page.getByRole('button', { name: /LOAD SAVED GAME|LOAD GAME|RESUME/i }).click()
      const loaded = await (await loading).json()
      const id = loaded.game_id
      const fixture = await request.post(backendURL + '/api/test/two-point-fixture', {
        data: { game_id: id, cell: good ? '2' : '0' },
      })
      expect(fixture.ok()).toBeTruthy()
      const before = await fixture.json()
      await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: 'GO FOR 2!', exact: true })).toBeVisible()
      const trying = page.waitForResponse(r => r.url().endsWith('/api/game/two-point'))
      await page.getByRole('button', { name: 'GO FOR 2!', exact: true }).click()
      const response = await trying
      expect(response.ok()).toBeTruthy()
      const result = await response.json()
      expect(result.result.conversion_success).toBe(good)
      expect(result.game_state.home_score).toBe(home ? good ? 8 : 6 : 0)
      expect(result.game_state.away_score).toBe(home ? 0 : good ? 8 : 6)
      expect(result.game_state).toMatchObject({
        quarter: 2, time_remaining: 20, pending_pat: false, can_go_for_two: false,
        possession: home ? 'home' : 'away', home_timeouts: 1, away_timeouts: 2,
      })
      await expect(page.getByText(good ? 'GOOD!' : 'NO GOOD!', { exact: true })).toBeVisible()
      const accounting = await (await request.get(backendURL + '/api/test/two-point-accounting/' + id)).json()
      expect(accounting.home).toEqual(before.accounting.home)
      expect(accounting.away).toEqual(before.accounting.away)
      expect(accounting.play_log_count).toBe(before.accounting.play_log_count)
      expect(accounting.call_history).toEqual(before.accounting.call_history)
      expect(accounting.scoring_plays.map(score => score.play_type)).toEqual(good ? ['TD', '2PT'] : ['TD'])
      expect(accounting.clock_trace.charged_seconds).toBe(0)
      await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeVisible()
      const kicking = page.waitForResponse(r => r.url().endsWith('/api/game/kickoff'))
      await page.getByRole('button', { name: 'KICK OFF', exact: true }).click()
      const kicked = await (await kicking).json()
      expect(kicked.game_state.possession).toBe(home ? 'away' : 'home')
      await request.delete(backendURL + '/api/game/' + id)
      await request.delete(backendURL + '/api/game/' + initial.game_id)
    })
  }
}

test('season prohibition clears an already eligible choice', async ({ page, request }) => {
  await page.goto('/')
  const created = await (await request.post(backendURL + '/api/game/new', {
    data: { player_team: 'Ironclads', season: '2026', play_as_home: true },
  })).json()
  // This case sets only a synthetic pending phase, then reads engine eligibility.
  const replay = { game_state: { ...created.game_state, pending_pat: true, possession: 'home', player_offense: true, ball_position: 98 }, season: '2026', play_history: [] }
  const loaded = await (await request.post(backendURL + '/api/game/load-replay', { data: { replay_data: replay } })).json()
  const configure = async eligible => (await request.post(backendURL + '/api/test/two-point-fixture', {
    data: { game_id: loaded.game_id, eligible },
  })).json()
  const show = async data => page.evaluate(async data => {
    const { useGameStore } = await import('/src/store/gameStore.js')
    useGameStore.getState().updateGameState(data.game_state)
    useGameStore.getState().setGamePhase('playing')
  }, data)
  await show(await configure(true))
  await expect(page.getByRole('button', { name: 'GO FOR 2!', exact: true })).toBeVisible()
  await show(await configure(false))
  await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'GO FOR 2!', exact: true })).toHaveCount(0)
  await request.delete(backendURL + '/api/game/' + loaded.game_id)
  await request.delete(backendURL + '/api/game/' + created.game_id)
})
