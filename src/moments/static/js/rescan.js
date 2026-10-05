/* Re-extract all albums, one after the other. Module state: keeps running across views.

   list ─► album[0] start ─► poll until !running ─► album[1] … ─► finished
                                   │
                                   └─ emit progress → subscribed views

   State: { running, index, count, albumId, done, total, failed: [albumId] }
*/

import { listAlbums, startExtract, getExtractStatus } from "./api.js";
import { poll } from "./poll.js";
import { POLL_INTERVAL_MS, Status } from "./constants.js";

let state = null;
const listeners = new Set();

// Current state (null if never run); view calls on mount.
export function rescanState() {
  return state;
}

// fn(state) on every change; unsubscribed when signal aborts (view unmount).
export function onRescan(fn, signal) {
  listeners.add(fn);
  signal.addEventListener("abort", () => listeners.delete(fn), { once: true });
}

export async function rescanAll() {
  if (state?.running) {
    return;
  }

  const albums = await listAlbums();
  update({ running: true, index: 0, count: albums.length, albumId: null, done: 0, total: 0, failed: [] });

  for (const [index, album] of albums.entries()) {
    update({ index, albumId: album.id, done: 0, total: 0 });

    const ok = await extractOne(album.id);
    if (!ok) {
      update({ failed: [...state.failed, album.id] });
    }
  }

  update({ running: false });
}

// Start + wait. false on failed status or network error; never throws (next album must run).
async function extractOne(albumId) {
  try {
    await startExtract(albumId);
    const final = await poll(
      () => getExtractStatus(albumId),
      (s) => {
        update({ done: s.done, total: s.total });
        return s.status !== Status.RUNNING;
      },
      POLL_INTERVAL_MS,
    );
    return final.status !== Status.FAILED;
  } catch {
    return false;
  }
}

function update(patch) {
  state = { ...state, ...patch };
  listeners.forEach((fn) => fn(state));
}
