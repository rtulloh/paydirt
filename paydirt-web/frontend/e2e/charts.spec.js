import { backendURL } from './ports.js'
import { test, expect } from './fixtures.js'

test('original-style chart sheets display real loaded teams without advancing play', async ({ page, request }, testInfo) => {
  const errors = []
  page.on('pageerror', error => errors.push(String(error)))
  await page.addInitScript(() => { Math.random = () => 0.75 })
  await page.goto('/')
  await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
  await page.getByRole('button', { name: '2026', exact: true }).click()
  await page.getByRole('button', { name: /Ironclads/ }).click()
  await page.getByRole('button', { name: /Thunderhawks/ }).click()
  const created = page.waitForResponse(response => response.url().endsWith('/api/game/new'))
  await page.getByRole('button', { name: 'START GAME', exact: true }).click()
  const { game_id: gameId } = await (await created).json()
  try {
    await page.getByTestId('choose-heads').click()
    await page.getByTestId('choose-receive').click()
    await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeVisible()
    const state = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()

    const trigger = page.getByRole('button', { name: 'CHARTS', exact: true })
    await trigger.click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Chart team').selectOption('home')
    await expect(dialog.getByRole('heading')).toContainText(`2026 ${state.home_team.name}`)
    await dialog.getByRole('button', { name: 'Offense', exact: true }).click()
    const grid = dialog.getByRole('region', { name: 'Offense chart grid' })
    await expect(grid.locator('tbody tr')).toHaveCount(30)
    await expect(grid.getByRole('columnheader', { name: 'Rushing plays', exact: true })).toBeVisible()
    await expect(grid.getByRole('columnheader', { name: 'Passing plays', exact: true })).toBeVisible()
    await expect(grid.locator('.paydirt-chart-cell-green').first()).toHaveCSS('background-color', 'rgb(0, 155, 0)')
    await expect(grid.locator('.paydirt-chart-cell-yellow').first()).toHaveCSS('background-color', 'rgb(255, 255, 0)')
    await expect(grid.locator('.paydirt-chart-cell-black').first()).toHaveCSS('background-color', 'rgb(0, 0, 0)')
    await page.screenshot({ path: testInfo.outputPath('chart-offense.png') })

    await dialog.getByRole('button', { name: 'Defense', exact: true }).click()
    const defense = dialog.getByRole('region', { name: 'Defense chart grid' })
    await expect(defense.locator('tbody tr')).toHaveCount(30)
    await expect(defense.getByRole('rowgroup').filter({ hasText: 'Standard' })).toBeVisible()
    await expect(defense.locator('.paydirt-chart-formation')).toHaveCount(6)
    await page.screenshot({ path: testInfo.outputPath('chart-defense.png') })
    await expect(dialog.getByRole('button', { name: 'Special Plays', exact: true })).toHaveCount(0)
    await dialog.getByRole('button', { name: 'Special Teams', exact: true }).click()
    await expect(dialog.getByRole('region', { name: 'Special Teams chart grid' }).locator('tbody tr')).toHaveCount(30)
    await dialog.getByLabel('Chart team').selectOption('away')
    await expect(dialog.getByRole('heading')).toContainText(`2026 ${state.away_team.name}`)
    await dialog.getByRole('button', { name: 'Offense', exact: true }).click()
    await page.setViewportSize({ width: 390, height: 844 })
    await expect.poll(() => grid.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true)
    expect((await dialog.boundingBox()).width).toBeLessThanOrEqual(390)
    const mobileSpecial = dialog.getByRole('region', { name: 'Special Plays chart grid' })
    await expect(mobileSpecial.locator('tbody tr')).toHaveCount(30)
    const mobileOffenseBox = await grid.boundingBox()
    const mobileSpecialBox = await mobileSpecial.boundingBox()
    expect(mobileSpecialBox.y).toBeGreaterThanOrEqual(mobileOffenseBox.y + mobileOffenseBox.height)
    expect(mobileSpecialBox.width).toBeLessThanOrEqual(300)
    await mobileSpecial.scrollIntoViewIfNeeded()
    expect(await mobileSpecial.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
    await page.keyboard.press('Tab')
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true)
    await page.keyboard.press('1')
    await page.keyboard.press('t')
    await page.keyboard.press('n')
    const after = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()
    expect(after).toEqual(state)
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    await trigger.click()
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Close charts', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    expect(errors).toEqual([])
  } finally {
    await request.delete(`${backendURL}/api/game/${gameId}`)
  }
})

async function startChartGame(page) {
  await page.addInitScript(() => { Math.random = () => 0.75 })
  await page.goto('/')
  await page.getByRole('button', { name: 'NEW GAME', exact: true }).click()
  await page.getByRole('button', { name: '2026', exact: true }).click()
  await page.getByRole('button', { name: /Ironclads/ }).click()
  await page.getByRole('button', { name: /Thunderhawks/ }).click()
  const created = page.waitForResponse(response => response.url().endsWith('/api/game/new'))
  await page.getByRole('button', { name: 'START GAME', exact: true }).click()
  const { game_id: gameId } = await (await created).json()
  await page.getByTestId('choose-heads').click()
  await page.getByTestId('choose-receive').click()
  await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeVisible()
  return gameId
}

async function expectCompleteSheet(page, grid) {
  await expect(grid.locator('tbody tr')).toHaveCount(30)
  const fit = await grid.evaluate(element => {
    const rows = element.querySelectorAll('tbody tr')
    return {
      top: rows[0].getBoundingClientRect().top,
      bottom: rows[29].getBoundingClientRect().bottom,
      height: element.clientHeight, scrollHeight: element.scrollHeight,
      width: element.clientWidth, scrollWidth: element.scrollWidth,
      font: parseFloat(getComputedStyle(rows[0].querySelector('td')).fontSize),
    }
  })
  expect(fit.top).toBeGreaterThanOrEqual(0)
  expect(fit.bottom).toBeLessThanOrEqual(page.viewportSize().height)
  expect(fit.scrollHeight).toBeLessThanOrEqual(fit.height)
  expect(fit.scrollWidth).toBeLessThanOrEqual(fit.width)
  expect(fit.font).toBeGreaterThanOrEqual(12)
}

for (const viewport of [{ width: 1440, height: 1100 }, { width: 1280, height: 900 }, { width: 1366, height: 768 }, { width: 1920, height: 1080 }]) {
  test(`all chart rows fit one desktop page at ${viewport.width}x${viewport.height}`, async ({ page, request }, testInfo) => {
    await page.setViewportSize(viewport)
    const gameId = await startChartGame(page)
    try {
      const before = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()
      const reference = await (await request.get(`${backendURL}/api/game/charts/${gameId}?side=home`)).json()
      await page.getByRole('button', { name: 'CHARTS', exact: true }).click()
      const dialog = page.getByRole('dialog')
      for (const section of ['Offense', 'Defense', 'Special Teams']) {
        await dialog.getByRole('button', { name: section, exact: true }).click()
        await expectCompleteSheet(page, dialog.getByRole('region', { name: `${section} chart grid` }))
        if (section === 'Offense') {
          const main = dialog.getByRole('region', { name: 'Offense chart grid' })
          const special = dialog.getByRole('region', { name: 'Special Plays chart grid' })
          await expectCompleteSheet(page, special)
          const mainBox = await main.boundingBox()
          const specialBox = await special.boundingBox()
          expect(specialBox.x).toBeGreaterThanOrEqual(mainBox.x + mainBox.width)
          expect(Math.abs(specialBox.y - mainBox.y)).toBeLessThanOrEqual(1)
          const mainRow = await main.locator('tbody tr').first().boundingBox()
          const specialRow = await special.locator('tbody tr').first().boundingBox()
          expect(Math.abs(mainRow.y - specialRow.y)).toBeLessThanOrEqual(1)
        }
        if (section === 'Offense') {
          const special = dialog.getByRole('region', { name: 'Special Plays chart grid' })
          expect((await special.boundingBox()).width).toBeLessThanOrEqual(300)
          const roll = special.locator('tbody tr').first().getByRole('rowheader')
          expect((await roll.boundingBox()).width).toBeLessThanOrEqual(36)
          await expect(special.getByRole('columnheader').last()).toHaveText('#')
          expect(await special.locator('tbody td > span:first-child').allTextContents()).toEqual(
            reference.special_plays.rows.flatMap(row => row.cells.map(cell => cell.label)),
          )
        }
        await expect(dialog.locator('details')).not.toHaveAttribute('open', '')
        const layout = await dialog.evaluate(element => ({ height: element.clientHeight, scrollHeight: element.scrollHeight }))
        expect(layout.scrollHeight).toBeLessThanOrEqual(layout.height)
        await page.screenshot({ path: testInfo.outputPath(`${section.toLowerCase().replaceAll(' ', '-')}-fit.png`) })
      }
      const after = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()
      expect(after).toEqual(before)
    } finally {
      await request.delete(`${backendURL}/api/game/${gameId}`)
    }
  })
}

for (const launcher of ['Open in new tab', 'Open in separate window']) {
  test(`${launcher} keeps independent charts while the parent remains playable`, async ({ page, context, request }) => {
    const gameId = await startChartGame(page)
    let child
    try {
      const before = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()
      const posts = []
      context.on('request', sent => { if (sent.method() === 'POST') posts.push(sent.url()) })
      await page.getByRole('button', { name: 'CHARTS', exact: true }).click()
      const dialog = page.getByRole('dialog')
      await dialog.getByLabel('Chart team').selectOption('away')
      await expect(dialog.getByRole('heading')).toContainText(before.away_team.name)
      await dialog.getByRole('button', { name: 'Defense', exact: true }).click()
      const opened = context.waitForEvent('page')
      await dialog.getByRole(launcher === 'Open in new tab' ? 'link' : 'button', { name: launcher, exact: true }).click()
      child = await opened
      await child.waitForLoadState()
      await expect(child.getByRole('table', { name: `Defense · ${before.away_team.name}` })).toBeVisible()
      expect(await child.evaluate(() => window.opener)).toBeNull()
      await expect(child.getByRole('button', { name: 'CHARTS', exact: true })).toHaveCount(0)
      await expect(dialog).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeEnabled()
      await child.reload()
      await expect(child.getByRole('table', { name: `Defense · ${before.away_team.name}` })).toBeVisible()
      await expectCompleteSheet(child, child.getByRole('region', { name: 'Defense chart grid' }))
      await child.getByLabel('Chart team').selectOption('home')
      await expect(child.getByRole('heading')).toContainText(before.home_team.name)
      for (const section of ['Offense', 'Special Teams']) {
        await child.getByRole('button', { name: section, exact: true }).click()
        await expectCompleteSheet(child, child.getByRole('region', { name: `${section} chart grid` }))
        if (section === 'Offense') await expectCompleteSheet(child, child.getByRole('region', { name: 'Special Plays chart grid' }))
      }
      await page.getByRole('button', { name: 'CHARTS', exact: true }).click()
      await expect(page.getByLabel('Chart team')).toHaveValue('home')
      // The receiving team starts in the defensive role during the opening kickoff.
      await expect(page.getByRole('table', { name: `Defense · ${before.home_team.name}` })).toBeVisible()
      await page.getByRole('button', { name: 'Close charts', exact: true }).click()
      expect(posts).toEqual([])
      expect(await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()).toEqual(before)
      // Advance the actual game to prove the separate chart page leaves play usable.
      const kickoff = page.waitForResponse(response => response.url().endsWith('/api/game/kickoff'))
      await page.getByRole('button', { name: 'KICK OFF', exact: true }).click()
      expect((await kickoff).ok()).toBe(true)
      await expect(child.getByRole('table', { name: /^Special Teams/ })).toBeVisible()
    } finally {
      await child?.close()
      await request.delete(`${backendURL}/api/game/${gameId}`)
    }
  })
}

test('an expired standalone chart link offers retry without mounting game setup', async ({ page }) => {
  const posts = []
  page.on('request', sent => { if (sent.method() === 'POST') posts.push(sent.url()) })
  await page.goto('/?charts=expired-game&side=away&view=defense')
  await expect(page.getByRole('alert')).toContainText('This game is no longer available')
  await expect(page.getByRole('button', { name: 'Retry charts', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'NEW GAME', exact: true })).toHaveCount(0)
  expect(posts).toEqual([])
})

test('an older Special Plays link opens combined Offense with the selected team', async ({ page, request }) => {
  const gameId = await startChartGame(page)
  try {
    const before = await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()
    await page.goto(`/?charts=${gameId}&side=away&view=special_plays`)
    await expect(page.getByRole('table', { name: `Offense · ${before.away_team.name}` })).toBeVisible()
    await expect(page.getByRole('table', { name: `Special Plays · ${before.away_team.name}` })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Special Plays', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Offense', exact: true })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByLabel('Chart team')).toHaveValue('away')
    await expect(page.getByRole('link', { name: 'Open in new tab' })).toHaveAttribute('href', /view=offense$/)
    expect(await (await request.get(`${backendURL}/api/game/state/${gameId}`)).json()).toEqual(before)
  } finally {
    await request.delete(`${backendURL}/api/game/${gameId}`)
  }
})
