import { backendURL } from './ports.js'
import { test, expect } from './fixtures.js'
import { resumeFixture } from './saved-checkpoint.js'
// AUD-016: labels and colors are team identity, not "who has the ball".
// Each case loads an away-human real-engine game and runs one snap through the
// rendered controls, once as offense and once as defense.
for (const playerOffense of [true, false]) {
  test(`play log labels the real teams with an away human on ${playerOffense ? 'offense' : 'defense'}`, async ({ page, request }) => {
    const legacySave = { gameId: 'obsolete-labels', ballPosition: 20 }
    let loadedId = null
    try {
      const restored = await resumeFixture(page, request, {
        kind: playerOffense ? 'label-offense' : 'label-defense', home: false,
        name: `AUD-016 ${playerOffense ? 'offense' : 'defense'}`, legacySave,
      })
      loadedId = restored.game_id
      expect(restored.game_state.player_offense).toBe(playerOffense)

      const possession = playerOffense ? 'away' : 'home'
      const offenseTeam = playerOffense ? 'HBI' : 'MCT'
      const defenseTeam = playerOffense ? 'MCT' : 'HBI'
      const humanTeam = 'HBI'

      const executing = page.waitForResponse(r => r.url().endsWith('/api/game/execute'))
      await page.getByTestId(playerOffense ? 'offense-play-6' : 'defense-play-a').click()
      const response = await executing
      expect(response.ok(), await response.text()).toBeTruthy()
      const executed = await response.json()
      if (executed.result?.pending_penalty_decision) {
        const deciding = page.waitForResponse(r => r.url().endsWith('/api/game/penalty-decision'))
        await page.getByRole('button', { name: /TAKE YARDAGE/i }).click()
        const decision = await deciding
        expect(decision.ok(), await decision.text()).toBeTruthy()
      }

      // Wait for the acknowledged action to reach the rendered log after autosave.
      await expect.poll(() => page.evaluate(async () => {
        const { useGameStore } = await import('/src/store/gameStore.js')
        return useGameStore.getState().playLog.length
      })).toBe(1)
      const log = await page.evaluate(async () => {
        const { useGameStore } = await import('/src/store/gameStore.js')
        return useGameStore.getState().playLog
      })
      expect(log).toHaveLength(1)
      expect(log[0]).toMatchObject({
        offenseTeam, defenseTeam, playerTeam: humanTeam, possession,
        possessionSemantics: 'preplay',
      })
      await expect(page.getByText(`${offenseTeam} vs ${defenseTeam}`, { exact: true })).toBeVisible()
      await expect(page.getByText(`OFF: ${log[0].offensePlay}`, { exact: true }))
        .toHaveClass(playerOffense ? 'text-green-400' : 'text-red-400')
      await expect(page.getByText(`DEF: ${log[0].defensePlay}`, { exact: true }))
        .toHaveClass(playerOffense ? 'text-red-400' : 'text-green-400')
      expect(await page.evaluate(() => localStorage.getItem('paydirt_save'))).toBe(JSON.stringify(legacySave))
    } finally {
      if (loadedId) await request.delete(backendURL + '/api/game/' + loadedId)
    }
  })
}
