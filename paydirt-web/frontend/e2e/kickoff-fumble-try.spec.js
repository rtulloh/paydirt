import { test, expect } from './fixtures.js'
import { backendURL } from './ports.js'

for (const home of [true, false]) {
 for (const stale of [false, true]) {
  test(`${stale ? 'old missing-flag' : 'new'} kickoff fumble touchdown offers and restores the human ${home ? 'home' : 'away'} try`, async ({ page, request }) => {
    const created = await request.post(`${backendURL}/api/game/new`, { data: {
      season: '2026', player_team: 'Ironclads', opponent_team: 'Thunderhawks', play_as_home: home,
    } })
    expect(created.ok(), await created.text()).toBe(true)
    const { game_id } = await created.json()
    const configured = await request.post(`${backendURL}/api/test/checkpoint-fixture`, {
      data: { game_id, kind: 'kickoff-fumble-td' },
    })
    expect(configured.ok(), await configured.text()).toBe(true)
    const initial = await configured.json()
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'SAVED GAMES', exact: true })).toBeVisible()
    // Initial synthetic situation comes from the isolated engine setup endpoint.
    // All scoring, saving, restoration and try actions below use real UI controls.
    await page.evaluate(async response => {
      const { useGameStore } = await import('/src/store/gameStore.js')
      useGameStore.getState().restoreSession(response)
    }, { game_id, ...initial })
    const kicking = page.waitForResponse(r => r.url().endsWith('/api/game/kickoff') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'KICK OFF', exact: true }).click()
    const kickedResponse = await kicking
    expect(kickedResponse.ok(), await kickedResponse.text()).toBe(true)
    const kicked = await kickedResponse.json()
    expect(kicked.result.touchdown).toBe(true)
    expect(kicked.game_state.human_is_home).toBe(home)
    expect(kicked.game_state[home ? 'home_score' : 'away_score']).toBe(6)
    expect(kicked.game_state.pending_pat).toBe(true)
    await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeEnabled()
    await expect(page.getByTestId('game-over')).toHaveCount(0)
    if (stale) {
      const staleResponse = await request.post(`${backendURL}/api/test/checkpoint-fixture`, {
        data: { game_id, kind: 'kickoff-stale-try' },
      })
      expect(staleResponse.ok(), await staleResponse.text()).toBe(true)
      expect((await staleResponse.json()).game_state.pending_pat).toBe(false)
    }
    await page.getByRole('button', { name: 'SAVE GAME', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: /^Game saved locally\.$/ })).toHaveText('Game saved locally.')
    const saved = await page.evaluate(async gameId => {
      const { sessionPersistence } = await import('/src/runtime/sessionPersistence.js')
      return sessionPersistence.getRecord(gameId)
    }, game_id)
    expect(saved?.checkpoint).toBeTruthy()
    expect((await request.delete(`${backendURL}/api/game/${game_id}`)).ok()).toBe(true)
    await page.reload()
    await page.getByRole('button', { name: 'SAVED GAMES', exact: true }).click()
    const restoring = page.waitForResponse(r => r.url().endsWith('/api/game/restore'))
    await page.getByRole('button', { name: `Resume ${saved.name}`, exact: true }).click()
    const restoredResponse = await restoring
    expect(restoredResponse.ok(), await restoredResponse.text()).toBe(true)
    const restored = await restoredResponse.json()
    expect(restored.game_id).not.toBe(game_id)
    expect(restored.game_state.pending_pat).toBe(true)
    expect(restored.game_state[home ? 'home_score' : 'away_score']).toBe(6)
    const restoredCheckpointResponse = await request.post(`${backendURL}/api/game/checkpoint/${restored.game_id}`)
    expect(restoredCheckpointResponse.ok(), await restoredCheckpointResponse.text()).toBe(true)
    const restoredCheckpoint = (await restoredCheckpointResponse.json()).checkpoint
    const savedState = JSON.parse(saved.checkpoint).engine.attrs.state.attrs
    const restoredState = JSON.parse(restoredCheckpoint).engine.attrs.state.attrs
    if (stale) {
      expect(restored.game_state).toMatchObject({ ball_position: 98, down: 1, yards_to_go: 2 })
      for (const key of ['ball_position', 'down', 'yards_to_go']) {
        delete savedState[key]
        delete restoredState[key]
      }
    }
    expect(restoredState).toEqual(savedState)
    const trying = page.waitForResponse(r => r.url().endsWith('/api/game/extra-point') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true }).click()
    const triedResponse = await trying
    expect(triedResponse.ok(), await triedResponse.text()).toBe(true)
    const tried = await triedResponse.json()
    expect(tried.game_state.pending_pat).toBe(false)
    expect([6, 7]).toContain(tried.game_state[home ? 'home_score' : 'away_score'])
    await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toHaveCount(0)
  })
}
}
