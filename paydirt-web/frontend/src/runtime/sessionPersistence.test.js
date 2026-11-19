import { describe, it, expect, vi } from 'vitest';
import { createSessionPersistence } from './sessionPersistence';
const opaque = '{"rng":999999999999999999999999}';
const engine = () => vi.fn(async () => ({ ok: true, json: async () => ({ checkpoint: opaque }) }));
function library() { const rows = new Map(); return { rows, put: vi.fn(async (record, { expectedRevision }) => {
 const old = rows.get(record.id);if ((old?.revision || 0)!==expectedRevision)throw Error('Changed in another tab');
 const saved = {...record, revision:expectedRevision+1,savedAt:'today'};rows.set(record.id,saved);return saved;
})}; }
describe('session save coordinator',()=>{
 it('captures after a successful new game, keeps opaque text, and increments local revisions',async()=>{
  const fetcher=engine(),store=library(),statuses=[];
  const session=createSessionPersistence({fetcher,library:store,onStatus:status=>statuses.push(status.status)});
  await session.afterMutation('/api/game/new',{}, {game_id:'engine',game_state:{home_team:{name:'Home'},away_team:{name:'Away'}}});
  await session.afterMutation('/api/game/execute',JSON.stringify({game_id:'engine'}),{game_state:{home_score:7}});
  expect(fetcher).toHaveBeenCalledTimes(2);expect(store.rows.get('engine').checkpoint).toBe(opaque);
  expect(store.rows.get('engine').revision).toBe(2);expect(session.getRecord('engine').revision).toBe(2);
  expect(statuses).toEqual(['saving','saved','saving','saved']);
 });
 it('skips checkpoint/restore/replay and non-game operations to prevent recursive export',async()=>{
  const fetcher=engine(),session=createSessionPersistence({fetcher,library:library()});
  for(const path of ['/api/game/checkpoint/x','/api/game/restore','/api/game/save-replay/x','/api/game/load-replay','/api/campaign/new'])await session.afterMutation(path,{game_id:'x'},{game_id:'x'});
  expect(fetcher).not.toHaveBeenCalled();expect(session.getFailure()).toBeNull();
 });
 it('maps a restored engine ID to the original save and revision without replacing its identity',async()=>{
  const store=library(),saved=await store.put({id:'durable',name:'Named game',checkpoint:opaque,metadata:{campaignId:'campaign'}},{expectedRevision:0});
  const session=createSessionPersistence({fetcher:engine(),library:store});session.registerRestored(saved,{game_id:'new-engine'});
  await session.capture('new-engine');expect(store.rows.size).toBe(1);expect(store.rows.get('durable')).toMatchObject({revision:2,metadata:{campaignId:'campaign',gameId:'new-engine'}});
 });
 it('retains the committed checkpoint after a failed write and clears failure only after successful retry',async()=>{
  const store=library(),session=createSessionPersistence({fetcher:engine(),library:store});await session.capture('x');
  store.put.mockRejectedValueOnce(new Error('Disk full'));
  await expect(session.capture('x')).rejects.toThrow('Disk full');expect(session.getFailure().message).toBe('Disk full');
  expect(session.getRecord('x').revision).toBe(1);expect(store.rows.get('x').revision).toBe(1);
  await session.capture('x');expect(session.getFailure()).toBeNull();expect(session.getRecord('x').revision).toBe(2);
 });
 it('serializes concurrent captures and lets an injected commit write game and campaign atomically',async()=>{
  const revisions=[],commit=vi.fn(async(record,{expectedRevision})=>{revisions.push(expectedRevision);return{...record,revision:expectedRevision+1}});
  const session=createSessionPersistence({fetcher:engine(),commit});await Promise.all([session.capture('x'),session.capture('x')]);
  expect(revisions).toEqual([0,1]);expect(commit.mock.calls[0][0].checkpoint).toBe(opaque);
 });
 it('reports engine export failures without claiming a durable save',async()=>{
  const store=library(),session=createSessionPersistence({fetcher:async()=>({ok:false,json:async()=>({detail:'Engine failed'})}),library:store});
  await expect(session.capture('x')).rejects.toThrow('Engine failed');expect(store.put).not.toHaveBeenCalled();expect(session.getFailure()).toBeInstanceOf(Error);
 });
});

it('does not clear another session’s failed write when a different game saves',async()=>{
 const store=library(),session=createSessionPersistence({fetcher:engine(),library:store});
 store.put.mockRejectedValueOnce(new Error('Quota exceeded'));
 await expect(session.capture('failed-game')).rejects.toThrow('Quota exceeded');
 await session.capture('other-game');expect(session.getFailure()?.gameId).toBe('failed-game');
 await session.capture('failed-game');expect(session.getFailure()).toBeNull();
});

it('clears a failed session only after explicit restore of the same durable save',async()=>{
 const store=library(),session=createSessionPersistence({fetcher:engine(),library:store});
 await session.capture('original-engine');const durable=session.getRecord('original-engine');
 store.put.mockRejectedValueOnce(new Error('Storage full'));await expect(session.capture('original-engine')).rejects.toThrow();
 session.registerRestored({...durable,id:'unrelated'},{game_id:'other-engine'});
 expect(session.getFailure()?.gameId).toBe('original-engine');
 session.registerRestored(durable,{game_id:'restored-engine'});
 expect(session.getFailure()).toBeNull();expect(session.getRecord('restored-engine').id).toBe(durable.id);
 await session.capture('restored-engine');expect(session.getRecord('restored-engine').revision).toBe(2);
});

it.each([{game_state:{game_over:true,pending_pat:true}}, {game_state:{game_over:true},pending_result:{pending_penalty_decision:true}}, {game_state:{game_over:true},result:{pending_end_zone_interception_return_decision:true}}])('saves an owed obligation without labelling its checkpoint final',async response=>{const store=library(),session=createSessionPersistence({fetcher:engine(),library:store});await session.afterMutation('/api/game/execute',{game_id:'owed'},response);expect(store.rows.get('owed').metadata.gameOver).toBe(false);expect(session.getFailure()).toBeNull()});
it('labels a legal final checkpoint after the owed try resolves',async()=>{const store=library(),session=createSessionPersistence({fetcher:engine(),library:store});await session.afterMutation('/api/game/execute',{game_id:'owed'},{game_state:{game_over:true,pending_pat:true}});await session.afterMutation('/api/game/extra-point',{game_id:'owed'},{game_state:{game_over:true,pending_pat:false}});expect(store.rows.get('owed')).toMatchObject({revision:2,metadata:{gameOver:true}})});

it('preflights saved revisions before a restored runtime is allowed to mutate',async()=>{const record={id:'durable',name:'Save',checkpoint:opaque,revision:2},store={get:vi.fn(async()=>({...record,revision:3})),put:vi.fn()};const session=createSessionPersistence({fetcher:engine(),library:store});session.registerRestored(record,{game_id:'runtime'});await expect(session.assertCurrent('runtime')).rejects.toThrow(/changed.*tab/i);store.get.mockResolvedValue(record);await expect(session.assertCurrent('runtime')).resolves.toBeUndefined();expect(store.get).toHaveBeenCalledWith('durable')});
