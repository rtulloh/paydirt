import { test, expect } from '../e2e/browser-fixture.js'

// These are browser integration checks against the published bundle, not unit fixtures.
const counts = { '1977': 28, '1983': 28, '2024': 32, '2026': 2 }

test('bundled inventory initializes every public team and renders its loaded charts', async ({ page, context }, testInfo) => {
  const apiRequests = []
  const errors = []
  await context.route('**/api/**', route => {
    apiRequests.push(route.request().url())
    return route.abort()
  })
  page.on('pageerror', error => errors.push(String(error)))
  await page.addInitScript(() => {
    const NativeWorker = window.Worker
    window.Worker = class extends NativeWorker {
      constructor(...args) { super(...args); window.__inventoryWorker = this }
    }
    window.__inventoryRequestId = 0
    window.__inventoryRequest = request => new Promise((resolve, reject) => {
      const id = --window.__inventoryRequestId
      const worker = window.__inventoryWorker
      const timer = setTimeout(() => {
        worker.removeEventListener('message', onReply)
        reject(new Error('Inventory worker request timed out: ' + request.path))
      }, 60_000)
      function onReply({ data }) {
        if (data.id !== id) return
        clearTimeout(timer)
        worker.removeEventListener('message', onReply)
        if (data.error) reject(new Error(data.error))
        else resolve(data.result)
      }
      worker.addEventListener('message', onReply)
      worker.postMessage({ id, request })
    })
  })
  await page.goto('./')
  await expect(page.getByRole('button', { name: 'NEW GAME', exact: true })).toBeVisible({ timeout: 120_000 })
  const manifestResponse = await page.request.get(new URL('browser/manifest.json', page.url()).href)
  expect(manifestResponse.ok()).toBe(true)
  const manifest = await manifestResponse.json()
  expect(manifest.scope).toBe('public-released-seasons')
  expect(Object.keys(manifest.seasons).sort()).toEqual(Object.keys(counts).sort())

  const dispatch = async (method, path, body) => {
    const response = await page.evaluate(request => window.__inventoryRequest(request), { method, path, ...(body ? { body } : {}) })
    expect(response.status, method + ' ' + path + ': ' + JSON.stringify(response.body)).toBe(200)
    return response.body
  }
  expect((await dispatch('GET', '/api/seasons')).seasons).toEqual(['2026', '2024', '1983', '1977'])
  const receipt = []
  for (const [year, count] of Object.entries(counts)) {
    const teams = (await dispatch('GET', '/api/teams/' + year)).teams
    expect(teams).toHaveLength(count)
    expect(teams.map(team => team.id).sort()).toEqual([...manifest.seasons[year]].sort())
    expect(new Set(teams.map(team => team.id)).size).toBe(count)
    const rules = await dispatch('GET', '/api/season-rules?season=' + year)
    const modern = Number(year) >= 1994
    expect(rules).toMatchObject({ season: Number(year), two_point_conversion: modern,
      overtime: { enabled: true, format: modern ? 'modified_sudden_death' : 'sudden_death',
        period_length_minutes: modern ? 10 : 15, max_periods_regular: 1, can_end_in_tie_regular: true } })
    // Pair every team once: all engines initialize normally; no coin toss or snap is injected.
    for (let index = 0; index < teams.length; index += 2) {
      const pair = teams.slice(index, index + 2)
      const game = await dispatch('POST', '/api/game/new', {
        season: year, player_team: pair[0].id, opponent_team: pair[1].id,
        play_as_home: true, difficulty: 'hard',
      })
      expect(game.game_state).toMatchObject({ quarter: 1, time_remaining: 900, home_score: 0, away_score: 0 })
      const before = await dispatch('GET', '/api/game/state/' + game.game_id)
      for (const [side, team] of [['home', pair[0]], ['away', pair[1]]]) {
        const book = await dispatch('GET', '/api/game/charts/' + game.game_id + '?side=' + side)
        expect(book.season).toBe(year)
        expect(book.team.id).toBe(team.id)
        for (const table of ['offense', 'defense', 'special_plays', 'special_teams']) {
          expect(book[table].columns.length).toBeGreaterThan(0)
          expect(book[table].rows.length).toBeGreaterThan(0)
          expect(book[table].rows.every(row => row.cells.length === book[table].columns.length)).toBe(true)
        }
        receipt.push({ year, team: team.id, side, game_id: game.game_id })
      }
      expect(await dispatch('GET', '/api/game/state/' + game.game_id)).toEqual(before)
    }
  }
  expect(receipt).toHaveLength(90)
  expect(apiRequests).toEqual([])
  expect(errors).toEqual([])
  await testInfo.attach('complete-public-team-inventory', { body: JSON.stringify({ archive: manifest.files[0].sha256, teams: receipt }), contentType: 'application/json' })
})
