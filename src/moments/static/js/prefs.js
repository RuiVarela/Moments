/* Preferences persisted in localStorage. */

import { PREF_KEYS, SortKey, SortOrder } from "./constants.js";

// Stored value may be a removed option (e.g. "mtime") → default; API would 400.
export function getSort() {
  try {
    const stored = localStorage.getItem(PREF_KEYS.SORT);
    return Object.values(SortKey).includes(stored) ? stored : SortKey.DATE;
  } catch {
    return SortKey.DATE;
  }
}

export function setSort(sort) {
  try {
    localStorage.setItem(PREF_KEYS.SORT, sort);
  } catch {
    // localStorage unavailable; silent fail.
  }
}

export function getOrder() {
  try {
    return localStorage.getItem(PREF_KEYS.ORDER) || SortOrder.ASC;
  } catch {
    return SortOrder.ASC;
  }
}

export function setOrder(order) {
  try {
    localStorage.setItem(PREF_KEYS.ORDER, order);
  } catch {
    // localStorage unavailable; silent fail.
  }
}
