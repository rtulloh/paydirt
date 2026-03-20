const SAVE_KEY = 'paydirt_saved_game'

export function saveGame(gameState) {
  const saveData = {
    timestamp: new Date().toISOString(),
    gameState,
  }
  localStorage.setItem(SAVE_KEY, JSON.stringify(saveData))
  return true
}

export function loadGame() {
  const saved = localStorage.getItem(SAVE_KEY)
  if (!saved) return null
  
  try {
    const data = JSON.parse(saved)
    
    // Migrate old saves that don't have humanTeamId
    if (data.gameState && !data.gameState.humanTeamId) {
      data.gameState = migrateOldSave(data.gameState)
    }
    
    return data
  } catch (e) {
    console.error('Failed to parse saved game:', e)
    return null
  }
}

function migrateOldSave(gameState) {
  // Try to determine human team from existing fields
  // Old saves might have playerTeamId instead of humanTeamId
  if (gameState.playerTeamId && !gameState.humanTeamId) {
    gameState.humanTeamId = gameState.playerTeamId
  }
  
  // Try to determine cpu team
  if (gameState.cpuTeamId) {
    // Already has cpuTeamId, nothing to do
  } else if (gameState.homeTeam?.id && gameState.awayTeam?.id) {
    // Determine based on playerTeamId or assume player is home
    if (gameState.humanTeamId === gameState.homeTeam.id) {
      gameState.cpuTeamId = gameState.awayTeam.id
    } else {
      gameState.cpuTeamId = gameState.homeTeam.id
    }
  }
  
  return gameState
}

export function deleteSavedGame() {
  localStorage.removeItem(SAVE_KEY)
}

export function hasSavedGame() {
  return localStorage.getItem(SAVE_KEY) !== null
}

export function getSavedGameInfo() {
  const saved = loadGame()
  if (!saved) return null
  
  return {
    timestamp: saved.timestamp,
    homeTeam: saved.gameState?.homeTeam?.name || 'Unknown',
    awayTeam: saved.gameState?.awayTeam?.name || 'Unknown',
    homeScore: saved.gameState?.homeScore || 0,
    awayScore: saved.gameState?.awayScore || 0,
    quarter: saved.gameState?.quarter || 1,
  }
}

// Export for manual migration in browser console
window.fixPaydirtSave = function() {
  const saved = localStorage.getItem(SAVE_KEY)
  if (!saved) {
    console.log('No saved game found')
    return
  }
  
  try {
    const data = JSON.parse(saved)
    if (data.gameState?.humanTeamId) {
      console.log('Save already has humanTeamId:', data.gameState.humanTeamId)
      return
    }
    
    console.log('Old save format found:', data.gameState)
    
    // Determine human team
    if (data.gameState.homeTeam?.id && data.gameState.awayTeam?.id) {
      // Assume player is home team (most common case)
      data.gameState.humanTeamId = data.gameState.homeTeam.id
      data.gameState.cpuTeamId = data.gameState.awayTeam.id
      
      localStorage.setItem(SAVE_KEY, JSON.stringify(data))
      console.log('Fixed save - player is HOME team:', data.gameState.humanTeamId)
      console.log('CPU team:', data.gameState.cpuTeamId)
    } else {
      console.log('Cannot determine teams from save')
    }
  } catch (e) {
    console.error('Failed to fix save:', e)
  }
}
