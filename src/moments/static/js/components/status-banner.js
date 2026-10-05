/* Status banner: extraction progress or error with retry.

   Returns { el, showProgress(done, total), showError(msg, onRetry), hide() }.
*/

import { h, clear } from "../dom.js";

const BannerKind = Object.freeze({
  PROGRESS: "progress",
  ERROR: "error",
});

export function statusBanner() {
  const el = h("div", { className: "status-banner", role: "status", hidden: true });

  function show(kind, ...children) {
    clear(el);
    el.dataset.kind = kind;
    el.append(...children);
    el.hidden = false;
  }

  return {
    el,

    showProgress(done, total) {
      const text = total ? `Extracting… ${done} / ${total}` : "Extracting…";
      const bar = h("progress", { max: total || 1, value: done });
      show(BannerKind.PROGRESS, h("span", {}, text), bar);
    },

    showError(message, onRetry) {
      const retry = h("button", { type: "button", onClick: onRetry }, "Retry");
      show(BannerKind.ERROR, h("span", {}, message), retry);
    },

    hide() {
      el.hidden = true;
    },
  };
}
