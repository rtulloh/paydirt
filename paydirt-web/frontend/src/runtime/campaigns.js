import { withWriterLease, assertSavedRevision } from './writerLease';
import { API_BASE } from '../config';
import { gameFetch } from './gameFetch';
import { openLibraryDB, validateGameRecord } from './gameLibrary';
import { routeRepository } from './nativeLibrary';

function campaignIdentity(campaign) {
  if (!campaign || typeof campaign.id !== 'string' || !campaign.id) throw new Error('Invalid season identity.');
}
function gameRevision(record, expectedRevision) {
  validateGameRecord(record);
  if (!Number.isInteger(expectedRevision) || expectedRevision < 0 || record.revision !== expectedRevision + 1) throw new Error('Invalid saved game revision.');
  if (typeof record.savedAt !== 'string' || !record.savedAt) throw new Error('Saved game needs a save timestamp.');
}
function bundleLinks(campaign, games) {
  campaignIdentity(campaign);
  if (!Array.isArray(games)) throw new Error('Invalid season game bundle.');
  const fixtures = (campaign.fixtures || []).filter(fixture => fixture.status === 'in_progress');
  if (games.length !== fixtures.length) throw new Error('Every in-progress fixture needs exactly one saved checkpoint.');
  const seen = new Set();
  for (const record of games) {
    validateGameRecord(record);
    if (seen.has(record.id)) throw new Error('Duplicate saved game identity in season bundle.');
    seen.add(record.id);
    if (record.metadata?.campaignId !== campaign.id) throw new Error('Saved checkpoint belongs to another season.');
    const matches = fixtures.filter(fixture => fixture.id === record.metadata.fixtureId && fixture.game_id === record.metadata.gameId);
    if (matches.length !== 1) throw new Error('Saved checkpoint does not match an in-progress fixture.');
  }
  for (const fixture of fixtures) {
    if (games.filter(record => record.metadata.fixtureId === fixture.id).length !== 1) throw new Error('A fixture has missing or duplicate saved checkpoints.');
  }
}

export function createCampaignRepository({ openDatabase = openLibraryDB } = {}) {
  async function transact(mode, work) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      let result, error;
      const tx = db.transaction(['campaigns', 'games'], mode);
      const fail = failure => { error = failure; tx.abort(); };
      tx.oncomplete = () => { db.close(); resolve(result); };
      tx.onabort = tx.onerror = () => { db.close(); reject(error || tx.error || new Error('Season storage failed. The previous save was retained.')); };
      try { work(tx, value => { result = value; }, fail); } catch (failure) { fail(failure); }
    });
  }
  return {
    list: () => transact('readonly', (tx, done) => {
      const request = tx.objectStore('campaigns').getAll();
      request.onsuccess = () => done(request.result.sort((a, b) => b.savedAt.localeCompare(a.savedAt)));
    }),
    get: id => transact('readonly', (tx, done) => {
      const request = tx.objectStore('campaigns').get(id);
      request.onsuccess = () => done(request.result || null);
    }),
    put: async (campaign, expectedRevision, gameRecord, expectedGameRevision) => {
      campaignIdentity(campaign);
      if (!Number.isInteger(expectedRevision) || expectedRevision < 0) throw new Error('Invalid season revision.');
      if (gameRecord) gameRevision(gameRecord, expectedGameRevision);
      return transact('readwrite', (tx, done, fail) => {
        const store = tx.objectStore('campaigns'), request = store.get(campaign.id);
        request.onsuccess = () => {
          if ((request.result?.revision || 0) !== expectedRevision) return fail(new Error('This season changed in another tab. Reopen it before continuing.'));
          const value = { id: campaign.id, campaign, revision: expectedRevision + 1, savedAt: new Date().toISOString() };
          const write = () => { store.put(value); done(value); };
          if (!gameRecord) return write();
          const games = tx.objectStore('games'), gameRequest = games.get(gameRecord.id);
          gameRequest.onsuccess = () => {
            if ((gameRequest.result?.revision || 0) !== expectedGameRevision) return fail(new Error('This game changed in another tab. Reopen it before continuing.'));
            games.put(gameRecord); write();
          };
        };
      });
    },
    exportBundle: record => transact('readonly', (tx, done, fail) => {
      const request = tx.objectStore('campaigns').get(record.id);
      request.onsuccess = () => {
        if (!request.result || request.result.revision !== record.revision) return fail(new Error('This season changed. Reopen it before exporting.'));
        const campaign = request.result.campaign;
        const gamesRequest = tx.objectStore('games').getAll();
        gamesRequest.onsuccess = () => {
          try {
            const games = gamesRequest.result.filter(game => game.metadata?.campaignId === campaign.id
              && campaign.fixtures.some(fixture => fixture.status === 'in_progress' && fixture.id === game.metadata.fixtureId && fixture.game_id === game.metadata.gameId));
            bundleLinks(campaign, games);
            done({ format: 'paydirt-campaign', version: 1, campaign, games });
          } catch (error) { fail(error); }
        };
      };
    }),
    importBundle: async (campaign, games) => {
      bundleLinks(campaign, games);
      games.forEach(game => gameRevision(game, 0));
      return transact('readwrite', (tx, done, fail) => {
        const store = tx.objectStore('campaigns'), gameStore = tx.objectStore('games');
        const request = store.get(campaign.id);
        request.onsuccess = () => {
          if (request.result) return fail(new Error('Imported season identity already exists; nothing was replaced.'));
          let remaining = games.length;
          const write = () => {
            const value = { id: campaign.id, campaign, revision: 1, savedAt: new Date().toISOString() };
            store.put(value); games.forEach(game => gameStore.put(game)); done(value);
          };
          if (!remaining) return write();
          for (const game of games) {
            const gameRequest = gameStore.get(game.id);
            gameRequest.onsuccess = () => {
              if (gameRequest.result) return fail(new Error('Imported saved game identity already exists; nothing was replaced.'));
              remaining -= 1;
              if (!remaining) write();
            };
          }
        };
      });
    },
    remove: record => transact('readwrite', (tx, done, fail) => {
      const store = tx.objectStore('campaigns'), request = store.get(record.id);
      request.onsuccess = () => {
        if (request.result?.revision !== record.revision) return fail(new Error('This season changed in another tab. Reopen it before continuing.'));
        store.delete(record.id);
        const games = tx.objectStore('games'), gamesRequest = games.getAll();
        gamesRequest.onsuccess = () => { for (const item of gamesRequest.result) if (item.metadata?.campaignId === record.id) games.delete(item.id); done(); };
      };
    }),
  };
}
export const campaignRepository = routeRepository('campaigns', createCampaignRepository());
const active = new Map();
export async function campaignCommand(path, body, fetcher=gameFetch) {
 const response=await fetcher(`${API_BASE}/api/campaign/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'The season command failed.');return data;
}
export async function listCampaigns(){const records=await campaignRepository.list();records.forEach(r=>active.set(r.id,r));return records;}
export async function saveCampaign(campaign, revision=0){
 return withWriterLease([`campaign:${campaign.id}`],async()=>{
  const current=await campaignRepository.get(campaign.id);
  if((current?.revision||0)!==revision)throw new Error('This season changed in another tab. Reopen it before continuing.');
  const r=await campaignRepository.put(campaign,revision);active.set(r.id,r);return r;
 });
}
export async function getCampaignTemplates(){const r=await gameFetch(`${API_BASE}/api/campaign/templates`);if(!r.ok)throw new Error('Could not load historical templates.');return (await r.json()).templates;}
export async function viewCampaign(campaign){return campaignCommand('view',{campaign});}
export async function createCampaign(spec){return saveCampaign(await campaignCommand('create',spec));}
export async function importCampaignFile(text) {
 const bundle = await campaignCommand('import', { text });
 const saved = await campaignRepository.importBundle(bundle.campaign, bundle.games);
 active.set(saved.id, saved);
 return saved;
}
export async function exportCampaignFile(record) {
 return JSON.stringify(await campaignRepository.exportBundle(record), null, 2);
}
export async function assertActiveCampaignCurrent(id) {
 const record=active.get(id);
 if(!record)throw new Error('Reopen this season before changing its game.');
 await assertSavedRevision(record,campaignRepository);
}
export async function withCampaignWriter(record, action, lease) {
 return withWriterLease([`campaign:${record.id}`], async owned => {
  await assertSavedRevision(record, campaignRepository);
  return action(owned);
 }, lease);
}
export async function removeCampaign(record){return withCampaignWriter(record,async()=>{await campaignRepository.remove(record);active.delete(record.id);});}
export async function startCampaignGame(record,fixtureId,options={}){
 return withCampaignWriter(record, async () => {
 const data=await campaignCommand('start',{campaign:record.campaign,fixture_id:fixtureId,...options});
 const response=await gameFetch(`${API_BASE}/api/game/checkpoint/${encodeURIComponent(data.game_id)}`,{method:'POST'}),body=await response.json();
 if(!response.ok)throw new Error(body.detail||'Could not checkpoint the new fixture.');
 const gameRecord={id:data.game_id,name:`${record.campaign.name} · Week ${data.campaign.fixtures.find(f=>f.id===fixtureId).week}`,checkpoint:body.checkpoint,revision:1,savedAt:new Date().toISOString(),metadata:{phase:data.game_phase||'coinToss',gameId:data.game_id,campaignId:record.id,fixtureId,homeTeam:data.game_state.home_team,awayTeam:data.game_state.away_team}};
 const updated=await campaignRepository.put(data.campaign,record.revision,gameRecord,0);active.set(updated.id,updated);
 const {registerSavedSession}=await import('./gameFetch');registerSavedSession(gameRecord,data);
 return {...data,campaignRecord:updated};
 });
}
export async function commitCampaignCheckpoint(record,{expectedRevision},fetcher){
 const id=record.metadata?.campaignId;if(!id)return null;
 const current=active.get(id);if(!current)throw new Error('Reopen this season before saving its game.');
 let campaign=current.campaign;
 if(record.metadata?.gameOver)campaign=await campaignCommand('complete',{campaign,fixture_id:record.metadata.fixtureId,game_id:record.metadata.gameId},fetcher);
 const gameRecord={...record,revision:expectedRevision+1,savedAt:new Date().toISOString()};
 const saved=await campaignRepository.put(campaign,current.revision,gameRecord,expectedRevision);active.set(id,saved);return gameRecord;
}
export async function relinkCampaignGame(record,response,lease){
 const id=record.metadata?.campaignId;if(!id)return record;
 const current=await campaignRepository.get(id);if(!current)throw new Error('Import the linked season before resuming this game.');
 return withCampaignWriter(current, async () => {
 const fixture = current.campaign.fixtures.find(item => item.id === record.metadata.fixtureId);
 if (fixture?.status === 'completed') {
   if (fixture.game_id !== record.metadata.gameId || !response.game_state?.game_over) throw new Error('This save does not match the accepted final.');
   // Viewing a final never changes its canonical result or stored engine identity.
   active.set(id, current);
   return { ...record, metadata: { ...record.metadata, readOnlyFinal: true } };
 }
 const campaign=await campaignCommand('resume',{campaign:current.campaign,fixture_id:record.metadata.fixtureId,old_game_id:record.metadata.gameId,new_game_id:response.game_id});
 const updatedGame={...record,metadata:{...record.metadata,gameId:response.game_id},revision:record.revision+1,savedAt:new Date().toISOString()};
 const saved=await campaignRepository.put(campaign,current.revision,updatedGame,record.revision);active.set(id,saved);return updatedGame;
 }, lease);
}
async function updateCampaign(record, path, fields = {}, lease) {
 return withCampaignWriter(record, async () => {
  const campaign = await campaignCommand(path, { campaign: record.campaign, ...fields });
  const saved = await campaignRepository.put(campaign, record.revision);
  active.set(saved.id, saved);
  return saved;
 }, lease);
}
export function simulateFixture(record,fixtureId){return updateCampaign(record,'simulate',{fixture_id:fixtureId});}
export function advancePostseason(record,size){return updateCampaign(record,'postseason',{size});}
export function editCampaignSchedule(record,fixtures){return updateCampaign(record,'definition',{fixtures});}
export function correctCampaignResult(record,fixtureId,gameId,expectedResultRevision,lease){return updateCampaign(record,'correct',{fixture_id:fixtureId,game_id:gameId,expected_result_revision:expectedResultRevision},lease);}
export function duplicateCampaign(record,name){return withCampaignWriter(record,async()=>saveCampaign(await campaignCommand('duplicate',{campaign:record.campaign,name}),0));}
