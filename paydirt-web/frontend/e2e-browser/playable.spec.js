import { test, expect } from '../e2e/browser-fixture.js'

// Observe genuine worker replies. All game-changing actions remain rendered UI clicks.
test('static GitHub build completes home and away games without an HTTP backend', async ({ page, context }, testInfo) => {
  const errors = []
  const apiRequests = []
  await context.route('**/api/**', route => {
    apiRequests.push(route.request().url())
    return route.abort()
  })
  page.on('pageerror', error => errors.push(String(error)))
  await page.addInitScript(() => {
    window.__engineReplies = []
    const NativeWorker = window.Worker
    window.Worker = class extends NativeWorker {
      constructor(...args) {
        super(...args)
        this.addEventListener('message', ({ data }) => {
          if (data.result) window.__engineReplies.push(data.result)
        })
      }
    }
    Math.random = () => 0.75
    const timeout = window.setTimeout.bind(window)
    window.setTimeout = (fn, delay, ...args) => timeout(fn, delay >= 300 && delay <= 2000 ? 0 : delay, ...args)
  })
  const replies = () => page.evaluate(() => window.__engineReplies)
  const state = () => page.evaluate(() => {
    for (const reply of [...window.__engineReplies].reverse()) {
      if (reply.body?.game_state) return reply.body.game_state
      if (reply.body?.quarter) return reply.body
    }
    return null
  })
  await page.goto('./')
  await expect(page.getByRole('button', { name: 'NEW GAME', exact: true })).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText(/temporary|session/i).first()).toBeVisible()
  const ids = []
  for (const home of [true, false]) {
    await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
    await expect(page.getByRole('button', { name: '2026', exact: true })).toBeVisible()
    await page.getByRole('button', { name: /Ironclads/ }).click()
    await page.getByRole('button', { name: /Thunderhawks/ }).click()
    await page.getByRole('button', { name: home ? 'HOME' : 'AWAY', exact: true }).click()
    await page.getByRole('button', { name: 'hard', exact: true }).click()
    await page.getByRole('button', { name: 'START GAME', exact: true }).click()
    await expect(page.getByTestId('choose-heads')).toBeVisible()
    const created = await state()
    expect(created).toMatchObject({ home_score: 0, away_score: 0, quarter: 1, time_remaining: 900, human_is_home: home })
    const allReplies = await replies()
    const id = [...allReplies].reverse().find(reply => reply.body?.game_id)?.body.game_id
    expect(ids).not.toContain(id)
    ids.push(id)
    await page.getByTestId('choose-heads').click()
    await page.getByTestId(home ? 'choose-receive' : 'choose-kick').click()
    const quarters = new Set()
    let halftime = 0
    let plays = 0
    let completed = false
    for (let step = 0; step < 500; step++) {
      const before = await state()
      quarters.add(before.quarter)
      if (await page.getByTestId('game-over').isVisible()) {
        expect(before.game_over).toBe(true)
        await expect(page.getByTestId('game-over').getByTestId('home-score')).toHaveText(String(before.home_score))
        await expect(page.getByTestId('game-over').getByTestId('away-score')).toHaveText(String(before.away_score))
        completed = true
        break
      }
      if (await page.getByTestId('halftime').isVisible()) {
        halftime++
        expect(before.quarter).toBe(3)
        expect(before.time_remaining).toBe(900)
        await page.getByTestId('continue-button').click()
        continue
      }
      let button
      for (const name of ['KICK OFF', 'KICK XP (1 PT)', 'TAKE TOUCHBACK', 'CONTINUE', 'NORMAL PUNT', 'EXECUTE PLAY']) {
        const candidate = page.getByRole('button', { name, exact: true })
        if (await candidate.isVisible()) { button = candidate; break }
      }
      if (!button) {
        const penalty = page.getByRole('button', { name: /^\[1\]/ })
        if (await penalty.isVisible()) button = penalty
      }
      if (!button) {
        const offense = page.getByTestId('offense-play-1')
        if (await offense.isVisible()) {
          const play = before.down === 4 ? (before.ball_position < 55 ? 'p' : 'f') : ['1', '2', '6', '7'][plays % 4]
          button = page.getByTestId('offense-play-' + play)
        } else {
          button = page.getByTestId('defense-play-' + ['a', 'b', 'c', 'd', 'e', 'f'][plays % 6])
        }
        plays++
      }
      await expect(button, 'An actionable control must exist at step ' + step).toBeEnabled()
      const count = (await replies()).length
      const closesResult = (await button.innerText()).trim() === 'CONTINUE'
      await button.click()
      await expect.poll(async () => {
        if ((await replies()).length > count) return true
        // Closing a result panel changes only the UI; it sends no engine operation.
        if (closesResult && !await button.isVisible()) return true
        if (await page.getByTestId('game-over').isVisible()) return true
        return await page.getByRole('button', { name: 'EXECUTE PLAY', exact: true }).isVisible()
          || await page.getByRole('button', { name: 'NORMAL PUNT', exact: true }).isVisible()
      }).toBe(true)
      // Let React finish response-driven phase changes without changing the engine clock.
      await page.waitForTimeout(20)
    }
    expect(completed, 'A full game must finish within the action limit').toBe(true)
    expect([...quarters]).toEqual(expect.arrayContaining([1, 2, 3, 4]))
    expect(halftime).toBe(1)
    expect(plays).toBeGreaterThan(80)
    const final = await state()
    await testInfo.attach('browser-game-' + id, { body: JSON.stringify({ id, home, final, plays, halftime }), contentType: 'application/json' })
    await page.getByTestId('new-game-button').click()
    // NEW GAME on the final screen goes directly to team selection.
    if (!home) break
    await page.getByRole('button', { name: /BACK/i }).click()
  }
  expect(ids).toHaveLength(2)
  expect(apiRequests).toEqual([])
  expect(errors).toEqual([])
  const failures = (await replies()).filter(reply => reply.status >= 400)
  expect(failures).toEqual([])
})
