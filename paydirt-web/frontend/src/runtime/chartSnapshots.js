const KEY = 'paydirt_browser_chart_snapshot';

// Read-only public chart data, never game state. Only the latest chart book is retained.
export function writeChartSnapshots(gameId, books) {
  try { localStorage.setItem(KEY, JSON.stringify({ gameId, books })); return true; }
  catch { return false; }
}
export function readChartSnapshot(gameId, side) {
  try {
    const snapshot = JSON.parse(localStorage.getItem(KEY) || 'null');
    return snapshot?.gameId === gameId ? snapshot.books[side] || null : null;
  } catch { return null; }
}
