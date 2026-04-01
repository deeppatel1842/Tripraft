/**
 * Data-unwrapping utilities for API response normalization.
 */

export function unwrap(r) {
  if (!r) return r;
  if (typeof r !== 'object') return r;
  if ('success' in r && 'data' in r) return r.data;
  return r;
}

export function toArray(raw, ...keys) {
  const d = unwrap(raw);
  if (Array.isArray(d)) return d;
  if (d && typeof d === 'object') {
    for (const k of keys) {
      if (Array.isArray(d[k])) return d[k];
    }
  }
  return [];
}

export function toObject(raw) {
  const d = unwrap(raw);
  if (d && typeof d === 'object' && !Array.isArray(d)) return d;
  return null;
}

export function getMarkerCategory(cat) {
  if (!cat) return 'PLACE';
  const c = cat.toLowerCase();
  if (c === 'res' || c === 'restaurant') return 'RES';
  if (c === 'event' || c === 'events') return 'EVENT';
  return 'PLACE';
}

export function sanitizePopup(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
