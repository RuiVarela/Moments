/* API client: ONLY place that calls fetch. */

import { NOMINATIM_URL, NOMINATIM_ZOOM, SortKey, SortOrder } from "./constants.js";

export class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function _fetch(url, options = {}) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    throw new ApiError(`${resp.status} ${resp.statusText}`, resp.status);
  }
  return resp;
}

// Album ids are folder names; may contain spaces, "#", "?".
function albumPath(id) {
  return `/api/albums/${encodeURIComponent(id)}`;
}

export async function listAlbums() {
  const resp = await _fetch("/api/albums");
  return resp.json();
}

// Also starts extraction server-side if album not yet extracted.
export async function getAlbum(id, sort = SortKey.DATE, order = SortOrder.ASC) {
  const params = new URLSearchParams({ sort, order });
  const resp = await _fetch(`${albumPath(id)}?${params}`);
  return resp.json();
}

export async function startExtract(id) {
  const resp = await _fetch(`${albumPath(id)}/extract`, { method: "POST" });
  return resp.json();
}

export async function getExtractStatus(id) {
  const resp = await _fetch(`${albumPath(id)}/extract/status`);
  return resp.json();
}

export async function setCover(id, hash) {
  const resp = await _fetch(`${albumPath(id)}/cover`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hash }),
  });
  return resp.json();
}

export function mediaUrl(albumId, mediaHash, kind) {
  return `${albumPath(albumId)}/media/${encodeURIComponent(mediaHash)}/${kind}`;
}

// Third-party OSM Nominatim: coords → address ({ city, town, country, ... }).
export async function reverseGeocode(lat, lon) {
  const params = new URLSearchParams({
    format: "jsonv2",
    lat,
    lon,
    zoom: NOMINATIM_ZOOM,
    "accept-language": navigator.language,
  });
  const resp = await _fetch(`${NOMINATIM_URL}?${params}`);
  const body = await resp.json();
  return body.address ?? {};
}
