import { test, expect } from './fixtures.js'
import { backendURL } from './ports.js'
import { findEnabledPenaltyChoice } from '../e2e-browser/penalty-choice.js'

// Synthetic situations are created only by the isolated E2E service. Checkpoint,
// restore, engine decisions and all recovery controls use the real product code.
async function recover(page, request, kind, entry = 'SAVED GAMES') {
  const created = await request.post(`${backendURL}/api/game/new`, { data: {
    season: '2026', player_team: 'Ironclads', opponent_team: 'Thunderhawks',
    play_as_home: true, player_end_zone_interception_policy: 'ask',
  } })
  expect(created.ok()).toBe(true)
  const initial = await created.json()
  const configured = await request.post(`${backendURL}/api/test/checkpoint-fixture`, {
    data: { game_id: initial.game_id, kind },
  })
  expect(configured.ok(), await configured.text()).toBe(true)
  const checkpointResponse = await request.post(`${backendURL}/api/game/checkpoint/${initial.game_id}`)
  expect(checkpointResponse.ok(), await checkpointResponse.text()).toBe(true)
  const { checkpoint } = await checkpointResponse.json()
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'SAVED GAMES', exact: true })).toBeVisible()
  await page.evaluate(async ({ checkpoint, id, kind, entry }) => {
    if (entry === 'LOAD GAME') localStorage.setItem('paydirt_save', JSON.stringify({gameId:'obsolete-session',ballPosition:20}))
    const { gameLibrary } = await import('/src/runtime/gameLibrary.js')
    await gameLibrary.put({ id, checkpoint, name: `Recovery ${kind}`, metadata: {
      gameId: id, phase: kind === 'halftime' ? 'halftime' : 'playing', gameOver: false,
    } }, { expectedRevision: 0 })
  }, { checkpoint, id: initial.game_id, kind, entry })
  expect((await request.delete(`${backendURL}/api/game/${initial.game_id}`)).ok()).toBe(true)
  expect((await request.get(`${backendURL}/api/game/state/${initial.game_id}`)).status()).toBe(404)
  await page.reload()
  await page.getByRole('button', { name: entry, exact: true }).click()
  const restoring = page.waitForResponse(r => r.url().endsWith('/api/game/restore'))
  await page.getByRole('button', { name: `Resume Recovery ${kind}`, exact: true }).click()
  const restored = await (await restoring).json()
  expect(restored.game_id).not.toBe(initial.game_id)
  return restored
}

for (const kind of ['penalty', 'interception']) {
  test(`restored ${kind} waits for exactly one rendered coaching decision`, async ({ page, request }) => {
    const mutations = []
    page.on('request', req => {
      if (req.method() === 'POST' && /\/api\/game\/(execute|extra-point|kickoff|penalty-decision|end-zone-interception-decision)$/.test(req.url())) mutations.push(req.url())
    })
    const restored = await recover(page, request, kind)
    expect(restored.pending_result[kind === 'penalty' ? 'pending_penalty_decision' : 'pending_end_zone_interception_return_decision']).toBe(true)
    if (kind === 'penalty') await expect(page.getByText('PENALTY ON THE PLAY!', { exact: true })).toBeVisible()
    else await expect(page.getByRole('button', { name: 'TAKE TOUCHBACK', exact: true })).toBeVisible()
    expect(mutations).toEqual([])
    await expect(page.getByTestId('game-over')).toHaveCount(0)
    const path = kind === 'penalty' ? 'penalty-decision' : 'end-zone-interception-decision'
    const deciding = page.waitForResponse(r => r.url().endsWith(`/api/game/${path}`))
    const button = kind === 'penalty' ? await findEnabledPenaltyChoice(page) : page.getByRole('button', { name: 'TAKE TOUCHBACK', exact: true })
    expect(button).toBeTruthy()
    await button.click()
    expect((await deciding).ok()).toBe(true)
    if (kind === 'penalty') await expect(page.getByText('PENALTY ON THE PLAY!', { exact: true })).toHaveCount(0)
    else await expect(page.getByRole('button', { name: 'TAKE TOUCHBACK', exact: true })).toHaveCount(0)
    expect(mutations).toHaveLength(1)
    const final = await (await request.get(`${backendURL}/api/game/state/${restored.game_id}`)).json()
    expect(final.game_over).toBe(false)
  })
}

test('restored halftime continues once into the engine-owned second-half kickoff', async ({ page, request }) => {
  const restored = await recover(page, request, 'halftime')
  expect(restored.game_state).toMatchObject({ halftime_pending: true, quarter: 3, time_remaining: 900 })
  await expect(page.getByTestId('halftime')).toHaveCount(1)
  await page.getByTestId('continue-button').click()
  await expect(page.getByTestId('halftime')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'KICK OFF', exact: true })).toBeVisible()
  const kicking = page.waitForResponse(r => r.url().endsWith('/api/game/kickoff'))
  await page.getByRole('button', { name: 'KICK OFF', exact: true }).click()
  const result = await (await kicking).json()
  expect(result.game_state.quarter).toBe(3)
  expect(result.game_state.time_remaining).toBeGreaterThan(0)
  expect(result.game_state.halftime_pending).toBe(false)
  await expect(page.getByTestId('halftime')).toHaveCount(0)
})

test('restored expired touchdown owes one try before the final screen', async ({ page, request }) => {
  const restored = await recover(page, request, 'expired-try')
  expect(restored.game_state).toMatchObject({ game_over: true, pending_pat: true, quarter: 4 })
  await expect(page.getByTestId('game-over')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeVisible()
  const tries = []
  page.on('request', req => { if (req.method() === 'POST' && req.url().endsWith('/api/game/extra-point')) tries.push(req.url()) })
  const trying = page.waitForResponse(r => r.url().endsWith('/api/game/extra-point'))
  await page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true }).click()
  const result = await (await trying).json()
  expect(result.game_state).toMatchObject({ game_over: true, pending_pat: false })
  await expect(page.getByTestId('game-over')).toBeVisible()
  expect(tries).toHaveLength(1)
  await expect(page.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toHaveCount(0)
})


test('post-punt checkpoint saves and resumes with a responsive receiving offense', async ({page, request}) => {
  const legacyRequests = []
  page.on('request',r=>{if(r.url().includes('/api/game/load-replay'))legacyRequests.push(r.url())})
  const restored = await recover(page, request, 'post-punt', 'LOAD GAME')
  expect(restored.game_state).toMatchObject({player_offense:true,down:1,is_kickoff:false})
  const play = page.getByTestId('offense-play-1')
  await expect(play).toBeEnabled()
  const executed = page.waitForResponse(r=>r.url().endsWith('/api/game/execute'))
  await play.click()
  expect((await executed).ok()).toBe(true)
  await expect(page.getByRole('button',{name:'SAVE GAME',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'SAVE GAME',exact:true}).click()
  await expect(page.getByText('Game saved locally.',{exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(legacyRequests).toEqual([])
})


test('field-goal penalty checkpoint resumes, accepts the foul, and saves its result',async({page,request})=>{
  const restored=await recover(page,request,'field-goal-penalty')
  expect(restored.pending_result.pending_penalty_decision).toBe(true)
  await expect(page.getByText('PENALTY ON THE PLAY!',{exact:true})).toBeVisible()
  const accepting=page.waitForResponse(r=>r.url().endsWith('/api/game/penalty-decision'))
  await page.getByRole('button',{name:/Synthetic FG foul/}).click()
  const accepted=await accepting
  expect(accepted.ok(),await accepted.text()).toBe(true)
  const data=await accepted.json()
  expect(data.result.pending_penalty_decision).toBe(false)
  expect(data.game_state.down).toBe(2)
  expect(data.game_state.yards_to_go).toBe(15)
  await expect(page.getByText('PENALTY ON THE PLAY!',{exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'SAVE GAME',exact:true}).click()
  await expect(page.getByText('Game saved locally.',{exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})


test('season final after a resolved penalty saves one result without a phantom choice',async({page})=>{
  await page.goto('/')
  await expect(page.getByRole('button',{name:'SEASONS',exact:true})).toBeVisible()
  const id=await page.evaluate(async()=>{
    const api=await import('/src/runtime/campaigns.js')
    const {gameFetch}=await import('/src/runtime/gameFetch.js')
    const {useGameStore}=await import('/src/store/gameStore.js')
    const record=await api.createCampaign({name:'Penalty final acceptance',rules_season:'2026',schedule:'single_round_robin',
      participants:[{season:'2026',team_id:'Ironclads'},{season:'2026',team_id:'Thunderhawks'}]})
    const started=await api.startCampaignGame(record,record.campaign.fixtures[0].id,{human_is_home:true})
    const response=await gameFetch('/api/test/checkpoint-fixture',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({game_id:started.game_id,kind:'penalty-final'})})
    if(!response.ok)throw Error(await response.text())
    const configured=await response.json()
    useGameStore.getState().restoreSession({...started,game_state:configured.game_state,game_phase:'playing',
      pending_result:configured.pending_result})
    return record.id
  })
  await expect(page.getByText('PENALTY ON THE PLAY!',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:/^\[1\]/}).click()
  await expect(page.getByTestId('game-over')).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  const final=await page.evaluate(async campaignId=>{
    const api=await import('/src/runtime/campaigns.js')
    const records=await api.listCampaigns(),record=records.find(r=>r.id===campaignId)
    return {campaign:record.campaign,view:await api.viewCampaign(record.campaign)}
  },id)
  expect(final.campaign.fixtures[0].status).toBe('completed')
  expect(final.campaign.fixtures[0].result).toMatchObject({home_score:21,away_score:20,revision:1})
  expect(final.view.standings.map(r=>r.played)).toEqual([1,1])
  await page.reload()
  await page.getByRole('button',{name:'SEASONS',exact:true}).click()
  await page.getByRole('tab',{name:'Schedule',exact:true}).click()
  await expect(page.getByText('20–21 · played',{exact:true})).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})
