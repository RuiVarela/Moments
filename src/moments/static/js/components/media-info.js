/* Media info panel: name, date, size, duration, GPS link, "Set as cover". */

import { h, duration, fileName } from "../dom.js";
import { CoverState, MS_PER_SECOND, OSM_URL, OSM_ZOOM } from "../constants.js";

// place: resolved name (e.g. "Lisbon, Portugal") or null → coords shown.
// cover: { state: CoverState, onSet } or null → no cover row.
export function mediaInfo(item, place = null, cover = null) {
  const rows = [
    row("File", fileName(item.path)),
    row("Date", formatDate(item.date)),
    item.width ? row("Size", `${item.width} × ${item.height}`) : null,
    item.duration ? row("Duration", duration(item.duration)) : null,
    item.gps ? row("Location", gpsLink(item.gps, place)) : null,
    cover ? row("Cover", coverButton(cover)) : null,
  ];

  return h("dl", { className: "media-info" }, rows);
}

function row(label, value) {
  return [h("dt", {}, label), h("dd", {}, value)];
}

function formatDate(seconds) {
  if (!seconds) {
    return "—";
  }
  return new Date(seconds * MS_PER_SECOND).toLocaleString();
}

// Example: 38.7139, -9.1394 → openstreetmap.org/?mlat=38.7139&mlon=-9.1394#map=15/38.7139/-9.1394
function gpsLink({ lat, lon }, place) {
  const coords = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  const url = `${OSM_URL}?mlat=${lat}&mlon=${lon}#map=${OSM_ZOOM}/${lat}/${lon}`;
  return h("a", { href: url, target: "_blank", rel: "noopener", title: coords }, place ?? coords);
}

const COVER_LABELS = Object.freeze({
  [CoverState.OTHER]: "Set as cover",
  [CoverState.CURRENT]: "Album cover ✓",
  [CoverState.SAVING]: "Saving…",
  [CoverState.FAILED]: "Failed, retry",
});

function coverButton({ state, onSet }) {
  const idle = state === CoverState.OTHER || state === CoverState.FAILED;
  return h("button", { type: "button", className: "cover-btn", disabled: !idle, onClick: onSet }, COVER_LABELS[state]);
}
