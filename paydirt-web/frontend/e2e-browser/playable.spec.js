import { test, expect } from '../e2e/browser-fixture.js'
import { createEngineObserver } from './engine-observer.mjs'
import { findEnabledPenaltyChoice, isActionable } from './penalty-choice.js'

// Re-evaluate procedures after every worker/React transition. A response can
// replace a normal-play control while its durable checkpoint is still saving.
async function findEnabledProcedure(page) {
  const penalty = await findEnabledPenaltyChoice(page)
  if (penalty) return penalty
  const controls = [
    page.getByRole('button', { name: 'KICK OFF', exact: true }),
    page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true }),
    page.getByRole('button', { name: /^\[1\]/ }),
    ...['TAKE TOUCHBACK', 'CONTINUE', 'NORMAL PUNT', 'EXECUTE PLAY'].map(name => page.getByRole('button', { name, exact: true })),
  ]
  for (const control of controls) {
    if (await isActionable(control)) return control
  }
  return null
}

test.afterEach(async ({ page }, testInfo) => {
  if (testInfo.status === testInfo.expectedStatus || page.isClosed()) return
  const evidence = await page.evaluate(() => ({ requests: window.__engineObserver.requests, replies: window.__engineObserver.replies, failures: window.__engineObserver.failures, count: window.__engineObserver.count }))
  await testInfo.attach('worker-failure-evidence', { body: JSON.stringify(evidence), contentType: 'application/json' })
})

// Observe genuine worker replies. All game-changing actions remain rendered UI clicks.
for (const year of ['2026', '1977', '1983', '2024']) {
test(`static ${year} build completes home and away games without an HTTP backend`, async ({ page, context }, testInfo) => {
  const errors = []
  const apiRequests = []
  await context.route('**/api/**', route => {
    apiRequests.push(route.request().url())
    return route.abort()
  })
  page.on('pageerror', error => errors.push(String(error)))
  await page.addInitScript(createEngineObserver)
  await page.addInitScript(() => {
    const NativeWorker = window.Worker
    window.Worker = class extends NativeWorker {
      constructor(...args) {
        super(...args)
        this.addEventListener('message', ({ data }) => {
          if (data.result) window.__engineObserver.reply(data.result)
        })
      }
      postMessage(...args) {
        window.__engineObserver.request(args[0])
        return super.postMessage(...args)
      }
    }
    Math.random = () => 0.75
    const timeout = window.setTimeout.bind(window)
    window.setTimeout = (fn, delay, ...args) => timeout(fn, delay >= 300 && delay <= 2000 ? 0 : delay, ...args)
  })
  const replyCount = () => page.evaluate(() => window.__engineObserver.count)
  const state = () => page.evaluate(() => window.__engineObserver.state)
  await page.goto('./')
  await expect(page.getByRole('button', { name: 'NEW GAME', exact: true })).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText('Browser edition · Public seasons: 1977, 1983, 2024 and 2026 sample teams. Saved games and seasons stay in this browser. Export backups to keep a portable copy. Offline engine loading is unavailable.', { exact: true })).toBeVisible()
  const manifestResponse = await page.request.get(new URL('browser/manifest.json', page.url()).href)
  expect(manifestResponse.ok()).toBe(true)
  const manifest = await manifestResponse.json()
  const expectedTeams = manifest.seasons[year]
  expect(expectedTeams.length).toBe(year === '2026' ? 2 : year === '2024' ? 32 : 28)
  const ids = []
  for (const home of [true, false]) {
    await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
    // Each team has its own chart year; select the player last to focus that catalog.
    await page.getByRole('combobox', { name: 'Opponent chart year', exact: true }).selectOption(year)
    await page.getByRole('combobox', { name: 'Your chart year', exact: true }).selectOption(year)
    await expect(page.getByRole('combobox', { name: 'Your chart year', exact: true })).toHaveValue(year)
    await expect(page.getByRole('combobox', { name: 'Opponent chart year', exact: true })).toHaveValue(year)
    await expect(page.getByRole('heading', { name: `TEAMS (${year})`, exact: true })).toBeVisible()
    let availableTeams
    await expect.poll(async () => {
      availableTeams = await page.evaluate(() => window.__engineObserver.teams)
      return availableTeams?.map(team => team.id).sort()
    }).toEqual([...expectedTeams].sort())
    for (const team of availableTeams.slice(0, 2)) {
      await page.getByRole('button').filter({ has: page.getByText(team.name, { exact: true }) }).click()
    }
    await page.getByRole('button', { name: home ? 'HOME' : 'AWAY', exact: true }).click()
    await page.getByRole('button', { name: 'hard', exact: true }).click()
    await page.getByRole('button', { name: 'START GAME', exact: true }).click()
    await expect(page.getByTestId('choose-heads')).toBeVisible()
    const created = await state()
    expect(created).toMatchObject({ home_score: 0, away_score: 0, quarter: 1, time_remaining: 900, human_is_home: home })
    const id = await page.evaluate(() => window.__engineObserver.gameId)
    expect(ids).not.toContain(id)
    ids.push(id)
    await page.getByTestId('choose-heads').click()
    await page.getByTestId(home ? 'choose-receive' : 'choose-kick').click()
    const quarters = new Set()
    let halftime = 0
    let patChoices = 0
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
      let button = await findEnabledPenaltyChoice(page)
      if (!button && await page.getByText('PENALTY ON THE PLAY!', { exact: true }).isVisible()) {
        await expect.poll(async () => {
          button = await findEnabledPenaltyChoice(page)
          return Boolean(button) || !await page.getByText('PENALTY ON THE PLAY!', { exact: true }).isVisible()
        }, { message: 'The pending penalty must offer an enabled choice or finish its CPU decision' }).toBe(true)
        if (!button) continue
      }
      // A worker response can arrive before its checkpoint and React commit.
      // Reacquire the procedure control while waiting rather than holding a
      // defense/offense locator that correctly becomes disabled by a new foul.
      let phaseChanged = false
      let selectedPlay = false
      await expect.poll(async () => {
        if (await page.getByTestId('halftime').isVisible() || await page.getByTestId('game-over').isVisible()) {
          phaseChanged = true
          return true
        }
        button = await findEnabledProcedure(page)
        selectedPlay = !button
        if (!button) {
          if (await page.getByTestId('offense-play-1').isVisible()) {
            const current = await state()
            const play = current.down === 4 ? (current.ball_position < 55 ? 'p' : 'f') : ['1', '2', '6', '7'][plays % 4]
            button = page.getByTestId('offense-play-' + play)
          } else {
            button = page.getByTestId('defense-play-' + ['a', 'b', 'c', 'd', 'e', 'f'][plays % 6])
          }
        }
        return isActionable(button)
      }, { message: 'An actionable control must exist at step ' + step }).toBe(true)
      if (phaseChanged) continue
      // The poll proved enabledness; click checks it again atomically. Do not
      // wait on a separate stale locator assertion if an automatic result closes.
      const selectedText = (await button.allTextContents()).join('').trim()
      if (!selectedText) {
        await expect.poll(async () => Boolean(await findEnabledProcedure(page))
          || await page.getByTestId('halftime').isVisible()
          || await page.getByTestId('game-over').isVisible(),
        { message: 'A disappeared control must expose its next phase' }).toBe(true)
        continue
      }
      if (selectedText === 'KICK XP (1 PT)') {
        const twoPoint = page.getByRole('button', { name: 'GO FOR 2!', exact: true })
        if (Number(year) >= 1994) await expect(twoPoint).toBeVisible()
        else await expect(twoPoint).toHaveCount(0)
        patChoices++
      }
      const count = await replyCount()
      const closesResult = selectedText === 'CONTINUE'
      try {
        await button.click(closesResult ? { timeout: 2000 } : {})
        if (selectedPlay) plays++
      } catch (error) {
        // A result may close through response-driven UI progress while click
        // waits for its animation. Only that vanished UI-only control may be
        // reevaluated; transport errors and a still-present button must fail.
        if (error.name !== 'TimeoutError' || !closesResult || await button.isVisible()) throw error
        await expect.poll(async () => {
          if (await replyCount() > count) return true
          if (await page.getByTestId('halftime').isVisible() || await page.getByTestId('game-over').isVisible()) return true
          for (const selector of ['[data-testid^="offense-play-"]', '[data-testid^="defense-play-"]']) {
            const controls = page.locator(selector)
            for (const control of await controls.all()) {
              if (await isActionable(control)) return true
            }
          }
          return Boolean(await findEnabledProcedure(page))
        }, { message: 'A vanished result must expose an advanced engine or actionable phase' }).toBe(true)
      }
      await expect.poll(async () => {
        if (await replyCount() > count) return true
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
    await testInfo.attach(`browser-game-${year}-${id}`, { body: JSON.stringify({ year, archive: manifest.files[0].sha256, id, home, final, plays, halftime, patChoices }), contentType: 'application/json' })
    await page.getByTestId('new-game-button').click()
    // NEW GAME on the final screen goes directly to team selection.
    if (!home) break
    await page.getByRole('button', { name: /BACK/i }).click()
  }
  expect(ids).toHaveLength(2)
  expect(apiRequests).toEqual([])
  expect(errors).toEqual([])
  const failures = await page.evaluate(() => window.__engineObserver.failures)
  expect(failures).toEqual([])
})
}
