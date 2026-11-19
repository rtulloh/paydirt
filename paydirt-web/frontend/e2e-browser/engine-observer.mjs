// Bounded observations only; recovery tests separately assert exact history.
export function createEngineObserver() {
 const push=(items,value)=>{items.push(value);if(items.length>40)items.shift();};
 const observer={count:0,replies:[],requests:[],failures:[],state:null,teams:null,gameId:null,
 request(value){const request=value.request||value;push(this.requests,{method:request.method,path:request.path});},
 reply(value){
  this.count++;const body=value.body||{};
  const source=body.game_state||(body.quarter?body:null);
  if(source){const {play_history,...state}=source;this.state=state;}
  if(body.teams)this.teams=body.teams;
  if(body.game_id)this.gameId=body.game_id;
  const projected={status:value.status,body:{...(source?{game_state:this.state}:{}),...(body.game_id?{game_id:body.game_id}:{}),...(body.teams?{teams:body.teams}:{}),...(body.detail!==undefined?{detail:body.detail}:{}),...(body.error!==undefined?{error:body.error}:{})}};
  push(this.replies,projected);if(value.status>=400)this.failures.push(projected);
 }};
 if(typeof window!=='undefined')window.__engineObserver=observer;
 return observer;
}
