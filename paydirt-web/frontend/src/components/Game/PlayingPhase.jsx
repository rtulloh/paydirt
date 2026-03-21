import React, { useEffect, useState } from 'react';
import Scoreboard from '../Scoreboard/Scoreboard';
import FootballField from '../Field/FootballField';
import DiceDisplay from '../Dice/DiceDisplay';
import OffensePlays from '../Plays/OffensePlays';
import DefensePlays from '../Plays/DefensePlays';
import PenaltyDecisionPanel from './PenaltyDecisionPanel';
import PATChoicePanel from './PATChoicePanel';
import CpuDecisionPanel from './CpuDecisionPanel';
import PlayLogDisplay from './PlayLogDisplay';
import GameControls from './GameControls.tsx';
import { useGameStore } from '../../store/gameStore';
import { API_BASE } from '../../config';

const BLACK_DIE = [1, 1, 2, 2, 3, 3];
const WHITE_DIE = [0, 1, 2, 3, 4, 5];
const RED_DIE = [1, 1, 1, 2, 2, 3];
const GREEN_DIE = [0, 0, 0, 0, 1, 2];

const randomFrom = (arr) => arr[Math.floor(Math.random() * arr.length)];

const PlayingPhase = () => {
  const store = useGameStore();
  const {
    gameId,
    homeTeam,
    awayTeam,
    homeScore,
    awayScore,
    quarter,
    timeRemaining,
    possession,
    ballPosition,
    down,
    yardsToGo,
    homeTimeouts,
    awayTimeouts,
    playerOffense,
    humanPlaySelected,
    setHumanPlay,
    updateGameState,
    setGamePhase,
    cpuFourthDownDecision,
    clearCpuFourthDownDecision,
    executing,
    lastResult,
    isRolling,
    diceResult,
    playLog,
    addToPlayLog,
    showCpuDecision,
    showPatChoice,
    patResult,
    canGoForTwo,
    cpuShouldGoForTwo,
    showPenaltyChoice,
    pendingPenaltyData,
    isKickoff,
    setIsKickoff,
  } = store;

  const [localLastResult, setLocalLastResult] = useState(null);
  const [localDiceResult, setLocalDiceResult] = useState(null);
  const [localIsRolling, setLocalIsRolling] = useState(false);
  const [localShowPatChoice, setLocalShowPatChoice] = useState(false);
  const [localPatResult, setLocalPatResult] = useState(null);
  const [localShowPenaltyChoice, setLocalShowPenaltyChoice] = useState(false);
  const [localPendingPenaltyData, setLocalPendingPenaltyData] = useState(null);
  const [localExecuting, setLocalExecuting] = useState(false);

  // Auto-clear result banner for non-special plays after 2 seconds
  useEffect(() => {
    if (localLastResult && !localExecuting && !localShowPatChoice && !localShowPenaltyChoice) {
      const isSpecial = localLastResult?.turnover || localLastResult?.touchdown || 
                        localLastResult?.safety || localLastResult?.pending_penalty_decision;
      
      if (!isSpecial) {
        const timer = setTimeout(() => {
          setLocalLastResult(null);
          setLocalDiceResult(null);
          setHumanPlay(null);
        }, 2000);
        return () => clearTimeout(timer);
      }
    }
  }, [localLastResult, localExecuting, localShowPatChoice, localShowPenaltyChoice]);

  const handleKickoff = async () => {
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
        console.log('=== KICKOFF RESULT ===');
        console.log('player_offense:', data.game_state.player_offense);
        console.log('possession:', data.game_state.possession);
        console.log('human_is_home:', data.game_state.human_is_home);
        console.log('human_team_id:', data.game_state.human_team_id);
        console.log('home_team:', data.game_state.home_team?.id);
        console.log('away_team:', data.game_state.away_team?.id);
        setLocalLastResult(data.result);
        updateGameState(data.game_state);
        console.log('After updateGameState:');
        console.log('  playerOffense from store:', useGameStore.getState().playerOffense);
        console.log('  possession from store:', useGameStore.getState().possession);
        console.log('  humanIsHome from store:', useGameStore.getState().humanIsHome);
        console.log('=======================');
        setLocalIsRolling(false);
        setLocalExecuting(false);  // Enable play buttons after kickoff
        setIsKickoff(false);
        
        // Log the kickoff
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
  };

  const handlePatKick = async () => {
    setLocalExecuting(true);
    try {
      const res = await fetch(`${API_BASE}/api/game/extra-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          play: 'XP',
        })
      });
      if (res.ok) {
        const data = await res.json();
        setLocalPatResult({
          type: 'extra_point',
          success: data.result.description.includes('GOOD'),
          description: data.result.description,
        });
        updateGameState(data.game_state);
        await new Promise(r => setTimeout(r, 2000));
        setLocalPatResult(null);
      }
    } catch (err) {
      console.error('Failed to attempt extra point:', err);
    } finally {
      setLocalExecuting(false);
      setLocalShowPatChoice(false);
    }
  };

  const handlePatTwoPoint = async () => {
    setLocalExecuting(true);
    try {
      const res = await fetch(`${API_BASE}/api/game/two-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          play: '2PT',
        })
      });
      if (res.ok) {
        const data = await res.json();
        setLocalPatResult({
          type: 'two_point',
          success: data.result.description.includes('GOOD'),
          description: data.result.description,
        });
        updateGameState(data.game_state);
        await new Promise(r => setTimeout(r, 2000));
        setLocalPatResult(null);
      }
    } catch (err) {
      console.error('Failed to attempt two-point conversion:', err);
    } finally {
      setLocalExecuting(false);
      setLocalShowPatChoice(false);
    }
  };

  const handleCpuPat = async () => {
    // CPU PAT is auto-handled by backend
    setLocalShowPatChoice(false);
  };

  const handleCpuTwoPoint = async () => {
    // CPU two-point is auto-handled by backend
    setLocalShowPatChoice(false);
  };

  const handleNewGame = () => {
    // Reset game state
    const { reset } = useGameStore.getState();
    reset();
    // Set phase to team select
    const { setGamePhase } = useGameStore.getState();
    setGamePhase('teamSelect');
  };

  const handleReturnToMenu = () => {
    const { reset, setGamePhase } = useGameStore.getState();
    reset();
    setGamePhase('menu');
  };

  const handleSaveGame = () => {
    const { saveGame } = useGameStore.getState();
    const state = useGameStore.getState();
    saveGame({
      gameId: state.gameId,
      homeTeam: state.homeTeam,
      awayTeam: state.awayTeam,
      homeScore: state.homeScore,
      awayScore: state.awayScore,
      quarter: state.quarter,
      timeRemaining: state.timeRemaining,
      possession: state.possession,
      ballPosition: state.ballPosition,
      down: state.down,
      yardsToGo: state.yardsToGo,
      homeTimeouts: state.homeTimeouts,
      awayTimeouts: state.awayTimeouts,
      humanPlaysOffense: state.humanPlaysOffense,
      humanTeamId: state.humanTeamId,
      cpuTeamId: state.cpuTeamId,
      playLog: state.playLog,
    });
  };

  const handleSaveReplay = async () => {
    if (!gameId) {
      console.error('No game ID for saving replay');
      return;
    }
    
    const { saveReplay } = useGameStore.getState();
    try {
      await saveReplay(gameId);
      alert('Replay saved! You can reload it from the menu.');
    } catch (err) {
      console.error('Failed to save replay:', err);
      alert('Failed to save replay');
    }
  };

  const executePlay = async (play) => {
    if (!gameId || localExecuting) return;
    
    // Store state BEFORE the play for the log
    const prePlayDown = down;
    const prePlayYardsToGo = yardsToGo;
    const prePlayBallPosition = ballPosition;
    
    setLocalExecuting(true);
    setLocalLastResult(null);
    setLocalDiceResult(null);
    setLocalIsRolling(false);
    
    let cpuPlayValue = null;
    
    try {
      // Get CPU's play choice
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
      
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Roll dice animation
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
      
      // Execute the play
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
        
        // Check if there's a penalty decision pending
        if (data.result && data.result.pending_penalty_decision && data.result.penalty_choice) {
          setLocalPendingPenaltyData(data.result);
          setLocalShowPenaltyChoice(true);
          setLocalIsRolling(false);
          setLocalExecuting(false);
          return;
        }
        
        setLocalLastResult(data.result);
        console.log('Backend response player_offense:', data.game_state.player_offense);
        console.log('Dice details from backend:', data.dice_details);
        updateGameState(data.game_state);
        console.log('Store playerOffense after update:', useGameStore.getState().playerOffense);
        setLocalIsRolling(false);
        
        // Use dice from backend response - already calculated correctly
        const offDice = data.dice_details?.offense;
        const defDice = data.dice_details?.defense;
        const offenseDice = offDice ? {
          black: offDice.black,
          white1: offDice.white1,
          white2: offDice.white2,
          total: offDice.total
        } : null;
        const defenseDice = defDice ? {
          red: defDice.red,
          green: defDice.green,
          total: defDice.total
        } : null;
        
        // Log the play with BEFORE state for down/distance, AFTER state for position
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
        
        // Use pre-play state for the play description, post-play for new position
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
  };

  const handleOffensePlay = (play) => {
    executePlay(play);
  };

  const handleDefensePlay = (play) => {
    executePlay(play);
  };

  const handlePenaltyDecision = async (acceptPenalty, penaltyIndex = 0) => {
    // Always dismiss the modal first
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
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      <Scoreboard
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        quarter={quarter}
        timeRemaining={timeRemaining}
        down={down}
        yardsToGo={yardsToGo}
        ballPosition={ballPosition}
        possession={possession}
        homeTimeouts={homeTimeouts}
        awayTimeouts={awayTimeouts}
      />

      <div className="flex-shrink-0 px-4 py-4">
        <FootballField 
          ballPosition={ballPosition} 
          possession={possession}
          homeEndzoneColor={homeTeam?.team_color || '#8B0000'}
          homeTeamName={homeTeam?.name || homeTeam?.abbreviation || 'HOME'}
          yardsToGo={yardsToGo}
        />
      </div>

      {/* Inline Kickoff Banner - More Prominent */}
      {isKickoff && !localExecuting && !localLastResult && (
        <div className="px-4 py-4 mx-4 mt-4 bg-gradient-to-r from-blue-800 to-blue-600 rounded-xl text-center shadow-lg border-2 border-blue-400">
          <div className="text-2xl font-bold text-white mb-3 uppercase tracking-wider">KICKOFF</div>
          <div className="text-lg text-blue-100 mb-4">
            {playerOffense 
              ? `${homeTeam?.short_name || 'HOME'} kicks off to ${awayTeam?.short_name || 'AWAY'}`
              : `${awayTeam?.short_name || 'AWAY'} kicks off to ${homeTeam?.short_name || 'HOME'}`
            }
          </div>
          <button
            onClick={handleKickoff}
            className="px-10 py-4 bg-white text-blue-700 rounded-lg font-bold text-xl hover:bg-blue-100 transition-all shadow-md"
          >
            KICK OFF
          </button>
        </div>
      )}

      {(localIsRolling || localDiceResult) && (
        <div className="px-4 pb-2">
          <DiceDisplay
            offenseRoll={localDiceResult?.offenseRoll}
            defenseRoll={localDiceResult?.defenseRoll}
            result={localDiceResult?.result}
            isRolling={localIsRolling}
            onAnimationComplete={() => {}}
          />
        </div>
      )}

      {localLastResult && (
        <div className="px-4 pb-2">
          <div className={`rounded-lg px-4 py-2 text-center ${
            localLastResult.big_play_factor >= 3 ? 'bg-red-700' :
            localLastResult.big_play_factor >= 2 ? 'bg-orange-700' :
            localLastResult.big_play_factor >= 1 ? 'bg-yellow-700' :
            'bg-gray-800'
          }`}>
            <div className="text-white font-bold text-lg">{localLastResult.headline || localLastResult.description}</div>
            {localLastResult.commentary && (
              <div className="text-white/80 text-sm mt-1">{localLastResult.commentary}</div>
            )}
          </div>
        </div>
      )}

      {showCpuDecision && cpuFourthDownDecision && (
        <div className="px-4 pb-2">
          <CpuDecisionPanel 
            decision={cpuFourthDownDecision} 
            onExecute={executePlay} 
            onCancel={() => {
              clearCpuFourthDownDecision();
            }}
          />
        </div>
      )}

      {localShowPatChoice && (
        <div className="px-4 pb-2">
          <PATChoicePanel 
            canGoForTwo={canGoForTwo} 
            cpuShouldGoForTwo={cpuShouldGoForTwo} 
            scoringTeamIsPlayer={false}
            onPatKick={handlePatKick}
            onPatTwoPoint={handlePatTwoPoint}
            onCpuPat={handleCpuPat}
            onCpuTwoPoint={handleCpuTwoPoint}
          />
        </div>
      )}

      {localPatResult && (
        <div className="px-4 pb-2">
          <div className={`rounded-lg px-4 py-4 text-center ${localPatResult.success ? 'bg-green-700' : 'bg-red-700'}`}>
            <div className="text-xl font-bold text-white">
              {localPatResult.type === 'two_point' ? 'TWO-POINT CONVERSION' : 'EXTRA POINT'}
            </div>
            <div className="text-2xl font-bold text-white mt-2">
              {localPatResult.success ? 'GOOD!' : 'NO GOOD!'}
            </div>
            <div className="text-white mt-1">{localPatResult.description}</div>
          </div>
        </div>
      )}

      {localShowPenaltyChoice && localPendingPenaltyData && (
        <div className="px-4 pb-2">
          <PenaltyDecisionPanel 
            penaltyData={localPendingPenaltyData} 
            onDecision={handlePenaltyDecision} 
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          {playerOffense ? (
            <OffensePlays
              selectedPlay={humanPlaySelected}
              onSelectPlay={handleOffensePlay}
              isHumanTurn={true}
              disabled={localExecuting}
            />
          ) : (
            <DefensePlays
              selectedPlay={humanPlaySelected}
              onSelectPlay={handleDefensePlay}
              isHumanTurn={true}
              disabled={localExecuting}
            />
          )}
          
          <PlayLogDisplay plays={playLog} onPlayClick={() => {}} />
        </div>
      </div>

      {/* Play Result - Show CONTINUE button for special plays only */}
      {localLastResult && !localExecuting && !localIsRolling && !localShowPatChoice && !localShowPenaltyChoice && (
        (() => {
          const result = localLastResult;
          const isSpecial = result?.turnover || result?.touchdown || result?.safety || result?.pending_penalty_decision;
          return isSpecial ? (
            <div className="px-4 pb-2">
              <button
                onClick={() => {
                  setLocalLastResult(null);
                  setLocalDiceResult(null);
                  setHumanPlay(null);
                }}
                className="w-full py-3 bg-green-600 text-white rounded-lg font-bold text-lg hover:bg-green-700"
              >
                CONTINUE
              </button>
            </div>
          ) : null;
        })()
      )}

      {/* Bottom Controls */}
      <div className="px-4 pb-4 flex justify-between items-center">
        <button
          onClick={handleReturnToMenu}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          EXIT
        </button>
        <div className="flex gap-2">
          <button
            onClick={handleSaveReplay}
            className="px-4 py-2 bg-purple-700 text-white rounded-lg hover:bg-purple-600 text-sm"
          >
            SAVE REPLAY
          </button>
          <button
            onClick={handleSaveGame}
            className="px-4 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-600"
          >
            SAVE GAME
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlayingPhase;