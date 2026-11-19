import { test, expect } from './fixtures.js'
import { resumeFixture } from './saved-checkpoint.js'
import { backendURL } from './ports.js'
for (const offense of [true, false]) {
  test(`clock labels, modifier help and visible save confirmation on ${offense ? 'offense' : 'defense'}`, async ({ page, request }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    const { game_id: gameId, saveId } = await resumeFixture(page, request, {
      kind: offense ? 'help-offense' : 'help-defense', name: `Player help ${offense}`,
      legacySave: { gameId: 'synthetic-help', currentSeason: '2026' },
    })
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
      const legacySave = await page.evaluate(() => localStorage.getItem('paydirt_save'))
      const checkpointed = page.waitForResponse(r => r.url().endsWith(`/api/game/checkpoint/${gameId}`) && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'SAVE GAME', exact: true }).click()
      const checkpointResponse = await checkpointed
      expect(checkpointResponse.ok()).toBeTruthy()
      const { checkpoint } = await checkpointResponse.json()
      expect(typeof checkpoint).toBe('string')
      expect(checkpoint.length).toBeGreaterThan(0)
      const saveConfirmation = page.getByRole('status').filter({ hasText: /^Game saved locally\.$/ })
      await expect(saveConfirmation).toBeVisible()
      await page.evaluate(() => window.scrollTo(0, 0))
      const box = await saveConfirmation.boundingBox()
      expect(box.y).toBeGreaterThanOrEqual(0)
      expect(box.y + box.height).toBeLessThanOrEqual(844)
      // SAVE GAME writes a full engine checkpoint to the canonical library.
      // The legacy replay source remains intact for compatibility/recovery.
      const saved = await page.evaluate(async id => {
        const { gameLibrary } = await import('/src/runtime/gameLibrary.js')
        return gameLibrary.get(id)
      }, saveId)
      expect(saved.id).toBe(saveId)
      expect(saved.metadata.gameId).toBe(gameId)
      expect(saved.revision).toBeGreaterThan(0)
      expect(saved.checkpoint).toBe(checkpoint)
      expect(await page.evaluate(() => localStorage.getItem('paydirt_save'))).toBe(legacySave)
      expect(JSON.parse(legacySave).gameId).toBe('synthetic-help')
      await page.screenshot({ path: testInfo.outputPath('player-help-save.png') })
    } finally {
      await request.delete(`${backendURL}/api/game/${gameId}`)
    }
  })
}
