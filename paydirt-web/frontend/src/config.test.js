import { afterEach, expect, it, vi } from 'vitest';

afterEach(()=>{vi.unstubAllEnvs();vi.unstubAllGlobals();vi.resetModules();});

it('uses the served origin including a native custom port',async()=>{
 vi.stubEnv('VITE_API_BASE','');vi.stubGlobal('location',{origin:'http://127.0.0.1:18765'});
 vi.resetModules();expect((await import('./config.js')).API_BASE).toBe('http://127.0.0.1:18765');
});
it('preserves an explicitly configured API endpoint',async()=>{
 vi.stubEnv('VITE_API_BASE','https://example.invalid/paydirt');vi.stubGlobal('location',{origin:'http://127.0.0.1:18765'});
 vi.resetModules();expect((await import('./config.js')).API_BASE).toBe('https://example.invalid/paydirt');
});
it('keeps relative requests available without a browser location',async()=>{
 vi.stubEnv('VITE_API_BASE','');vi.stubGlobal('location',undefined);
 vi.resetModules();expect((await import('./config.js')).API_BASE).toBe('');
});
