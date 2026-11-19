import { expect,it } from 'vitest';
import { useGameStore } from './gameStore';
it('uses canonical live history without duplicating component display entries',()=>{
 useGameStore.getState().reset();
 const history=[{description:'Engine kickoff',possession:'away',possessionSemantics:'preplay'}];
 useGameStore.getState().updateGameState({play_history:history});
 useGameStore.getState().addToPlayLog({description:'Duplicate component kickoff'});
 expect(useGameStore.getState().playLog).toEqual(history);
 useGameStore.getState().restoreSession({game_id:'restored',game_state:{play_history:history},play_history:history});
 expect(useGameStore.getState().playLog).toEqual(history);
});
it('retains component append compatibility without canonical history',()=>{
 useGameStore.getState().reset();useGameStore.getState().addToPlayLog({description:'Legacy'});
 expect(useGameStore.getState().playLog).toEqual([{description:'Legacy'}]);
});
it('restores a pending coin toss instead of prematurely opening play',()=>{useGameStore.getState().restoreSession({game_id:'new',game_state:{game_over:false,home_team:{},away_team:{}},play_history:[]},{phase:'coinToss'});expect(useGameStore.getState().gamePhase).toBe('coinToss')});
it('displays completed games as finals and resets stale UI selections',()=>{useGameStore.setState({pendingDefensePlay:'BLITZ',selectedModifier:'S'});useGameStore.getState().restoreSession({game_id:'new',game_state:{game_over:true,home_team:{},away_team:{}},play_history:[{description:'Final'}]});expect(useGameStore.getState()).toMatchObject({gamePhase:'gameOver',pendingDefensePlay:null,selectedModifier:null,playLog:[{description:'Final'}]})});

it('keeps governing rules separate from each chart year',()=>{useGameStore.getState().restoreSession({game_id:'mixed',game_state:{home_team:{season:'2026'},away_team:{season:'2025'},rules_season:'2024'}});expect(useGameStore.getState().rulesSeason).toBe('2024');expect(useGameStore.getState().homeTeam.season).toBe('2026')});

it.each([{pending_penalty_decision:true,penalty_choice:{description:'Choose foul'}},{pending_end_zone_interception_return_decision:true,int_catch_depth:4}])('restores authoritative pending choice before terminal phase',pending=>{useGameStore.getState().restoreSession({game_id:'pending',game_state:{game_over:true,halftime_pending:true},pending_result:pending});expect(useGameStore.getState()).toMatchObject({gamePhase:'playing',restoredPendingResult:pending})});
it('clears pending choice on a different restore',()=>{useGameStore.setState({restoredPendingResult:{pending_penalty_decision:true}});useGameStore.getState().restoreSession({game_id:'plain',game_state:{}});expect(useGameStore.getState().restoredPendingResult).toBeNull()});

it('keeps an expired regulation touchdown in play until its owed try resolves',()=>{useGameStore.getState().restoreSession({game_id:'owed',game_state:{game_over:true,pending_pat:true}});expect(useGameStore.getState()).toMatchObject({gamePhase:'playing',gameOver:true,pendingPat:true})});
