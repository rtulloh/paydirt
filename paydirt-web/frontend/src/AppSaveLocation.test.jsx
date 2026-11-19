import React from 'react';
import {render,screen,act,cleanup} from '@testing-library/react';
import {it,expect,afterEach,vi} from 'vitest';
import App from './App';
vi.mock('./runtime/gameFetch',()=>({gameFetch:vi.fn(async()=>({ok:true,json:async()=>({})})),browserMode:false,saveCurrentSession:vi.fn()}));
vi.mock('./runtime/nativeLibrary',async()=>({...await vi.importActual('./runtime/nativeLibrary'),libraryTransport:{enabled:vi.fn(async()=>true)}}));
afterEach(cleanup);
it('describes a native acknowledged save as stored in the application',async()=>{render(<App/>);await act(async()=>window.dispatchEvent(new CustomEvent('paydirt-save-status',{detail:{status:'saved',record:{savedAt:'2026-11-18T12:00:00Z'}}})));expect(await screen.findByText(/Saved in this application/)).toBeVisible();expect(screen.queryByText(/Saved in this browser/)).toBeNull()});
