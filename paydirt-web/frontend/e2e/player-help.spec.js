import { test, expect } from '@playwright/test'

for (const offense of [true, false]) {
  test(`clock labels, modifier help and visible save confirmation on ${offense ? 'offense' : 'defense'}`, async ({ page, request }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.addInitScript(({ offense }) => {
      localStorage.setItem('paydirt_save', JSON.stringify({
        gameId: 'synthetic-help', currentSeason: '2026',
        homeTeam: { id: 'Ironclads' }, awayTeam: { id: 'Thunderhawks' },
        humanTeamId: 'Ironclads', cpuTeamId: 'Thunderhawks',
        humanPlaysOffense: offense, possession: offense ? 'home' : 'away',
        quarter: 2, timeRemaining: 41, down: 3, yardsToGo: 9, ballPosition: 77,
        homeScore: 0, awayScore: 0, homeTimeouts: 3, awayTimeouts: 1,
        playLog: [
          { quarter: 2, timeRemaining: 41, description: 'Synthetic first-half play' },
          { quarter: 3, timeRemaining: 900, description: 'Synthetic second-half play' },
        ],
      }))
    }, { offense })
    await page.goto('/')
    const loaded = page.waitForResponse(r => r.url().endsWith('/api/game/load-replay'))
    await page.getByRole('button', { name: 'LOAD GAME', exact: true }).click()
    const response = await loaded
    expect(response.ok()).toBeTruthy()
    const { game_id: gameId } = await response.json()
    try {
      const scoreboard = page.getByTestId('scoreboard')
      const homeTimeouts = scoreboard.getByLabel('Ironclads timeouts remaining')
      const awayTimeouts = scoreboard.getByLabel('Thunderhawks timeouts remaining')
      await expect(homeTimeouts).toHaveText('TO: 3')
      await expect(awayTimeouts).toHaveText('TO: 1')
      for (const count of [homeTimeouts, awayTimeouts]) {
        const box = await count.boundingBox()
        expect(box.x).toBeGreaterThanOrEqual(0)
        expect(box.x + box.width).toBeLessThanOrEqual(390)
      }
      const modifiers = page.getByTestId('play-modifiers')
      const timeout = modifiers.getByRole('radio', { name: 'Timeout (3 left) [T]' })
      await expect(timeout).toBeEnabled()
      await expect(timeout.locator('..')).toHaveAttribute('title', /running clock/)
      if (offense) {
        await expect(modifiers.getByRole('radio', { name: 'Out of bounds [O]' }).locator('..')).toHaveAttribute('title', /five yards/)
      } else {
        await expect(modifiers.getByRole('radio', { name: 'Out of bounds [O]' })).toHaveCount(0)
      }
      await expect(page.getByText('Q2 0:41', { exact: true })).toBeVisible()
      await expect(page.getByText('Q3 15:00', { exact: true })).toBeVisible()
      await page.getByRole('button', { name: 'SAVE GAME', exact: true }).click()
      await expect(page.getByRole('status')).toHaveText('Game saved in this browser.')
      await page.evaluate(() => window.scrollTo(0, 0))
      const box = await page.getByRole('status').boundingBox()
      expect(box.y).toBeGreaterThanOrEqual(0)
      expect(box.y + box.height).toBeLessThanOrEqual(844)
      expect((await page.evaluate(() => JSON.parse(localStorage.getItem('paydirt_save')))).gameId).toBe(gameId)
      await page.screenshot({ path: testInfo.outputPath('player-help-save.png') })
    } finally {
      await request.delete(new URL(`/api/game/${gameId}`, response.url()).href)
    }
  })
}
