import React from 'react';
import { act, render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import SeasonDesk from './SeasonDesk';
import * as api from '../../runtime/campaigns';
import {libraryTransport} from '../../runtime/nativeLibrary';
import { gameFetch } from '../../runtime/gameFetch';
vi.mock('../../runtime/nativeLibrary',()=>({libraryTransport:{enabled:vi.fn(async()=>false)}}));
vi.mock('../../runtime/campaigns', () => ({ listCampaigns:vi.fn(), viewCampaign:vi.fn(),
 duplicateCampaign:vi.fn(),editCampaignSchedule:vi.fn(),createCampaign:vi.fn(), getCampaignTemplates:vi.fn(), saveCampaign:vi.fn(),
 startCampaignGame:vi.fn(), importCampaignFile:vi.fn(), exportCampaignFile:vi.fn(),
 simulateFixture:vi.fn(), advancePostseason:vi.fn(), removeCampaign:vi.fn() }));
vi.mock('../../runtime/gameFetch', () => ({gameFetch: vi.fn(async()=>({ok:true,json:async()=>({seasons:['2026'],teams:[{id:'Ironclads',name:'Ironclads'},{id:'Thunderhawks',name:'Thunderhawks'}]})}))}));
const campaign={id:'one',name:'My first season',rules_season:'2026',participants:[{id:'a',season:'2026',team_id:'Ironclads',name:'Ironclads'},{id:'b',season:'2026',team_id:'Thunderhawks',name:'Thunderhawks'}],fixtures:[{id:'f',week:1,phase:'REG',home_id:'a',away_id:'b',status:'scheduled'}]};
afterEach(cleanup);
beforeEach(()=>{vi.clearAllMocks();libraryTransport.enabled.mockResolvedValue(false);gameFetch.mockImplementation(async()=>({ok:true,json:async()=>({seasons:['2026'],teams:[{id:'Ironclads',name:'Ironclads'},{id:'Thunderhawks',name:'Thunderhawks'}]})}));api.listCampaigns.mockResolvedValue([{id:'one',campaign,revision:1}]);api.viewCampaign.mockImplementation(async c=>({...c,standings:[{id:'a',name:'Ironclads',season:'2026',wins:0,losses:0,ties:0,points_for:0,points_against:0}],statistics:[],leaders:{},ranking_policy:'Win percentage, point differential, points for, name'}));api.getCampaignTemplates.mockResolvedValue([]);});
it('shows persisted campaigns and no invented leaders',async()=>{render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);await screen.findByRole('heading',{name:'My first season'});fireEvent.click(screen.getByRole('tab',{name:'Leaders'}));expect(screen.getByText(/No completed games with statistics/i)).toBeInTheDocument();});
it('launches a selected fixture using returned engine state',async()=>{const play=vi.fn();api.startCampaignGame.mockResolvedValue({game_id:'g',game_state:{},campaign});render(<SeasonDesk onMenu={()=>{}} onPlay={play}/>);await screen.findByRole('heading',{name:'My first season'});fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));fireEvent.click(screen.getByRole('button',{name:'Play fixture'}));fireEvent.click(screen.getByRole('button',{name:'Start game'}));await waitFor(()=>expect(play).toHaveBeenCalledWith(expect.objectContaining({game_id:'g'})));});
it('reports persistence failures instead of claiming an empty league',async()=>{api.listCampaigns.mockRejectedValue(new Error('Storage is blocked'));render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);expect(await screen.findByRole('alert')).toHaveTextContent('Storage is blocked');});

it('hides the previous campaign while a different campaign view is loading',async()=>{
 let resolve;const pending=new Promise(yes=>{resolve=yes});
 const other={...campaign,id:'two',name:'Second campaign'};
 api.listCampaigns.mockResolvedValue([{id:'one',campaign,revision:1},{id:'two',campaign:other,revision:1}]);
 const normal=api.viewCampaign.getMockImplementation();api.viewCampaign.mockImplementation(c=>c.id==='two'?pending:normal(c));
 render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);await screen.findByRole('heading',{name:'My first season'});
 fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));fireEvent.change(screen.getByLabelText('Your seasons'),{target:{value:'two'}});
 expect(screen.queryByRole('heading',{name:'My first season'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Play fixture'})).not.toBeInTheDocument();
 await act(async()=>resolve(await normal(other)));expect(await screen.findByRole('heading',{name:'Second campaign'})).toBeVisible();
});
it('uses installed rules when the initial default year is unavailable',async()=>{
 gameFetch.mockImplementation(async()=>({ok:true,json:async()=>({seasons:['2099'],teams:[{id:'A',name:'Synthetic A'},{id:'B',name:'Synthetic B'}]})}));
 api.createCampaign.mockResolvedValue({id:'one',campaign,revision:1});
 render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);fireEvent.click(screen.getByRole('button',{name:'+ New season'}));
 const dialog=screen.getByRole('dialog');await within(dialog).findByRole('option',{name:'Synthetic A'});
 fireEvent.click(within(dialog).getByRole('button',{name:'+ Add team edition'}));
 fireEvent.change(within(dialog).getByLabelText('Team'),{target:{value:'B'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'+ Add team edition'}));
 fireEvent.click(within(dialog).getByRole('button',{name:'Create season'}));
 await waitFor(()=>expect(api.createCampaign).toHaveBeenCalled());expect(api.createCampaign.mock.calls[0][0].rules_season).toBe('2099');
});
it('provides a friendly manual fixture editor and submits its selected editions',async()=>{
 api.createCampaign.mockResolvedValue({id:'one',campaign,revision:1});
 render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);fireEvent.click(screen.getByRole('button',{name:'+ New season'}));
 const dialog=screen.getByRole('dialog');await within(dialog).findByRole('option',{name:'Ironclads'});
 fireEvent.click(within(dialog).getByRole('button',{name:'+ Add team edition'}));
 fireEvent.change(within(dialog).getByLabelText('Team'),{target:{value:'Thunderhawks'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'+ Add team edition'}));
 fireEvent.change(within(dialog).getByLabelText('Schedule'),{target:{value:'manual'}});
 fireEvent.change(within(dialog).getByLabelText('Fixture week'),{target:{value:'3'}});
 fireEvent.change(within(dialog).getByLabelText('Home team edition'),{target:{value:'2026/Ironclads'}});
 fireEvent.change(within(dialog).getByLabelText('Away team edition'),{target:{value:'2026/Thunderhawks'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Add fixture'}));
 expect(within(dialog).queryByRole('textbox',{name:/JSON/})).not.toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'Create season'}));
 await waitFor(()=>expect(api.createCampaign).toHaveBeenCalled());
 expect(api.createCampaign.mock.calls[0][0].fixtures).toEqual([{week:3,home:'2026/Ironclads',away:'2026/Thunderhawks'}]);
});
it('focuses the dialog, traps tab navigation, closes on Escape, and restores trigger focus',async()=>{
 render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);const trigger=screen.getByRole('button',{name:'+ New season'});trigger.focus();fireEvent.click(trigger);
 const dialog=screen.getByRole('dialog');expect(within(dialog).getByLabelText('Season name')).toHaveFocus();
 await within(dialog).findByRole('option',{name:'Ironclads'});
 const close=within(dialog).getByRole('button',{name:'Close'});close.focus();fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});
 expect(within(dialog).getByLabelText('Rules for every game')).toHaveFocus();
 fireEvent.keyDown(dialog,{key:'Tab'});expect(close).toHaveFocus();
 fireEvent.keyDown(dialog,{key:'Escape'});expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(trigger).toHaveFocus();
});
it('renders a readable final box score without exposing internal result JSON',async()=>{
 const finished={...campaign,fixtures:[{...campaign.fixtures[0],status:'completed',result:{game_id:'internal-session-id',home_score:21,away_score:14,source:'played',home_stats:{total_yards:321,rushing_yards:121},away_stats:{total_yards:280,rushing_yards:90},revision:1}}]};
 api.listCampaigns.mockResolvedValue([{id:'one',campaign:finished,revision:1}]);render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);
 await screen.findByRole('heading',{name:'My first season'});fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));fireEvent.click(screen.getByText('Box score'));
 expect(screen.getByText('Total yards')).toBeVisible();expect(screen.getByText('321')).toBeVisible();expect(screen.getByText('280')).toBeVisible();
 expect(screen.queryByText(/internal-session-id/)).not.toBeInTheDocument();
});

it('waits for the installed year catalog before requesting teams',async()=>{
 let resolve;const catalog=new Promise(yes=>{resolve=yes});
 gameFetch.mockImplementation(url=>url.endsWith('/api/seasons')?catalog:Promise.resolve({ok:true,json:async()=>({teams:[{id:'A',name:'Synthetic A'}]})}));
 render(<SeasonDesk onMenu={()=>{}} onPlay={()=>{}}/>);fireEvent.click(screen.getByRole('button',{name:'+ New season'}));
 expect(gameFetch.mock.calls.some(([url])=>url.includes('/api/teams'))).toBe(false);
 await act(async()=>resolve({ok:true,json:async()=>({seasons:['2099']})}));
 await screen.findByRole('option',{name:'Synthetic A'});
 expect(gameFetch.mock.calls.filter(([url])=>url.includes('/api/teams')).map(([url])=>url)).toEqual([expect.stringContaining('season=2099')]);
});

it('duplicates a season as a fresh independently selected campaign',async()=>{const fresh={id:'fresh',revision:1,campaign:{...campaign,id:'fresh',name:'Fresh replay'}};const prompt=vi.spyOn(window,'prompt').mockReturnValue('Fresh replay');api.duplicateCampaign.mockImplementation(async()=>{api.listCampaigns.mockResolvedValue([{id:'one',campaign,revision:1},fresh]);return fresh});render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('button',{name:'Duplicate season'}));await waitFor(()=>expect(api.duplicateCampaign).toHaveBeenCalledWith(expect.objectContaining({id:'one'}),'Fresh replay'));expect(await screen.findByRole('heading',{name:'Fresh replay'})).toBeVisible();prompt.mockRestore()});
it('reviews and edits a generated schedule before the first game',async()=>{api.editCampaignSchedule.mockResolvedValue({id:'one',campaign,revision:2});render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));fireEvent.click(screen.getByRole('button',{name:'Edit schedule'}));const dialog=screen.getByRole('dialog',{name:'Edit season schedule'});expect(within(dialog).getByText(/Week 1/)).toBeVisible();fireEvent.click(within(dialog).getByRole('button',{name:'Remove fixture 1'}));fireEvent.change(within(dialog).getByLabelText('Fixture week'),{target:{value:'4'}});fireEvent.click(within(dialog).getByRole('button',{name:'Add fixture'}));fireEvent.click(within(dialog).getByRole('button',{name:'Save schedule'}));await waitFor(()=>expect(api.editCampaignSchedule).toHaveBeenCalledWith(expect.objectContaining({id:'one'}),[{week:4,home_id:'a',away_id:'b'}]))});
it('hides schedule editing once a fixture has started',async()=>{const started={...campaign,locked:true,fixtures:[{...campaign.fixtures[0],status:'in_progress'}]};api.listCampaigns.mockResolvedValue([{id:'one',campaign:started,revision:2}]);render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));expect(screen.queryByRole('button',{name:'Edit schedule'})).not.toBeInTheDocument()});
it('filters standings by conference and shows every supported team counter',async()=>{api.viewCampaign.mockResolvedValue({...campaign,participants:campaign.participants.map((p,i)=>({...p,conference:i?'West':'East',division:'One'})),standings:[{...campaign.participants[0],conference:'East',division:'One'},{...campaign.participants[1],conference:'West',division:'One'}],statistics:[{...campaign.participants[0],stat_games:1,offense:{first_downs:17,penalties:3,penalty_yards:25,passing_yards:201,sack_yards:12,interceptions_thrown:2,fumbles_lost:1}}],leaders:{}});render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.change(screen.getByLabelText('Standings scope'),{target:{value:'conference:East'}});const table=screen.getByRole('table');expect(within(table).getByText('2026 Ironclads')).toBeVisible();expect(within(table).queryByText('2026 Thunderhawks')).toBeNull();fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));for(const label of ['First downs','Penalties','Penalty yards','Gross passing yards','Sack yards lost','Interceptions thrown','Fumbles lost'])expect(screen.getByRole('columnheader',{name:label})).toBeVisible()});
it('describes native season storage accurately',async()=>{libraryTransport.enabled.mockResolvedValue(true);render(<SeasonDesk/>);expect(await screen.findByText(/Saved in this application.*Export/i)).toBeVisible();expect(screen.queryByText(/Clearing site data removes/)).toBeNull()});

it('persists a followed team and scopes its next fixture while showing all divisions',async()=>{const league={...campaign,followed_participant_id:'a',participants:[{...campaign.participants[0],conference:'East',division:'One'},{...campaign.participants[1],conference:'West',division:'Two'}],fixtures:[{...campaign.fixtures[0],id:'done',week:1,status:'completed',result:{home_score:14,away_score:7,source:'played'}},{...campaign.fixtures[0],week:3}]};api.listCampaigns.mockResolvedValue([{id:'one',campaign:league,revision:1}]);api.viewCampaign.mockImplementation(async c=>({...c,standings:c.participants,statistics:[],leaders:{}}));api.saveCampaign.mockResolvedValue({id:'one',campaign:{...league,followed_participant_id:'b'},revision:2});render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});expect(screen.getByLabelText('Follow team')).toHaveValue('a');expect(screen.getByText('Current week: 3')).toBeVisible();expect(screen.getByRole('heading',{name:'Recent results for 2026 Ironclads'})).toBeVisible();expect(screen.getByLabelText('Standings scope')).toHaveValue('all');fireEvent.change(screen.getByLabelText('Follow team'),{target:{value:'b'}});await waitFor(()=>expect(api.saveCampaign).toHaveBeenCalledWith(expect.objectContaining({followed_participant_id:'b'}),1))});

it('shows per-counter coverage and partial totals and rates for both sides',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{...campaign.participants[0],participant_id:'a',played:3}],
  statistics:[{...campaign.participants[0],participant_id:'a',stat_games:2,
   offense:{total_yards:420,rushing_yards:0},offense_per_game:{total_yards:210,rushing_yards:0},
   offense_games:{total_yards:2,rushing_yards:3,passing_yards:0},
   defense:{total_yards:300},defense_per_game:{total_yards:300},defense_games:{total_yards:1}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const cell=label=>within(screen.getByRole('table')).getAllByRole('cell')[screen.getAllByRole('columnheader').findIndex(h=>(h.getAttribute('aria-label') || h.textContent)===label || (h.getAttribute('aria-label') || h.textContent)===`${label} allowed`)];
 expect(cell('Total yards')).toHaveTextContent('420');
 expect(cell('Total yards')).toHaveTextContent('2/3 games · Partial');
 expect(cell('Rushing yards')).toHaveTextContent('0');
 expect(cell('Rushing yards')).toHaveTextContent('3/3 games');
 expect(cell('Rushing yards')).not.toHaveTextContent('Partial');
 expect(cell('Gross passing yards')).toHaveTextContent('—');
 expect(cell('Gross passing yards')).toHaveTextContent('0/3 games · Not recorded');
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 expect(cell('Total yards')).toHaveTextContent('210.0');
 expect(cell('Total yards')).toHaveTextContent('2/3 games · Partial');
 fireEvent.click(screen.getByRole('button',{name:'Defense',exact:true}));
 expect(cell('Total yards')).toHaveTextContent('300.0');
 expect(cell('Total yards')).toHaveTextContent('1/3 games · Partial');
 expect(cell('Rushing yards')).toHaveTextContent('Coverage unavailable');
});

async function openPregame() {
 render(<SeasonDesk onPlay={vi.fn()} />);
 await screen.findByRole('heading', {name:campaign.name});
 fireEvent.click(screen.getByRole('tab', {name:'Schedule'}));
 const trigger=screen.getByRole('button', {name:'Play fixture'});
 trigger.focus(); fireEvent.click(trigger);
 return {dialog:screen.getByRole('dialog', {name:'Game setup'}), trigger};
}
it.each(['easy','medium','hard'])('starts a fixture only after confirming %s difficulty and side', async difficulty=>{
 api.startCampaignGame.mockResolvedValue({game_id:'g',game_state:{},campaign});
 const {dialog}=await openPregame();
 expect(api.startCampaignGame).not.toHaveBeenCalled();
 expect(within(dialog).getByLabelText('Difficulty')).toHaveValue('medium');
 expect(within(dialog).getByText('Week 1 · 2026 Thunderhawks at 2026 Ironclads')).toBeVisible();
 fireEvent.change(within(dialog).getByLabelText('Difficulty'),{target:{value:difficulty}});
 fireEvent.change(within(dialog).getByLabelText('Coach'),{target:{value:'away'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Start game'}));
 await waitFor(()=>expect(api.startCampaignGame).toHaveBeenCalledWith(
  expect.objectContaining({id:'one'}),'f',{human_is_home:false,difficulty}));
});
it('cancels game setup without starting a game and restores focus',async()=>{
 const {dialog,trigger}=await openPregame();
 expect(within(dialog).getByLabelText('Coach')).toHaveFocus();
 const cancel=within(dialog).getByRole('button',{name:'Cancel'});
 cancel.focus();fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});
 expect(within(dialog).getByRole('button',{name:'Start game'})).toHaveFocus();
 fireEvent.keyDown(dialog,{key:'Tab'});expect(cancel).toHaveFocus();
 fireEvent.keyDown(dialog,{key:'Escape'});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(trigger).toHaveFocus();expect(api.startCampaignGame).not.toHaveBeenCalled();
});
it('keeps failed setup open for retry and prevents duplicate starts while saving',async()=>{
 let reject;api.startCampaignGame.mockImplementation(()=>new Promise((_,no)=>{reject=no}));
 const {dialog}=await openPregame();
 const start=within(dialog).getByRole('button',{name:'Start game'});
 fireEvent.click(start);expect(start).toBeDisabled();
 expect(within(dialog).getByRole('button',{name:'Cancel'})).toBeDisabled();
 fireEvent.keyDown(dialog,{key:'Escape'});expect(dialog).toBeVisible();
 await act(async()=>reject(new Error('Could not save game')));
 expect(within(dialog).getByRole('alert')).toHaveTextContent('Could not save game');
 expect(start).toBeEnabled();expect(api.startCampaignGame).toHaveBeenCalledTimes(1);
 fireEvent.click(within(dialog).getByRole('button',{name:'Cancel'}));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('passes the confirmed difficulty into the game UI when the launch response omits it',async()=>{
 const onPlay=vi.fn();api.startCampaignGame.mockResolvedValue({game_id:'g',game_state:{},campaign});
 render(<SeasonDesk onPlay={onPlay}/>);
 await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Schedule'}));
 fireEvent.click(screen.getByRole('button',{name:'Play fixture'}));
 const dialog=screen.getByRole('dialog',{name:'Game setup'});
 fireEvent.change(within(dialog).getByLabelText('Difficulty'),{target:{value:'hard'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Start game'}));
 await waitFor(()=>expect(onPlay).toHaveBeenCalledWith(expect.objectContaining({difficulty:'hard'})));
});


it('opens with division standings grouped NFC first, then AFC, including custom conferences',async()=>{
 const participants=[['a','AFC','East'],['b','NFC','West'],['c','NFC','East'],['d','Custom','North']].map(([id,conference,division])=>({id,name:`Team ${id}`,season:'2026',team_id:id,conference,division}));
 api.viewCampaign.mockResolvedValue({...campaign,participants,followed_participant_id:'a',standings:participants.map(p=>({...p,wins:1,losses:0,ties:0,points_for:7,points_against:0,win_pct:1})),statistics:[],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 expect(screen.getByLabelText('Standings scope')).toHaveValue('all');
 expect(screen.getByRole('heading',{name:'Standings',exact:true}).compareDocumentPosition(screen.getByRole('heading',{name:/Recent results/})) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 expect(screen.getAllByRole('region',{name:/ standings$/}).map(region=>within(region).getByRole('heading',{level:3}).textContent)).toEqual(['NFC','AFC','Custom']);
 expect(within(screen.getByRole('region',{name:'NFC standings'})).getAllByRole('heading',{level:4}).map(h=>h.textContent)).toEqual(['East','West']);
 expect(within(screen.getByRole('region',{name:'AFC standings'})).getByText('2026 Team a')).toBeVisible();
 fireEvent.change(screen.getByLabelText('Standings scope'),{target:{value:'NFC / West'}});
 expect(screen.getAllByRole('table')).toHaveLength(1);
 expect(within(screen.getByRole('table')).getByText('2026 Team b')).toBeVisible();
 expect(within(screen.getByRole('table')).queryByText('2026 Team c')).toBeNull();
});


it('shows team kicking totals, authoritative percentage and distance bands with unknown coverage',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:2}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:2,
 offense:{field_goals_attempted:3,field_goals_made:2,field_goal_percentage:66.6666667,field_goals_40_49_attempted:2,field_goals_40_49_made:1},
 offense_games:{field_goal_percentage:1,field_goals_attempted:1,field_goals_made:1,field_goals_40_49_attempted:1,field_goals_40_49_made:1}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 fireEvent.click(screen.getByRole('button',{name:'Kicking',exact:true}));
 for(const name of ['FG made','FG attempted','FG %','0–19 yd made','20–29 yd made','30–39 yd made','40–49 yd made','50+ yd made']) expect(screen.getByRole('columnheader',{name,exact:true})).toBeVisible();
 const cells=within(screen.getByRole('table')).getAllByRole('cell');
 expect(cells[2]).toHaveTextContent('2');expect(cells[2]).toHaveTextContent('1/2 games · Partial');
 expect(cells[3]).toHaveTextContent('3');expect(cells[4]).toHaveTextContent('66.7%');
 expect(cells[5]).toHaveTextContent('—');
 expect(screen.queryByLabelText('View')).toBeNull();
});


it('separates offense defense and kicking and labels defensive takeaways and sacks',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:1}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:1,
 offense:{interceptions_thrown:1,fumbles_lost:2,sacks:3},defense:{interceptions_thrown:4,fumbles_lost:5,sacks:6},
 defense_games:{interceptions_thrown:1,fumbles_lost:1,sacks:1}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const categories=screen.getByRole('group',{name:'Statistics category'});
 expect(within(categories).getByRole('button',{name:'Offense',exact:true})).toHaveAttribute('aria-pressed','true');
 fireEvent.click(within(categories).getByRole('button',{name:'Defense',exact:true}));
 expect(screen.getByRole('heading',{name:'Defense statistics',exact:true})).toBeVisible();
 const headings=screen.getAllByRole('columnheader').map(h=>h.getAttribute('aria-label') || h.textContent);
 const cells=within(screen.getByRole('table')).getAllByRole('cell');
 for(const [label,value] of [['Interceptions',4],['Fumble recoveries',5],['Sacks',6]]) expect(cells[headings.indexOf(label)]).toHaveTextContent(`${value}1/1 games`);
 expect(screen.queryByRole('columnheader',{name:'Interceptions thrown',exact:true})).toBeNull();
 expect(screen.queryByRole('columnheader',{name:'Fumbles lost',exact:true})).toBeNull();
 fireEvent.click(within(categories).getByRole('button',{name:'Kicking',exact:true}));
 expect(screen.getByRole('heading',{name:'Kicking statistics',exact:true})).toBeVisible();
 fireEvent.click(within(categories).getByRole('button',{name:'Offense',exact:true}));
 expect(screen.getByRole('columnheader',{name:'Interceptions thrown',exact:true})).toBeVisible();
});


it('shows offensive attempts completions rushing volume and weighted passing efficiency',async()=>{
 const offense={passing_attempts:30,passing_completions:20,passing_touchdowns:2,rushing_attempts:25,completion_percentage:66.6667,passer_rating:106.25,passing_yards_per_attempt:8.3333,rushing_yards_per_attempt:4.8};
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:2}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:2,offense,offense_per_game:{...offense,passing_attempts:15},offense_games:Object.fromEntries(Object.keys(offense).map(k=>[k,2]))}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const cell=label=>within(screen.getByRole('table')).getAllByRole('cell')[screen.getAllByRole('columnheader').findIndex(h=>(h.getAttribute('aria-label') || h.textContent)===label)];
 for(const label of ['Pass attempts','Completions','Passing TDs','Rush attempts']) expect(screen.getByRole('columnheader',{name:label,exact:true})).toBeVisible();
 for(const [label,value] of [['Completion %','66.7%'],['Team passer rating','106.3'],['Yards/pass attempt','8.3'],['Yards/rush attempt','4.8']]) expect(within(cell(label)).getByText(value)).toBeVisible();
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 expect(within(cell('Pass attempts')).getByText('15.0')).toBeVisible();
 expect(within(cell('Completion %')).getByText('66.7%')).toBeVisible();
 expect(within(cell('Team passer rating')).getByText('106.3')).toBeVisible();
});


it('sorts statistics numerically in both directions with missing values last and coverage attached',async()=>{
 const values=[['a','Alpha',9,8,70.041],['b','Beta',100,2,70.049],['c','Gamma',null,null,null],['d','Delta',0,0,0],['e','Epsilon',-3,-1,5]];
 api.viewCampaign.mockResolvedValue({...campaign,standings:values.map(([id])=>({participant_id:id,played:4})),statistics:values.map(([id,name,total,rate,pct])=>({participant_id:id,name,season:'2026',stat_games:id==='a'?2:4,offense:{total_yards:total,completion_percentage:pct},offense_per_game:{total_yards:rate},offense_games:{total_yards:id==='a'?2:4}})),leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const names=()=>within(screen.getByRole('table')).getAllByRole('row').slice(1).map(row=>within(row).getAllByRole('cell')[0].textContent);
 fireEvent.click(screen.getByRole('button',{name:'Total yards',exact:true}));
 expect(names()).toEqual(['2026 Beta','2026 Alpha','2026 Delta','2026 Epsilon','2026 Gamma']);
 expect(screen.getByRole('columnheader',{name:'Total yards',exact:true})).toHaveAttribute('aria-sort','descending');
 expect(within(screen.getByRole('row',{name:/2026 Alpha/})).getByText('2/4 games · Partial')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Total yards',exact:true}));
 expect(names()).toEqual(['2026 Epsilon','2026 Delta','2026 Alpha','2026 Beta','2026 Gamma']);
 expect(screen.getByRole('columnheader',{name:'Total yards',exact:true})).toHaveAttribute('aria-sort','ascending');
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 expect(names()).toEqual(['2026 Epsilon','2026 Delta','2026 Beta','2026 Alpha','2026 Gamma']);
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'totals'}});
 fireEvent.click(screen.getByRole('button',{name:'Completion %',exact:true}));
 expect(names().slice(0,2)).toEqual(['2026 Beta','2026 Alpha']);
 fireEvent.click(screen.getByRole('button',{name:'Team edition',exact:true}));
 expect(names()).toEqual(['2026 Alpha','2026 Beta','2026 Delta','2026 Epsilon','2026 Gamma']);
});

it('sorts standings inside their divisions without changing conference grouping',async()=>{
 const rows=[['a','Alpha',2,'NFC'],['b','Beta',10,'NFC'],['c','Gamma',8,'AFC']].map(([id,name,wins,conference])=>({id,name,wins,season:'2026',conference,division:'East',losses:0,ties:0,points_for:0,points_against:0}));
 api.viewCampaign.mockResolvedValue({...campaign,participants:rows,standings:rows,statistics:[],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 const nfc=screen.getByRole('region',{name:'NFC standings'});
 fireEvent.click(within(nfc).getByRole('button',{name:'W',exact:true}));
 expect(within(nfc).getAllByRole('row').slice(1).map(r=>within(r).getAllByRole('cell')[0].textContent)).toEqual(['2026 Beta','2026 Alpha']);
 expect(screen.getAllByRole('region',{name:/ standings$/}).map(r=>within(r).getByRole('heading',{level:3}).textContent)).toEqual(['NFC','AFC']);
 expect(within(screen.getByRole('region',{name:'AFC standings'})).getByText('2026 Gamma')).toBeVisible();
});


it('opens focused ESPN-style team categories without mixing passing and rushing columns',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[],statistics:[],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const directory=screen.getByRole('navigation',{name:'Team statistics categories'});
 expect(within(directory).getAllByRole('button')).toHaveLength(13);
 fireEvent.click(within(directory).getByRole('button',{name:'Offense: Passing',exact:true}));
 expect(screen.getByRole('heading',{name:'Offense · Passing'})).toBeVisible();
 expect(screen.getByRole('columnheader',{name:'Team passer rating',exact:true})).toBeVisible();
 expect(screen.queryByRole('columnheader',{name:'Rush attempts',exact:true})).toBeNull();
 fireEvent.click(within(directory).getByRole('button',{name:'Offense: Receiving',exact:true}));
 expect(screen.getByRole('columnheader',{name:'Receptions',exact:true})).toBeVisible();
 expect(screen.getByRole('columnheader',{name:'Receiving yards',exact:true})).toBeVisible();
 expect(screen.queryByRole('columnheader',{name:'Sacks taken',exact:true})).toBeNull();
 fireEvent.click(within(directory).getByRole('button',{name:'Defense: Turnovers',exact:true}));
 expect(screen.getByRole('columnheader',{name:'Interceptions',exact:true})).toBeVisible();
 expect(screen.getByRole('columnheader',{name:'Fumble recoveries',exact:true})).toBeVisible();
 expect(screen.queryByRole('columnheader',{name:'Gross passing yards allowed',exact:true})).toBeNull();
 fireEvent.click(within(directory).getByRole('button',{name:'Special teams: Punting',exact:true}));
 expect(screen.getByRole('columnheader',{name:'Net punt average',exact:true})).toBeVisible();
 expect(screen.getByRole('columnheader',{name:'Punts inside 20',exact:true})).toBeVisible();
 expect(screen.queryByText(/Punting counters are not yet recorded/)).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Offense',exact:true}));
 expect(screen.getByRole('columnheader',{name:'Total yards',exact:true})).toBeVisible();
});


it('shows compact statistical headers with full accessible names and five top-five leader cards',async()=>{
 const entries=Array.from({length:7},(_,i)=>({rank:i+1,name:`Sample ${i}`,season:'2026',value:400-i,games:2}));
 api.viewCampaign.mockResolvedValue({...campaign,standings:[],statistics:[],leaders:Object.fromEntries(['total_offense','passing_offense','rushing_offense','total_defense','scoring_offense','scoring_defense'].map(key=>[key,entries]))});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 expect(screen.getByRole('columnheader',{name:'Pass attempts',exact:true})).toHaveTextContent('ATT');
 expect(screen.getByRole('columnheader',{name:'Team passer rating',exact:true})).toHaveTextContent('RTG');
 expect(screen.getByRole('button',{name:'Pass attempts',exact:true})).toHaveAttribute('title','Pass attempts');
 const overview=screen.getByRole('region',{name:'Season leaders at a glance'});
 expect(within(overview).getAllByRole('list')).toHaveLength(5);
 for(const list of within(overview).getAllByRole('list'))expect(within(list).getAllByRole('listitem')).toHaveLength(5);
 expect(within(overview).queryByText('2026 Sample 5')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Offense: Passing',exact:true}));
 expect(screen.queryByRole('region',{name:'Season leaders at a glance'})).toBeNull();
});


it('completes every team category from authoritative counters and keeps legacy unknowns explicit',async()=>{
 const counters={points_scored:51,longest_pass:61,longest_rush:42,longest_reception:57,
 rushing_touchdowns:4,rushing_fumbles:3,rushing_fumbles_lost:2,receiving_fumbles:2,receiving_fumbles_lost:1,
 receiving_yards_per_reception:13.75,first_downs_rushing:15,first_downs_passing:22,first_downs_penalty:3,
 third_down_attempts:25,third_down_conversions:11,third_down_conversion_percentage:44,
 fourth_down_attempts:4,fourth_down_conversions:3,fourth_down_conversion_percentage:75,
 extra_points_made:6,extra_points_attempted:7,extra_point_percentage:85.714,longest_field_goal:53,
 kickoff_returns:4,kickoff_return_yards:111,longest_kickoff_return:38,kickoff_return_touchdowns:1,kickoff_return_average:27.75,
 punt_returns:5,punt_return_yards:61,longest_punt_return:25,punt_return_touchdowns:1,punt_return_fair_catches:2,punt_return_average:12.2,
 punts:8,punt_yards:350,longest_punt:58,punts_blocked:1,punts_inside_20:3,punt_touchbacks:1,punt_fair_catches:2,punts_returned:4,punt_return_yards_allowed:37,
 gross_punt_average:43.75,net_punt_average:36.625};
 const coverage=Object.fromEntries(Object.keys(counters).map(key=>[key,2]));
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:3}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:2,
 offense:counters,defense:{...counters,longest_pass:66},offense_per_game:{...counters,points_scored:25.5},defense_per_game:{...counters,longest_pass:66},
 offense_games:coverage,defense_games:coverage}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 const check=(category,label,value)=>{
  fireEvent.click(screen.getByRole('button',{name:category,exact:true}));
  const heading=screen.getByRole('columnheader',{name:label,exact:true});
  const table=heading.closest('table');const index=within(table).getAllByRole('columnheader').indexOf(heading);
  const cell=within(table).getAllByRole('cell')[index];
  expect(cell).toHaveTextContent(value);expect(cell).toHaveTextContent('2/3 games · Partial');
  expect(within(heading).getByRole('button')).toHaveAttribute('title',label);
 };
 check('Offense: Total yards','Points scored','51');
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 check('Offense: Total yards','Points scored','25.5');
 check('Offense: Passing','Longest pass','61');
 expect(screen.getByRole('columnheader',{name:'Longest pass'}).closest('table')).not.toHaveTextContent('61.0');
 for(const [label,value] of [['Rushing TDs','4.0'],['Rushing fumbles','3.0'],['Rushing fumbles lost','2.0'],['Longest rush','42']]) check('Offense: Rushing',label,value);
 for(const [label,value] of [['Yards/reception','13.8'],['Longest reception','57'],['Receiving fumbles','2.0'],['Receiving fumbles lost','1.0']]) check('Offense: Receiving',label,value);
 for(const [label,value] of [['Rushing first downs','15.0'],['Passing first downs','22.0'],['Penalty first downs','3.0'],['Third-down attempts','25.0'],['Third-down conversions','11.0'],['Third-down conversion %','44.0%'],['Fourth-down attempts','4.0'],['Fourth-down conversions','3.0'],['Fourth-down conversion %','75.0%']]) check('Offense: Downs',label,value);
 check('Defense: Passing','Longest pass allowed','66');
 check('Defense: Receiving','Yards/reception allowed','13.8');
 for(const [label,value] of [['XP made','6'],['XP attempted','7'],['XP %','85.7%'],['Longest field goal','53']]) check('Special teams: Kicking',label,value);
 for(const [label,value] of [['Punts','8'],['Punt yards','350'],['Gross punt average','43.8'],['Net punt average','36.6'],['Longest punt','58'],['Punts blocked','1'],['Punts inside 20','3'],['Punt touchbacks','1'],['Punt fair catches','2'],['Punts returned','4'],['Punt return yards allowed','37']]) check('Special teams: Punting',label,value);
 for(const [label,value] of [['Kickoff returns','4'],['Kickoff return yards','111'],['Kickoff return average','27.8'],['Longest kickoff return','38'],['Kickoff return TDs','1'],['Punt returns','5'],['Punt return yards','61'],['Punt return average','12.2'],['Longest punt return','25'],['Punt return TDs','1'],['Punt return fair catches','2']]) check('Special teams: Returning',label,value);
 expect(screen.queryByText(/not yet recorded|not yet available/)).toBeNull();
});

it.each([
 ['Offense: Passing','Longest pass'],['Offense: Rushing','Rushing TDs'],
 ['Offense: Receiving','Yards/reception'],['Offense: Downs','Third-down conversion %'],
 ['Defense: Yards allowed','Rushing TDs allowed'],['Special teams: Kicking','XP %'],
 ['Special teams: Punting','Net punt average'],['Special teams: Returning','Kickoff return average'],
])('exposes complete %s counters while older records stay unknown',async(category,label)=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:2}],
 statistics:[{...campaign.participants[0],participant_id:'a',stat_games:1,offense:{},defense:{},offense_games:{},defense_games:{}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 fireEvent.click(screen.getByRole('button',{name:category,exact:true}));
 const header=screen.getByRole('columnheader',{name:label,exact:true});const table=header.closest('table');
 const index=within(table).getAllByRole('columnheader').indexOf(header);
 const cell=within(table).getAllByRole('cell')[index];expect(cell).toHaveTextContent('—');expect(cell).toHaveTextContent('Coverage unavailable');
});

it('keeps standings and recent results together in Overview without a duplicate Standings tab',async()=>{
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 expect(screen.getByRole('tab',{name:'Overview',exact:true})).toHaveAttribute('aria-selected','true');
 expect(screen.queryByRole('tab',{name:'Standings',exact:true})).toBeNull();
 expect(screen.getByRole('heading',{name:'Standings',exact:true})).toBeVisible();
 expect(screen.getByLabelText('Standings scope')).toBeVisible();
 expect(screen.getByRole('heading',{name:'Recent results',exact:true})).toBeVisible();
 fireEvent.click(screen.getByRole('tab',{name:'Schedule',exact:true}));
 expect(screen.queryByRole('heading',{name:'Standings',exact:true})).toBeNull();
 fireEvent.click(screen.getByRole('tab',{name:'Overview',exact:true}));
 expect(screen.getByRole('heading',{name:'Standings',exact:true})).toBeVisible();
 expect(screen.getByRole('heading',{name:'Recent results',exact:true})).toBeVisible();
});

it('shows paired authoritative giveaways takeaways differential and opponent punt return average',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:3}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:3,
 offense:{turnovers:100,punt_return_average_allowed:-2.75},offense_games:{turnovers:3,punt_return_average_allowed:2},
 defense:{turnovers:200,interceptions_thrown:3,fumbles_lost:5},defense_games:{turnovers:3,interceptions_thrown:3,fumbles_lost:3},
 turnover_summary:{giveaways:4,takeaways:8,differential:4,games:2}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});
 fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 fireEvent.change(screen.getByLabelText('View'),{target:{value:'per_game'}});
 fireEvent.click(screen.getByRole('button',{name:'Defense: Turnovers',exact:true}));
 expect(screen.queryByLabelText('View')).toBeNull();
 const cell=label=>{const header=screen.getByRole('columnheader',{name:label,exact:true});const table=header.closest('table');return within(table).getAllByRole('cell')[within(table).getAllByRole('columnheader').indexOf(header)]};
 for(const [label,value] of [['Giveaways','4'],['Takeaways','8'],['Turnover differential','4']]){
 expect(cell(label).querySelector('span')).toHaveTextContent(value);expect(cell(label)).toHaveTextContent('2/3 games · Partial');
 }
 expect(cell('Interceptions').querySelector('span')).toHaveTextContent('3');
 expect(cell('Fumble recoveries').querySelector('span')).toHaveTextContent('5');
 fireEvent.click(screen.getByRole('button',{name:'Special teams: Punting',exact:true}));
 expect(cell('Opponent punt return average').querySelector('span')).toHaveTextContent('-2.8');
 expect(cell('Opponent punt return average')).toHaveTextContent('2/3 games · Partial');
});
it('leaves unpaired legacy turnover balance unknown',async()=>{
 api.viewCampaign.mockResolvedValue({...campaign,standings:[{participant_id:'a',played:1}],statistics:[{...campaign.participants[0],participant_id:'a',stat_games:1,
 offense:{turnovers:2},defense:{turnovers:3},offense_games:{turnovers:1},defense_games:{turnovers:1},
 turnover_summary:{giveaways:null,takeaways:null,differential:null,games:0}}],leaders:{}});
 render(<SeasonDesk/>);await screen.findByRole('heading',{name:campaign.name});fireEvent.click(screen.getByRole('tab',{name:'Team statistics'}));
 fireEvent.click(screen.getByRole('button',{name:'Defense: Turnovers',exact:true}));
 const header=screen.getByRole('columnheader',{name:'Turnover differential',exact:true});
 const table=header.closest('table');const cell=within(table).getAllByRole('cell')[within(table).getAllByRole('columnheader').indexOf(header)];
 expect(cell).toHaveTextContent('—');expect(cell).toHaveTextContent('0/1 games · Not recorded');
});
