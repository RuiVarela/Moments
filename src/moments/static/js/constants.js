/* Constants and enums. */

export const RoutePath = Object.freeze({
  LANDING: "",
  ALBUM: "a",
  VIEWER: "m",
});

export const SortKey = Object.freeze({
  DATE: "date",
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

// Rendition widths (px) for srcset; mirror config thumb_size / preview_size defaults.
export const THUMB_PX = 200;
export const PREVIEW_PX = 800;

// Album card rendered width; browser picks thumb or preview from it.
export const COVER_SIZES = "(max-width: 600px) 50vw, 300px";

// "Set as cover" button in viewer info panel.
export const CoverState = Object.freeze({
  OTHER: "other",
  CURRENT: "current",
  SAVING: "saving",
  FAILED: "failed",
});

export const CachePolicy = Object.freeze({
  USE: "use",
  REFRESH: "refresh",
});

export const SORT_LABELS = Object.freeze({
  [SortKey.DATE]: "Date taken",
  [SortKey.NAME]: "Name",
});

export const OSM_URL = "https://www.openstreetmap.org/";
export const OSM_ZOOM = 15;

// Reverse geocoding (place names). Usage policy: max 1 request/s.
export const NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse";
export const NOMINATIM_ZOOM = 10; // City level.
export const NOMINATIM_INTERVAL_MS = 1000;
export const MS_PER_SECOND = 1000;

export const POLL_INTERVAL_MS = 1000;
export const PRELOAD_NEIGHBORS = 1;
export const SWIPE_THRESHOLD_PX = 50;
export const TAP_SLOP_PX = 10;
export const DOUBLE_TAP_MS = 300;
export const DOUBLE_TAP_SLOP_PX = 40;
export const WHEEL_ZOOM_RATE = 0.002; // Per wheel px: 100 px → ×1.22.
export const WHEEL_LINE_PX = 16;
export const MAX_ZOOM = 8;

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
