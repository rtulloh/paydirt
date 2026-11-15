import { backendURL } from './ports.js'
import { test, expect } from './fixtures.js'

// AUD-016: labels and colors are team identity, not "who has the ball".
// Each case loads an away-human real-engine game and runs one snap through the
// rendered controls, once as offense and once as defense.
for (const playerOffense of [true, false]) {
  test(`play log labels the real teams with an away human on ${playerOffense ? 'offense' : 'defense'}`, async ({ page, request }) => {
    const created = await request.post(backendURL + '/api/game/new', {
      data: {
        player_team: 'Ironclads', opponent_team: 'Thunderhawks',
        season: '2026', play_as_home: false,
      },
    })
    expect(created.ok()).toBeTruthy()
    const game = await created.json()
    let loadedId = null
    try {
      const state = game.game_state
      const save = {
        gameId: game.game_id, currentSeason: '2026',
        homeTeam: state.home_team, awayTeam: state.away_team,
        humanTeamId: state.human_team_id, cpuTeamId: state.cpu_team_id,
        humanPlaysOffense: playerOffense, homeScore: 0, awayScore: 0,
        quarter: 1, timeRemaining: 900,
        possession: playerOffense ? 'away' : 'home',
        ballPosition: 20, down: 1, yardsToGo: 10,
        homeTimeouts: 3, awayTimeouts: 3, playLog: [],
      }
      await page.addInitScript(save => localStorage.setItem('paydirt_save', JSON.stringify(save)), save)
      await page.goto('/')
      const loading = page.waitForResponse(r => r.url().endsWith('/api/game/load-replay'))
      await page.getByRole('button', { name: /LOAD SAVED GAME|LOAD GAME|RESUME/i }).click()
      loadedId = (await (await loading).json()).game_id

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
    } finally {
      if (loadedId) await request.delete(backendURL + '/api/game/' + loadedId)
      await request.delete(backendURL + '/api/game/' + game.game_id)
    }
  })
}
