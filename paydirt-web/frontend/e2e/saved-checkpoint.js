import { expect } from './fixtures.js'
import { backendURL } from './ports.js'

// Seed only test storage; restoring and all subsequent actions use rendered UI.
export async function resumeFixture(page, request, { kind, home = true, name, legacySave }) {
  const created = await request.post(`${backendURL}/api/game/new`, { data: {
    season: '2026', player_team: 'Ironclads', opponent_team: 'Thunderhawks',
    play_as_home: home,
  } })
  expect(created.ok(), await created.text()).toBe(true)
  const initial = await created.json()
  const configured = await request.post(`${backendURL}/api/test/checkpoint-fixture`, {
    data: { game_id: initial.game_id, kind },
  })
  expect(configured.ok(), await configured.text()).toBe(true)
  const checkpointResponse = await request.post(`${backendURL}/api/game/checkpoint/${initial.game_id}`)
  expect(checkpointResponse.ok(), await checkpointResponse.text()).toBe(true)
  const { checkpoint } = await checkpointResponse.json()
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'SAVED GAMES', exact: true })).toBeVisible()
  await page.evaluate(async ({ id, checkpoint, name, legacySave }) => {
    localStorage.setItem('paydirt_save', JSON.stringify(legacySave))
    const { gameLibrary } = await import('/src/runtime/gameLibrary.js')
    await gameLibrary.put({ id, checkpoint, name, metadata: {
      gameId: id, phase: 'playing', gameOver: false,
    } }, { expectedRevision: 0 })
  }, { id: initial.game_id, checkpoint, name, legacySave })
  expect((await request.delete(`${backendURL}/api/game/${initial.game_id}`)).ok()).toBe(true)
  await page.reload()
  await page.getByRole('button', { name: 'SAVED GAMES', exact: true }).click()
  const restoring = page.waitForResponse(r => r.url().endsWith('/api/game/restore') && r.request().method() === 'POST')
  await page.getByRole('button', { name: `Resume ${name}`, exact: true }).click()
  const response = await restoring
  expect(response.ok(), await response.text()).toBe(true)
  const restored = await response.json()
  expect(restored.game_id).not.toBe(initial.game_id)
  expect(restored.game_state.human_is_home).toBe(home)
  await expect(page.getByTestId('scoreboard')).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('paydirt_save'))).toBe(JSON.stringify(legacySave))
  return { ...restored, saveId: initial.game_id }
}
