import { routeRepository } from './nativeLibrary';

const DATABASE = 'paydirt-library';
const MAX_CHECKPOINT_BYTES = 16 * 1024 * 1024;

export function openLibraryDB({ indexedDB = globalThis.indexedDB, databaseName = DATABASE } = {}) {
  return new Promise((resolve, reject) => {
    if (!indexedDB) { reject(new Error('Browser storage (IndexedDB) is unavailable. Export your game to keep a copy.')); return; }
    const request = indexedDB.open(databaseName, 1);
    request.onupgradeneeded = () => {
      for (const store of ['games', 'campaigns']) {
        if (!request.result.objectStoreNames.contains(store)) request.result.createObjectStore(store, { keyPath: 'id' });
      }
    };
    request.onsuccess = () => {
      request.result.onversionchange = () => request.result.close();
      resolve(request.result);
    };
    request.onerror = () => reject(request.error || new Error('Could not open browser storage.'));
    request.onblocked = () => reject(new Error('Close older Paydirt tabs before updating saved-game storage.'));
  });
}

export function validateGameRecord(record) {
  if (!record || typeof record !== 'object' || typeof record.id !== 'string' || !record.id || record.id.length > 200) throw new Error('Invalid saved game identity.');
  if (typeof record.name !== 'string' || !record.name.trim() || record.name.length > 200) throw new Error('A saved game needs a name of at most 200 characters.');
  if (typeof record.checkpoint !== 'string' || !record.checkpoint || record.checkpoint.length > MAX_CHECKPOINT_BYTES) throw new Error('Invalid or oversized game checkpoint.');
  // Never parse the engine text: Python integers may exceed JavaScript precision.
  if (record.metadata !== undefined && (!record.metadata || typeof record.metadata !== 'object' || Array.isArray(record.metadata))) throw new Error('Invalid game metadata.');
  return record;
}

export function createGameLibrary(options = {}) {
  const open = options.openDatabase || (() => openLibraryDB(options));
  async function transaction(mode, work) {
    const database = await open();
    return new Promise((resolve, reject) => {
      let result, failure;
      const tx = database.transaction('games', mode);
      const fail = error => { failure = error; tx.abort(); };
      tx.oncomplete = () => { database.close?.(); resolve(result); };
      tx.onerror = () => { database.close?.(); reject(failure || tx.error || new Error('Could not store saved game.')); };
      tx.onabort = () => { database.close?.(); reject(failure || tx.error || new Error('Saved game transaction was interrupted.')); };
      try { work(tx.objectStore('games'), value => { result = value; }, fail); } catch (error) { fail(error); }
    });
  }
  function revisionMatches(existing, expectedRevision) {
    if (!Number.isInteger(expectedRevision) || expectedRevision < 0) throw new Error('An expected revision is required to change a saved game.');
    if ((existing?.revision || 0) !== expectedRevision) throw new Error('This saved game changed in another tab. Reload before saving again.');
  }
  return {
    list: () => transaction('readonly', (store, done) => {
      const request = store.getAll();
      request.onsuccess = () => done(request.result.sort((a, b) => b.savedAt.localeCompare(a.savedAt)));
    }),
    get: id => transaction('readonly', (store, done) => {
      const request = store.get(id);
      request.onsuccess = () => done(request.result || null);
    }),
    put: async (record, { expectedRevision } = {}) => {
      validateGameRecord(record);
      return transaction('readwrite', (store, done, fail) => {
        const request = store.get(record.id);
        request.onsuccess = () => {
          try {
            revisionMatches(request.result, expectedRevision);
            const value = { id: record.id, name: record.name.trim(), checkpoint: record.checkpoint,
              metadata: record.metadata || {}, revision: expectedRevision + 1, savedAt: new Date().toISOString() };
            store.put(value); done(value);
          } catch (error) { fail(error); }
        };
      });
    },
    remove: (id, { expectedRevision } = {}) => transaction('readwrite', (store, done, fail) => {
      const request = store.get(id);
      request.onsuccess = () => {
        try { revisionMatches(request.result, expectedRevision); store.delete(id); done(); } catch (error) { fail(error); }
      };
    }),
  };
}

export const gameLibrary = routeRepository('games', createGameLibrary());
