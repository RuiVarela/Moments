/* Month divider: full-width grid header, e.g. "March 2006". */

import { h } from "../dom.js";

export function monthDivider(label) {
  return h("h2", { className: "month-divider" }, label);
}
