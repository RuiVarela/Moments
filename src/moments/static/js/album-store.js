/* Album cache: album view and viewer share one fetch. */

import { getAlbum } from "./api.js";
import { CachePolicy } from "./constants.js";

let cached = null;

// USE: reuse last result for same album+sort (album → viewer, instant).
// REFRESH: always refetch (album view, after extraction).
export async function loadAlbum(id, sort, order, policy) {
  const key = `${id}|${sort}|${order}`;

  if (policy === CachePolicy.USE && cached?.key === key) {
    return cached.album;
  }

  const album = await getAlbum(id, sort, order);
  cached = { key, album };
  return album;
}
