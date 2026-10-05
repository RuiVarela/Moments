/* API client: ONLY place that calls fetch. */

import { MediaKind } from "./constants.js";

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
    throw new ApiError(
      `${resp.status} ${resp.statusText}`,
      resp.status
    );
  }
  return resp;
}

export async function listAlbums() {
  const resp = await _fetch("/api/albums");
  return resp.json();
}

export async function getAlbum(id, sort = "date", order = "asc") {
  const params = new URLSearchParams({ sort, order });
  const resp = await _fetch(`/api/albums/${id}?${params}`);
  return resp.json();
}

export async function startExtract(id) {
  const resp = await _fetch(`/api/albums/${id}/extract`, {
    method: "POST",
  });
  return resp.json();
}

export async function getExtractStatus(id) {
  const resp = await _fetch(`/api/albums/${id}/extract/status`);
  return resp.json();
}

export function mediaUrl(albumId, mediaHash, kind) {
  return `/api/albums/${albumId}/media/${mediaHash}/${kind}`;
}
