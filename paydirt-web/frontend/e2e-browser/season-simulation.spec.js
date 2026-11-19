import { test, expect } from '../e2e/browser-fixture.js'

async function storedSeason(page, name) {
  return page.evaluate(seasonName => new Promise((resolve, reject) => {
    const opened = indexedDB.open('paydirt-library', 1)
    opened.onerror = () => reject(opened.error)
    opened.onsuccess = () => {
      const db = opened.result
      const request = db.transaction('campaigns', 'readonly').objectStore('campaigns').getAll()
      request.onerror = () => { db.close(); reject(request.error) }
      request.onsuccess = () => {
        db.close()
        resolve(request.result.find(record => record.campaign.name === seasonName) || null)
      }
    }
  }), name)
}

test('static season simulates two fixtures without an HTTP backend and keeps both finals after reload', async ({ page, context }, testInfo) => {
  const errors = []
  const apiRequests = []
  await context.route('**/api/**', route => { apiRequests.push(route.request().url()); return route.abort() })
  page.on('pageerror', error => errors.push(String(error)))
  await page.addInitScript(() => {
    window.__seasonObserver = { failures: [], requests: [], view: null, simulations: 0 }
    const NativeWorker = window.Worker
    window.Worker = class extends NativeWorker {
      constructor(...args) {
        super(...args)
        this.pendingPaths = new Map()
        this.addEventListener('message', ({ data }) => {
          const path = this.pendingPaths.get(data.id)
          this.pendingPaths.delete(data.id)
          if (data.error || data.result?.status >= 400) window.__seasonObserver.failures.push({ path, error: data.error, result: data.result })
          if (path === '/api/campaign/simulate' && data.result?.status === 200) window.__seasonObserver.simulations++
          if (path === '/api/campaign/view' && data.result?.status === 200) window.__seasonObserver.view = data.result.body
        })
      }
      postMessage(message, ...args) {
        this.pendingPaths.set(message.id, message.request?.path)
        window.__seasonObserver.requests.push(message.request?.path)
        return super.postMessage(message, ...args)
      }
    }
  })
  const name = 'Wasm two-fixture season'
  await page.goto('./')
  await expect(page.getByRole('button', { name: 'SEASONS', exact: true })).toBeVisible({ timeout: 120_000 })
  await page.getByRole('button', { name: 'SEASONS', exact: true }).click()
  await page.getByRole('button', { name: '+ New season', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Create season', exact: true })
  await dialog.getByLabel('Season name', { exact: true }).fill(name)
  await dialog.getByLabel(/^Chart year/).selectOption('2026')
  await expect(dialog.getByLabel(/^Team/).locator('option')).toHaveCount(2)
  await dialog.getByLabel('Conference', { exact: true }).fill('Sample conference')
  await dialog.getByLabel('Division', { exact: true }).fill('Sample division')
  for (const team of ['Ironclads', 'Thunderhawks']) {
    await dialog.getByLabel(/^Team/).selectOption(team)
    await dialog.getByRole('button', { name: '+ Add team edition', exact: true }).click()
  }
  await expect(dialog.getByLabel(/^Rules for every game/)).toHaveValue('2026')
  await dialog.getByRole('button', { name: 'Create season', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Play fixture', exact: true })).toHaveCount(2)
  await page.getByRole('tab', { name: 'Schedule', exact: true }).click()
  await page.getByRole('button', { name: 'Simulate unplayed games', exact: true }).click()
  await expect(page.getByText('2 of 2 games completed', { exact: false })).toBeVisible({ timeout: 180_000 })
  await expect(page.getByText(/A game action is already in progress/)).toHaveCount(0)
  const before = await storedSeason(page, name)
  expect(before.campaign.fixtures).toHaveLength(2)
  expect(before.campaign.fixtures.every(fixture => fixture.status === 'completed' && fixture.result.source === 'simulated')).toBe(true)
  expect(await page.evaluate(() => window.__seasonObserver.simulations)).toBe(2)
  expect(await page.evaluate(() => window.__seasonObserver.failures)).toEqual([])
  await page.reload()
  await expect(page.getByRole('button', { name: 'SEASONS', exact: true })).toBeVisible({ timeout: 120_000 })
  await page.getByRole('button', { name: 'SEASONS', exact: true }).click()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__seasonObserver.view?.standings?.reduce((sum, row) => sum + row.played, 0))).toBe(4)
  const view = await page.evaluate(() => window.__seasonObserver.view)
  expect(view.statistics).toHaveLength(2)
  for (const row of view.standings) {
    expect(row.played).toBe(2)
    const displayed = page.getByRole('row').filter({ hasText: `2026 ${row.name}` })
    await expect(displayed.getByRole('cell').nth(1)).toHaveText(String(row.wins))
    await expect(displayed.getByRole('cell').nth(2)).toHaveText(String(row.losses))
    await expect(displayed.getByRole('cell').nth(4)).toHaveText(String(row.points_for))
  }
  await page.getByRole('tab', { name: 'Team statistics', exact: true }).click()
  for (const row of view.statistics) {
    expect(row.offense_games.total_yards).toBe(2)
    const displayed = page.getByRole('row').filter({ hasText: `2026 ${row.name}` })
    await expect(displayed.getByRole('cell').nth(1)).toHaveText('2')
    await expect(displayed.getByRole('cell').nth(3).locator('span')).toHaveText(String(row.offense.total_yards))
  }
  expect((await storedSeason(page, name)).campaign).toEqual(before.campaign)
  expect(await page.evaluate(() => window.__seasonObserver.failures)).toEqual([])
  expect(errors).toEqual([])
  expect(apiRequests).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('two-fixture-season-reloaded.png'), fullPage: true })
})
