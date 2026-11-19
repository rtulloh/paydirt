import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createEngineObserver } from './engine-observer.mjs';
test('observer bounds diagnostics without losing progress, latest state, catalogs or failures', () => {
 const observer = createEngineObserver();
 const huge = 'x'.repeat(100000);
 observer.reply({status:400,body:{detail:'kept failure'}});
 observer.reply({status:200,body:{teams:[{id:'sample'}]}});
 for(let i=0;i<1000;i++) {
  observer.request({request:{method:'POST',path:'/api/game/restore',body:huge}});
  observer.reply({status:200,body:{game_id:'game',checkpoint:huge,game_state:{quarter:4,home_score:i,play_history:[huge]}}});
 }
 assert.equal(observer.count,1002);
 assert.equal(observer.state.home_score,999);
 assert.equal(observer.state.play_history,undefined);
 assert.equal(observer.gameId,'game');
 assert.deepEqual(observer.teams,[{id:'sample'}]);
 assert.equal(observer.failures.length,1);
 assert.equal(observer.replies.length,40);
 assert.equal(observer.requests.length,40);
 assert(JSON.stringify(observer).length<20000);
});

test('projection leaves genuine replies untouched and observes direct state responses',()=>{
 const observer=createEngineObserver();
 const state={quarter:2,time_remaining:123,play_history:[{description:'canonical'}]};
 observer.reply({status:200,body:state});
 assert.equal(observer.state.quarter,2);
 assert.equal(observer.state.time_remaining,123);
 assert.equal(observer.state.play_history,undefined);
 assert.deepEqual(state.play_history,[{description:'canonical'}]);
 observer.reply({status:200,body:{checkpoint:'opaque'}});
 assert.equal(observer.state.quarter,2);
});
