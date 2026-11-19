import { test, expect } from './fixtures.js'
import { backendURL } from './ports.js'

test('recorded result review confirms trusted finals, retains revisions and cancels safely', async ({ page, request }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'SAVED GAMES', exact: true })).toBeVisible()
  const setup = await page.evaluate(async () => {
    const api = await import('/src/runtime/campaigns.js')
    const { saveCurrentSession } = await import('/src/runtime/gameFetch.js')
    const campaign = await api.createCampaign({ name: 'Result review acceptance', rules_season: '2026',
      schedule: 'double_round_robin', participants: [
        { season: '2026', team_id: 'Ironclads' }, { season: '2026', team_id: 'Thunderhawks' },
      ] })
    const fixtureId = campaign.campaign.fixtures[0].id
    const started = await api.startCampaignGame(campaign, fixtureId, { human_is_home: true })
    const configured = await fetch('/api/test/checkpoint-fixture', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ game_id: started.game_id, kind: 'recorded-final' }) })
    if (!configured.ok) throw new Error(await configured.text())
    // Test-only engine setup bypasses gameFetch, so provide its authoritative
    // response explicitly instead of reusing the earlier new-game response.
    const saved = await saveCurrentSession(started.game_id, { responseBody: await configured.json() })
    return { campaignId: campaign.id, fixtureId, gameId: started.game_id, saveId: saved.record?.id || saved.id }
  })
  const inspect = () => page.evaluate(async ({ campaignId, fixtureId }) => {
    const api = await import('/src/runtime/campaigns.js')
    const record = await api.campaignRepository.get(campaignId)
    const fixture = record.campaign.fixtures.find(item => item.id === fixtureId)
    const view = await api.campaignCommand('view', { campaign: record.campaign })
    return { fixture, homeStats: view.statistics.find(row => row.participant_id === fixture.home_id) }
  }, setup)
  const corrections = [], previews = [], deleted = []
  page.on('request', req => {
    if (req.method() === 'POST' && req.url().endsWith('/api/campaign/correct')) corrections.push(req.postDataJSON())
    if (req.method() === 'DELETE' && /\/api\/game\//.test(req.url())) deleted.push(req.url().split('/').pop())
  })
  page.on('response', async response => {
    if (response.url().endsWith('/api/game/restore') && response.ok()) previews.push((await response.json()).game_id)
  })
  await page.getByRole('button', { name: 'SAVED GAMES', exact: true }).click()
  const review = page.getByRole('button', { name: 'Review recorded result', exact: true })
  await expect(review).toBeVisible()
  const before = await inspect()
  expect(before.fixture.result).toMatchObject({ revision: 1, home_score: 21, away_score: 14 })
  // A cancelled review may restore a temporary engine, but must not alter the ledger.
  page.once('dialog', async dialog => {
    expect(dialog.message()).toContain('revision 1')
    expect(dialog.message()).toContain('Team statistics come from the actual engine checkpoint')
    await dialog.dismiss()
  })
  await review.click()
  await expect.poll(() => deleted.length).toBe(1)
  expect(await inspect()).toEqual(before)
  expect(corrections).toEqual([])
  // Reviewing the identical checkpoint is idempotent at the result revision.
  page.once('dialog', dialog => dialog.accept())
  await review.click()
  await expect.poll(() => deleted.length).toBe(2)
  expect((await inspect()).fixture).toEqual(before.fixture)
  expect(corrections).toHaveLength(1)
  // Replace only the trusted checkpoint in test setup; the user supplies no score/stat fields.
  const configured = await request.post(`${backendURL}/api/test/checkpoint-fixture`, {
    data: { game_id: setup.gameId, kind: 'corrected-final' },
  })
  expect(configured.ok()).toBe(true)
  const checkpointResponse = await request.post(`${backendURL}/api/game/checkpoint/${setup.gameId}`)
  expect(checkpointResponse.ok()).toBe(true)
  const { checkpoint } = await checkpointResponse.json()
  await page.evaluate(async ({ checkpoint, gameId }) => {
    const { gameLibrary } = await import('/src/runtime/gameLibrary.js')
    const record = (await gameLibrary.list()).find(row => row.metadata.gameId === gameId)
    await gameLibrary.put({ ...record, checkpoint }, { expectedRevision: record.revision })
  }, { checkpoint, gameId: setup.gameId })
  await page.reload()
  await page.getByRole('button', { name: 'SAVED GAMES', exact: true }).click()
  page.once('dialog', async dialog => {
    expect(dialog.message()).toMatch(/21.*14/)
    expect(dialog.message()).toMatch(/24.*14/)
    await dialog.dismiss()
  })
  await review.click()
  await expect.poll(() => deleted.length).toBe(3)
  expect(await inspect()).toEqual(before)
  page.once('dialog', dialog => dialog.accept())
  await review.click()
  await expect.poll(() => deleted.length).toBe(4)
  const corrected = await inspect()
  expect(corrected.fixture.game_id).toBe(setup.gameId)
  expect(corrected.fixture.result).toMatchObject({ revision: 2, home_score: 24, away_score: 14 })
  expect(corrected.fixture.result_history).toHaveLength(1)
  expect(corrected.fixture.result_history[0]).toMatchObject({ revision: 1, home_score: 21 })
  expect(corrected.homeStats.offense.total_yards).toBe(420)
  expect(corrections).toHaveLength(2)
  for (const body of corrections) {
    expect(Object.keys(body).sort()).toEqual(['campaign', 'expected_result_revision', 'fixture_id', 'game_id'])
    expect(body.game_id).not.toBe(setup.gameId)
    expect(body.expected_result_revision).toBe(1)
  }
  expect(previews).toHaveLength(4)
  expect(deleted.sort()).toEqual([...previews].sort())
  for (const id of previews) expect((await request.get(`${backendURL}/api/game/state/${id}`)).status()).toBe(404)
  expect((await request.get(`${backendURL}/api/game/state/${setup.gameId}`)).ok()).toBe(true)
})
