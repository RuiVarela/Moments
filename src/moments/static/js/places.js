/* Place names: coords → "Lisbon, Portugal". Cached; requests spaced per Nominatim policy. */

import { reverseGeocode } from "./api.js";
import { NOMINATIM_INTERVAL_MS } from "./constants.js";

// ~100 m; nearby photos share one lookup.
const KEY_DECIMALS = 3;

// Most specific locality first; address keys vary by country/size.
const LOCALITY_KEYS = ["city", "town", "village", "municipality", "county", "state"];

const cache = new Map();
let queue = Promise.resolve();

// Resolves to label or null (no address / network error).
export function placeName({ lat, lon }) {
  const key = `${lat.toFixed(KEY_DECIMALS)},${lon.toFixed(KEY_DECIMALS)}`;

  if (!cache.has(key)) {
    cache.set(key, throttle(() => lookup(lat, lon)).catch(() => {
      cache.delete(key); // Retry on next open.
      return null;
    }));
  }
  return cache.get(key);
}

async function lookup(lat, lon) {
  const address = await reverseGeocode(lat, lon);
  const locality = LOCALITY_KEYS.map((k) => address[k]).find(Boolean);
  const label = [locality, address.country].filter(Boolean).join(", ");
  return label || null;
}

// Run fn after previous request + interval.
function throttle(fn) {
  const run = queue.then(fn);
  queue = run.catch(() => {}).then(() => new Promise((r) => setTimeout(r, NOMINATIM_INTERVAL_MS)));
  return run;
}
