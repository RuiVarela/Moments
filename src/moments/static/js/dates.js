/* Date helpers: month grouping for the album timeline. */

import { MS_PER_SECOND } from "./constants.js";

const UNDATED_LABEL = "Undated";
const MONTH_FORMAT = Object.freeze({ month: "long", year: "numeric" });

// Consecutive items in the same month → one group. Input already date-sorted (server).
// [Mar 3 2006, Mar 20 2006, Apr 1 2006, null]
//   → [{label: "March 2006", items: 2}, {label: "April 2006", items: 1}, {label: "Undated", items: 1}]
export function groupByMonth(items, locale = undefined) {
  const groups = [];

  for (const item of items) {
    const key = monthKey(item.date);
    const last = groups.at(-1);

    if (last && last.key === key) {
      last.items.push(item);
      continue;
    }

    groups.push({ key, label: monthLabel(item.date, locale), items: [item] });
  }

  return groups;
}

// "2006-2" (March 2006; months 0-based) or null when undated.
function monthKey(seconds) {
  if (seconds == null) {
    return null;
  }

  const date = new Date(seconds * MS_PER_SECOND);
  return `${date.getFullYear()}-${date.getMonth()}`;
}

function monthLabel(seconds, locale) {
  if (seconds == null) {
    return UNDATED_LABEL;
  }

  return new Date(seconds * MS_PER_SECOND).toLocaleDateString(locale, MONTH_FORMAT);
}
