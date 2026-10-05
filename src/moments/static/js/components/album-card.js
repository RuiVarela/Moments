/* Album card: cover, name, count, extraction badge. */

import { h, icon } from "../dom.js";
import { COVER_SIZES, PREVIEW_PX, Status, THUMB_PX } from "../constants.js";

// previewUrl: sharper cover; browser takes it when card is wider than thumb.
export function albumCard({ album, previewUrl, onOpen }) {
  const srcset = previewUrl ? `${album.cover} ${THUMB_PX}w, ${previewUrl} ${PREVIEW_PX}w` : null;
  const cover = album.cover
    ? h("img", { src: album.cover, srcset, sizes: COVER_SIZES, alt: "", loading: "lazy" })
    : h("div", { className: "album-cover-placeholder" }, icon("photo"));

  const badge = album.status === Status.RUNNING
    ? h("span", { className: "album-badge" }, "Extracting…")
    : null;

  return h("button", { type: "button", className: "album-card", onClick: onOpen },
    h("div", { className: "album-cover" }, cover),
    h("div", { className: "album-info" },
      h("span", { className: "album-name" }, album.id),
      h("span", { className: "album-meta" }, countLabel(album.count)),
      badge,
    ),
  );
}

// Unextracted albums report 0; don't claim "empty".
function countLabel(count) {
  if (!count) {
    return "Not indexed yet";
  }
  return `${count} item${count === 1 ? "" : "s"}`;
}
