import { API_BASE } from '../config';

// Capability is explicit and shared by both repositories. Once selected, a
// native failure must never silently create a second browser-owned library.
export function createLibraryTransport({ browser = import.meta.env.VITE_PAYDIRT_BROWSER === '1', fetcher = (...args) => globalThis.fetch(...args) } = {}) {
  let capability;
  async function enabled() {
    if (browser) return false;
    if (!capability) {
      const probe = (async () => {
      const response = await fetcher(`${API_BASE}/api/library/status`);
      if (response.status === 404) return false;
      if (!response.ok) throw new Error('Could not determine saved-game storage capability. Retry before saving.');
      const status = await response.json();
      if (status.enabled !== true && status.enabled !== false) throw new Error('Invalid saved-game storage capability response.');
      return status.enabled;
      })();
      capability = probe;
      // A failed discovery selects no storage owner. Allow the next explicit
      // operation to retry, without resetting a newer or successful selection.
      probe.catch(() => { if (capability === probe) capability = undefined; });
    }
    return capability;
  }
  return {
    enabled,
    async command(body) {
      const response = await fetcher(`${API_BASE}/api/library/command`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const value = await response.json();
      if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Native saved-game storage failed. Your previous save was retained.');
      return value;
    },
  };
}

export function routeRepository(store, local, transport = libraryTransport) {
  const argumentsFor = store === 'games' ? {
    list: () => ({}), get: id => ({id}),
    put: (record, {expectedRevision} = {}) => ({record,expectedRevision}),
    remove: (id, {expectedRevision} = {}) => ({id,expectedRevision}),
  } : {
    list: () => ({}), get: id => ({id}),
    put: (campaign,expectedRevision,gameRecord,expectedGameRevision) => ({campaign,expectedRevision,gameRecord,expectedGameRevision}),
    remove: record => ({record}), exportBundle: record => ({record}),
    importBundle: (campaign,games) => ({campaign,games}),
  };
  return Object.fromEntries(Object.entries(argumentsFor).map(([action, encode]) => [action, async (...args) => {
    if (!await transport.enabled()) return local[action](...args);
    return transport.command({store,action,...encode(...args)});
  }]));
}

export const libraryTransport = createLibraryTransport();
