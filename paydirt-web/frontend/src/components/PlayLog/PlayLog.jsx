import { useState, useRef, useEffect } from 'react'

const OFFENSE_PLAY_NAMES = {
  '1': 'Line Plunge', '2': 'Off Tackle', '3': 'End Run', '4': 'Draw',
  '5': 'Screen', '6': 'Short Pass', '7': 'Medium Pass', '8': 'Long Pass', '9': 'TE/Sideline',
  'Q': 'QB Sneak', 'K': 'Kneel', 'P': 'Punt', 'F': 'Field Goal', 'S': 'Spike', 'KO': 'Kickoff'
}

const DEFENSE_PLAY_NAMES = {
  'A': 'Standard', 'B': 'Short Yardage', 'C': 'Spread', 'D': 'Short Pass', 'E': 'Long Pass'
}

function formatFieldPosition(position, offenseTeam) {
  if (position === null || position === undefined) return ''
  
  // Use the same display logic as the CLI game
  // Position is from offense's perspective (yards to opponent's goal line)
  if (position <= 50) {
    return position === 0 ? 'Goal Line' : `${position} yard line`
  }
  return `${100 - position} yard line`
}

export function PlayLog({ entries }) {
  const [isOpen, setIsOpen] = useState(false)
  const scrollRef = useRef(null)
  const prevEntriesLength = useRef(entries.length)
  const hasAutoOpened = useRef(false)

  // Auto-open log when entries are loaded (e.g. from a saved game)
  useEffect(() => {
    if (entries.length > 0 && !hasAutoOpened.current) {
      setIsOpen(true)
      hasAutoOpened.current = true
    }
  }, [entries.length])

  // Auto-scroll to bottom when new entries are added
  useEffect(() => {
    // Only scroll if we're open AND a new entry was added
    if (isOpen && entries.length > prevEntriesLength.current && scrollRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
      })
    }
    prevEntriesLength.current = entries.length
  }, [entries.length, isOpen])
  
  // Scroll to bottom when log is first opened
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
      })
    }
  }, [isOpen])
  
  if (entries.length === 0) return null
  
  return (
    <div className="fixed bottom-0 right-0 z-50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-gray-800 text-white px-3 py-1 rounded-t-lg text-sm font-bold"
      >
        {isOpen ? '▼' : '▲'} LOG ({entries.length})
      </button>
      
      <div 
        className={`bg-gray-900 text-gray-300 text-xs max-h-48 overflow-y-auto w-[400px] border border-gray-700 rounded-tl-lg transition-all duration-200 ${isOpen ? 'block' : 'hidden'}`}
      >
        <div ref={scrollRef} className="p-2 space-y-1">
          {entries.map((entry, index) => (
            <div key={index} className="border-b border-gray-700 pb-1">
              <div className="flex justify-between">
                <span className="text-yellow-400">
                  {entry.quarter}Q {entry.time}
                </span>
                <span className="text-gray-500">
                  {entry.down} & {entry.yardsToGo}
                  {entry.ballPosition !== null && entry.ballPosition !== undefined && (
                    <span className="text-gray-400 ml-2">
                      @ {formatFieldPosition(entry.ballPosition, entry.offense)}
                    </span>
                  )}
                </span>
              </div>
              <div className="flex justify-between mt-0.5">
                <span className={entry.offense === entry.playerTeam ? 'text-green-400' : 'text-red-400'}>
                  <span className="font-bold">{entry.offense}</span> (Off): {OFFENSE_PLAY_NAMES[entry.offensePlay] || entry.offensePlay} ({entry.offensePlay})
                </span>
              </div>
              <div className="flex justify-between mt-0.5">
                <span className={entry.defense === entry.playerTeam ? 'text-green-400' : 'text-red-400'}>
                  <span className="font-bold">{entry.defense}</span> (Def): {DEFENSE_PLAY_NAMES[entry.defensePlay] || entry.defensePlay} ({entry.defensePlay})
                </span>
              </div>
              <div className="mt-1 text-white">
                {entry.description}
                {entry.yards !== 0 && <span className={entry.yards > 0 ? 'text-green-500' : 'text-red-500'}> ({entry.yards > 0 ? '+' : ''}{entry.yards})</span>}
                {entry.scoreChange && <span className="text-yellow-400 font-bold ml-2">{entry.scoreChange}</span>}
                {entry.turnover && <span className="text-red-400 font-bold ml-2">TURNOVER</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function logPlay(playData, consoleLog = true) {
  const logEntry = {
    quarter: playData.quarter,
    time: playData.timeRemaining,
    down: playData.down,
    yardsToGo: playData.yardsToGo,
    ballPosition: playData.ballPosition || null,
    offense: playData.offenseTeam,
    defense: playData.defenseTeam,
    playerTeam: playData.playerTeam,
    offensePlay: playData.offensePlay,
    defensePlay: playData.defensePlay,
    description: playData.description,
    yards: playData.yards,
    scoreChange: playData.scoreChange,
    turnover: playData.turnover,
  }
  
  if (consoleLog) {
    const oName = OFFENSE_PLAY_NAMES[logEntry.offensePlay] || logEntry.offensePlay
    const dName = DEFENSE_PLAY_NAMES[logEntry.defensePlay] || logEntry.defensePlay
    const fp = formatFieldPosition(logEntry.ballPosition, logEntry.offense)
    console.log(`[${logEntry.quarter}Q ${logEntry.time}s] ${logEntry.offense} vs ${logEntry.defense} | ${oName} vs ${dName} | ${logEntry.description} (${logEntry.yards}) | ${logEntry.down} & ${logEntry.yardsToGo} @ ${fp}`)
  }
  
  return logEntry
}

export default PlayLog
