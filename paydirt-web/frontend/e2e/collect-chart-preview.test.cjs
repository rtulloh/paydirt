const {test} = require('node:test');
const assert = require('node:assert/strict');
const {requestFailure} = require('./collect-chart-preview.cjs');

const expected = '/api/game/charts/game_synthetic';
const cases = [
  ['expected canceled chart fetch', {}, true],
  ['real connection failure', {error: 'net::ERR_CONNECTION_REFUSED'}, false],
  ['unknown failure', {error: undefined}, false],
  ['other game', {url: 'http://localhost:8000/api/game/charts/other?side=home'}, false],
  ['wrong side', {url: 'http://localhost:8000/api/game/charts/game_synthetic?side=away'}, false],
  ['remote origin', {url: 'http://example.com:8000/api/game/charts/game_synthetic?side=home'}, false],
  ['different port', {url: 'http://localhost:8004/api/game/charts/game_synthetic?side=home'}, false],
  ['game action', {method: 'POST'}, false],
  ['navigation', {resource: 'document'}, false],
  ['unexpected query', {url: 'http://localhost:8000/api/game/charts/game_synthetic?side=home&extra=1'}, false],
  ['IPv4 alias', {url: 'http://127.0.0.1:8000/api/game/charts/game_synthetic?side=home'}, true],
];
for (const [name, changes, canceled] of cases) {
  test(name, () => {
    assert.equal(typeof requestFailure, 'function', 'Collector must retain expected chart cancellations separately from failures');
    const input = {url: 'http://localhost:8000/api/game/charts/game_synthetic?side=home',
      method: 'GET', resource: 'fetch', error: 'net::ERR_ABORTED', ...changes};
    const incoming = {url: () => input.url, method: () => input.method,
      resourceType: () => input.resource, failure: () => ({errorText: input.error})};
    const result = requestFailure(incoming, expected, 'home');
    assert.equal(result.canceled, canceled);
    assert.equal(result.request.url, input.url);
    assert.equal(result.request.method, input.method);
    assert.equal(result.request.error, input.error || 'Unknown request failure');
  });
}
