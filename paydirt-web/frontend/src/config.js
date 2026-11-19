// Native installs can choose a free port; development uses Vite's /api proxy.
// Keep requests with the application that served this page by default.
export const API_BASE = import.meta.env.VITE_API_BASE || globalThis.location?.origin || '';
