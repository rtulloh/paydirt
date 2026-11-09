import { backendURL, guardLocalRoute } from './ports.js'
import { test, expect } from './fixtures.js'

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
    humanTimeouts: s.humanIsHome ? s.homeTimeouts : s.awayTimeouts,
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
  let lateCpuConfirmations = 0
  let defensiveTimeouts = 0
  let timeoutKeyboardExercised = false
  let previousLogLength = 0
  let defenseSelectionCount = 0
  let lastDefenseCall = null
  let saveVerified = false
  const defensiveCalls = new Set()
  const actions = []
  for (let step = 0; step < 450; step++) {
    const state = await snapshot(page)
    quarters.add(state.quarter)
    const penaltyVisible = await page.getByText('PENALTY ON THE PLAY!', { exact: true }).isVisible()
    if (state.gameOver && !state.pendingPat && !penaltyVisible) {
      await expect(page.getByTestId('game-over'), 'Engine final state must reach the final-score screen').toBeVisible()
      const res = await request.get(backendURL + '/api/game/state/' + gameId)
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
      expect(defensiveTimeouts, 'Use a defensive timeout through the rendered controls').toBeGreaterThan(0)
      expect(timeoutKeyboardExercised).toBe(true)
      expect([...defensiveCalls].sort()).toEqual(['A', 'B', 'C', 'D', 'E', 'F'])
      expect(saveVerified).toBe(true)
      console.info('Completed game', gameId, {
        score: [final.home_score, final.away_score], executeCount, kickoffCount, halftimeCount, defensiveTimeouts,
      })
      return { final, actions, executeCount, kickoffCount, halftimeCount, lateCpuConfirmations, defensiveTimeouts }
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
      const defense = ['a', 'b', 'c', 'd', 'e', 'f'][defenseSelectionCount % 6]
      if (!state.playerOffense) {
        lastDefenseCall = defense.toUpperCase()
        defenseSelectionCount++
      }
      button = page.getByTestId(state.playerOffense ? 'offense-play-' + play : 'defense-play-' + defense)
      endpoint = 'execute'
    }
    const saveButton = page.getByRole('button', { name: 'SAVE GAME', exact: true })
    if (!saveVerified && await saveButton.isEnabled()) {
      await saveButton.click()
      await expect(page.getByRole('status')).toHaveText('Game saved in this browser.')
      const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('paydirt_save')))
      expect(saved).toMatchObject({ gameId, timeRemaining: state.timeRemaining, ballPosition: state.ballPosition })
      saveVerified = true
    }
    if (endpoint === 'execute' && !state.playerOffense) {
      const modifiers = page.getByTestId('play-modifiers')
      await expect(modifiers.getByRole('radio', { name: 'Out of bounds [O]' })).toHaveCount(0)
      await expect(modifiers.getByRole('radio', { name: 'Spike [S]' })).toHaveCount(0)
      const timeout = modifiers.getByRole('radio', { name: `Timeout (${state.humanTimeouts} left) [T]` })
      if (state.humanTimeouts > 0) {
        await timeout.check()
        if (!timeoutKeyboardExercised) {
          await page.keyboard.press('0')
          await expect(modifiers.getByRole('radio', { name: 'None [0]' })).toBeChecked()
          await page.keyboard.press('t')
          await expect(timeout).toBeChecked()
          timeoutKeyboardExercised = true
        }
      } else {
        await expect(timeout).toBeDisabled()
      }
    }
    await expect(button, 'No available action at step ' + step + ': ' + JSON.stringify(state)).toBeEnabled()
    let receivedResponse
    let responseError
    const pending = page.waitForResponse(r => r.url().endsWith('/api/game/' + endpoint) && r.request().method() === 'POST', { timeout: 5_000 })
      .then(response => { receivedResponse = response }, error => { responseError = error })
    await button.click()
    // A defense click may only reveal the asynchronously arriving CPU kick
    // decision. Wait for either execution or the next required UI action.
    let followup
    let cpuConfirmation = false
    await expect.poll(async () => {
      if (responseError) throw responseError
      if (receivedResponse) return true
      const normalPunt = page.getByRole('button', { name: 'NORMAL PUNT', exact: true })
      const cpuExecute = page.getByRole('button', { name: 'EXECUTE PLAY', exact: true })
      if (await normalPunt.isVisible()) {
        followup = normalPunt
        return true
      }
      if (await cpuExecute.isVisible()) {
        followup = cpuExecute
        cpuConfirmation = true
        return true
      }
      return false
    }, { message: 'Action must execute or reveal its confirmation', timeout: 5_000 }).toBe(true)
    if (!receivedResponse && followup) {
      await followup.click()
      if (cpuConfirmation) lateCpuConfirmations++
    }
    await pending
    if (responseError) throw responseError
    const response = receivedResponse
    expect(response.ok(), endpoint + ': ' + await response.text()).toBeTruthy()
    const data = await response.json()
    if (data.result?.defensive_timeout_used) {
      defensiveTimeouts++
      const sent = response.request().postDataJSON()
      expect(sent.call_defensive_timeout).toBe(true)
      expect(sent.player_play).toBe(['P', 'F'].includes(sent.cpu_play) ? 'A' : lastDefenseCall)
      const remaining = data.game_state.human_is_home ? data.game_state.home_timeouts : data.game_state.away_timeouts
      expect(remaining).toBe(state.humanTimeouts - 1)
      expect(data.result.description).toContain('Defensive timeout: clock stopped.')
    }
    if (endpoint === 'execute') {
      if (!state.playerOffense) {
        const sent = response.request().postDataJSON()
        // A confirmed CPU kick uses A as a placeholder; its formation is not
        // used by kick resolution. Ordinary plays must use the selected call.
        const cpuKick = ['P', 'F'].includes(sent.cpu_play)
        expect(sent.player_play).toBe(cpuKick ? 'A' : lastDefenseCall)
        if (!cpuKick) defensiveCalls.add(sent.player_play)
      }
      await expect.poll(async () => (await snapshot(page)).selectedModifier).toBeNull()
    }
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
  // Each full game gets the normal three-minute budget in this shared session.
  test.setTimeout(2 * 180_000)
  // Forward genuine engine responses, holding the first CPU kick decision
  // until a defense click to reproduce the CI panel-arrival race.
  let decisionHeld = false
  let lateDecisionExercised = false
  let delayNextDecision = true
  let releaseDecision
  const defenseClicked = new Promise(resolve => { releaseDecision = resolve })
  await page.exposeBinding('paydirtDefenseClicked', () => {
    if (decisionHeld) {
      lateDecisionExercised = true
      releaseDecision()
    }
  })
  await page.route('**/api/game/cpu-4th-down-decision/**', guardLocalRoute(async route => {
    const delay = delayNextDecision
    delayNextDecision = false
    if (delay) decisionHeld = true
    const response = await route.fetch()
    if (delay) {
      await defenseClicked
      await new Promise(resolve => setTimeout(resolve, 100))
      decisionHeld = false
    }
    await route.fulfill({ response })
  }))
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
    document.addEventListener('click', event => {
      if (event.target.closest('[data-testid^="defense-play-"]')) {
        window.paydirtDefenseClicked()
      }
    }, true)
    Math.random = () => 0.75 // Heads; test each receive/kick choice explicitly.
    const original = window.setTimeout.bind(window)
    window.setTimeout = (fn, delay, ...args) => original(fn, delay >= 300 && delay <= 2000 ? 0 : delay, ...args)
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
  const ids = []
  try {
    for (const options of [
      { home: true, seed: 20261026, player: 'Ironclads', receives: true },
      { home: false, seed: 20261027, player: 'Thunderhawks', receives: false },
    ]) {
      const id = await startGame(page, options)
      expect(ids).not.toContain(id)
      ids.push(id)
      const result = await completeGame(page, request, id)
      if (options.home) expect(result.lateCpuConfirmations).toBeGreaterThan(0)
      await testInfo.attach('game-' + id, { body: JSON.stringify(result, null, 2), contentType: 'application/json' })
      expect(errors).toEqual([])
      await page.getByTestId('new-game-button').click()
      expect(await snapshot(page)).toMatchObject({
        gameId: null, gameOver: false, pendingPat: false, isKickoff: false,
        homeScore: 0, awayScore: 0, quarter: 1, timeRemaining: 900, log: [],
      })
    }
    expect(ids).toHaveLength(2)
    expect(lateDecisionExercised).toBe(true)
  } finally {
    releaseDecision()
    for (const id of ids) await request.delete(backendURL + '/api/game/' + id)
  }
})
