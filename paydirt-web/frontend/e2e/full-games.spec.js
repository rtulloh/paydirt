import { test, expect } from '@playwright/test'

// Read-only inspection: actions below are exclusively clicks in the rendered UI.
const snapshot = page => page.evaluate(async () => {
  const { useGameStore } = await import('/src/store/gameStore.js')
  const s = useGameStore.getState()
  return {
    gameId: s.gameId, gamePhase: s.gamePhase, gameOver: s.gameOver,
    quarter: s.quarter, timeRemaining: s.timeRemaining,
    homeScore: s.homeScore, awayScore: s.awayScore,
    playerOffense: s.playerOffense, down: s.down, ballPosition: s.ballPosition,
    isKickoff: s.isKickoff, pendingPat: s.pendingPat,
    pendingCpuFourthDown: s.pendingCpuFourthDown,
    selectedModifier: s.selectedModifier, noHuddleMode: s.noHuddleMode,
    log: s.playLog,
  }
})

async function startGame(page, { home, seed, player, receives }) {
  await page.setExtraHTTPHeaders({ 'X-Paydirt-Test-Seed': String(seed) })
  await expect(page.getByRole('heading', { name: 'SELECT TEAMS' })).toBeVisible()
  await expect(page.getByRole('button', { name: '2026', exact: true })).toBeVisible()
  const opponent = player === 'Ironclads' ? 'Thunderhawks' : 'Ironclads'
  await page.getByRole('button', { name: new RegExp(player) }).click()
  await page.getByRole('button', { name: new RegExp(opponent) }).click()
  await page.getByRole('button', { name: home ? 'HOME' : 'AWAY', exact: true }).click()
  await page.getByRole('button', { name: 'hard', exact: true }).click()
  const created = page.waitForResponse(r => r.url().endsWith('/api/game/new') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'START GAME', exact: true }).click()
  const response = await created
  expect(response.ok()).toBeTruthy()
  const data = await response.json()
  expect(data.game_state.home_score).toBe(0)
  expect(data.game_state.away_score).toBe(0)
  expect(data.game_state.quarter).toBe(1)
  expect(data.game_state.time_remaining).toBe(900)
  expect(data.game_state.human_is_home).toBe(home)
  const fresh = await snapshot(page)
  expect(fresh).toMatchObject({
    gameId: data.game_id, homeScore: 0, awayScore: 0,
    quarter: 1, timeRemaining: 900, gameOver: false, pendingPat: false,
    pendingCpuFourthDown: null, selectedModifier: null, noHuddleMode: false, log: [],
  })
  await page.getByTestId('choose-heads').click()
  await expect(page.getByTestId('coin-toss')).toContainText(/You won the toss!|You lost the toss/)
  await page.getByTestId(receives ? 'choose-receive' : 'choose-kick').click()
  await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeVisible()
  return data.game_id
}

async function completeGame(page, request, gameId) {
  const quarters = new Set()
  let halftimeCount = 0
  let executeCount = 0
  let kickoffCount = 0
  let previousLogLength = 0
  const actions = []
  for (let step = 0; step < 450; step++) {
    const state = await snapshot(page)
    quarters.add(state.quarter)
    const penaltyVisible = await page.getByText('PENALTY ON THE PLAY!', { exact: true }).isVisible()
    if (state.gameOver && !state.pendingPat && !penaltyVisible) {
      await expect(page.getByTestId('game-over'), 'Engine final state must reach the final-score screen').toBeVisible()
      const res = await request.get('http://localhost:8000/api/game/state/' + gameId)
      expect(res.ok()).toBeTruthy()
      const final = await res.json()
      expect(final.game_over).toBe(true)
      expect(final.pending_pat).toBe(false)
      expect(final.is_kickoff).toBe(false)
      expect(final.quarter).toBeGreaterThanOrEqual(4)
      await expect(page.getByTestId('game-over').getByTestId('home-score')).toHaveText(String(final.home_score))
      await expect(page.getByTestId('game-over').getByTestId('away-score')).toHaveText(String(final.away_score))
      expect([...quarters]).toEqual(expect.arrayContaining([1, 2, 3, 4]))
      expect(halftimeCount).toBe(1)
      expect(executeCount).toBeGreaterThan(80)
      expect(kickoffCount).toBeGreaterThanOrEqual(2)
      expect(state.log.length).toBeGreaterThan(80)
      expect(state.log.some(p => p.offensePlay === 'KO')).toBe(true)
      expect(actions).toContain('execute')
      expect(actions).toContain('penalty-decision')
      expect(actions).toContain('extra-point')
      console.info('Completed game', gameId, {
        score: [final.home_score, final.away_score], executeCount, kickoffCount, halftimeCount,
      })
      return { final, actions, executeCount, kickoffCount, halftimeCount }
    }
    let button
    let endpoint
    if (await page.getByTestId('halftime').isVisible()) {
      halftimeCount++
      expect(state.quarter).toBe(3)
      expect(state.timeRemaining).toBe(900)
      await page.getByTestId('continue-button').click()
      continue
    } else if (await page.getByRole('button', { name: 'KICK OFF', exact: true }).isVisible()) {
      button = page.getByRole('button', { name: 'KICK OFF', exact: true })
      endpoint = 'kickoff'
      kickoffCount++
    } else if (await page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true }).isVisible()) {
      button = page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })
      endpoint = 'extra-point'
    } else if (await page.getByRole('button', { name: /^\[1\]/ }).isVisible()) {
      button = page.getByRole('button', { name: /^\[1\]/ })
      endpoint = 'penalty-decision'
    } else if (await page.getByRole('button', { name: 'CONTINUE', exact: true }).isVisible()) {
      // Offsetting penalties use CONTINUE too.
      const penalty = await page.getByText('OFFSETTING PENALTIES', { exact: true }).isVisible()
      if (!penalty) {
        await page.getByRole('button', { name: 'CONTINUE', exact: true }).click()
        continue
      }
      button = page.getByRole('button', { name: 'CONTINUE', exact: true })
      endpoint = 'penalty-decision'
    } else if (await page.getByRole('button', { name: 'EXECUTE PLAY', exact: true }).isVisible()) {
      button = page.getByRole('button', { name: 'EXECUTE PLAY', exact: true })
      endpoint = 'execute'
    } else {
      // Simple human policy: varied run/pass calls; punt or FG on fourth down.
      const play = state.down === 4 ? (state.ballPosition < 55 ? 'p' : 'f') : ['1', '2', '6', '7'][executeCount % 4]
      button = page.getByTestId(state.playerOffense ? 'offense-play-' + play : 'defense-play-a')
      endpoint = 'execute'
    }
    await expect(button, 'No available action at step ' + step + ': ' + JSON.stringify(state)).toBeEnabled()
    const pending = page.waitForResponse(r => r.url().endsWith('/api/game/' + endpoint) && r.request().method() === 'POST')
    await button.click()
    if (await page.getByText('PUNT OPTIONS', { exact: true }).isVisible()) {
      await page.getByRole('button', { name: 'NORMAL PUNT', exact: true }).click()
    }
    const response = await pending
    expect(response.ok(), endpoint + ': ' + await response.text()).toBeTruthy()
    const data = await response.json()
    actions.push(endpoint)
    if (endpoint === 'execute') executeCount++
    // Pending decisions do not add a log entry until resolved; PATs update state.
    if (data.result?.pending_penalty_decision) {
      await expect(page.getByText('PENALTY ON THE PLAY!', { exact: true })).toBeVisible()
    } else if (endpoint === 'extra-point') {
      await expect.poll(async () => (await snapshot(page)).pendingPat).toBe(false)
    } else {
      await expect.poll(async () => {
        const s = await snapshot(page)
        return s.log.length > previousLogLength || s.gameOver
      }).toBe(true)
      if (data.game_state.pending_pat && !data.game_state.player_offense) {
        await expect.poll(async () => (await snapshot(page)).pendingPat).toBe(false)
      }
    }
    const after = await snapshot(page)
    previousLogLength = after.log.length
    if (!data.result?.pending_penalty_decision) {
      await expect.poll(async () => (await snapshot(page)).quarter).toBe(data.game_state.quarter)
    }
  }
  throw new Error('Game did not finish within 450 UI actions: ' + JSON.stringify(await snapshot(page)))
}

test('two complete real-engine games in one browser session, home then away', async ({ page, request }, testInfo) => {
  const errors = []
  page.on('pageerror', error => errors.push(String(error)))
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
  page.on('dialog', async dialog => { errors.push(dialog.message()); await dialog.dismiss() })
  page.on('response', response => {
    if (response.url().includes('/api/') && !response.ok()) {
      errors.push(response.status() + ' ' + response.url())
    }
  })
  // Make the UI coin toss deterministic and skip cosmetic waits only.
  // The backend RNG, dice outcomes, and full-length game clock are untouched.
  await page.addInitScript(() => {
    Math.random = () => 0.75 // Heads; test each receive/kick choice explicitly.
    const original = window.setTimeout.bind(window)
    window.setTimeout = (fn, delay, ...args) => original(fn, delay >= 300 && delay <= 2000 ? 0 : delay, ...args)
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
  const ids = []
  try {
    for (const options of [
      { home: true, seed: 20261017, player: 'Ironclads', receives: true },
      { home: false, seed: 20261018, player: 'Thunderhawks', receives: false },
    ]) {
      const id = await startGame(page, options)
      expect(ids).not.toContain(id)
      ids.push(id)
      const result = await completeGame(page, request, id)
      await testInfo.attach('game-' + id, { body: JSON.stringify(result, null, 2), contentType: 'application/json' })
      expect(errors).toEqual([])
      await page.getByTestId('new-game-button').click()
      expect(await snapshot(page)).toMatchObject({
        gameId: null, gameOver: false, pendingPat: false, isKickoff: false,
        homeScore: 0, awayScore: 0, quarter: 1, timeRemaining: 900, log: [],
      })
    }
    expect(ids).toHaveLength(2)
  } finally {
    for (const id of ids) await request.delete('http://localhost:8000/api/game/' + id)
  }
})
