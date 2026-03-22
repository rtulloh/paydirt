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

  const isHomeScoring = gameState.possession === 'home';
  const scoringTeamIsPlayer = (gameState.human_is_home && isHomeScoring) ||
                              (!gameState.human_is_home && !isHomeScoring);

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
