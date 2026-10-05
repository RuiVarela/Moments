/* Constants and enums. */

export const RoutePath = Object.freeze({
  LANDING: "",
  ALBUM: "a",
  VIEWER: "m",
});

export const SortKey = Object.freeze({
  DATE: "date",
  MTIME: "mtime",
  NAME: "name",
});

export const SortOrder = Object.freeze({
  ASC: "asc",
  DESC: "desc",
});

export const MediaType = Object.freeze({
  IMAGE: "image",
  VIDEO: "video",
});

export const Status = Object.freeze({
  IDLE: "idle",
  RUNNING: "running",
  FAILED: "failed",
});

export const MediaKind = Object.freeze({
  THUMB: "thumb",
  PREVIEW: "preview",
  ORIGINAL: "original",
});

export const CachePolicy = Object.freeze({
  USE: "use",
  REFRESH: "refresh",
});

export const SORT_LABELS = Object.freeze({
  [SortKey.DATE]: "Date taken",
  [SortKey.MTIME]: "Modified",
  [SortKey.NAME]: "Name",
});

export const OSM_URL = "https://www.openstreetmap.org/";
export const OSM_ZOOM = 15;
export const MS_PER_SECOND = 1000;

export const POLL_INTERVAL_MS = 1000;
export const PRELOAD_NEIGHBORS = 1;
export const SWIPE_THRESHOLD_PX = 50;

export const KEY_NAMES = Object.freeze({
  ARROW_LEFT: "ArrowLeft",
  ARROW_RIGHT: "ArrowRight",
  ESCAPE: "Escape",
  I: "i",
});

export const PREF_KEYS = Object.freeze({
  SORT: "moments_sort",
  ORDER: "moments_order",
});

export const MIME_TYPES = Object.freeze({
  JPEG: "image/jpeg",
  PNG: "image/png",
  WEBP: "image/webp",
  GIF: "image/gif",
  HEIC: "image/heic",
  MP4: "video/mp4",
  WEBM: "video/webm",
  MOV: "video/quicktime",
});

export const HEIC_EXTS = new Set([".heic", ".heif"]);
