import { useCallback } from 'react';
import { useGameStore } from '../store/gameStore';
import { API_BASE } from '../../config';

const BLACK_DIE = [1, 1, 2, 2, 3, 3];
const WHITE_DIE = [0, 1, 2, 3, 4, 5];
const RED_DIE = [1, 1, 1, 2, 2, 3];
const GREEN_DIE = [0, 0, 0, 0, 1, 2];

const randomFrom = (arr: number[]): number => arr[Math.floor(Math.random() * arr.length)];

interface DiceResult {
  offenseRoll: {
    black: number;
    white1: number;
    white2: number;
  };
  defenseRoll: {
    red: number;
    green: number;
  };
  result: number;
}

interface UseGameLogicReturn {
  executePlay: (play: string, cpuPlayValue: string | null) => Promise<void>;
  handleKickoff: () => Promise<void>;
  handlePenaltyDecision: (acceptPenalty: boolean, penaltyIndex: number) => Promise<void>;
  setLocalExecuting: (value: boolean) => void;
  setLocalIsRolling: (value: boolean) => void;
  setLocalDiceResult: (result: DiceResult | null) => void;
  setLocalLastResult: (result: any) => void;
  setLocalShowPenaltyChoice: (value: boolean) => void;
  setLocalPendingPenaltyData: (data: any) => void;
  localDiceResult: DiceResult | null;
  localIsRolling: boolean;
}

export function useGameLogic(
  localDiceResult: DiceResult | null,
  setLocalDiceResult: (result: DiceResult | null) => void,
  localIsRolling: boolean,
  setLocalIsRolling: (value: boolean) => void,
  setLocalLastResult: (result: any) => void,
  setLocalExecuting: (value: boolean) => void,
  setLocalShowPenaltyChoice: (value: boolean) => void,
  setLocalPendingPenaltyData: (data: any) => void,
): UseGameLogicReturn {
  const store = useGameStore();
  const {
    gameId,
    homeTeam,
    awayTeam,
    down,
    yardsToGo,
    ballPosition,
    playerOffense,
    updateGameState,
    addToPlayLog,
    setIsKickoff,
    setGamePhase,
    setHumanPlaySelected,
  } = store;

  const handleKickoff = useCallback(async () => {
    setLocalExecuting(true);
    setLocalLastResult(null);
    setLocalDiceResult(null);
    setLocalIsRolling(false);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setLocalIsRolling(true);
      setLocalDiceResult({
        offenseRoll: {
          black: randomFrom(BLACK_DIE),
          white1: randomFrom(WHITE_DIE),
          white2: randomFrom(WHITE_DIE),
        },
        defenseRoll: {
          red: randomFrom(RED_DIE),
          green: randomFrom(GREEN_DIE),
        },
        result: 0,
      });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const res = await fetch(`${API_BASE}/api/game/kickoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          kickoff_spot: 35,
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setLocalLastResult(data.result);
        updateGameState(data.game_state);
        setLocalIsRolling(false);
        setIsKickoff(false);
        
        const kickingTeam = data.game_state.possession === 'home' 
          ? (homeTeam?.short_name || 'HOME') 
          : (awayTeam?.short_name || 'AWAY');
        const receivingTeam = data.game_state.possession === 'home' 
          ? (awayTeam?.short_name || 'AWAY') 
          : (homeTeam?.short_name || 'HOME');
        
        const offDice = localDiceResult?.offenseRoll;
        const defDice = localDiceResult?.defenseRoll;
        
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: 1,
          yardsToGo: 10,
          ballPosition: 35,
          lineOfScrimmage: 35,
          offenseTeam: kickingTeam,
          defenseTeam: receivingTeam,
          homeTeamAbbrev: homeTeam?.short_name || 'HOME',
          awayTeamAbbrev: awayTeam?.short_name || 'AWAY',
          playerTeam: playerOffense ? kickingTeam : receivingTeam,
          offensePlay: 'KO',
          defensePlay: 'KR',
          offenseDice: offDice ? {
            black: offDice.black,
            white1: offDice.white1,
            white2: offDice.white2,
            total: offDice.black + offDice.white1 + offDice.white2
          } : null,
          defenseDice: defDice ? {
            red: defDice.red,
            green: defDice.green,
            total: defDice.red + defDice.green
          } : null,
          description: data.result.description,
          yards: data.result.yards || 0,
          newPosition: data.game_state.ball_position,
          scoreChange: data.result.touchdown ? `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}` : null,
        });
        
        if (data.game_state.game_over) {
          setGamePhase('gameOver');
        }
      }
    } catch (err) {
      console.error('Failed to perform kickoff:', err);
    } finally {
      setLocalExecuting(false);
    }
  }, [gameId, homeTeam, awayTeam, playerOffense, addToPlayLog, localDiceResult, setIsKickoff, setGamePhase, setLocalDiceResult, setLocalExecuting, setLocalIsRolling, setLocalLastResult, updateGameState]);

  const handlePenaltyDecision = useCallback(async (acceptPenalty: boolean, penaltyIndex: number = 0) => {
    setLocalShowPenaltyChoice(false);
    setLocalPendingPenaltyData(null);
    
    if (!gameId) {
      console.error('No game ID for penalty decision');
      return;
    }
    
    setLocalExecuting(true);
    try {
      const body = {
        game_id: gameId,
        penalty_index: Number(penaltyIndex) || 0,
        accept_penalty: Boolean(acceptPenalty),
      };
      
      const res = await fetch(`${API_BASE}/api/game/penalty-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (res.ok) {
        const data = await res.json();
        updateGameState(data.game_state);
      } else {
        const error = await res.text();
        console.error('Penalty decision failed:', res.status, error);
      }
    } catch (err) {
      console.error('Failed to handle penalty decision:', err);
    } finally {
      setLocalExecuting(false);
    }
  }, [gameId, setLocalShowPenaltyChoice, setLocalPendingPenaltyData, setLocalExecuting, updateGameState]);

  const executePlay = useCallback(async (play: string, cpuPlayValue: string | null = null) => {
    if (!gameId) return;
    
    const prePlayDown = down;
    const prePlayYardsToGo = yardsToGo;
    const prePlayBallPosition = ballPosition;
    
    setLocalExecuting(true);
    setLocalLastResult(null);
    setLocalDiceResult(null);
    setLocalIsRolling(false);
    
    try {
      if (!cpuPlayValue) {
        const cpuRes = await fetch(`${API_BASE}/api/game/cpu-play`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            game_id: gameId,
            player_play: play,
          })
        });
        
        if (cpuRes.ok) {
          const cpuData = await cpuRes.json();
          cpuPlayValue = cpuData.cpu_play;
        }
      }
      
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setLocalIsRolling(true);
      setLocalDiceResult({
        offenseRoll: {
          black: randomFrom(BLACK_DIE),
          white1: randomFrom(WHITE_DIE),
          white2: randomFrom(WHITE_DIE),
        },
        defenseRoll: {
          red: randomFrom(RED_DIE),
          green: randomFrom(GREEN_DIE),
        },
        result: 0,
      });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const res = await fetch(`${API_BASE}/api/game/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_play: play,
          cpu_play: cpuPlayValue,
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (data.result && data.result.pending_penalty_decision && data.result.penalty_choice) {
          setLocalPendingPenaltyData(data.result);
          setLocalShowPenaltyChoice(true);
          setLocalIsRolling(false);
          setLocalExecuting(false);
          return;
        }
        
        setLocalLastResult(data.result);
        updateGameState(data.game_state);
        setLocalIsRolling(false);
        
        const offDice = localDiceResult?.offenseRoll;
        const defDice = localDiceResult?.defenseRoll;
        const offenseDice = offDice ? {
          black: offDice.black,
          white1: offDice.white1,
          white2: offDice.white2,
          total: offDice.black + offDice.white1 + offDice.white2
        } : null;
        const defenseDice = defDice ? {
          red: defDice.red,
          green: defDice.green,
          total: defDice.red + defDice.green
        } : null;
        
        const offenseTeam = playerOffense 
          ? (homeTeam?.short_name || 'HOME') 
          : (awayTeam?.short_name || 'AWAY');
        const defenseTeam = playerOffense 
          ? (awayTeam?.short_name || 'AWAY') 
          : (homeTeam?.short_name || 'HOME');
        const homeAbbrev = homeTeam?.short_name || 'HOME';
        const awayAbbrev = awayTeam?.short_name || 'AWAY';
        const scoreChange = data.result.touchdown || data.result.safety
          ? `SCORE! ${data.game_state.home_score}-${data.game_state.away_score}`
          : null;
        
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: prePlayDown,
          yardsToGo: prePlayYardsToGo,
          ballPosition: prePlayBallPosition,
          lineOfScrimmage: prePlayBallPosition,
          offenseTeam,
          defenseTeam,
          homeTeamAbbrev: homeAbbrev,
          awayTeamAbbrev: awayAbbrev,
          playerTeam: playerOffense ? offenseTeam : defenseTeam,
          offensePlay: play,
          defensePlay: cpuPlayValue,
          offenseDice,
          defenseDice,
          description: data.result.description,
          headline: data.result.headline,
          yards: data.result.yards || 0,
          newPosition: data.game_state.ball_position,
          scoreChange,
          turnover: data.result.turnover,
          bigPlayFactor: data.result.big_play_factor,
        });
      }
    } catch (err) {
      console.error('Failed to execute play:', err);
    } finally {
      setLocalExecuting(false);
    }
  }, [gameId, down, yardsToGo, ballPosition, homeTeam, awayTeam, playerOffense, addToPlayLog, localDiceResult, setLocalDiceResult, setLocalExecuting, setLocalIsRolling, setLocalLastResult, setLocalPendingPenaltyData, setLocalShowPenaltyChoice, updateGameState]);

  return {
    executePlay,
    handleKickoff,
    handlePenaltyDecision,
    setLocalExecuting,
    setLocalIsRolling,
    setLocalDiceResult,
    setLocalLastResult,
    setLocalShowPenaltyChoice,
    setLocalPendingPenaltyData,
    localDiceResult,
    localIsRolling,
  };
}
