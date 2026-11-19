import { test, expect } from './fixtures.js'

// Synthetic standings isolate geometry from historical charts and game results.
const participants = []
for (const [conference, sizes] of [['NFC', [5, 3, 4]], ['AFC', [4, 5, 3]], ['Custom', [2]]]) {
  for (const [index, size] of sizes.entries()) {
    for (let team = 0; team < size; team++) participants.push({
      id: `${conference}-${index}-${team}`, season: '2026',
      name: `${conference} sample ${index}-${team}`, team_id: 'Ironclads',
      conference, division: ['Central', 'East', 'West'][index],
      wins: 0, losses: 0, ties: 0, points_for: 0, points_against: 0, win_pct: 0,
    })
  }
}
const campaign = { id: 'layout-fixture', name: 'Unequal divisions', rules_season: '2026',
  participants, fixtures: [], kind: 'custom', standings: participants,
  statistics: [], leaders: {}, ranking_policy: 'Synthetic layout fixture' }

async function headingBox(page, conference, division) {
  return page.getByRole('region', { name: `${conference} standings`, exact: true })
    .getByRole('heading', { name: division, exact: true }).boundingBox()
}

test('unequal conference divisions align on desktop and stack in conference order on phones', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.route('**/api/campaign/view', route => route.fulfill({ json: campaign }))
  await page.goto('/')
  await page.evaluate(async value => {
    const { createCampaignRepository } = await import('/src/runtime/campaigns.js')
    await createCampaignRepository().put(value, 0)
  }, campaign)
  await page.getByRole('button', { name: 'SEASONS', exact: true }).click()
  await expect(page.getByRole('heading', { name: campaign.name, exact: true })).toBeVisible()
  for (const division of ['Central', 'East', 'West']) {
    const nfc = await headingBox(page, 'NFC', division)
    const afc = await headingBox(page, 'AFC', division)
    expect(nfc.x).toBeLessThan(afc.x)
    expect(Math.abs(nfc.y - afc.y)).toBeLessThanOrEqual(1)
  }
  // A single-conference scope must retain all its differently sized divisions.
  await page.getByLabel('Standings scope').selectOption('conference:AFC')
  await expect(page.getByRole('region', { name: 'NFC standings', exact: true })).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'AFC standings', exact: true }).getByRole('table')).toHaveCount(3)
  await page.getByLabel('Standings scope').selectOption('all')
  await page.setViewportSize({ width: 390, height: 844 })
  const nfcWest = await headingBox(page, 'NFC', 'West')
  const afcCentral = await headingBox(page, 'AFC', 'Central')
  const afcWest = await headingBox(page, 'AFC', 'West')
  const custom = await headingBox(page, 'Custom', 'Central')
  expect(nfcWest.y).toBeLessThan(afcCentral.y)
  expect(afcWest.y).toBeLessThan(custom.y)
  expect(Math.abs(nfcWest.x - afcCentral.x)).toBeLessThanOrEqual(1)
})
