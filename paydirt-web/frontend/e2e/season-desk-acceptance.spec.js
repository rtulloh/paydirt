import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { test, expect } from './fixtures.js'
import { frontendURL, isForeignLoopback } from './ports.js'

// Only public 2026 editions. Every season change and simulation is a rendered
// control; runtime reads below inspect durable identity and engine-derived data.
async function openSeasons(page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'SEASONS', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Every game has a place.' })).toBeVisible()
}

async function createCustom(page, name, conferences = ['Sample conference', 'Sample conference']) {
  await page.getByRole('button', { name: '+ New season', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Create season', exact: true })
  await expect(dialog.getByLabel('Season name', { exact: true })).toBeFocused()
  await dialog.getByLabel('Season name', { exact: true }).fill(name)
  await dialog.getByLabel(/^Chart year/).selectOption('2026')
  await expect(dialog.getByLabel(/^Team/).locator('option')).toHaveCount(2)
  await dialog.getByLabel('Conference', { exact: true }).fill(conferences[0])
  await dialog.getByLabel('Division', { exact: true }).fill('North')
  await dialog.getByLabel(/^Team/).selectOption('Ironclads')
  await dialog.getByRole('button', { name: '+ Add team edition', exact: true }).click()
  await dialog.getByLabel('Conference', { exact: true }).fill(conferences[1])
  await dialog.getByLabel('Division', { exact: true }).fill('South')
  await dialog.getByLabel(/^Team/).selectOption('Thunderhawks')
  await dialog.getByRole('button', { name: '+ Add team edition', exact: true }).click()
  await expect(dialog.getByLabel(/^Rules for every game/)).toHaveValue('2026')
  // Both directions of the real focus trap, followed by keyboard submission.
  const create = dialog.getByRole('button', { name: 'Create season', exact: true })
  const close = dialog.getByRole('button', { name: 'Close', exact: true })
  await create.focus()
  await page.keyboard.press('Tab')
  await expect(close).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(create).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Play fixture', exact: true })).toHaveCount(2)
}

async function storedCampaign(page, name) {
  return page.evaluate(async campaignName => {
    const api = await import('/src/runtime/campaigns.js')
    const records = await api.listCampaigns()
    const record = records.find(item => item.campaign.name === campaignName)
    if (!record) throw new Error('Rendered campaign is missing from durable storage')
    return { record, view: await api.viewCampaign(record.campaign) }
  }, name)
}

async function noPageOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    width: window.innerWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }))
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.width + 1)
  expect(dimensions.body).toBeLessThanOrEqual(dimensions.width + 1)
}

test('rendered season desk supports schedule review, team tracking, real results, keyboard and phone tables', async ({ page }, testInfo) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await openSeasons(page)
  await createCustom(page, 'Rendered sample season')
  await expect(page.getByText('Saved in this browser.', { exact: false })).toBeVisible()

  // Editing the generated calendar is available before the first game.
  const edit = page.getByRole('button', { name: 'Edit schedule', exact: true })
  await edit.click()
  let editor = page.getByRole('dialog', { name: 'Edit season schedule' })
  await expect(editor.getByRole('button', { name: 'Close', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(editor).toBeHidden()
  await expect(edit).toBeFocused()
  await edit.click()
  editor = page.getByRole('dialog', { name: 'Edit season schedule' })
  await editor.getByRole('button', { name: 'Remove fixture 2', exact: true }).click()
  await editor.getByLabel('Fixture week', { exact: true }).fill('3')
  await editor.getByRole('button', { name: 'Add fixture', exact: true }).click()
  await editor.getByRole('button', { name: 'Save schedule', exact: true }).click()
  await expect(editor).toBeHidden()
  const before = await storedCampaign(page, 'Rendered sample season')
  expect(before.record.campaign.fixtures.map(fixture => fixture.week)).toEqual([1, 3])
  expect(before.view.standings.every(row => row.played === 0)).toBe(true)

  const follow = page.getByLabel(/^Follow team/)
  await follow.selectOption({ label: '2026 Harbor Bay Ironclads' })
  await expect(page.getByText(/Next for 2026 .*Ironclads/)).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Standings', exact: true })).toHaveCount(0)
  await page.getByRole('tab', { name: 'Overview', exact: true }).focus()
  await page.keyboard.press('Space')
  await expect(page.getByRole('tab', { name: 'Overview', exact: true })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByLabel(/^Standings scope/)).toHaveValue('all')
  await expect(page.getByRole('table')).toHaveCount(2)
  await page.getByLabel(/^Standings scope/).selectOption('conference:Sample conference')
  await expect(page.getByRole('table')).toHaveCount(2)
  await page.getByRole('tab', { name: 'Leaders', exact: true }).click()
  await expect(page.getByText('No completed games with statistics yet. Team leaders appear after games finish.')).toBeVisible()

  await page.getByRole('tab', { name: 'Schedule', exact: true }).click()
  await page.getByRole('button', { name: 'Simulate unplayed games', exact: true }).click()
  await expect(page.getByText('2 of 2 games completed', { exact: false })).toBeVisible({ timeout: 60_000 })
  await expect(page.getByRole('button', { name: 'Edit schedule', exact: true })).toHaveCount(0)
  const final = await storedCampaign(page, 'Rendered sample season')
  expect(final.record.campaign.fixtures.every(fixture => fixture.status === 'completed' && fixture.result.source === 'simulated')).toBe(true)
  expect(final.view.standings.reduce((sum, row) => sum + row.played, 0)).toBe(4)
  expect(final.record.campaign.followed_participant_id).toBeTruthy()

  await page.getByRole('tab', { name: 'Overview', exact: true }).click()
  await page.getByLabel(/^Standings scope/).selectOption('all')
  for (const expected of final.view.standings) {
    const row = page.getByRole('row').filter({ hasText: `2026 ${expected.name}` })
    await expect(row.getByRole('cell').nth(1)).toHaveText(String(expected.wins))
    await expect(row.getByRole('cell').nth(2)).toHaveText(String(expected.losses))
    await expect(row.getByRole('cell').nth(4)).toHaveText(String(expected.points_for))
  }
  await page.getByRole('tab', { name: 'Team statistics', exact: true }).click()
  await expect(page.getByRole('columnheader')).toHaveCount(23)
  for (const expected of final.view.statistics) {
    const row = page.getByRole('row').filter({ hasText: `2026 ${expected.name}` })
    await expect(row.getByRole('cell').nth(1)).toHaveText('2')
    await expect(row.getByRole('cell').nth(3).locator('span')).toHaveText(String(expected.offense.total_yards))
    await expect(row.getByRole('cell').nth(3).locator('small')).toHaveText(`${expected.offense_games.total_yards}/2 games`)
    await expect(row.getByRole('cell').nth(2).locator('span')).toHaveText(String(expected.offense.points_scored))
    const headers = await page.getByRole('columnheader').evaluateAll(es=>es.map(e=>e.getAttribute('aria-label') || e.textContent))
    for (const [label,key] of [['Pass attempts','passing_attempts'],['Completions','passing_completions'],['Rush attempts','rushing_attempts']]) {
      await expect(row.getByRole('cell').nth(headers.indexOf(label)).locator('span')).toHaveText(String(expected.offense[key]))
    }
    for (const [label,key] of [['Completion %','completion_percentage'],['Team passer rating','passer_rating'],['Yards/pass attempt','passing_yards_per_attempt'],['Yards/rush attempt','rushing_yards_per_attempt']]) {
      const value = expected.offense[key]
      await expect(row.getByRole('cell').nth(headers.indexOf(label)).locator('span')).toHaveText(value == null ? '—' : value.toFixed(1)+(key==='completion_percentage'?'%':''))
    }
  }
  const yardsHeader = page.getByRole('columnheader', {name:'Total yards',exact:true})
  await yardsHeader.getByRole('button').focus()
  await page.keyboard.press('Enter')
  await expect(yardsHeader).toHaveAttribute('aria-sort','descending')
  const teamNames = () => page.getByRole('table').locator('tbody tr td:first-child').allTextContents()
  const descending = [...final.view.statistics].sort((a,b)=>b.offense.total_yards-a.offense.total_yards).map(row=>`2026 ${row.name}`)
  expect(await teamNames()).toEqual(descending)
  await page.keyboard.press('Space')
  await expect(yardsHeader).toHaveAttribute('aria-sort','ascending')
  expect(await teamNames()).toEqual([...final.view.statistics].sort((a,b)=>a.offense.total_yards-b.offense.total_yards).map(row=>`2026 ${row.name}`))
  await page.getByLabel(/^View/).selectOption('per_game')
  await page.getByRole('button',{name:'Defense',exact:true}).click()
  for (const expected of final.view.statistics) {
    const row = page.getByRole('row').filter({ hasText: `2026 ${expected.name}` })
    await expect(row.getByRole('cell').nth(3).locator('span')).toHaveText(Number(expected.defense_per_game.total_yards).toFixed(1))
    await expect(row.getByRole('cell').nth(3).locator('small')).toHaveText(`${expected.defense_games.total_yards}/2 games`)
    await expect(row.getByRole('cell').nth(2).locator('span')).toHaveText(Number(expected.defense_per_game.points_scored).toFixed(1))
    const headers = await page.getByRole('columnheader').evaluateAll(es=>es.map(e=>e.getAttribute('aria-label') || e.textContent))
    for (const [label,key] of [['Interceptions','interceptions_thrown'],['Fumble recoveries','fumbles_lost'],['Sacks','sacks']]) {
      await expect(row.getByRole('cell').nth(headers.indexOf(label)).locator('span')).toHaveText(expected.defense_per_game[key].toFixed(1))
    }
  }
  await page.getByRole('button',{name:'Kicking',exact:true}).click()
  await expect(page.getByRole('columnheader', {name:'FG %', exact:true})).toBeVisible()
  for (const expected of final.view.statistics) {
    const row = page.getByRole('row').filter({ hasText: `2026 ${expected.name}` })
    await expect(row.getByRole('cell').nth(2).locator('span')).toHaveText(String(expected.offense.field_goals_made))
    await expect(row.getByRole('cell').nth(3).locator('span')).toHaveText(String(expected.offense.field_goals_attempted))
    await expect(row.getByRole('cell').nth(4).locator('span')).toHaveText(expected.offense.field_goal_percentage == null ? '—' : `${expected.offense.field_goal_percentage.toFixed(1)}%`)
    await expect(row.getByRole('cell').nth(3).locator('small')).toHaveText('2/2 games')
  }
  await page.screenshot({ path: testInfo.outputPath('season-statistics-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await noPageOverflow(page)
  const scroll = page.locator('.season-table')
  const geometry = await scroll.evaluate(element => ({ left: element.getBoundingClientRect().left,
    right: element.getBoundingClientRect().right, client: element.clientWidth, content: element.scrollWidth }))
  expect(geometry.left).toBeGreaterThanOrEqual(0)
  expect(geometry.right).toBeLessThanOrEqual(391)
  expect(geometry.content).toBeGreaterThan(geometry.client)
  await scroll.evaluate(element => { element.scrollLeft = element.scrollWidth })
  expect(await scroll.evaluate(element => element.scrollLeft)).toBeGreaterThan(0)
  await page.screenshot({ path: testInfo.outputPath('season-statistics-phone.png'), fullPage: true })
  await page.getByRole('tab', { name: 'Leaders', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'scoring offense', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'passing offense', exact: true })).toBeVisible()
  await noPageOverflow(page)
  await page.getByRole('tab', { name: 'Schedule', exact: true }).click()
  await page.getByRole('button', { name: 'Seed playoffs', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Play fixture', exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Simulate unplayed games', exact: true }).click()
  await expect(page.getByText('3 of 3 games completed', { exact: false })).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Advance playoffs', exact: true }).click()
  await expect(page.getByText('Season champion', { exact: true })).toBeVisible()
  const champion = await storedCampaign(page, 'Rendered sample season')
  expect(champion.record.campaign.champion_id).toBeTruthy()
  expect(champion.view.standings.reduce((sum, row) => sum + row.played, 0)).toBe(4)
  expect(errors).toEqual([])
})

test('browser-owned campaign and followed team survive closing and restarting Chromium with the same profile', async ({ playwright }, testInfo) => {
  const profile = await mkdtemp(path.join(tmpdir(), 'paydirt-season-acceptance-'))
  let context
  try {
    context = await playwright.chromium.launchPersistentContext(profile, { headless: true, baseURL: frontendURL })
    await context.route(isForeignLoopback, route => route.abort('blockedbyclient'))
    let page = context.pages()[0]
    await openSeasons(page)
    await createCustom(page, 'Browser restart season')
    await page.getByLabel(/^Follow team/).selectOption({ label: '2026 Harbor Bay Ironclads' })
    await expect(page.getByText(/Next for 2026 .*Ironclads/)).toBeVisible()
    const before = await storedCampaign(page, 'Browser restart season')
    const native = await page.request.get(`${frontendURL}/api/library/status`)
    expect(await native.json()).toEqual({ enabled: false })
    const database = await page.evaluate(async () => {
      const databases = await indexedDB.databases()
      return databases.some(item => item.name === 'paydirt-library')
    })
    expect(database).toBe(true)
    await context.close()
    context = await playwright.chromium.launchPersistentContext(profile, { headless: true, baseURL: frontendURL })
    await context.route(isForeignLoopback, route => route.abort('blockedbyclient'))
    page = context.pages()[0]
    await openSeasons(page)
    await expect(page.getByRole('heading', { name: 'Browser restart season', exact: true })).toBeVisible()
    await expect(page.getByLabel(/^Follow team/)).toHaveValue(before.record.campaign.followed_participant_id)
    const after = await storedCampaign(page, 'Browser restart season')
    expect(after.record).toEqual(before.record)
    await page.screenshot({ path: testInfo.outputPath('season-browser-restart.png'), fullPage: true })
  } finally {
    await context?.close()
    await rm(profile, { recursive: true, force: true })
  }
})


test('season Play confirms difficulty and side before creating a resumable game', async ({page}, testInfo) => {
  await openSeasons(page)
  await createCustom(page, 'Pregame acceptance')
  const play = page.getByRole('button', {name:'Play fixture', exact:true}).first()
  await play.click()
  let setup = page.getByRole('dialog', {name:'Game setup'})
  await expect(setup.getByRole('combobox', {name:'Coach',exact:true})).toBeFocused()
  await expect(setup.getByRole('combobox', {name:'Difficulty',exact:true})).toHaveValue('medium')
  await setup.getByRole('button', {name:'Cancel', exact:true}).click()
  await expect(setup).toBeHidden()
  await expect(play).toBeFocused()
  let stored = await storedCampaign(page, 'Pregame acceptance')
  expect(stored.record.campaign.fixtures.every(f=>f.status==='scheduled')).toBe(true)
  await play.click()
  setup = page.getByRole('dialog', {name:'Game setup'})
  await setup.getByRole('combobox', {name:'Coach',exact:true}).selectOption('away')
  await setup.getByRole('combobox', {name:'Difficulty',exact:true}).selectOption('hard')
  await page.setViewportSize({width:390,height:844})
  await noPageOverflow(page)
  await page.screenshot({path:testInfo.outputPath('season-pregame-phone.png'),fullPage:true})
  await setup.getByRole('button', {name:'Start game', exact:true}).click()
  await expect(page.getByTestId('coin-toss')).toBeVisible()
  const game = await page.evaluate(async()=>{
    const {useGameStore}=await import('/src/store/gameStore.js')
    const {gameFetch}=await import('/src/runtime/gameFetch.js')
    const store=useGameStore.getState()
    const response=await gameFetch(`/api/game/state/${store.gameId}`)
    return {difficulty:store.difficulty,phase:store.gamePhase,state:await response.json(), checkpoint:await (await gameFetch(`/api/game/checkpoint/${store.gameId}`,{method:'POST'})).json()}
  })
  expect(game.difficulty).toBe('hard')
  expect(game.phase).toBe('coinToss')
  expect(game.state.human_is_home).toBe(false)
  expect(Object.fromEntries(JSON.parse(game.checkpoint.checkpoint).session.mapping)).toMatchObject({difficulty:'hard',human_is_home:false})
  await page.reload()
  await page.getByRole('button',{name:'SAVED GAMES',exact:true}).click()
  await page.getByRole('button',{name:/Resume Pregame acceptance/}).click()
  await expect(page.getByTestId('coin-toss')).toBeVisible()
  const resumed=await page.evaluate(async()=>{
    const {useGameStore}=await import('/src/store/gameStore.js')
    const {gameFetch}=await import('/src/runtime/gameFetch.js')
    const store=useGameStore.getState()
    return {difficulty:store.difficulty,state:await (await gameFetch(`/api/game/state/${store.gameId}`)).json()}
  })
  expect(resumed.difficulty).toBe('hard')
  expect(resumed.state.human_is_home).toBe(false)

})


test('division standings show NFC beside AFC on desktop and above AFC on phones', async ({page}, testInfo) => {
  await openSeasons(page)
  await createCustom(page, 'Conference layout', ['AFC', 'NFC'])
  await page.getByRole('tab', {name:'Overview', exact:true}).click()
  const nfc = page.getByRole('region', {name:'NFC standings', exact:true})
  const afc = page.getByRole('region', {name:'AFC standings', exact:true})
  await expect(nfc).toBeVisible()
  await expect(afc).toBeVisible()
  const headings = await page.getByRole('heading', {level:2}).allTextContents()
  expect(headings.indexOf('Standings')).toBeLessThan(headings.indexOf('Recent results'))
  const left = await nfc.boundingBox(), right = await afc.boundingBox()
  expect(left.x).toBeLessThan(right.x)
  expect(Math.abs(left.y-right.y)).toBeLessThan(2)
  await page.screenshot({path:testInfo.outputPath('divisions-desktop.png'),fullPage:true})
  await page.setViewportSize({width:390,height:844})
  const top = await nfc.boundingBox(), bottom = await afc.boundingBox()
  expect(top.y + top.height).toBeLessThanOrEqual(bottom.y)
  await noPageOverflow(page)
  await page.screenshot({path:testInfo.outputPath('divisions-phone.png'),fullPage:true})
})


test('team statistics directory uses three aligned columns and focused sortable receiving tables', async ({page}) => {
  await openSeasons(page)
  await createCustom(page, 'Statistics directory sample')
  await page.getByRole('button', {name:'Simulate unplayed games', exact:true}).click()
  await expect(page.getByText('2 of 2 games completed', {exact:false})).toBeVisible({timeout:60_000})
  await page.getByRole('tab', {name:'Team statistics', exact:true}).click()
  const directory=page.getByRole('navigation', {name:'Team statistics categories'})
  await expect(directory.getByRole('button')).toHaveCount(13)
  const overview=page.getByRole('region', {name:'Season leaders at a glance'})
  await expect(overview.getByRole('list')).toHaveCount(5)
  await expect(page.getByRole('columnheader', {name:'Completions',exact:true})).toHaveText('CMP')
  await expect(page.getByRole('columnheader', {name:'Games with stats',exact:true})).toHaveText('GP')
  const layout=await directory.evaluate(e=>({display:getComputedStyle(e).display, boxes:[...e.children].map(c=>({top:c.getBoundingClientRect().top,width:c.getBoundingClientRect().width}))}))
  expect(layout.display).toBe('grid')
  expect(layout.boxes.every(b=>b.width>200 && Math.abs(b.top-layout.boxes[0].top)<1)).toBe(true)
  await directory.getByRole('button', {name:'Offense: Receiving', exact:true}).click()
  await expect(page.getByRole('columnheader', {name:'Receptions', exact:true})).toBeVisible()
  await expect(page.getByRole('columnheader', {name:'Sacks taken', exact:true})).toHaveCount(0)
  await page.getByRole('button', {name:'Receiving yards', exact:true}).click()
  await expect(page.getByRole('columnheader', {name:'Receiving yards', exact:true})).toHaveAttribute('aria-sort','descending')
  await directory.getByRole('button', {name:'Special teams: Punting', exact:true}).click()
  await expect(page.getByRole('columnheader', {name:'Net punt average',exact:true})).toHaveText('NET AVG')
  await expect(page.getByRole('columnheader', {name:'Punts inside 20',exact:true})).toBeVisible()
  await expect(page.getByRole('columnheader', {name:'Opponent punt return average',exact:true})).toHaveText('OPP AVG')
  const recorded=await storedCampaign(page,'Statistics directory sample')
  for(const row of recorded.view.statistics) {
    expect(row.offense_games.punts).toBe(2)
    expect(Number.isInteger(row.offense.longest_punt)).toBe(true)
    expect(row.offense.longest_punt).toBeGreaterThanOrEqual(0)
  }
  for(const [category,headers] of [
    ['Offense: Total yards',['Points scored']],
    ['Offense: Passing',['Longest pass']],
    ['Offense: Rushing',['Rushing TDs','Longest rush','Rushing fumbles']],
    ['Offense: Receiving',['Yards/reception','Longest reception','Receiving fumbles lost']],
    ['Offense: Downs',['Rushing first downs','Third-down conversion %','Fourth-down attempts']],
    ['Defense: Yards allowed',['Points allowed','Rushing TDs allowed']],
    ['Defense: Passing',['Longest pass allowed']],
    ['Defense: Receiving',['Yards/reception allowed']],
    ['Defense: Downs',['Fourth-down conversion % allowed']],
    ['Defense: Turnovers',['Giveaways','Takeaways','Turnover differential']],
    ['Special teams: Kicking',['XP made','XP %','Longest field goal']],
    ['Special teams: Returning',['Kickoff return average','Punt return fair catches']],
  ]) {
    await directory.getByRole('button',{name:category,exact:true}).click()
    for(const name of headers)await expect(page.getByRole('columnheader',{name,exact:true})).toBeVisible()
    if(category==='Defense: Turnovers') {
      await expect(page.getByLabel('View',{exact:true})).toHaveCount(0)
      const labels=await page.getByRole('columnheader').evaluateAll(es=>es.map(e=>e.getAttribute('aria-label')))
      for(const expected of recorded.view.statistics) {
        const row=page.getByRole('row').filter({has:page.getByRole('cell',{name:`${expected.season} ${expected.name}`,exact:true})})
        for(const [label,key] of [['Giveaways','giveaways'],['Takeaways','takeaways'],['Turnover differential','differential']]) {
          const value=expected.turnover_summary[key]
          await expect(row.getByRole('cell').nth(labels.indexOf(label)).locator('span')).toHaveText(value==null?'—':String(value))
        }
      }
    }
    await expect(page.getByText(/not yet recorded|not yet available/)).toHaveCount(0)
  }
  await expect(page.getByRole('table')).toHaveCount(2)
  await page.setViewportSize({width:390,height:844})
  await noPageOverflow(page)
  const boxes=await directory.locator('section').evaluateAll(es=>es.map(e=>({left:e.getBoundingClientRect().left,top:e.getBoundingClientRect().top})))
  expect(boxes[1].left).toBe(boxes[0].left)
  expect(boxes[1].top).toBeGreaterThan(boxes[0].top)
})
