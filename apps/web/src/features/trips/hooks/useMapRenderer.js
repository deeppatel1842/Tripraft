// Purpose: Provides reusable React state/query behavior for Map Renderer.
import { useState, useEffect } from 'react';
import { LEAFLET_CSS_URL, LEAFLET_JS_URL } from '../constants/mapConfig';

/**
 * Loads Leaflet CSS + JS from CDN, returns true when window.L is ready.
 */
export default function useLeaflet() {
  const [ready, setReady] = useState(!!window.L);

  useEffect(() => {
    if (window.L) { setReady(true); return; }

    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = LEAFLET_CSS_URL;
      document.head.appendChild(link);
    }

    let script = document.getElementById('leaflet-js');
    if (!script) {
      script = document.createElement('script');
      script.id = 'leaflet-js';
      script.src = LEAFLET_JS_URL;
      document.head.appendChild(script);
    }
    const onLoad = () => setReady(true);
    script.addEventListener('load', onLoad);
    return () => script.removeEventListener('load', onLoad);
  }, []);

  return ready;
}
