export function Halftime({ homeTeam, awayTeam, homeScore, awayScore, quarter, onContinue }) {
  return (
    <div className="board-panel p-6 text-center" data-testid="halftime">
      <h2 className="text-3xl font-heading font-bold mb-4 text-gray-800">
        HALFTIME
      </h2>

      <div className="mb-6">
        <div className="text-base text-gray-600 mb-4">
          {quarter === 2 ? 'End of 1st Half' : 'End of 2nd Quarter'}
        </div>

        <div className="flex justify-center items-center gap-6 mb-4">
          <div className="text-center">
            <div 
              className="w-14 h-14 mx-auto mb-2 rounded-full flex items-center justify-center text-white text-lg font-bold"
              style={{ backgroundColor: homeTeam?.team_color || '#666' }}
              data-testid="home-team-icon"
            >
              {homeTeam?.short_name?.slice(0, 2) || 'HM'}
            </div>
            <div className="text-base font-bold text-gray-800">
              {homeTeam?.name || 'Home'}
            </div>
            <div className="text-2xl font-bold text-gray-700 mt-1" data-testid="home-score">
              {homeScore}
            </div>
          </div>

          <div className="text-xl text-gray-400 font-bold">-</div>

          <div className="text-center">
            <div 
              className="w-14 h-14 mx-auto mb-2 rounded-full flex items-center justify-center text-white text-lg font-bold"
              style={{ backgroundColor: awayTeam?.team_color || '#666' }}
              data-testid="away-team-icon"
            >
              {awayTeam?.short_name?.slice(0, 2) || 'AW'}
            </div>
            <div className="text-base font-bold text-gray-800">
              {awayTeam?.name || 'Away'}
            </div>
            <div className="text-2xl font-bold text-gray-700 mt-1" data-testid="away-score">
              {awayScore}
            </div>
          </div>
        </div>

        <div className="text-base text-gray-600">
          {homeScore > awayScore && `${homeTeam?.name} leads`}
          {awayScore > homeScore && `${awayTeam?.name} leads`}
          {homeScore === awayScore && 'Game is tied'}
        </div>
      </div>

      <button
        onClick={onContinue}
        className="play-button text-base px-6 py-3"
        data-testid="continue-button"
      >
        START 2ND HALF
      </button>
    </div>
  )
}

export default Halftime
