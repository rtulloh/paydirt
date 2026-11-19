import { test, expect } from './fixtures.js'

// Uses the real runtime and IndexedDB; only setup bypasses rendered controls.
// Recovery itself must go through Saved games after the engine session is gone.
test('season fixture survives reload and imports as an independent campaign', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'SAVED GAMES', exact: true })).toBeVisible()
  const original = await page.evaluate(async () => {
    const api = await import('/src/runtime/campaigns.js')
    const { gameFetch } = await import('/src/runtime/gameFetch.js')
    const { useGameStore } = await import('/src/store/gameStore.js')
    const record = await api.createCampaign({
      name: 'Recovery acceptance', rules_season: '2026', schedule: 'double_round_robin',
      participants: [{ season: '2026', team_id: 'Ironclads' }, { season: '2026', team_id: 'Thunderhawks' }],
    })
    const fixtureId = record.campaign.fixtures[0].id
    const started = await api.startCampaignGame(record, fixtureId, { human_is_home: false, difficulty: 'hard' })
    useGameStore.getState().restoreSession({ ...started, game_phase: 'coinToss' })
    const deleted = await gameFetch(`/api/game/${started.game_id}`, { method: 'DELETE' })
    if (!deleted.ok) throw new Error('Could not remove the original engine session')
    const absent = await gameFetch(`/api/game/state/${started.game_id}`)
    if (absent.status !== 404) throw new Error('Recovery must not reuse a live engine session')
    return { gameId: started.game_id, campaignId: record.id, fixtureId }
  })
  await expect(page.getByTestId('coin-toss')).toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: 'SAVED GAMES', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Saved games', exact: true })).toBeVisible()
  await page.getByRole('button', { name: /Resume Recovery acceptance/ }).click()
  await expect(page.getByTestId('coin-toss')).toBeVisible()
  const recovered = await page.evaluate(async () => {
    const { useGameStore } = await import('/src/store/gameStore.js')
    const api = await import('/src/runtime/campaigns.js')
    const records = await api.listCampaigns()
    const record = records.find(item => item.campaign.name === 'Recovery acceptance')
    const imported = await api.importCampaignFile(await api.exportCampaignFile(record))
    const { gameLibrary } = await import('/src/runtime/gameLibrary.js')
    const saves = await gameLibrary.list()
    const importedSave = saves.find(save => save.metadata?.campaignId === imported.id)
    const state = useGameStore.getState()
    return {
      gameId: state.gameId, phase: state.gamePhase, rules: state.rulesSeason,
      fixture: record.campaign.fixtures[0], originalId: record.id,
      importedId: imported.id, importedFixture: imported.campaign.fixtures[0],
      importedSave: importedSave && { id: importedSave.id, metadata: importedSave.metadata },
    }
  })
  expect(recovered.gameId).not.toBe(original.gameId)
  expect(recovered).toMatchObject({ phase: 'coinToss', rules: '2026', originalId: original.campaignId })
  expect(recovered.fixture).toMatchObject({ id: original.fixtureId, game_id: recovered.gameId, status: 'in_progress' })
  expect(recovered.importedId).not.toBe(original.campaignId)
  expect(recovered.importedFixture.id).not.toBe(original.fixtureId)
  expect(recovered.importedFixture.game_id).not.toBe(recovered.gameId)
  expect(recovered.importedSave.metadata).toMatchObject({
    campaignId: recovered.importedId, fixtureId: recovered.importedFixture.id,
    gameId: recovered.importedFixture.game_id, phase: 'coinToss',
  })
})
