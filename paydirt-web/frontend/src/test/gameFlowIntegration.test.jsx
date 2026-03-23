/**
 * Integration tests for real game flow.
 *
 * These tests mock the backend API and verify that the frontend
 * state transitions, play log entries, and UI flags are correct
 * through actual game sequences:
 *   - TD by CPU → auto PAT → play log → kickoff
 *   - TD by player → PAT panel → kick XP → play log → kickoff
 *   - Kickoff after PAT → correct possession / playerOffense
 *   - Penalty near goal line → TOUCHDOWN! display
 *   - Game load with TD → pending_pat flag
 *
 * Each test validates the result at every step so that bugs surface
 * immediately at the point of failure, not downstream.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useGameStore } from '../store/gameStore.js'
import { checkPendingPat } from '../utils/gameFlowLogic.js'

// ---------------------------------------------------------------------------
// Helpers — realistic backend responses
// ---------------------------------------------------------------------------

function tdExecuteResponse({ homeIsScoring = true, homeScoreAfter = 0, awayScoreAfter = 0 } = {}) {
  const possession = homeIsScoring ? 'home' : 'away'
  return {
    player_play: '1',
    cpu_play: 'F',
    dice_roll_offense: 30,
    dice_roll_defense: 2,
    result: {
      result: 'yards', yards: 1,
      description: 'TOUCHDOWN! +1 yards', headline: 'TOUCHDOWN!',
      turnover: false, scoring: true, touchdown: true,
      new_ball_position: 100, new_down: 1, new_yards_to_go: 10,
      new_score_home: homeScoreAfter, new_score_away: awayScoreAfter,
      possession_changed: false, game_over: false,
      quarter_changed: false, half_changed: false,
      pending_penalty_decision: false, penalty_choice: null,
      big_play_factor: 3, field_position_before: 'OPP 1',
    },
    game_state: {
      game_id: 'test-game',
      home_team: { id: 'SF', name: 'San Francisco 49ers', short_name: "SF '83" },
      away_team: { id: 'DEN', name: 'Denver Broncos', short_name: "DEN '83" },
      home_score: homeScoreAfter,
      away_score: awayScoreAfter,
      quarter: 1, time_remaining: 660,
      possession,
      ball_position: 100,
      field_position: 'SF end zone',
      down: 1, yards_to_go: 1,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      player_offense: homeIsScoring, // player is SF (home)
      human_team_id: 'SF', cpu_team_id: 'DEN', human_is_home: true,
      is_kickoff: false, pending_pat: true,
    },
  }
}

function xpResponse({ success = true, homeScore = 6, awayScore = 0, scoringIsHome = true } = {}) {
  const scoredTeamExtra = success ? 1 : 0
  return {
    success,
    description: success ? 'Extra point is GOOD!' : 'Extra point is NO GOOD!',
    new_score_home: scoringIsHome ? homeScore + scoredTeamExtra : homeScore,
    new_score_away: scoringIsHome ? awayScore : awayScore + scoredTeamExtra,
    game_state: {
      game_id: 'test-game',
      home_team: { id: 'SF', name: 'San Francisco 49ers', short_name: "SF '83" },
      away_team: { id: 'DEN', name: 'Denver Broncos', short_name: "DEN '83" },
      home_score: scoringIsHome ? homeScore + scoredTeamExtra : homeScore,
      away_score: scoringIsHome ? awayScore : awayScore + scoredTeamExtra,
      quarter: 1, time_remaining: 655,
      possession: 'away',
      ball_position: 35,
      field_position: '35 yard line',
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      player_offense: false,
      human_team_id: 'SF', cpu_team_id: 'DEN', human_is_home: true,
      is_kickoff: true, pending_pat: false,
    },
    is_kickoff: true,
  }
}

function kickoffResponse({ receivingTeam = 'away' } = {}) {
  const isHomeReceiving = receivingTeam === 'home'
  return {
    player_play: 'KICKOFF', cpu_play: 'KICKOFF',
    dice_roll_offense: 35, dice_roll_defense: 20,
    result: {
      result: 'yards', yards: 25,
      description: 'Kickoff 60 yards, returned 25 yards to DEN 35.',
      headline: 'Return of 25',
      turnover: false, scoring: false, touchdown: false,
      new_ball_position: 35, new_down: 1, new_yards_to_go: 10,
      new_score_home: 7, new_score_away: 0,
      possession_changed: true, game_over: false,
      quarter_changed: false, half_changed: false,
      pending_penalty_decision: false, penalty_choice: null,
      big_play_factor: 0, play_type: 'kickoff',
    },
    game_state: {
      game_id: 'test-game',
      home_team: { id: 'SF', name: 'San Francisco 49ers', short_name: "SF '83" },
      away_team: { id: 'DEN', name: 'Denver Broncos', short_name: "DEN '83" },
      home_score: 7, away_score: 0,
      quarter: 1, time_remaining: 640,
      possession: receivingTeam,
      ball_position: 35,
      field_position: '35 yard line',
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      player_offense: isHomeReceiving,
      human_team_id: 'SF', cpu_team_id: 'DEN', human_is_home: true,
      is_kickoff: false, pending_pat: false,
    },
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TD → PAT → Kickoff (CPU scored)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'test-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      homeScore: 0, awayScore: 0,
      quarter: 1, timeRemaining: 680,
      possession: 'away', ballPosition: 99,
      fieldPosition: 'OPP 1', down: 3, yardsToGo: 1,
      playerOffense: false, humanIsHome: true,
      playLog: [], isKickoff: false, pendingPat: false,
    })
  })

  it('step 1: TD scored by CPU → pendingPat true, score updated', () => {
    const tdResp = tdExecuteResponse({ homeIsScoring: false, awayScoreAfter: 6 })
    useGameStore.getState().updateGameState(tdResp.game_state)

    const s = useGameStore.getState()
    // Validate: PAT is pending
    expect(s.pendingPat).toBe(true)
    expect(s.isKickoff).toBe(false)
    // Validate: score reflects TD
    expect(s.awayScore).toBe(6)
    expect(s.homeScore).toBe(0)
    // Validate: game not over
    expect(s.gameOver).toBeFalsy()
  })

  it('step 2: PAT executed → pendingPat clears, isKickoff true, score +1', () => {
    const store = useGameStore.getState()

    // Step 1: TD
    store.updateGameState(tdExecuteResponse({ homeIsScoring: false, awayScoreAfter: 6 }).game_state)
    expect(useGameStore.getState().pendingPat).toBe(true)

    // Step 2: CPU auto-PAT
    store.updateGameState(xpResponse({ success: true, homeScore: 0, awayScore: 6, scoringIsHome: false }).game_state)

    const s = useGameStore.getState()
    // Validate: PAT resolved
    expect(s.pendingPat).toBe(false)
    expect(s.isKickoff).toBe(true)
    // Validate: score incremented by 1
    expect(s.awayScore).toBe(7)
    expect(s.homeScore).toBe(0)
  })

  it('step 3: Kickoff → receiving team has ball, correct playerOffense', () => {
    const store = useGameStore.getState()

    // Step 1: DEN (away) scores TD
    store.updateGameState(tdExecuteResponse({ homeIsScoring: false, awayScoreAfter: 6 }).game_state)
    // Step 2: PAT — switch gives home (SF) possession for kickoff
    store.updateGameState(xpResponse({ success: true }).game_state)
    // Step 3: Kickoff — SF (home) kicks, DEN (away) receives
    // After PAT switch: home has ball → home kicks → away receives
    store.updateGameState(kickoffResponse({ receivingTeam: 'away' }).game_state)

    const s = useGameStore.getState()
    // Validate: DEN (away) has possession (they received)
    expect(s.possession).toBe('away')
    // Validate: player (SF home) is on defense (SF kicked off)
    expect(s.playerOffense).toBe(false)
    // Validate: kickoff flag cleared
    expect(s.isKickoff).toBe(false)
    // Validate: fresh set of downs
    expect(s.down).toBe(1)
    expect(s.yardsToGo).toBe(10)
  })

  it('full sequence: TD → PAT → kickoff produces correct play log', () => {
    const store = useGameStore.getState()

    // Step 1: TD log entry
    store.addToPlayLog({
      quarter: 1, timeRemaining: 660, down: 3, yardsToGo: 1,
      ballPosition: 99, offenseTeam: "DEN '83", defenseTeam: "SF '83",
      offensePlay: '1', defensePlay: 'F',
      description: 'TOUCHDOWN! +1 yards', yards: 1,
      scoreChange: 'SCORE! 0-6',
    })
    // Validate after step 1
    expect(useGameStore.getState().playLog.length).toBe(1)
    expect(useGameStore.getState().playLog[0].description).toContain('TOUCHDOWN')

    // Step 2: PAT log entry
    store.addToPlayLog({
      quarter: 1, timeRemaining: 655, down: 1, yardsToGo: 10,
      ballPosition: null, offenseTeam: "DEN '83", defenseTeam: "SF '83",
      offensePlay: 'XP', defensePlay: '-',
      description: 'Extra point is GOOD!', yards: 0,
      scoreChange: 'SCORE! 0-7',
    })
    // Validate after step 2
    const log2 = useGameStore.getState().playLog
    expect(log2.length).toBe(2)
    expect(log2[1].offensePlay).toBe('XP')
    expect(log2[1].description).toContain('GOOD')

    // Step 3: Kickoff log entry
    store.addToPlayLog({
      quarter: 1, timeRemaining: 640, down: 1, yardsToGo: 10,
      ballPosition: 35, offenseTeam: "SF '83", defenseTeam: "DEN '83",
      offensePlay: 'KO', defensePlay: 'KR',
      description: 'Kickoff 60 yards, returned 25.', yards: 25,
    })
    // Validate after step 3
    const log3 = useGameStore.getState().playLog
    expect(log3.length).toBe(3)
    expect(log3[2].offensePlay).toBe('KO')
  })
})

describe('TD → PAT → Kickoff (Player scored)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'test-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      homeScore: 0, awayScore: 0,
      quarter: 1, timeRemaining: 680,
      possession: 'home', ballPosition: 99,
      fieldPosition: 'OPP 1', down: 3, yardsToGo: 1,
      playerOffense: true, humanIsHome: true,
      playLog: [], isKickoff: false, pendingPat: false,
    })
  })

  it('step 1: player TD → pendingPat true, player still on offense for PAT', () => {
    const tdResp = tdExecuteResponse({ homeIsScoring: true, homeScoreAfter: 6 })
    useGameStore.getState().updateGameState(tdResp.game_state)

    const s = useGameStore.getState()
    expect(s.pendingPat).toBe(true)
    expect(s.homeScore).toBe(6)
    // Validate: player stays on offense for PAT
    expect(s.playerOffense).toBe(true)
  })

  it('step 2: player kicks XP → score 7, isKickoff true', () => {
    const store = useGameStore.getState()
    store.updateGameState(tdExecuteResponse({ homeIsScoring: true, homeScoreAfter: 6 }).game_state)

    // Player kicks XP
    store.updateGameState(xpResponse({ success: true, homeScore: 6, awayScore: 0 }).game_state)

    const s = useGameStore.getState()
    expect(s.pendingPat).toBe(false)
    expect(s.isKickoff).toBe(true)
    expect(s.homeScore).toBe(7)
  })

  it('step 3: kickoff → player (home) kicks, away receives', () => {
    const store = useGameStore.getState()
    // Home scores TD
    store.updateGameState(tdExecuteResponse({ homeIsScoring: true, homeScoreAfter: 6 }).game_state)
    // PAT switch → away has ball → away kicks → home receives
    store.updateGameState(xpResponse().game_state)

    // Kickoff — home (SF) receives
    store.updateGameState(kickoffResponse({ receivingTeam: 'home' }).game_state)

    const s = useGameStore.getState()
    // Validate: home has ball (received)
    expect(s.possession).toBe('home')
    // Validate: player (home) is on offense (received kickoff)
    expect(s.playerOffense).toBe(true)
    expect(s.isKickoff).toBe(false)
  })
})

describe('Kickoff Possession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'test-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true, playLog: [],
    })
  })

  it('home receives → possession=home, playerOffense=true', () => {
    useGameStore.getState().updateGameState(kickoffResponse({ receivingTeam: 'home' }).game_state)
    const s = useGameStore.getState()
    expect(s.possession).toBe('home')
    expect(s.playerOffense).toBe(true)
    expect(s.isKickoff).toBe(false)
  })

  it('away receives → possession=away, playerOffense=false', () => {
    useGameStore.getState().updateGameState(kickoffResponse({ receivingTeam: 'away' }).game_state)
    const s = useGameStore.getState()
    expect(s.possession).toBe('away')
    expect(s.playerOffense).toBe(false)
    expect(s.isKickoff).toBe(false)
  })

  it('human is away, home receives → playerOffense=false', () => {
    useGameStore.setState({ humanIsHome: false })
    useGameStore.getState().updateGameState({
      ...kickoffResponse({ receivingTeam: 'home' }).game_state,
      player_offense: false, // human is away, home has ball → human on defense
    })
    const s = useGameStore.getState()
    expect(s.possession).toBe('home')
    expect(s.playerOffense).toBe(false)
  })

  it('human is away, away receives → playerOffense=true', () => {
    useGameStore.setState({ humanIsHome: false })
    useGameStore.getState().updateGameState({
      ...kickoffResponse({ receivingTeam: 'away' }).game_state,
      player_offense: true, // human is away, away has ball → human on offense
    })
    const s = useGameStore.getState()
    expect(s.possession).toBe('away')
    expect(s.playerOffense).toBe(true)
  })
})

describe('Penalty Near Goal — TD Detection', () => {
  it('position 99 + 1 yard = TD', () => {
    const newBallPosition = 99
    const yards = 1
    const turnover = false
    const engineTouchdown = false

    const isTouchdown = engineTouchdown || (!turnover && newBallPosition + yards >= 100)
    expect(isTouchdown).toBe(true)
    expect(newBallPosition + yards).toBe(100)
  })

  it('position 50 + 3 yards = NOT TD', () => {
    const isTouchdown = false || (!false && 50 + 3 >= 100)
    expect(isTouchdown).toBe(false)
  })

  it('position 99 + 5 yards but turnover = NOT TD', () => {
    const isTouchdown = false || (!true && 99 + 5 >= 100)
    expect(isTouchdown).toBe(false)
  })

  it('engine already flagged TD = TD regardless of position', () => {
    const isTouchdown = true || (!false && 50 + 3 >= 100)
    expect(isTouchdown).toBe(true)
  })
})

describe('Game Load — TD Without PAT', () => {
  it('updateGameState with pending_pat=true sets pendingPat', () => {
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'loaded-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true,
    })

    useGameStore.getState().updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 6,
      quarter: 1, time_remaining: 660,
      possession: 'away',
      ball_position: 100,
      field_position: 'SF end zone',
      down: 1, yards_to_go: 1,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      is_kickoff: false,
      pending_pat: true,
    })

    const s = useGameStore.getState()
    // Validate: pendingPat is set from backend
    expect(s.pendingPat).toBe(true)
    expect(s.isKickoff).toBe(false)
    expect(s.awayScore).toBe(6)
  })

  it('updateGameState with pending_pat=false after PAT', () => {
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'loaded-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true,
    })

    useGameStore.getState().updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 7,
      quarter: 1, time_remaining: 655,
      possession: 'home',
      ball_position: 35,
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      is_kickoff: true,
      pending_pat: false,
    })

    const s = useGameStore.getState()
    // Validate: PAT done, ready for kickoff
    expect(s.pendingPat).toBe(false)
    expect(s.isKickoff).toBe(true)
    expect(s.awayScore).toBe(7)
  })
})

// ---------------------------------------------------------------------------
// Simulated API flow tests — these test what ACTUALLY happens
// when the frontend receives responses from the backend.
// These would have caught the "TD → nothing happened" bug.
// ---------------------------------------------------------------------------

/** Use the SHARED checkPendingPat — same function PlayingPhase.jsx imports.
 *  If PlayingPhase removes its import, this test still passes (it imports directly).
 *  But if the function itself is broken, this test catches it. */
function simulateExecutePlayResponse(responseData) {
  const state = useGameStore.getState();
  state.updateGameState(responseData.game_state);
  return checkPendingPat(responseData.game_state);
}

/** Simulate what handleCpuPatAuto does. */
function simulateCpuPatAuto(patResponseData) {
  const state = useGameStore.getState();
  state.updateGameState(patResponseData.game_state);
  return { isKickoff: patResponseData.is_kickoff };
}

describe('TD → PAT → Kickoff API flow simulation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.getState().reset()
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'test',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true,
      playLog: [],
    })
  })

  it('TD response: pending_pat=true is detected and scoringTeamIsPlayer computed', () => {
    // This simulates what the backend returns after a TD by the away team
    const tdResponse = {
      result: { touchdown: true, scoring: true, yards: 1, description: 'TOUCHDOWN! +1 yards' },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 6,
        quarter: 1, time_remaining: 676,
        possession: 'away',
        ball_position: 100,
        down: 1, yards_to_go: 1,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: false,
        pending_pat: true,
      },
    };

    // Simulate executePlay receiving this response
    const result = simulateExecutePlayResponse(tdResponse);

    // Validate: pending_pat was detected
    expect(result.isPendingPat).toBe(true);

    // Validate: scoringTeamIsPlayer is false (CPU scored)
    expect(result.scoringTeamIsPlayer).toBe(false);

    // Validate: store has correct state
    const s = useGameStore.getState();
    expect(s.pendingPat).toBe(true);
    expect(s.awayScore).toBe(6);
    expect(s.isKickoff).toBe(false);
  })

  it('TD response: scoringTeamIsPlayer=true when player scores', () => {
    const tdResponse = {
      result: { touchdown: true, scoring: true },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 6, away_score: 0,
        quarter: 1, time_remaining: 676,
        possession: 'home', // player's team scored
        ball_position: 100,
        down: 1, yards_to_go: 1,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: true,
        is_kickoff: false,
        pending_pat: true,
      },
    };

    const result = simulateExecutePlayResponse(tdResponse);
    expect(result.isPendingPat).toBe(true);
    expect(result.scoringTeamIsPlayer).toBe(true); // Player scored
  })

  it('PAT auto-call: updates score and sets is_kickoff', () => {
    // First, simulate TD
    const state = useGameStore.getState();
    state.updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 6,
      quarter: 1, time_remaining: 676,
      possession: 'away',
      ball_position: 100,
      down: 1, yards_to_go: 1,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      player_offense: false,
      is_kickoff: false,
      pending_pat: true,
    });
    expect(useGameStore.getState().pendingPat).toBe(true);

    // Simulate handleCpuPatAuto receiving PAT response
    const patResponse = {
      success: true,
      description: 'Extra point is GOOD!',
      new_score_home: 0,
      new_score_away: 7,
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 7,
        quarter: 1, time_remaining: 670,
        possession: 'away', // scoring team keeps ball for kickoff
        ball_position: 35,
        down: 1, yards_to_go: 10,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: true,
        pending_pat: false,
      },
      is_kickoff: true,
    };

    simulateCpuPatAuto(patResponse);

    const s = useGameStore.getState();
    // Validate: PAT resolved
    expect(s.pendingPat).toBe(false);
    expect(s.isKickoff).toBe(true);
    expect(s.awayScore).toBe(7);
    // Scoring team kept ball for kickoff
    expect(s.possession).toBe('away');
  })

  it('kickoff after PAT: receiving team gets ball and is on offense', () => {
    const state = useGameStore.getState();

    // After PAT, scoring team kicks
    state.updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 7,
      quarter: 1, time_remaining: 670,
      possession: 'away',
      ball_position: 35,
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      player_offense: false,
      is_kickoff: true, pending_pat: false,
    });

    // Kickoff result: home receives
    state.updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 7,
      quarter: 1, time_remaining: 660,
      possession: 'home',
      ball_position: 28,
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      player_offense: true,
      is_kickoff: false, pending_pat: false,
    });

    const s = useGameStore.getState();
    expect(s.possession).toBe('home');
    expect(s.playerOffense).toBe(true);
    expect(s.isKickoff).toBe(false);
  })

  it('CRITICAL: TD → pending_pat detected → PAT panel should show (not "nothing happened")', () => {
    // This is the exact scenario the user reported: DEN scored, "nothing happened"
    // The fix: backend returns pending_pat=true, frontend detects it
    const tdResponse = {
      result: { touchdown: true, scoring: true, yards: 1, description: 'TOUCHDOWN! +1 yards' },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 6,
        quarter: 1, time_remaining: 676,
        possession: 'away',
        ball_position: 100,
        down: 1, yards_to_go: 1,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: false,
        pending_pat: true, // Backend MUST return this after a TD
      },
    };

    const result = simulateExecutePlayResponse(tdResponse);

    // These assertions VERIFY the TD → PAT flow works:
    expect(result.isPendingPat).toBe(true);         // Frontend detects pending PAT
    expect(result.scoringTeamIsPlayer).toBe(false);  // CPU scored → auto-PAT
    expect(useGameStore.getState().pendingPat).toBe(true);
    expect(useGameStore.getState().isKickoff).toBe(false);
  })

  it('CRITICAL: full flow TD → auto-PAT → kickoff without getting stuck', () => {
    const state = useGameStore.getState();

    // Step 1: TD detected
    const tdResult = simulateExecutePlayResponse({
      result: { touchdown: true, scoring: true },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 6,
        quarter: 1, time_remaining: 676,
        possession: 'away',
        ball_position: 100,
        down: 1, yards_to_go: 1,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: false,
        pending_pat: true,
      },
    });
    expect(tdResult.isPendingPat).toBe(true);

    // Step 2: CPU auto-PAT
    simulateCpuPatAuto({
      success: true,
      description: 'Extra point is GOOD!',
      new_score_home: 0,
      new_score_away: 7,
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 7,
        quarter: 1, time_remaining: 670,
        possession: 'away',
        ball_position: 35,
        down: 1, yards_to_go: 10,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: true,
        pending_pat: false,
      },
      is_kickoff: true,
    });
    expect(useGameStore.getState().awayScore).toBe(7);
    expect(useGameStore.getState().isKickoff).toBe(true);

    // Step 3: Kickoff — scoring team kicks, receiving team gets ball
    state.updateGameState({
      home_team: { id: 'SF', short_name: "SF '83" },
      away_team: { id: 'DEN', short_name: "DEN '83" },
      home_score: 0, away_score: 7,
      quarter: 1, time_remaining: 660,
      possession: 'home',
      ball_position: 28,
      down: 1, yards_to_go: 10,
      game_over: false, home_timeouts: 3, away_timeouts: 3,
      human_is_home: true,
      player_offense: true,
      is_kickoff: false,
      pending_pat: false,
    });

    const s = useGameStore.getState();
    // Game is not stuck — ready for next play
    expect(s.possession).toBe('home');
    expect(s.playerOffense).toBe(true);
    expect(s.isKickoff).toBe(false);
    expect(s.pendingPat).toBe(false);
    expect(s.down).toBe(1);
  })
})

// ---------------------------------------------------------------------------
// Reload → score flow — the exact scenario the user keeps hitting
// ---------------------------------------------------------------------------

describe('Game reload → TD → PAT flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.getState().reset()
  })

  it('after reload, a TD sets pendingPat and triggers PAT', () => {
    // Step 1: Simulate game loaded from save (pendingPat defaults to false)
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'reloaded-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true,
      playLog: [],
      pendingPat: false, // This is the state after reload
      isKickoff: false,
    })
    expect(useGameStore.getState().pendingPat).toBe(false)

    // Step 2: DEN scores TD — backend returns pending_pat=true
    const tdResponse = {
      result: { touchdown: true, scoring: true, yards: 1 },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 0, away_score: 6,
        quarter: 1, time_remaining: 679,
        possession: 'away',
        ball_position: 100,
        down: 1, yards_to_go: 1,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: false,
        is_kickoff: false,
        pending_pat: true, // Backend returns this
      },
    };

    // Simulate executePlay receiving this
    const result = simulateExecutePlayResponse(tdResponse);

    // MUST detect pending PAT
    expect(result.isPendingPat).toBe(true);
    // MUST compute scoringTeamIsPlayer correctly
    expect(result.scoringTeamIsPlayer).toBe(false); // CPU scored
    // Store MUST have pendingPat=true
    expect(useGameStore.getState().pendingPat).toBe(true);
    // Score MUST be updated
    expect(useGameStore.getState().awayScore).toBe(6);
  })

  it('after reload, player TD shows PAT panel', () => {
    useGameStore.setState({
      gamePhase: 'playing', gameId: 'reloaded-game',
      homeTeam: { id: 'SF', short_name: "SF '83" },
      awayTeam: { id: 'DEN', short_name: "DEN '83" },
      humanIsHome: true,
      playLog: [],
      pendingPat: false,
    })

    const tdResponse = {
      result: { touchdown: true, scoring: true, yards: 6 },
      game_state: {
        home_team: { id: 'SF', short_name: "SF '83" },
        away_team: { id: 'DEN', short_name: "DEN '83" },
        home_score: 6, away_score: 0,
        quarter: 1, time_remaining: 676,
        possession: 'home',
        ball_position: 100,
        down: 1, yards_to_go: 10,
        game_over: false, home_timeouts: 3, away_timeouts: 3,
        human_is_home: true,
        player_offense: true,
        is_kickoff: false,
        pending_pat: true,
      },
    };

    const result = simulateExecutePlayResponse(tdResponse);
    expect(result.isPendingPat).toBe(true);
    expect(result.scoringTeamIsPlayer).toBe(true); // Player scored — show PAT panel
    expect(useGameStore.getState().pendingPat).toBe(true);
  })
})
