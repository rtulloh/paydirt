import React from 'react';
import {render,screen,cleanup,fireEvent,act,waitFor} from '@testing-library/react';
import {it,expect,afterEach,vi} from 'vitest';
import {gameFetch} from '../../runtime/gameFetch';
import PlayingPhase from './PlayingPhase';
import {useGameStore} from '../../store/gameStore';
const handlers=vi.hoisted(()=>({}));
vi.mock('../../runtime/sessionPersistence',()=>({sessionPersistence:{getFailure:()=>null}}));
vi.mock('../../runtime/gameFetch',()=>({gameFetch:vi.fn(async()=>({ok:true,json:async()=>({game_state:{home_team:{},away_team:{},quarter:3,time_remaining:900,pending_pat:false},result:{description:'Try complete'}})})),browserMode:false,saveCurrentSession:vi.fn()}));
vi.mock('../Scoreboard/Scoreboard',()=>({default:()=>null}));
vi.mock('../Field/FootballField',()=>({default:()=>null}));
vi.mock('../Dice/DiceDisplay',()=>({default:()=>null}));
vi.mock('../Plays/OffensePlays',()=>({default:props=>{handlers.offense=props.onSelectPlay;return <button disabled={props.disabled}>offense snap</button>}}));
vi.mock('../Plays/DefensePlays',()=>({default:props=>{handlers.defense=props.onSelectPlay;return <button disabled={props.disabled}>defense snap</button>}}));
afterEach(()=>{cleanup();vi.clearAllMocks();useGameStore.getState().reset()});
function setup(extra={}){useGameStore.getState().restoreSession({game_id:'half',game_state:{home_team:{},away_team:{},quarter:3,time_remaining:900,player_offense:true,halftime_pending:true,down:1,...extra}});render(<PlayingPhase/>)}
it.each([true,false])('blocks a fast normal play at halftime, offense=%s',async offense=>{
 setup({player_offense:offense});
 expect(screen.getByRole('button',{name:offense?'offense snap':'defense snap'})).toBeDisabled();
 await act(async()=>handlers[offense?'offense':'defense']('1'));
 expect(gameFetch).not.toHaveBeenCalled();
});
it('keeps normal snaps blocked after acknowledgment until the second-half kickoff',async()=>{
 setup();fireEvent.click(screen.getByTestId('continue-button'));
 await act(async()=>handlers.offense('1'));
 expect(gameFetch).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'KICK OFF',exact:true}));
 await waitFor(()=>expect(gameFetch).toHaveBeenCalled(),{timeout:3000});
 expect(gameFetch.mock.calls[0][0]).toContain('/api/game/kickoff');
});
it('does not suppress the owed human try while halftime is pending',async()=>{
 setup({pending_pat:true,player_offense:true});
 expect(screen.queryByTestId('halftime')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'KICK XP (1 PT)',exact:true}));
 await waitFor(()=>expect(gameFetch).toHaveBeenCalled());
 expect(gameFetch.mock.calls[0][0]).toContain('/api/game/extra-point');
});
it('permits a normal first-half coaching request',async()=>{
 setup({quarter:2,halftime_pending:false,time_remaining:200});
 expect(screen.getByRole('button',{name:'offense snap'})).toBeEnabled();
 await act(async()=>handlers.offense('1'));
 expect(gameFetch.mock.calls[0][0]).toContain('/api/game/cpu-play');
});

it('rejects an already captured click callback after authoritative halftime arrives',async()=>{
 setup({quarter:2,halftime_pending:false});
 const earlyClick=handlers.offense;
 act(()=>useGameStore.setState({halftimePending:true,quarter:3,timeRemaining:900}));
 await act(async()=>earlyClick('1'));
 expect(gameFetch).not.toHaveBeenCalled();
});

it.each([true,false])('withholds normal plays while a kickoff is owed, offense=%s',async offense=>{
 setup({halftime_pending:false,quarter:1,is_kickoff:true,player_offense:offense});
 expect(screen.getByRole('button',{name:offense?'offense snap':'defense snap'})).toBeDisabled();
 await act(async()=>handlers[offense?'offense':'defense']('1'));
 expect(gameFetch).not.toHaveBeenCalled();
 expect(screen.getByRole('button',{name:'KICK OFF',exact:true})).toBeEnabled();
});
it('rejects an old normal-play callback when a kickoff becomes authoritative',async()=>{
 setup({halftime_pending:false,quarter:1,is_kickoff:false});
 const earlyClick=handlers.offense;
 act(()=>useGameStore.setState({isKickoff:true}));
 await act(async()=>earlyClick('1'));
 expect(gameFetch).not.toHaveBeenCalled();
});
