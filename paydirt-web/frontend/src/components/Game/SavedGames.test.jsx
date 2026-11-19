import React from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import SavedGames from './SavedGames';
import {libraryTransport} from '../../runtime/nativeLibrary';
import {gameLibrary} from '../../runtime/gameLibrary';
import {gameFetch,registerSavedSession} from '../../runtime/gameFetch';
import {relinkCampaignGame} from '../../runtime/campaigns';
import {downloadFile} from './SeasonDesk';
import {campaignRepository,exportCampaignFile,correctCampaignResult} from '../../runtime/campaigns';
import {importCheckpoint} from '../../runtime/checkpoints';
import {restoreCheckpoint} from '../../runtime/checkpoints';
vi.mock('../../runtime/nativeLibrary',()=>({libraryTransport:{enabled:vi.fn(async()=>false)}}));
vi.mock('../../runtime/gameLibrary',()=>({gameLibrary:{list:vi.fn(),get:vi.fn(),put:vi.fn(),remove:vi.fn()}}));
vi.mock('../../runtime/writerLease',async()=>{const actual=await vi.importActual('../../runtime/writerLease');return {...actual,withWriterLease:vi.fn(async(keys,action)=>action({keys}))}});
beforeEach(()=>{libraryTransport.enabled.mockResolvedValue(false);gameLibrary.get.mockImplementation(async id=>(await gameLibrary.list()).find(row=>row.id===id));vi.clearAllMocks()});
vi.mock('../../runtime/checkpoints',()=>({restoreCheckpoint:vi.fn(),importCheckpoint:vi.fn(),exportCheckpoint:vi.fn()}));
vi.mock('../../runtime/gameFetch',()=>({gameFetch:vi.fn(),registerSavedSession:vi.fn()}));
vi.mock('./SeasonDesk',()=>({downloadFile:vi.fn()}));
vi.mock('../../runtime/campaigns',()=>({campaignRepository:{get:vi.fn()},exportCampaignFile:vi.fn(),correctCampaignResult:vi.fn(),relinkCampaignGame:vi.fn(async record=>record)}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks()});
it('resumes the selected durable checkpoint and passes saved UI phase',async()=>{const r={id:'g',revision:1,name:'My save',metadata:{phase:'coinToss'}};gameLibrary.list.mockResolvedValue([r]);restoreCheckpoint.mockResolvedValue({game_id:'restored',game_state:{}});const onResume=vi.fn();render(<SavedGames onMenu={()=>{}} onResume={onResume}/>);fireEvent.click(await screen.findByRole('button',{name:'Resume My save'}));await waitFor(()=>expect(onResume).toHaveBeenCalledWith({game_id:'restored',game_state:{}},r.metadata))});
it('shows storage errors without removing saves',async()=>{gameLibrary.list.mockRejectedValue(new Error('Storage blocked'));render(<SavedGames onMenu={()=>{}} onResume={()=>{}}/>);expect(await screen.findByRole('alert')).toHaveTextContent('Storage blocked');expect(gameLibrary.remove).not.toHaveBeenCalled()});

it('exports linked saves as the complete season bundle',async()=>{const r={id:'g',name:'Fixture',metadata:{campaignId:'c'}};gameLibrary.list.mockResolvedValue([r]);const campaign={id:'c'};campaignRepository.get.mockResolvedValue(campaign);exportCampaignFile.mockResolvedValue('season bundle');render(<SavedGames/>);fireEvent.click(await screen.findByText('Export'));await waitFor(()=>expect(downloadFile).toHaveBeenCalledWith('season bundle','paydirt-season.json'));expect(exportCampaignFile).toHaveBeenCalledWith(campaign)});
it('rejects standalone imports carrying season linkage',async()=>{gameLibrary.list.mockResolvedValue([]);importCheckpoint.mockReturnValue({id:'imported',metadata:{campaignId:'missing',fixtureId:'f'}});render(<SavedGames/>);const input=document.querySelector('input[type=file]');fireEvent.change(input,{target:{files:[{size:10,text:async()=> 'old linked file'}]}});expect(await screen.findByRole('alert')).toHaveTextContent(/season bundle/i);expect(gameLibrary.put).not.toHaveBeenCalled()});

it('requests browser save protection only after an explicit click',async()=>{
 const persist=vi.fn().mockResolvedValue(true);
 vi.stubGlobal('navigator',{storage:{persist}});
 gameLibrary.list.mockResolvedValue([]);
 render(<SavedGames/>);
 await screen.findByText('No saved games yet');
 expect(persist).not.toHaveBeenCalled();
 fireEvent.click(await screen.findByRole('button',{name:'Protect local saves'}));
 expect(await screen.findByText(/Browser protection is enabled/)).toBeVisible();
 expect(persist).toHaveBeenCalledTimes(1);
 expect(screen.queryByRole('button',{name:'Protect local saves'})).not.toBeInTheDocument();
});

it('keeps a save resumable and recommends export when browser protection is declined',async()=>{
 vi.stubGlobal('navigator',{storage:{persist:vi.fn().mockResolvedValue(false)}});
 gameLibrary.list.mockResolvedValue([{id:'g',name:'Recoverable',metadata:{}}]);
 render(<SavedGames/>);
 fireEvent.click(await screen.findByRole('button',{name:'Protect local saves'}));
 expect(await screen.findByText(/Browser protection was not granted/)).toBeVisible();
 expect(screen.getByRole('button',{name:'Resume Recoverable'})).toBeEnabled();
 expect(screen.getByText(/Export files for backup/)).toBeVisible();
});

it('refuses a stale Resume before restoring or relinking the engine',async()=>{const record={id:'stale',revision:1,name:'Stale',metadata:{}};gameLibrary.list.mockResolvedValue([record]);gameLibrary.get.mockResolvedValue({...record,revision:2});render(<SavedGames onResume={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Resume Stale'}));expect(await screen.findByRole('alert')).toHaveTextContent(/changed.*tab/i);expect(restoreCheckpoint).not.toHaveBeenCalled()});

it('shows application-local storage and hides browser protection for native saves',async()=>{libraryTransport.enabled.mockResolvedValue(true);const persist=vi.fn();vi.stubGlobal('navigator',{storage:{persist}});gameLibrary.list.mockResolvedValue([]);render(<SavedGames/>);expect(await screen.findByText(/Saved in this application.*Export/)).toBeVisible();expect(screen.queryByRole('button',{name:'Protect local saves'})).toBeNull();expect(screen.queryByText(/Clearing browser site data/)).toBeNull();expect(persist).not.toHaveBeenCalled()});

function acceptedFinal(){
 const record={id:'final-save',name:'Accepted final',revision:4,checkpoint:'opaque',metadata:{campaignId:'c',fixtureId:'f',gameId:'original-engine',gameOver:true}};
 const campaign={id:'c',revision:8,campaign:{id:'c',name:'Season',fixtures:[{id:'f',status:'completed',game_id:'original-engine',result:{revision:3,home_score:14,away_score:7}}]}};
 gameLibrary.list.mockResolvedValue([record]);campaignRepository.get.mockResolvedValue(campaign);
 restoreCheckpoint.mockResolvedValue({game_id:'preview-engine',game_state:{game_over:true,pending_pat:false,home_score:17,away_score:10,home_team:{name:'Home'},away_team:{name:'Away'}}});
 correctCampaignResult.mockResolvedValue({...campaign,revision:9});gameFetch.mockResolvedValue({ok:true});return{record,campaign};
}
it('cancels a result review without correcting, relinking or altering the saved final',async()=>{acceptedFinal();const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);render(<SavedGames/>);fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));await waitFor(()=>expect(confirm).toHaveBeenCalled());expect(confirm.mock.calls[0][0]).toMatch(/revision 3/);expect(confirm.mock.calls[0][0]).toMatch(/14.*7/);expect(confirm.mock.calls[0][0]).toMatch(/17.*10/);expect(confirm.mock.calls[0][0]).toMatch(/statistics.*checkpoint/i);await waitFor(()=>expect(gameFetch).toHaveBeenCalledWith(expect.stringMatching(/api\/game\/preview-engine$/),{method:'DELETE'}));expect(correctCampaignResult).not.toHaveBeenCalled();expect(relinkCampaignGame).not.toHaveBeenCalled();expect(registerSavedSession).not.toHaveBeenCalled();expect(gameLibrary.put).not.toHaveBeenCalled();expect(gameLibrary.remove).not.toHaveBeenCalled()});
it('corrects only after confirmation using the trusted runtime and accepted revision',async()=>{const{campaign}=acceptedFinal();vi.spyOn(window,'confirm').mockReturnValue(true);render(<SavedGames/>);fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));await waitFor(()=>expect(correctCampaignResult).toHaveBeenCalledWith(campaign,'f','preview-engine',3,expect.objectContaining({keys:expect.arrayContaining(['campaign:c','game:final-save'])})));await waitFor(()=>expect(gameFetch).toHaveBeenCalledWith(expect.stringMatching(/preview-engine$/),{method:'DELETE'}));expect(gameLibrary.list.mock.calls.length).toBeGreaterThan(1);expect(campaign.campaign.fixtures[0].game_id).toBe('original-engine');expect(gameLibrary.put).not.toHaveBeenCalled();expect(relinkCampaignGame).not.toHaveBeenCalled()});
it('rejects a stale completed checkpoint before restore or correction transport',async()=>{const{record}=acceptedFinal();gameLibrary.get.mockResolvedValue({...record,revision:5});render(<SavedGames/>);fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));expect(await screen.findByRole('alert')).toHaveTextContent(/changed.*tab/i);expect(restoreCheckpoint).not.toHaveBeenCalled();expect(correctCampaignResult).not.toHaveBeenCalled();expect(gameFetch).not.toHaveBeenCalled()});
it.each(['Results are frozen after postseason seeding','Result revision changed; reopen it before correcting'])('retains the prior checkpoint and ledger after correction rejection: %s',async message=>{acceptedFinal();vi.spyOn(window,'confirm').mockReturnValue(true);correctCampaignResult.mockRejectedValueOnce(Error(message));render(<SavedGames/>);fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));expect(await screen.findByRole('alert')).toHaveTextContent(message);expect(screen.getByRole('button',{name:'Resume Accepted final'})).toBeEnabled();expect(gameLibrary.put).not.toHaveBeenCalled();expect(gameLibrary.remove).not.toHaveBeenCalled();expect(await screen.findByRole('button',{name:'Review recorded result'})).toBeEnabled();expect(gameFetch).toHaveBeenCalledWith(expect.stringMatching(/preview-engine$/),{method:'DELETE'})});

it('never deletes or corrects an original engine returned as a preview',async()=>{
 acceptedFinal();
 restoreCheckpoint.mockResolvedValue({game_id:'original-engine',game_state:{game_over:true}});
 render(<SavedGames/>);
 fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));
 expect(await screen.findByRole('alert')).toHaveTextContent(/independent result preview/);
 expect(gameFetch).not.toHaveBeenCalled();
 expect(correctCampaignResult).not.toHaveBeenCalled();
});
it('cleans up a preview with an unresolved engine obligation without confirming a correction',async()=>{
 acceptedFinal();
 restoreCheckpoint.mockResolvedValue({game_id:'pending-preview',game_state:{game_over:true,pending_pat:true}});
 const confirm=vi.spyOn(window,'confirm');
 render(<SavedGames/>);
 fireEvent.click(await screen.findByRole('button',{name:'Review recorded result'}));
 expect(await screen.findByRole('alert')).toHaveTextContent(/owes an engine decision/);
 expect(confirm).not.toHaveBeenCalled();
 expect(correctCampaignResult).not.toHaveBeenCalled();
 expect(gameFetch).toHaveBeenCalledWith(expect.stringMatching(/pending-preview$/),{method:'DELETE'});
});
