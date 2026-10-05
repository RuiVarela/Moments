/* Preferences persisted in localStorage. */

import { PREF_KEYS, SortKey, SortOrder } from "./constants.js";

export function getSort() {
  try {
    return localStorage.getItem(PREF_KEYS.SORT) || SortKey.DATE;
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
