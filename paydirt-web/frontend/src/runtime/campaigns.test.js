import {withWriterLease} from './writerLease';
import { expect, it, vi } from 'vitest';
import { createCampaignRepository, campaignRepository, relinkCampaignGame, simulateFixture, correctCampaignResult } from './campaigns';
import { gameFetch } from './gameFetch';
vi.mock('./writerLease',async()=>{const actual=await vi.importActual('./writerLease');return {...actual,withWriterLease:vi.fn(async(keys,action)=>action())}});
vi.mock('./gameFetch',()=>({gameFetch:vi.fn()}));
function storage(){const stores={campaigns:new Map(),games:new Map()};return {stores,openDatabase:async()=>({close(){},transaction(){const copies=Object.fromEntries(Object.entries(stores).map(([k,v])=>[k,new Map(v)]));let pending=0,aborted=false;const tx={abort(){aborted=true;queueMicrotask(()=>tx.onabort?.())},objectStore:name=>({get:id=>req(()=>copies[name].get(id)),getAll:()=>req(()=>[...copies[name].values()]),put:value=>req(()=>copies[name].set(value.id,structuredClone(value))),delete:id=>req(()=>copies[name].delete(id))})};function finish(){queueMicrotask(()=>{if(!pending&&!aborted){for(const name of Object.keys(stores)){stores[name].clear();for(const [k,v] of copies[name])stores[name].set(k,v)}tx.oncomplete?.()}})}function req(fn){pending++;const r={};queueMicrotask(()=>{if(aborted)return;r.result=fn();r.onsuccess?.();pending--;finish()});return r}finish();return tx}})}}
const campaign={id:'c',name:'Test season',participants:[],fixtures:[]};
it('persists independent campaigns with explicit revisions',async()=>{const db=storage(),repo=createCampaignRepository(db);const first=await repo.put(campaign,0);expect(first.revision).toBe(1);await repo.put({...campaign,id:'other'},0);expect((await createCampaignRepository(db).list()).length).toBe(2);await expect(repo.put({...campaign,name:'stale'},0)).rejects.toThrow(/another tab/);expect((await repo.get('c')).campaign.name).toBe('Test season')});
it('commits a fixture checkpoint and campaign together or neither on conflict',async()=>{const db=storage(),repo=createCampaignRepository(db);await repo.put(campaign,0);const game={id:'g',name:'Fixture save',checkpoint:'opaque',metadata:{campaignId:'c'},revision:1,savedAt:'today'};await expect(repo.put(campaign,0,game,0)).rejects.toThrow(/another tab/);expect(db.stores.games.size).toBe(0);await repo.put(campaign,1,game,0);expect(db.stores.games.get('g').checkpoint).toBe('opaque');expect((await repo.get('c')).revision).toBe(2)});

it('rejects malformed game records and impossible revisions without changing either store',async()=>{
 const db=storage(),repo=createCampaignRepository(db);await repo.put(campaign,0);
 const game={id:'g',name:'Fixture',checkpoint:'opaque',metadata:{campaignId:'c'},revision:1,savedAt:'today'};
 await expect(repo.put(campaign,1,{...game,checkpoint:{}},0)).rejects.toThrow(/checkpoint/i);
 await expect(repo.put(campaign,1,game,-1)).rejects.toThrow(/revision/i);
 await expect(repo.put(campaign,1,{...game,revision:4},0)).rejects.toThrow(/revision/i);
 expect((await repo.get('c')).revision).toBe(1);expect(db.stores.games.size).toBe(0);
});
it('exports one consistent campaign snapshot with exactly its live linked checkpoints',async()=>{
 const db=storage(),repo=createCampaignRepository(db),live={...campaign,fixtures:[{id:'fixture',status:'in_progress',game_id:'engine'}]};
 const game={id:'save',name:'Fixture',checkpoint:'opaque 9999999999999999999',metadata:{campaignId:'c',fixtureId:'fixture',gameId:'engine'},revision:1,savedAt:'today'};
 const saved=await repo.put(live,0,game,0);const bundle=await repo.exportBundle(saved);
 expect(bundle).toEqual({format:'paydirt-campaign',version:1,campaign:live,games:[game]});
 await expect(repo.exportBundle({...saved,revision:0})).rejects.toThrow(/changed|reopen/i);
});
it('refuses an incomplete active campaign export rather than lose a live game',async()=>{
 const db=storage(),repo=createCampaignRepository(db),saved=await repo.put({...campaign,fixtures:[{id:'fixture',status:'in_progress',game_id:'missing'}]},0);
 await expect(repo.exportBundle(saved)).rejects.toThrow(/checkpoint|save/i);
});
it('imports a new campaign and all its checkpoints atomically and rejects collisions',async()=>{
 const db=storage(),repo=createCampaignRepository(db),live={...campaign,fixtures:[{id:'fixture',status:'in_progress',game_id:'engine'}]};
 const game={id:'save',name:'Fixture',checkpoint:'opaque',metadata:{campaignId:'c',fixtureId:'fixture',gameId:'engine'},revision:1,savedAt:'today'};
 const saved=await repo.importBundle(live,[game]);expect(saved.revision).toBe(1);expect(db.stores.games.get('save').checkpoint).toBe('opaque');
 const collision={...live,id:'new'};
 await expect(repo.importBundle(collision,[{...game,metadata:{...game.metadata,campaignId:'new'}}])).rejects.toThrow(/already|collision/i);
 expect(await repo.get('new')).toBeNull();expect((await repo.get('c')).revision).toBe(1);
 await expect(repo.importBundle(live,[game])).rejects.toThrow(/already|collision/i);
});

it('opens a restored completed fixture as read-only without rebinding or recording its final again',async()=>{
 const record={id:'save',name:'Final',checkpoint:'opaque',revision:1,metadata:{campaignId:'c',fixtureId:'f',gameId:'original'}};
 const stored={id:'c',revision:3,campaign:{...campaign,fixtures:[{id:'f',status:'completed',game_id:'original'}]}};
 const get=vi.spyOn(campaignRepository,'get').mockResolvedValue(stored),put=vi.spyOn(campaignRepository,'put');
 gameFetch.mockClear();
 try {
  const opened=await relinkCampaignGame(record,{game_id:'restored-runtime',game_state:{game_over:true}});
  expect(opened).toMatchObject({revision:1,metadata:{gameId:'original',readOnlyFinal:true}});
  expect(gameFetch).not.toHaveBeenCalled();expect(put).not.toHaveBeenCalled();
  await expect(relinkCampaignGame(record,{game_id:'restored-runtime',game_state:{game_over:false}})).rejects.toThrow(/accepted final/);
 }finally{get.mockRestore();put.mockRestore();}
});

it('rejects stale campaign actions before calling the engine',async()=>{const record={id:'c',revision:1,campaign};const get=vi.spyOn(campaignRepository,'get').mockResolvedValue({...record,revision:2}),put=vi.spyOn(campaignRepository,'put').mockResolvedValue(record);gameFetch.mockResolvedValue({ok:true,json:async()=>campaign});gameFetch.mockClear();try{await expect(simulateFixture(record,'f')).rejects.toThrow(/changed.*tab/i);expect(gameFetch).not.toHaveBeenCalled();expect(put).not.toHaveBeenCalled()}finally{get.mockRestore();put.mockRestore()}});

it('passes an existing correction lease and sends only engine identity plus accepted revision',async()=>{const record={id:'c',campaign,revision:4},lease={keys:['campaign:c','game:g']};const get=vi.spyOn(campaignRepository,'get').mockResolvedValue(record),put=vi.spyOn(campaignRepository,'put').mockResolvedValue({...record,revision:5});gameFetch.mockResolvedValue({ok:true,json:async()=>campaign});withWriterLease.mockClear();try{await correctCampaignResult(record,'f','restored-runtime',3,lease);expect(withWriterLease).toHaveBeenCalledWith(['campaign:c'],expect.any(Function),lease);expect(JSON.parse(gameFetch.mock.calls.at(-1)[1].body)).toEqual({campaign,fixture_id:'f',game_id:'restored-runtime',expected_result_revision:3});expect(put).toHaveBeenCalledWith(campaign,4)}finally{get.mockRestore();put.mockRestore()}});
