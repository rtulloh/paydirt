import { backendURL } from './ports.js'
import { test, expect } from './fixtures.js'
import { resumeFixture } from './saved-checkpoint.js'
// Public charts and a synthetic saved pending touchdown establish the situation.
// The visible buttons call the real conversion and kickoff APIs without mocks.
for (const home of [true, false]) {
  for (const good of [true, false]) {
    test(`real engine two-point ${good ? 'success' : 'failure'}, human ${home ? 'home' : 'away'}`, async ({ page, request }) => {
      const legacySave = { gameId: 'obsolete-two-point', pendingPat: true }
      const loaded = await resumeFixture(page, request, {
        kind: 'pending-try', home, name: `Two-point ${home} ${good}`, legacySave,
      })
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
      expect(await page.evaluate(() => localStorage.getItem('paydirt_save'))).toBe(JSON.stringify(legacySave))
      await request.delete(backendURL + '/api/game/' + id)
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
