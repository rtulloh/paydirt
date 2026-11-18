const PYODIDE_ROOT = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let runtime;

async function initialize(manifestLocation) {
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_ROOT}pyodide.mjs`);
  const pyodide = await loadPyodide({ indexURL: PYODIDE_ROOT });
  await pyodide.loadPackage(['pydantic', 'pyyaml']);
  const manifestUrl = new URL(manifestLocation);
  const manifestResponse = await fetch(manifestUrl);
  if (!manifestResponse.ok) throw new Error('Could not download the browser game manifest.');
  const manifest = await manifestResponse.json();
  if (manifest.version !== 1 || manifest.scope !== 'public-released-seasons' || manifest.files?.length !== 1) throw new Error('Unsupported browser game manifest.');
  const archive = manifest.files[0];
  if (archive.url !== 'python.zip' || archive.mount !== '/app' || !/^[a-f0-9]{64}$/.test(archive.sha256)) throw new Error('Invalid browser game archive manifest.');
  const response = await fetch(new URL(archive.url, manifestUrl));
  if (!response.ok) throw new Error('Could not download the browser game engine.');
  const bytes = await response.arrayBuffer();
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
  if (digest !== archive.sha256 || bytes.byteLength !== archive.bytes) throw new Error('Browser game download failed its integrity check. Reload to try again.');
  pyodide.unpackArchive(bytes, 'zip', { extractDir: '/app' });
  await pyodide.runPythonAsync("import sys\nsys.path[:0] = ['/app', '/app/paydirt-web/backend']\nimport browser_bridge");
  return pyodide;
}

// One queue owns every Python action. A lost reply never triggers an automatic replay.
let queue = Promise.resolve();
self.addEventListener('message', ({ data }) => {
  queue = queue.then(async () => {
    try {
      runtime ||= initialize(data.manifestUrl);
      const pyodide = await runtime;
      pyodide.globals.set('_browser_request', JSON.stringify(data.request));
      const raw = await pyodide.runPythonAsync('await browser_bridge.dispatch_json(_browser_request)');
      self.postMessage({ id: data.id, result: JSON.parse(raw) });
    } catch (error) {
      self.postMessage({ id: data.id, error: `Could not run the browser game: ${error.message}` });
    }
  });
});
