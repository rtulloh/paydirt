import React, { useEffect, useState, useRef } from 'react';
import Scoreboard from '../Scoreboard/Scoreboard';
import FootballField from '../Field/FootballField';
import DiceDisplay from '../Dice/DiceDisplay';
import OffensePlays from '../Plays/OffensePlays';
import DefensePlays from '../Plays/DefensePlays';
import PenaltyDecisionPanel from './PenaltyDecisionPanel';
import PATChoicePanel from './PATChoicePanel';
import CpuDecisionPanel from './CpuDecisionPanel';
import PuntOptionsPanel from './PuntOptionsPanel';
import PlayLogDisplay from './PlayLogDisplay';
import GameControls from './GameControls.tsx';
import { useGameStore } from '../../store/gameStore';
import { checkPendingPat, deriveKickoffTeams } from '../../utils/gameFlowLogic';
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
    fieldPosition,
    down,
    yardsToGo,
    homeTimeouts,
    awayTimeouts,
    humanIsHome,
    playerOffense,
    humanPlaySelected,
    setHumanPlay,
    updateGameState,
    setGamePhase,
    cpuFourthDownDecision,
    clearCpuFourthDownDecision,
    setCpuFourthDownDecision,
    pendingDefensePlay,
    setPendingDefensePlay,
    clearPendingDefensePlay,
    pendingCpuFourthDown,
    setPendingCpuFourthDown,
    clearPendingCpuFourthDown,
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
    pendingPat,
    setPendingPat,
    isOvertime,
    otPeriod,
  } = store;

  const [localLastResult, setLocalLastResult] = useState(null);
  const [localDiceResult, setLocalDiceResult] = useState(null);
  const [localIsRolling, setLocalIsRolling] = useState(false);
  const [localShowPatChoice, setLocalShowPatChoice] = useState(false);
  const [localPatResult, setLocalPatResult] = useState(null);
  const [scoringTeamIsPlayer, setScoringTeamIsPlayer] = useState(false);
  const [localShowPenaltyChoice, setLocalShowPenaltyChoice] = useState(false);
  const [localPendingPenaltyData, setLocalPendingPenaltyData] = useState(null);
  const [homeScoreFlash, setHomeScoreFlash] = useState(false);
  const [awayScoreFlash, setAwayScoreFlash] = useState(false);
  const prevScoresRef = useRef({ homeScore: undefined, awayScore: undefined });
  const [localExecuting, setLocalExecuting] = useState(false);
  const [showPuntOptions, setShowPuntOptions] = useState(false);
  const [pendingPuntPlay, setPendingPuntPlay] = useState(null);
  const [isKickPlay, setIsKickPlay] = useState(false);

  // Sync pendingPat from store to local state to show PAT panel
  // Only show if player scored (CPU auto-handles their own PAT)
  useEffect(() => {
    if (pendingPat && !localShowPatChoice) {
      // Check if scoring team is the player (not CPU)
      // When player is on offense and pendingPat, they scored
      // When player is on defense and pendingPat, CPU scored (auto-handled)
      const playerScored = playerOffense; // If player has ball, they scored
      if (playerScored) {
        setLocalShowPatChoice(true);
        setScoringTeamIsPlayer(true); // Player scored, so they should see PAT options
      }
    }
  }, [pendingPat, localShowPatChoice, playerOffense]);

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

  // Check for 4th down CPU decision when player is on defense
  useEffect(() => {
    if (!gameId || localExecuting || isKickoff) return;
    if (playerOffense) return;  // Player is on offense, no special handling needed
    if (down !== 4) return;  // Not 4th down
    if (pendingCpuFourthDown) return;  // Already awaiting CPU decision
    
    // Clear any previous CPU decision
    clearPendingCpuFourthDown();
    
    // Call CPU 4th down decision
    const checkCpuDecision = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/game/cpu-4th-down-decision/${gameId}`);
        if (res.ok) {
          const decision = await res.json();
          if (decision.decision === 'go_for_it') {
            // CPU going for it - player needs to pick defense
            // Don't set pendingCpuFourthDown, let player pick defense
          } else {
            // CPU punts or kicks FG - set pending, show panel
            setPendingCpuFourthDown(decision);
          }
        }
      } catch (err) {
        console.error('Failed to get CPU 4th down decision:', err);
      }
    };
    
    checkCpuDecision();
  }, [gameId, localExecuting, isKickoff, playerOffense, down, pendingCpuFourthDown, clearPendingCpuFourthDown, setPendingCpuFourthDown]);

  // Flash scoreboard when home team scores
  useEffect(() => {
    if (homeScoreFlash) {
      const timer = setTimeout(() => setHomeScoreFlash(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [homeScoreFlash]);

  // Flash scoreboard when away team scores
  useEffect(() => {
    if (awayScoreFlash) {
      const timer = setTimeout(() => setAwayScoreFlash(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [awayScoreFlash]);

  // Track score changes to trigger flash effects
  useEffect(() => {
    const prevScores = prevScoresRef.current;
    if (prevScores.homeScore !== undefined && homeScore > prevScores.homeScore) {
      setHomeScoreFlash(true);
    }
    if (prevScores.awayScore !== undefined && awayScore > prevScores.awayScore) {
      setAwayScoreFlash(true);
    }
    prevScoresRef.current = { homeScore, awayScore };
  }, [homeScore, awayScore]);

  const handleKickoff = async () => {
    setLocalExecuting(true);
    setLocalLastResult(null);
    setLocalDiceResult(null);
    setLocalIsRolling(false);
    setIsKickPlay(true);
    
    // Clear any lingering CPU 4th down decision UI
    clearCpuFourthDownDecision();
    clearPendingCpuFourthDown();
    
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
        
        // Check for pending penalty decision on kickoff
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
        setLocalExecuting(false);  // Enable play buttons after kickoff
        setIsKickoff(false);
        
        // Log the kickoff
        // Uses shared deriveKickoffTeams — if this function is removed, tests will fail
        const { kickingTeam, receivingTeam } = deriveKickoffTeams(
          data.game_state.possession, homeTeam, awayTeam
        );
        
        const offDice = localDiceResult?.offenseRoll;
        const defDice = localDiceResult?.defenseRoll;
        
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: 1,
          yardsToGo: 10,
          ballPosition: 35,
          lineOfScrimmage: 35,
          fieldPosition: '35 yard line', // Kickoff spot
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
          newFieldPosition: data.game_state.field_position,
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
          player_play: 'XP',
        })
      });
      if (res.ok) {
        const data = await res.json();
        setLocalPatResult({
          type: 'extra_point',
          success: data.success,
          description: data.description,
        });
        updateGameState(data.game_state);
        setIsKickoff(data.is_kickoff);
        await new Promise(r => setTimeout(r, 2000));
        setLocalPatResult(null);
        setLocalShowPatChoice(false);
        setLocalLastResult(null);
      }
    } catch (err) {
      console.error('Failed to attempt extra point:', err);
    } finally {
      setLocalExecuting(false);
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

  const handleCpuPatAuto = async (gid) => {
    // CPU scored — auto-attempt extra point, show result then kickoff
    try {
      const res = await fetch(`${API_BASE}/api/game/extra-point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gid,
          player_play: 'XP',
        })
      });
      if (res.ok) {
        const data = await res.json();
        setLocalPatResult({
          type: 'extra_point',
          success: data.success,
          description: data.description,
        });

        // Add PAT to play log
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: 1,
          yardsToGo: 10,
          ballPosition: null,
          lineOfScrimmage: null,
          fieldPosition: null,
          offenseTeam: playerOffense
            ? (homeTeam?.short_name || 'HOME')
            : (awayTeam?.short_name || 'AWAY'),
          defenseTeam: playerOffense
            ? (awayTeam?.short_name || 'AWAY')
            : (homeTeam?.short_name || 'HOME'),
          homeTeamAbbrev: homeTeam?.short_name || 'HOME',
          awayTeamAbbrev: awayTeam?.short_name || 'AWAY',
          playerTeam: playerOffense
            ? (homeTeam?.short_name || 'HOME')
            : (awayTeam?.short_name || 'AWAY'),
          offensePlay: 'XP',
          defensePlay: '-',
          description: data.description,
          headline: data.success ? 'Extra Point GOOD' : 'Extra Point NO GOOD',
          yards: 0,
          scoreChange: data.success ? `SCORE! ${data.new_score_home}-${data.new_score_away}` : null,
        });

        updateGameState(data.game_state);
        setIsKickoff(data.is_kickoff);
        await new Promise(r => setTimeout(r, 2000));
        setLocalPatResult(null);
        setLocalLastResult(null);
      }
    } catch (err) {
      console.error('Failed to auto-attempt CPU extra point:', err);
    }
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
      currentSeason: state.currentSeason,
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

  const executePlay = async (play, cpuPlayOverride = null, puntOptions = null) => {
    if (!gameId || localExecuting) return;
    
    // Store state BEFORE the play for the log
    const prePlayDown = down;
    const prePlayYardsToGo = yardsToGo;
    const prePlayBallPosition = ballPosition;
    const prePlayFieldPosition = fieldPosition; // Backend-calculated field position
    
    // Check if this is a kick play (P=punt, F=field goal, K=kickoff)
    const isKick = ['P', 'F', 'K'].includes(play.toUpperCase()) || 
                   ['P', 'F'].includes(cpuPlayOverride?.toUpperCase());
    setIsKickPlay(isKick);
    
    setLocalExecuting(true);
    setLocalLastResult(null);
    setLocalDiceResult(null);
    setLocalIsRolling(false);
    
    // Clear any lingering CPU 4th down decision UI before executing a play
    clearCpuFourthDownDecision();
    clearPendingCpuFourthDown();
    
    let cpuPlayValue = cpuPlayOverride;
    
    try {
      // Get CPU's play choice (unless already provided)
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
          short_drop: puntOptions?.short_drop || false,
          coffin_corner_yards: puntOptions?.coffin_corner_yards || 0,
        })
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('Execute play error:', res.status, errorText);
        alert('Execute play failed: ' + errorText);
        setLocalIsRolling(false);
        setLocalExecuting(false);
        return;
      }
      
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
          fieldPosition: prePlayFieldPosition, // Pre-calculated by backend
          offenseTeam,
          defenseTeam,
          homeTeamAbbrev: homeAbbrev,
          awayTeamAbbrev: awayAbbrev,
          playerTeam: playerOffense ? offenseTeam : defenseTeam,
          offensePlay: playerOffense ? play : cpuPlayValue,
          defensePlay: playerOffense ? cpuPlayValue : play,
          offenseDice,
          defenseDice,
          description: data.result.description,
          headline: data.result.headline,
          yards: data.result.yards || 0,
          newPosition: data.game_state.ball_position,
          newFieldPosition: data.game_state.field_position,
          scoreChange,
          turnover: data.result.turnover,
          bigPlayFactor: data.result.big_play_factor,
          humanIsHome,
          possession: data.game_state.possession,
        });
        
        // After a touchdown, show PAT choice instead of transitioning to kickoff
        // Uses shared checkPendingPat — if this function is removed, tests will fail
        const { isPendingPat, scoringTeamIsPlayer: scoringIsPlayer, canGoForTwo: can2pt } = checkPendingPat(data.game_state);
        if (isPendingPat) {
          setScoringTeamIsPlayer(scoringIsPlayer);
          // Update canGoForTwo in store based on season rules
          if (can2pt !== undefined) {
            store.setCanGoForTwo?.(can2pt);
          }
          
          if (scoringIsPlayer) {
            // Player scored — show PAT choice panel
            setLocalShowPatChoice(true);
            setLocalExecuting(false);
            return;
          } else {
            // CPU scored — auto-attempt extra point
            setLocalExecuting(false);
            await handleCpuPatAuto(gameId);
            return;
          }
        }
      }
    } catch (err) {
      console.error('Failed to execute play:', err);
    } finally {
      setLocalExecuting(false);
    }
  };

  const handleOffensePlay = (play) => {
    // Check if it's a punt - show punt options panel
    if (play === 'P' && playerOffense) {
      setPendingPuntPlay(play);
      setShowPuntOptions(true);
      return;
    }
    executePlay(play);
  };

  const handlePuntOptions = (puntOptions) => {
    setShowPuntOptions(false);
    setPendingPuntPlay(null);
    executePlay('P', null, puntOptions);
  };

  const handleCpuDecisionExecute = () => {
    if (!cpuFourthDownDecision || !pendingDefensePlay) return;
    
    // Execute the CPU's chosen play (punt or FG) with user's defense
    const cpuPlay = cpuFourthDownDecision.play;
    
    // Clear the decision state
    clearCpuFourthDownDecision();
    clearPendingDefensePlay();
    
    // Execute the play
    executePlay(pendingDefensePlay, cpuPlay);
  };

  const handleCpuFourthDownExecute = () => {
    if (!pendingCpuFourthDown) return;
    
    const decision = pendingCpuFourthDown;
    const cpuPlay = decision.play;  // 'F' or 'P'
    
    // When CPU kicks, you're not picking a defense
    // executePlay(play, cpuPlayOverride) where:
    // - play = player's choice (offense or defense based on who's kicking)
    // - cpuPlayOverride = CPU's choice
    // Since CPU is kicking and you're on defense, pass CPU's play as first param with dummy defense
    const playerPlay = 'A';  // Dummy - doesn't matter when CPU kicks
    const cpuPlayOverride = cpuPlay;  // 'F' or 'P'
    
    // Log the CPU's decision
    const offenseTeam = playerOffense 
      ? (homeTeam?.short_name || 'HOME') 
      : (awayTeam?.short_name || 'AWAY');
    const defenseTeam = playerOffense 
      ? (awayTeam?.short_name || 'AWAY') 
      : (homeTeam?.short_name || 'HOME');
    
    addToPlayLog({
      quarter,
      timeRemaining,
      down: 4,
      yardsToGo: yardsToGo,
      ballPosition,
      fieldPosition,
      offenseTeam,
      defenseTeam,
      homeTeamAbbrev: homeTeam?.short_name || 'HOME',
      awayTeamAbbrev: awayTeam?.short_name || 'AWAY',
      playerTeam: playerOffense ? offenseTeam : defenseTeam,
      offensePlay: cpuPlay,
      defensePlay: 'A',  // Default, doesn't matter for punt/FG
      description: `4th & ${yardsToGo} - CPU ${decision.decision === 'punt' ? 'punts' : 'kicks FG'}`,
    });
    
    // Clear the pending state
    clearPendingCpuFourthDown();
    
    // Execute the play
    // play = player's defense ('A'), cpuPlayOverride = CPU's offense ('F' or 'P')
    // Backend: player_play='A' → defense, cpu_play='F' → offense (FG)
    executePlay(playerPlay, cpuPlayOverride);
  };

  const handleDefensePlay = (play) => {
    if (!gameId || localExecuting) return;
    
    // If CPU already decided to punt/FG on 4th down, don't let player pick defense
    if (pendingCpuFourthDown) return;
    
    // On 4th down, need to check CPU decision first
    if (down === 4) {
      // Call CPU decision synchronously - don't allow play until we know the decision
      fetch(`${API_BASE}/api/game/cpu-4th-down-decision/${gameId}`)
        .then(res => res.json())
        .then(decision => {
          if (decision.decision === 'punt' || decision.decision === 'field_goal') {
            // CPU decided to kick - show panel
            setPendingCpuFourthDown(decision);
          } else {
            // CPU going for it - execute the play
            executePlay(play);
          }
        })
        .catch(err => {
          console.error('Failed to get CPU 4th down decision:', err);
          // On error, just execute the play
          executePlay(play);
        });
      return;
    }
    
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
        
        // Log the penalty decision play
        const offenseTeam = playerOffense 
          ? (homeTeam?.short_name || 'HOME') 
          : (awayTeam?.short_name || 'AWAY');
        const defenseTeam = playerOffense 
          ? (awayTeam?.short_name || 'AWAY') 
          : (homeTeam?.short_name || 'HOME');
        const homeAbbrev = homeTeam?.short_name || 'HOME';
        const awayAbbrev = awayTeam?.short_name || 'AWAY';
        
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: data.game_state.down,
          yardsToGo: data.game_state.yards_to_go,
          ballPosition: data.game_state.ball_position,
          lineOfScrimmage: data.game_state.ball_position,
          fieldPosition: data.game_state.field_position,
          newFieldPosition: data.game_state.field_position,
          offenseTeam,
          defenseTeam,
          homeTeamAbbrev: homeAbbrev,
          awayTeamAbbrev: awayAbbrev,
          playerTeam: playerOffense ? offenseTeam : defenseTeam,
          offensePlay: 'PENALTY',
          defensePlay: 'CPU',
          description: data.result.description || 'Penalty decision',
          yards: data.result.yards || 0,
          newPosition: data.game_state.ball_position,
          possession: data.game_state.possession,
        });
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

  const handleCallTimeout = async () => {
    if (!gameId || localExecuting) return;
    
    // Check if human has timeouts
    const humanTimeouts = humanIsHome ? homeTimeouts : awayTimeouts;
    if (humanTimeouts <= 0) return;
    
    setLocalExecuting(true);
    try {
      const res = await fetch(`${API_BASE}/api/game/timeout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      
      if (res.ok) {
        const data = await res.json();
        updateGameState(data.game_state);
        // Log the timeout
        const teamAbbr = humanIsHome ? (homeTeam?.abbreviation || 'HOME') : (awayTeam?.abbreviation || 'AWAY');
        addToPlayLog({
          quarter: data.game_state.quarter,
          timeRemaining: data.game_state.time_remaining,
          down: down,
          yardsToGo: yardsToGo,
          ballPosition: ballPosition,
          offenseTeam: teamAbbr,
          defenseTeam: '',
          playerTeam: teamAbbr,
          offensePlay: 'TO',
          defensePlay: '-',
          description: `${teamAbbr} calls timeout`,
          yards: 0,
          turnover: false,
        });
      } else {
        const error = await res.text();
        console.error('Timeout failed:', res.status, error);
      }
    } catch (err) {
      console.error('Failed to call timeout:', err);
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
        fieldPosition={fieldPosition}
        possession={possession}
        homeTimeouts={homeTimeouts}
        awayTimeouts={awayTimeouts}
        humanIsHome={humanIsHome}
        onCallTimeout={handleCallTimeout}
        canCallTimeout={!localExecuting && !localShowPatChoice && !localShowPenaltyChoice}
        isOvertime={isOvertime || false}
        otPeriod={otPeriod || 0}
        homeScoreFlash={homeScoreFlash}
        awayScoreFlash={awayScoreFlash}
      />

      <div className="flex-shrink-0 px-4 py-4">
        <FootballField 
          ballPosition={ballPosition} 
          possession={possession}
          quarter={quarter}
          homeEndzoneColor={homeTeam?.team_color || '#8B0000'}
          awayEndzoneColor={awayTeam?.team_color || '#1E3A8A'}
          homeTeamName={homeTeam?.name || homeTeam?.abbreviation || 'HOME'}
          awayTeamName={awayTeam?.name || awayTeam?.abbreviation || 'AWAY'}
          yardsToGo={yardsToGo}
        />
      </div>

      {/* Fixed-height container for info panels - prevents layout shifts */}
      <div className="flex-shrink-0 min-h-[140px]">
        {/* Inline Kickoff Banner - More Prominent */}
        {isKickoff && !localExecuting && !localLastResult && (
          <div className="px-4 py-4 mx-4 mt-4 bg-gradient-to-r from-blue-800 to-blue-600 rounded-xl text-center shadow-lg border-2 border-blue-400">
            <div className="text-2xl font-bold text-white mb-3 uppercase tracking-wider">KICKOFF</div>
            <div className="text-lg text-blue-100 mb-4">
              {possession === 'home'
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

        {/* Dice Display - always reserve space */}
        <div className="px-4 pb-2 min-h-[80px] flex items-center justify-center">
          {(localIsRolling || localDiceResult) ? (
            <DiceDisplay
              offenseRoll={localDiceResult?.offenseRoll}
              defenseRoll={localDiceResult?.defenseRoll}
              result={localDiceResult?.result}
              isRolling={localIsRolling}
              onAnimationComplete={() => { setIsKickPlay(false); }}
              hideDefenseDice={isKickPlay}
            />
          ) : (
            <div className="h-[80px] flex items-center justify-center text-gray-500 text-sm">
              {/* Placeholder to reserve space */}
            </div>
          )}
        </div>

        {/* Result Banner */}
        {localLastResult && (
          <div className="px-4 pb-2">
            <div className={`rounded-lg px-4 py-2 text-center ${
              localLastResult.big_play_factor >= 3 ? 'bg-red-700' :
              localLastResult.big_play_factor >= 2 ? 'bg-orange-700' :
              localLastResult.big_play_factor >= 1 ? 'bg-yellow-700' :
              'bg-gray-800'
            }`}>
              {localLastResult.is_first_down && (
                <div className="text-green-400 font-bold text-lg mb-1">FIRST DOWN!</div>
              )}
              <div className="text-white font-bold text-lg">{localLastResult.headline || localLastResult.description}</div>
              {localLastResult.commentary && (
                <div className="text-white/80 text-sm mt-1">{localLastResult.commentary}</div>
              )}
            </div>
          </div>
        )}

        {/* CPU Decision Panel */}
        {showCpuDecision && cpuFourthDownDecision && (
          <div className="px-4 pb-2">
            <CpuDecisionPanel 
              decision={cpuFourthDownDecision} 
              onExecute={handleCpuDecisionExecute} 
              onCancel={() => {
                clearCpuFourthDownDecision();
                clearPendingDefensePlay();
              }}
            />
          </div>
        )}

        {pendingCpuFourthDown && !showCpuDecision && (
          <div className="px-4 pb-2">
            <CpuDecisionPanel 
              decision={pendingCpuFourthDown} 
              onExecute={handleCpuFourthDownExecute} 
              onCancel={() => {
                clearPendingCpuFourthDown();
              }}
            />
          </div>
        )}

        {/* Punt Options Panel */}
        {showPuntOptions && (
          <div className="px-4 pb-2">
            <PuntOptionsPanel 
              ballPosition={ballPosition}
              onSelect={handlePuntOptions}
              onCancel={() => {
                setShowPuntOptions(false);
                setPendingPuntPlay(null);
              }}
            />
          </div>
        )}

        {/* PAT Choice Panel */}
        {localShowPatChoice && (
          <div className="px-4 pb-2">
            <PATChoicePanel 
              canGoForTwo={canGoForTwo}
              cpuShouldGoForTwo={cpuShouldGoForTwo}
              scoringTeamIsPlayer={scoringTeamIsPlayer}
              onPatKick={handlePatKick}
              onPatTwoPoint={handlePatTwoPoint}
              onCpuPat={handleCpuPat}
              onCpuTwoPoint={handleCpuTwoPoint}
            />
          </div>
        )}

        {/* PAT Result */}
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

        {/* Penalty Decision Panel */}
        {localShowPenaltyChoice && localPendingPenaltyData && (
          <div className="px-4 pb-2">
            <PenaltyDecisionPanel 
              penaltyData={localPendingPenaltyData} 
              onDecision={handlePenaltyDecision}
              cpuIsOnDefense={playerOffense}
            />
          </div>
        )}
      </div>

      {/* Play Selector - fixed position, stays in same place */}
      <div className="flex-shrink-0 px-4 pb-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Show offense plays when player is on offense, defense plays when player is on defense */}
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
            disabled={isKickoff || pendingPat || pendingPenaltyData}
            className="px-4 py-2 bg-purple-700 text-white rounded-lg hover:bg-purple-600 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            SAVE REPLAY
          </button>
          <button
            onClick={handleSaveGame}
            disabled={isKickoff || pendingPat || pendingPenaltyData}
            className="px-4 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            SAVE GAME
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlayingPhase;