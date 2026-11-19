import { describe, it, expect, vi } from 'vitest';
import { createLibraryTransport, routeRepository } from './nativeLibrary';

const response = (body, status=200) => ({ok:status>=200&&status<300,status,json:async()=>body});
describe('explicit native library capability',()=>{
 it('keeps browser builds entirely in IndexedDB',async()=>{
  const fetcher=vi.fn(), local={list:vi.fn(async()=>['local'])};
  const repo=routeRepository('games',local,createLibraryTransport({browser:true,fetcher}));
  expect(await repo.list()).toEqual(['local']);expect(fetcher).not.toHaveBeenCalled();
 });
 it('uses local storage only when the server explicitly disables native storage',async()=>{
  for(const status of [200,404]){
   const fetcher=vi.fn(async()=>response({enabled:false},status));
   const repo=routeRepository('games',{get:async id=>id},createLibraryTransport({fetcher}));
   expect(await repo.get('x')).toBe('x');expect(await repo.get('y')).toBe('y');expect(fetcher).toHaveBeenCalledTimes(1);
  }
 });
 it('forwards CAS and atomic campaign writes as one native command',async()=>{
  const calls=[],fetcher=vi.fn(async(url,options)=>{
   if(!options)return response({enabled:true});
   calls.push(JSON.parse(options.body));return response({revision:3});
  });
  const transport=createLibraryTransport({fetcher}),local={put:vi.fn()};
  const games=routeRepository('games',local,transport),campaigns=routeRepository('campaigns',local,transport);
  await games.put({id:'g'},{expectedRevision:2});
  await campaigns.put({id:'c'},2,{id:'g',revision:4},3);
  await campaigns.importBundle({id:'import'},[{id:'checkpoint'}]);
  expect(calls).toEqual([
   {store:'games',action:'put',record:{id:'g'},expectedRevision:2},
   {store:'campaigns',action:'put',campaign:{id:'c'},expectedRevision:2,gameRecord:{id:'g',revision:4},expectedGameRevision:3},
   {store:'campaigns',action:'importBundle',campaign:{id:'import'},games:[{id:'checkpoint'}]},
  ]);expect(local.put).not.toHaveBeenCalled();
 });
 it('never forks into browser storage after native errors or capability failures',async()=>{
  const local={put:vi.fn()},fetcher=vi.fn().mockResolvedValueOnce(response({enabled:true})).mockResolvedValue(response({detail:'Revision conflict'},409));
  const repo=routeRepository('games',local,createLibraryTransport({fetcher}));
  await expect(repo.put({id:'g'},{expectedRevision:0})).rejects.toThrow('Revision conflict');expect(local.put).not.toHaveBeenCalled();
  const unavailable=routeRepository('games',local,createLibraryTransport({fetcher:async()=>response({},503)}));
  await expect(unavailable.put({},{})).rejects.toThrow(/storage capability/i);expect(local.put).not.toHaveBeenCalled();
 });
 it('preserves get/list/remove/export argument contracts',async()=>{
  const calls=[],fetcher=async(url,options)=>options?(calls.push(JSON.parse(options.body)),response(null)):response({enabled:true});
  const t=createLibraryTransport({fetcher}),g=routeRepository('games',{},t),c=routeRepository('campaigns',{},t);
  await g.list();await g.get('g');await g.remove('g',{expectedRevision:7});await c.exportBundle({id:'c',revision:2});await c.remove({id:'c',revision:2});
  expect(calls).toEqual([{store:'games',action:'list'},{store:'games',action:'get',id:'g'},{store:'games',action:'remove',id:'g',expectedRevision:7},{store:'campaigns',action:'exportBundle',record:{id:'c',revision:2}},{store:'campaigns',action:'remove',record:{id:'c',revision:2}}]);
 });
 it('rejects ambiguous capability and generic native errors without touching browser data',async()=>{
  const local={list:vi.fn()};
  const malformed=routeRepository('games',local,createLibraryTransport({fetcher:async()=>response({enabled:'true'})}));
  await expect(malformed.list()).rejects.toThrow(/capability response/);
  const native=routeRepository('games',local,createLibraryTransport({fetcher:async(url,options)=>options?response({},500):response({enabled:true})}));
  await expect(native.list()).rejects.toThrow(/previous save was retained/);
  expect(local.list).not.toHaveBeenCalled();
 });
 it('preserves opaque checkpoint bytes without parsing large engine integers',async()=>{
  const checkpoint='{"roll":123456789012345678901234567890}',record={id:'g',checkpoint};
  let received;
  const repo=routeRepository('games',{},createLibraryTransport({fetcher:async(url,options)=>{
   if(!options)return response({enabled:true});received=JSON.parse(options.body).record;return response({...received,revision:1});
  }}));
  expect((await repo.put(record,{expectedRevision:0})).checkpoint).toBe(checkpoint);
  expect(received.checkpoint).toBe(checkpoint);
 });
 it('retries a failed capability probe but keeps enabled native storage after command failure',async()=>{
  const fetcher=vi.fn().mockRejectedValueOnce(new Error('temporarily offline'))
   .mockResolvedValueOnce(response({enabled:true}))
   .mockResolvedValueOnce(response({detail:'Disk busy'},503))
   .mockResolvedValueOnce(response([{id:'durable'}]));
  const local={list:vi.fn()},repo=routeRepository('games',local,createLibraryTransport({fetcher}));
  await expect(repo.list()).rejects.toThrow('temporarily offline');
  await expect(repo.list()).rejects.toThrow('Disk busy');
  expect(await repo.list()).toEqual([{id:'durable'}]);
  expect(fetcher).toHaveBeenCalledTimes(4);expect(local.list).not.toHaveBeenCalled();
 });
});
