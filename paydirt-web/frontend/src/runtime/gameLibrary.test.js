import { describe, it, expect } from 'vitest';
import { createGameLibrary, openLibraryDB } from './gameLibrary';
// Small transactional IndexedDB substitute: requests complete asynchronously,
// writes stay provisional until completion, and abort discards the transaction.
function storage() {
 const records = new Map();
 const database = { transaction() {
  const copy=new Map(records);let pending=0,aborted=false;
  const transaction={ error:null, abort(){aborted=true;queueMicrotask(()=>transaction.onabort?.());}, objectStore(){return {
   get(id){return request(()=>copy.get(id));},getAll(){return request(()=>Array.from(copy.values()));},
   put(value){return request(()=>copy.set(value.id,structuredClone(value)));},delete(id){return request(()=>copy.delete(id));}
  };}};
  function finish(){queueMicrotask(()=>{if(!pending&&!aborted){records.clear();for(const [key,value] of copy)records.set(key,value);transaction.oncomplete?.();}})}
  function request(read){pending++;const request={};queueMicrotask(()=>{if(aborted)return;request.result=read();request.onsuccess?.();pending--;finish();});return request;}
  finish();return transaction;
 }};
 return {openDatabase:async()=>database,records};
}
const game={id:'game',name:'My game',checkpoint:'{"full":true}',metadata:{gameId:'engine'}};
describe('durable game library',()=>{
 it('reports unavailable browser storage instead of claiming a save',async()=>{
  const library=createGameLibrary({indexedDB:null});
  await expect(library.put(game,{expectedRevision:0})).rejects.toThrow(/storage|IndexedDB/i);
 });
 it('commits revisions and survives a new library instance',async()=>{
  const store=storage(),first=createGameLibrary(store);
  const saved=await first.put(game,{expectedRevision:0});expect(saved.revision).toBe(1);
  expect(saved.savedAt).toMatch(/^\d{4}-/);
  const second=createGameLibrary(store);expect(await second.get('game')).toEqual(saved);
  expect(await second.list()).toEqual([saved]);
 });
 it('rejects a stale writer without replacing the recoverable checkpoint',async()=>{
  const library=createGameLibrary(storage());
  await library.put(game,{expectedRevision:0});
  await expect(library.put({...game,checkpoint:'{"wrong":true}'},{expectedRevision:0})).rejects.toThrow(/another tab|changed|conflict/i);
  expect((await library.get('game')).checkpoint).toBe(game.checkpoint);
 });
 it('requires an expected revision for replacement and deletion',async()=>{
  const library=createGameLibrary(storage());await library.put(game,{expectedRevision:0});
  await expect(library.put(game)).rejects.toThrow(/revision/i);
  await expect(library.remove('game',{expectedRevision:0})).rejects.toThrow(/another tab|changed|conflict/i);
  await library.remove('game',{expectedRevision:1});expect(await library.get('game')).toBeNull();
 });
 it('rejects malformed records before opening storage',async()=>{
  const library=createGameLibrary({indexedDB:null});
  await expect(library.put({...game,checkpoint:{}},{expectedRevision:0})).rejects.toThrow(/checkpoint/i);
 });
});

describe('IndexedDB connection lifecycle', () => {
 it('creates both stores on upgrade and closes on a version change', async () => {
  const made=[],db={objectStoreNames:{contains:name=>name==='games'},createObjectStore:(...args)=>made.push(args),close:()=>{db.closed=true;}};
  let request;
  const promise=openLibraryDB({indexedDB:{open:()=>{request={result:db};return request;}}});
  request.onupgradeneeded();request.onsuccess();expect(await promise).toBe(db);
  expect(made).toEqual([['campaigns',{keyPath:'id'}]]);
  db.onversionchange();expect(db.closed).toBe(true);
 });
 it('surfaces blocked upgrades and opening failures', async () => {
  let request;const indexedDB={open:()=>{request={};return request;}};
  const blocked=openLibraryDB({indexedDB});request.onblocked();await expect(blocked).rejects.toThrow(/older Paydirt tabs/);
  const failed=openLibraryDB({indexedDB});request.onerror();await expect(failed).rejects.toThrow(/open browser storage/);
 });
});
