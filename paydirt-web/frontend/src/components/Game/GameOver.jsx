export function GameOver({ homeTeam, awayTeam, homeScore, awayScore, onNewGame }) {
  const isHomeWinner = homeScore > awayScore
  const isAwayWinner = awayScore > homeScore
  const isTie = homeScore === awayScore
  
  const winner = isHomeWinner ? homeTeam : isAwayWinner ? awayTeam : null

  return (
    <div className="board-panel p-6 text-center" data-testid="game-over">
      <h2 className="text-3xl font-heading font-bold mb-4 text-gray-800">
        GAME OVER
      </h2>

      <div className="mb-6">
        <div className="flex justify-center items-center gap-6 mb-4">
          <div className="text-center">
            <div 
              className="w-16 h-16 mx-auto mb-2 rounded-full flex items-center justify-center text-white text-lg font-bold"
              style={{ backgroundColor: homeTeam?.team_color || '#666' }}
              data-testid="home-team-icon"
            >
              {homeTeam?.short_name?.slice(0, 2) || 'HM'}
            </div>
            <div className="text-base font-bold text-gray-800">
              {homeTeam?.name || 'Home Team'}
            </div>
            <div 
              className={`text-3xl font-bold mt-1 ${isHomeWinner ? 'text-green-600' : 'text-gray-600'}`}
              data-testid="home-score"
            >
              {homeScore}
            </div>
          </div>

          <div className="text-2xl text-gray-400 font-bold">vs</div>

          <div className="text-center">
            <div 
              className="w-16 h-16 mx-auto mb-2 rounded-full flex items-center justify-center text-white text-lg font-bold"
              style={{ backgroundColor: awayTeam?.team_color || '#666' }}
              data-testid="away-team-icon"
            >
              {awayTeam?.short_name?.slice(0, 2) || 'AW'}
            </div>
            <div className="text-base font-bold text-gray-800">
              {awayTeam?.name || 'Away Team'}
            </div>
            <div 
              className={`text-3xl font-bold mt-1 ${isAwayWinner ? 'text-green-600' : 'text-gray-600'}`}
              data-testid="away-score"
            >
              {awayScore}
            </div>
          </div>
        </div>

        {winner && (
          <div className="text-xl font-bold text-yellow-600 mb-2 animate-pulse">
            {winner.name} WINS!
          </div>
        )}
        
        {isTie && (
          <div className="text-xl font-bold text-gray-500 mb-2">
            IT'S A TIE!
          </div>
        )}
      </div>

      <div className="flex justify-center gap-4">
        <button
          onClick={onNewGame}
          className="play-button text-base px-6 py-3"
          data-testid="new-game-button"
        >
          NEW GAME
        </button>
      </div>
    </div>
  )
}

export default GameOver
