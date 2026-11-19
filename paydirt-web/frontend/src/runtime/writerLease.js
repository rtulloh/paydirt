// Web Locks release automatically when their owning tab closes or crashes.
// A timed storage lease cannot safely fence a suspended tab, so unsupported
// browsers fail closed instead of allowing concurrent engine mutations.
export function createWriterLeases({ locks } = {}) {
  const active = new WeakSet();
  async function run(keys, action, lease) {
    const resources = [...new Set(keys)].sort();
    if (!resources.length || resources.some(key => typeof key !== 'string' || !key)) throw new Error('Invalid writer lease resource.');
    if (lease) {
      if (!active.has(lease) || resources.some(key => !lease.keys.includes(key))) throw new Error('The writer lease is expired or does not cover this action.');
      return action(lease);
    }
    const manager = locks === undefined ? globalThis.navigator?.locks : locks;
    if (!manager?.request) throw new Error('This browser does not support safe writable sessions (Web Locks). Use a current browser over HTTPS or localhost.');
    const owned = { keys: resources };
    async function acquire(index) {
      if (index === resources.length) {
        active.add(owned);
        try { return await action(owned); } finally { active.delete(owned); }
      }
      return manager.request(`paydirt-writer:${resources[index]}`, { mode: 'exclusive', ifAvailable: true }, lock => {
        if (!lock) throw new Error('This game or season is being changed in another tab. Wait for it, then reopen the latest save.');
        return acquire(index + 1);
      });
    }
    return acquire(0);
  }
  return { run };
}
const leases = createWriterLeases();
export const withWriterLease = (...args) => leases.run(...args);
export function gameWriterKeys(record, gameId = record?.id) {
  return [`game:${record?.id || gameId}`, ...(record?.metadata?.campaignId ? [`campaign:${record.metadata.campaignId}`] : [])];
}
export async function assertSavedRevision(record, repository) {
  const current = await repository.get(record.id);
  if (!current || current.revision !== record.revision) throw new Error('This save changed in another tab. Reopen the latest save before continuing.');
  return current;
}
