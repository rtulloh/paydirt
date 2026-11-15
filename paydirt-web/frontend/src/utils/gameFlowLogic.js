/**
 * Shared game flow logic — used by both the component and tests.
 * If this code is missing from PlayingPhase.jsx, the tests will fail
 * because they import and use these same functions.
 */

/**
 * Determine if a TD response should trigger the PAT flow.
 * Returns { isPendingPat, scoringTeamIsPlayer, canGoForTwo }.
 */
export function checkPendingPat(gameState) {
  const isPendingPat = gameState.pending_pat === true;
  if (!isPendingPat) {
    return { isPendingPat: false, scoringTeamIsPlayer: false, canGoForTwo: false };
  }

  // The engine owns scoring and player identity; never infer it from UI state.
  const scoringTeamIsPlayer = gameState.player_offense === true;

  return { 
    isPendingPat, 
    scoringTeamIsPlayer,
    canGoForTwo: gameState.can_go_for_two || false
  };
}

/**
 * Derive kickoff team labels from the post-kickoff game state.
 * After kickoff, possession = receiving team.
 */
export function deriveKickoffTeams(possessionAfterKickoff, homeTeam, awayTeam) {
  const receivingTeam = possessionAfterKickoff === 'home'
    ? (homeTeam?.short_name || 'HOME')
    : (awayTeam?.short_name || 'AWAY');
  const kickingTeam = possessionAfterKickoff === 'home'
    ? (awayTeam?.short_name || 'AWAY')
    : (homeTeam?.short_name || 'HOME');
  return { kickingTeam, receivingTeam };
}

/**
 * Derive play-log team labels from the engine-owned possession flag.
 *
 * ``playerOffense`` only says whether the human has the ball on this snap. It
 * cannot identify the teams: an away human on offense must still be labelled
 * AWAY, not HOME. Possession is the common fact in every game state.
 */
export function derivePlayLogTeams({ possession, homeTeam, awayTeam, humanIsHome }) {
  const homeAbbrev = homeTeam?.short_name || 'HOME';
  const awayAbbrev = awayTeam?.short_name || 'AWAY';
  const homeHasBall = possession === 'home';

  return {
    offenseTeam: homeHasBall ? homeAbbrev : awayAbbrev,
    defenseTeam: homeHasBall ? awayAbbrev : homeAbbrev,
    playerTeam: humanIsHome ? homeAbbrev : awayAbbrev,
    homeTeamAbbrev: homeAbbrev,
    awayTeamAbbrev: awayAbbrev,
    possession: homeHasBall ? 'home' : 'away',
    // Marks the possession field as pre-play. Older entries recorded post-play
    // possession, so the renderer must not reinterpret them.
    possessionSemantics: 'preplay',
  };
}

/**
 * Resolve the display teams for an existing play-log entry.
 *
 * Only entries explicitly written with pre-play possession carry enough
 * information to re-derive identity. Older entries stored post-play possession,
 * so re-deriving them would reverse interceptions, lost fumbles and turnovers
 * on downs; those keep their recorded teams. Returns null for legacy entries.
 */
export function derivePlayLogDisplayTeams(entry) {
  if (entry?.possessionSemantics !== 'preplay') return null;
  const homeAbbrev = entry.homeTeamAbbrev || 'HOME';
  const awayAbbrev = entry.awayTeamAbbrev || 'AWAY';
  const homeHasBall = entry.possession === 'home';
  const playerTeam = entry.humanIsHome === undefined
    ? entry.playerTeam
    : (entry.humanIsHome ? homeAbbrev : awayAbbrev);
  return {
    offenseTeam: homeHasBall ? homeAbbrev : awayAbbrev,
    defenseTeam: homeHasBall ? awayAbbrev : homeAbbrev,
    playerTeam: playerTeam || entry.playerTeam || '',
  };
}

/**
 * Verify that after a scoring play, the game state is correct.
 * Returns an array of issues found.
 */
export function validateScoringState(gameState, expectedScoringTeam) {
  const issues = [];

  if (gameState.pending_pat) {
    // PAT pending: scoring team should have possession for kickoff
    // Ball should be at 35 for kickoff
    if (gameState.ball_position !== 35) {
      issues.push(`PAT pending but ball at ${gameState.ball_position}, expected 35`);
    }
  }

  if (gameState.is_kickoff) {
    if (gameState.ball_position !== 35) {
      issues.push(`Kickoff but ball at ${gameState.ball_position}, expected 35`);
    }
    if (gameState.down !== 1) {
      issues.push(`Kickoff but down=${gameState.down}, expected 1`);
    }
    if (gameState.yards_to_go !== 10) {
      issues.push(`Kickoff but yards_to_go=${gameState.yards_to_go}, expected 10`);
    }
  }

  return issues;
}
