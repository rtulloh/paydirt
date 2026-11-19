import React from 'react';
import {render,screen,fireEvent,act,cleanup} from '@testing-library/react';
import {it,expect,vi,afterEach,beforeEach} from 'vitest';
import PlayingPhase from './PlayingPhase';
import {useGameStore} from '../../store/gameStore';
import {gameFetch} from '../../runtime/gameFetch';
vi.mock('../../runtime/gameFetch',()=>({gameFetch:vi.fn(),browserMode:false,saveCurrentSession:vi.fn()}));
vi.mock('../Scoreboard/Scoreboard',()=>({default:()=>null}));
vi.mock('../Field/FootballField',()=>({default:()=>null}));
vi.mock('../Dice/DiceDisplay',()=>({default:({isRolling})=><div>Rolling: {String(isRolling)}</div>}));
vi.mock('./PATChoicePanel',()=>({default:({onPatKick,onPatTwoPoint})=><><button onClick={onPatKick}>Try kick</button><button onClick={onPatTwoPoint}>Try two</button></>}));
beforeEach(()=>{vi.useFakeTimers();gameFetch.mockReset()});
afterEach(()=>{cleanup();vi.clearAllTimers();vi.useRealTimers();useGameStore.getState().reset()});
const state={home_team:{short_name:'H'},away_team:{short_name:'A'},player_offense:true};
it.each(['kickoff','kick','two'])('shows a rejected %s request and retains the pending action for retry',async kind=>{
 gameFetch.mockRejectedValueOnce(Error('This game is already open in another tab.'));
 useGameStore.getState().restoreSession({game_id:'g',game_state:{...state,is_kickoff:kind==='kickoff',pending_pat:kind!=='kickoff',can_go_for_two:true}});
 render(<PlayingPhase/>);
 const label=kind==='kickoff'?'KICK OFF':kind==='kick'?'Try kick':'Try two';
 fireEvent.click(screen.getByRole('button',{name:label}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(screen.getByRole('alert')).toHaveTextContent('already open in another tab');
 expect(screen.getByRole('button',{name:label})).toBeEnabled();
 expect(kind==='kickoff'?useGameStore.getState().isKickoff:useGameStore.getState().pendingPat).toBe(true);
 expect(gameFetch).toHaveBeenCalledTimes(1);
 expect(screen.queryByText('Rolling: true')).toBeNull();
});
it('shows the conflict for an automatic CPU try without clearing its obligation',async()=>{
 gameFetch.mockRejectedValueOnce(Error('Another tab holds this season.'));
 useGameStore.getState().restoreSession({game_id:'cpu',game_state:{...state,player_offense:false,pending_pat:true}});
 render(<PlayingPhase/>);
 await act(async()=>{});
 expect(screen.getByRole('alert')).toHaveTextContent('Another tab holds this season');
 expect(useGameStore.getState().pendingPat).toBe(true);
 expect(gameFetch).toHaveBeenCalledTimes(1);
});

it('lets the user retry a rejected CPU try after the other writer releases it',async()=>{
 gameFetch.mockRejectedValueOnce(Error('Another tab holds this season.'));
 useGameStore.getState().restoreSession({game_id:'cpu',game_state:{...state,player_offense:false,pending_pat:true}});
 render(<PlayingPhase/>);
 await act(async()=>{});
 gameFetch.mockResolvedValueOnce({ok:true,json:async()=>({game_state:{...state,player_offense:false,pending_pat:false},is_kickoff:true,description:'Extra point good'})});
 fireEvent.click(screen.getByRole('button',{name:'Retry automatic try'}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(gameFetch).toHaveBeenCalledTimes(2);
 expect(screen.queryByRole('alert')).toBeNull();
 expect(useGameStore.getState().pendingPat).toBe(false);
});

it('shows a blocked normal play instead of silently ignoring the click',async()=>{
 gameFetch.mockRejectedValueOnce(Error('Save needs attention before another play: Native library command failed; prior save retained'));
 useGameStore.getState().restoreSession({game_id:'punt',game_state:{...state,player_offense:true,down:1}});
 render(<PlayingPhase/>);
 fireEvent.click(screen.getByTestId('offense-play-1'));
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(screen.getByRole('alert')).toHaveTextContent('Save needs attention');
 expect(screen.getByTestId('offense-play-1')).toBeEnabled();
 expect(screen.queryByText('Rolling: true')).toBeNull();
});

it.each(['transport','http'])('shows a rejected penalty choice (%s) and keeps both choices available for retry',async kind=>{
 if(kind==='transport') gameFetch.mockRejectedValueOnce(Error('Save needs attention before another play'));
 else gameFetch.mockResolvedValueOnce({ok:false,status:409,text:async()=>'Save needs attention before another play'});
 useGameStore.getState().restoreSession({game_id:'penalty',game_state:{...state,player_offense:false},
  pending_result:{pending_penalty_decision:true,penalty_choice:{offended_team:'defense',
   penalty_options:[{description:'Accept synthetic foul',yards:5}]}}});
 render(<PlayingPhase/>);
 const accept=screen.getByRole('button',{name:/Accept synthetic foul/});
 fireEvent.click(accept);await act(async()=>{});
 expect(screen.getByRole('alert')).toHaveTextContent('Save needs attention');
 expect(accept).toBeEnabled();expect(screen.getByText('PENALTY ON THE PLAY!')).toBeVisible();
 gameFetch.mockResolvedValueOnce({ok:true,json:async()=>({game_state:{...state,down:2,player_offense:false},result:{description:'Penalty accepted'}})});
 fireEvent.click(accept);await act(async()=>{});
 expect(screen.queryByRole('alert')).toBeNull();
 expect(screen.queryByText('PENALTY ON THE PLAY!')).toBeNull();
});

it.each([true, false])('keeps an expired-clock kickoff touchdown in playing only while a try is owed (%s)', async pendingPat => {
 gameFetch.mockResolvedValueOnce({ok:true,json:async()=>({
  game_state:{...state,is_kickoff:false,pending_pat:pendingPat,game_over:true,quarter:4,time_remaining:0},
  result:{description:'Kickoff fumble recovered for a touchdown',touchdown:true,turnover:true},
 })});
 useGameStore.getState().restoreSession({game_id:'final-kick',game_state:{...state,is_kickoff:true,quarter:4,time_remaining:1}});
 render(<PlayingPhase/>);
 fireEvent.click(screen.getByRole('button',{name:'KICK OFF'}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(gameFetch).toHaveBeenCalledTimes(1);
 expect(useGameStore.getState().gameOver).toBe(true);
 expect(useGameStore.getState().pendingPat).toBe(pendingPat);
 expect(useGameStore.getState().gamePhase).toBe(pendingPat?'playing':'gameOver');
 if(pendingPat) expect(screen.getByRole('button',{name:'Try kick'})).toBeVisible();
});

it('automatically takes a CPU-owned kickoff touchdown try exactly once', async () => {
 gameFetch.mockResolvedValueOnce({ok:true,json:async()=>({
  game_state:{...state,player_offense:false,is_kickoff:false,pending_pat:true,home_score:0,away_score:6},
  result:{description:'CPU recovers kickoff fumble for a touchdown',touchdown:true,turnover:true},
 })}).mockResolvedValueOnce({ok:true,json:async()=>({
  game_state:{...state,player_offense:false,is_kickoff:true,pending_pat:false,home_score:0,away_score:7},
  is_kickoff:true,success:true,description:'Extra point good',
 })});
 useGameStore.getState().restoreSession({game_id:'cpu-kick',game_state:{...state,is_kickoff:true}});
 render(<PlayingPhase/>);
 fireEvent.click(screen.getByRole('button',{name:'KICK OFF'}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(gameFetch).toHaveBeenCalledTimes(2);
 expect(gameFetch.mock.calls[1][0]).toMatch(/\/api\/game\/extra-point$/);
 expect(JSON.parse(gameFetch.mock.calls[1][1].body)).toEqual({game_id:'cpu-kick',player_play:'XP'});
 await act(async()=>{await vi.advanceTimersByTimeAsync(2100)});
 expect(gameFetch).toHaveBeenCalledTimes(2);
 expect(useGameStore.getState().pendingPat).toBe(false);
 expect(useGameStore.getState().awayScore).toBe(7);
 expect(screen.getByRole('button',{name:'KICK OFF'})).toBeVisible();
});
