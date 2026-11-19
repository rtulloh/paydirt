import {API_BASE} from '../../config';
import {useNativeLibrary} from '../../runtime/useNativeLibrary';
import {withWriterLease,gameWriterKeys,assertSavedRevision} from '../../runtime/writerLease';
import React,{useEffect,useRef,useState} from 'react';
import {gameLibrary} from '../../runtime/gameLibrary';
import {restoreCheckpoint,exportCheckpoint,importCheckpoint} from '../../runtime/checkpoints';
import {gameFetch,registerSavedSession} from '../../runtime/gameFetch';
import {relinkCampaignGame,campaignRepository,exportCampaignFile,correctCampaignResult} from '../../runtime/campaigns';
import {downloadFile} from './SeasonDesk';
export default function SavedGames({onMenu,onResume}){
 const native=useNativeLibrary();
 const [notice,setNotice]=useState('');
 const [records,setRecords]=useState([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[protectionNote,setProtectionNote]=useState(''),[protectedStorage,setProtectedStorage]=useState(false),input=useRef();
 async function load(){setRecords(await gameLibrary.list())}
 useEffect(()=>{load().catch(e=>setError(e.message))},[]);
 async function run(fn){setBusy(true);setError('');setNotice('');try{await fn()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function exportRecord(record) {
  await run(async () => {
   if (record.metadata?.campaignId) {
    const campaign = await campaignRepository.get(record.metadata.campaignId);
    if (!campaign) throw Error('Linked season is missing. Restore its season bundle first.');
    downloadFile(await exportCampaignFile(campaign), 'paydirt-season.json');
   } else downloadFile(exportCheckpoint(record), 'paydirt-game.json');
  });
 }
 async function reviewResult(record) {
  await run(() => withWriterLease(gameWriterKeys(record), async lease => {
   await assertSavedRevision(record, gameLibrary);
   const campaign = await campaignRepository.get(record.metadata.campaignId);
   const fixture = campaign?.campaign.fixtures.find(item => item.id === record.metadata.fixtureId);
   if (!fixture || fixture.status !== 'completed' || fixture.game_id !== record.metadata.gameId) {
    throw new Error('This checkpoint does not match the recorded final. Reopen its season before reviewing.');
   }
   let temporaryGameId;
   try {
    const restored = await restoreCheckpoint(record, gameFetch);
    const originalIds = [record.id, record.metadata.gameId, fixture.game_id];
    if (!restored.game_id || originalIds.includes(restored.game_id)) {
     throw new Error('The engine did not create an independent result preview.');
    }
    temporaryGameId = restored.game_id;
    const state = restored.game_state;
    const choice = restored.pending_result;
    if (!state?.game_over || state.pending_pat || choice?.pending_penalty_decision || choice?.pending_end_zone_interception_return_decision) {
     throw new Error('This checkpoint still owes an engine decision and cannot replace a recorded final.');
    }
    const home = state.home_team?.name || 'Home';
    const away = state.away_team?.name || 'Away';
    const confirmed = window.confirm(
     `Review recorded revision ${fixture.result.revision}: ${home} ${fixture.result.home_score} – ${away} ${fixture.result.away_score}\n` +
     `Checkpoint final: ${home} ${state.home_score} – ${away} ${state.away_score}\n\n` +
     'Replace the recorded result with this checkpoint final? Team statistics come from the actual engine checkpoint. Earlier result revisions are retained. Results are frozen after playoff seeding.'
    );
    if (!confirmed) return;
    await correctCampaignResult(campaign, fixture.id, restored.game_id, fixture.result.revision, lease);
    await load();
    setNotice('Recorded result reviewed from the checkpoint. Earlier revisions are retained when a result changes.');
   } finally {
    if (temporaryGameId) {
     // This preview is never registered as a playable session or saved over the final.
     try { await gameFetch(`${API_BASE}/api/game/${encodeURIComponent(temporaryGameId)}`, { method: 'DELETE' }); } catch { /* Preserve the original correction error if cleanup transport fails. */ }
    }
   }
  }));
 }
 async function resume(record){await run(()=>withWriterLease(gameWriterKeys(record),async lease=>{await assertSavedRevision(record,gameLibrary);const response=await restoreCheckpoint(record,gameFetch);const updated=await relinkCampaignGame(record,response,lease);registerSavedSession(updated,response);onResume(response,updated.metadata)}))}
 return <div className="season-desk"><header><b className="season-brand">PAYDIRT.</b><button onClick={onMenu}>Menu</button></header><main><div className="season-row"><div><small className="season-eyebrow">Ready when you are</small><h1>Saved games</h1><p>Exhibitions and season fixtures, saved {native===true?'in this application':native===false?'in this browser':'locally'}.</p></div><button disabled={busy} onClick={()=>input.current.click()}>Import saved game</button></div>
 {error&&<div className="season-error" role="alert">{error}</div>}{busy&&<p role="status">Working…</p>}{notice&&<p role="status">{notice}</p>}
 <input hidden ref={input} type="file" accept="application/json" onChange={e=>{const file=e.target.files[0];if(file)run(async()=>{if(file.size>20*1024*1024)throw Error('Saved game file is too large.');const record=importCheckpoint(await file.text());if(record.metadata?.campaignId)throw Error('Import the complete season bundle from Seasons to preserve fixture linkage.');await gameLibrary.put(record,{expectedRevision:0});await load()});e.target.value=''}}/>
 {!records.length&&!error&&<section className="season-card"><h2>No saved games yet</h2><p>A game is saved automatically after each acknowledged action. You can also use Save Game.</p></section>}
 {records.map(r=><section className="season-card" key={r.id}><div className="season-row"><div><h2>{r.name}</h2><p>{r.metadata?.campaignId?'Season fixture':'Exhibition'} · {r.savedAt?new Date(r.savedAt).toLocaleString():'Imported save'}</p><small>{r.metadata?.homeTeam?.season} {r.metadata?.homeTeam?.name} vs {r.metadata?.awayTeam?.season} {r.metadata?.awayTeam?.name}</small></div><div className="season-actions"><button className="season-primary" disabled={busy} aria-label={`Resume ${r.name}`} onClick={()=>resume(r)}>{r.metadata?.gameOver?'View final':'Resume'}</button>{r.metadata?.gameOver&&r.metadata?.campaignId&&<button disabled={busy} onClick={()=>reviewResult(r)}>Review recorded result</button>}<button disabled={busy} onClick={()=>exportRecord(r)}>Export</button><button disabled={busy} onClick={()=>{const name=window.prompt('Save name',r.name);if(name?.trim())run(()=>withWriterLease(gameWriterKeys(r),async()=>{await assertSavedRevision(r,gameLibrary);await gameLibrary.put({...r,name:name.trim()},{expectedRevision:r.revision});await load()}))}}>Rename</button><button disabled={busy} onClick={()=>{if(window.confirm('Delete this saved game? Export a copy first if you want to keep it.'))run(()=>withWriterLease(gameWriterKeys(r),async()=>{await assertSavedRevision(r,gameLibrary);if(r.metadata?.campaignId)throw Error('Keep this linked fixture save, or delete its campaign from Seasons.');await gameLibrary.remove(r.id,{expectedRevision:r.revision});await load()}))}}>Delete</button></div></div></section>)}
 <footer>
 {native===false&&typeof navigator.storage?.persist==='function'&&!protectedStorage&&<button disabled={busy} onClick={()=>run(async()=>{const granted=await navigator.storage.persist();setProtectedStorage(granted);setProtectionNote(granted?'Browser protection is enabled. Clearing site data still deletes local saves.':'Browser protection was not granted. Export backups to keep another copy.');})}>Protect local saves</button>}
 {protectionNote&&<p role="status">{protectionNote}</p>}
 <p>{native===true?'Saved in this application’s local data. Export files for backup and transfer.':native===false?'Clearing browser site data removes local saves. Export files for backup and transfer.':'Saved locally. Export files for backup and transfer.'} Engine and chart compatibility is checked on restore.</p></footer></main></div>
}
