/* Media tile: lazy thumb; videos get play badge + duration. */

import { h, icon, duration, fileName } from "../dom.js";
import { MediaType } from "../constants.js";

export function mediaTile({ item, thumbUrl, onOpen }) {
  const name = fileName(item.path);
  const thumb = h("img", { src: thumbUrl, alt: "", loading: "lazy", decoding: "async" });

  // Thumb missing (file failed extraction) → neutral placeholder.
  thumb.addEventListener("error", () => thumb.replaceWith(placeholder()), { once: true });

  const badge = item.type === MediaType.VIDEO
    ? h("span", { className: "media-tile-badge" }, icon("play"), " ", duration(item.duration))
    : null;

  return h("button", { type: "button", className: "media-tile", "aria-label": name, onClick: onOpen },
    thumb,
    badge,
  );
}

function placeholder() {
  return h("span", { className: "media-tile-placeholder" }, icon("photo"));
}
