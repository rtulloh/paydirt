import { useEffect, useState } from 'react';
import { libraryTransport } from './nativeLibrary';
export function useNativeLibrary() {
  const [native, setNative] = useState(null);
  useEffect(() => {
    let active = true;
    libraryTransport.enabled().then(value => { if (active) setNative(value); }).catch(() => {});
    return () => { active = false; };
  }, []);
  return native;
}
