/* Viewer: full-screen media, one item at a time.

   ┌──────────────────────────────────┐
   │ 3 / 42                    ℹ  ✕   │  top bar
   │ ❮          [ media ]          ❯  │  stage (swipe ◄ ►)
   │ [ info panel, toggled by "i" ]   │
   └──────────────────────────────────┘
   Keys: ← → navigate, Esc close, i info.
   Next/prev replace the URL (no history entry per photo).
*/

import { h, clear, icon } from "../dom.js";
import { mediaUrl } from "../api.js";
import { loadAlbum } from "../album-store.js";
import { getSort, getOrder } from "../prefs.js";
import { Route } from "../router.js";
import {
  CachePolicy, HEIC_EXTS, KEY_NAMES, MediaKind, MediaType, PRELOAD_NEIGHBORS, RoutePath,
} from "../constants.js";
import { SwipeDetector } from "../components/swipe.js";
import { mediaInfo } from "../components/media-info.js";
import { placeName } from "../places.js";

const Step = Object.freeze({
  PREV: -1,
  NEXT: 1,
});

export function renderViewer(app, route, ctx) {
  const viewer = new Viewer(route.albumId, ctx);
  viewer.mount(app);
  viewer.open(route.mediaHash);
}

class Viewer {
  #albumId;
  #ctx;
  #items = [];
  #index = 0;
  #media = null;
  #stage = h("div", { className: "viewer-stage" });
  #counter = h("span", { className: "viewer-counter" });
  #info = h("div", { className: "viewer-info", hidden: true });
  #prevBtn;
  #nextBtn;
  #closeBtn;

  constructor(albumId, ctx) {
    this.#albumId = albumId;
    this.#ctx = ctx;

    this.#prevBtn = navButton("prev", "Previous", () => this.#step(Step.PREV));
    this.#nextBtn = navButton("next", "Next", () => this.#step(Step.NEXT));
    this.#closeBtn = navButton("close", "Close", () => this.#close());
  }

  mount(app) {
    const top = h("div", { className: "viewer-top" },
      this.#counter,
      h("div", { className: "viewer-actions" },
        navButton("info", "Info", () => this.#toggleInfo()),
        this.#closeBtn,
      ),
    );

    const body = h("div", { className: "viewer-body" }, this.#prevBtn, this.#stage, this.#nextBtn);

    app.appendChild(h("div", { className: "viewer", role: "dialog", "aria-label": "Media viewer" },
      top, body, this.#info,
    ));

    new SwipeDetector(this.#stage, {
      onSwipeLeft: () => this.#step(Step.NEXT),
      onSwipeRight: () => this.#step(Step.PREV),
    });

    document.addEventListener("keydown", (e) => this.#onKey(e), { signal: this.#ctx.signal });
    this.#closeBtn.focus();
  }

  // Load album items (cached when coming from album view), show requested hash.
  async open(hash) {
    try {
      const album = await loadAlbum(this.#albumId, getSort(), getOrder(), CachePolicy.USE);
      if (this.#ctx.signal.aborted) {
        return;
      }

      this.#items = album.items;
      const index = this.#items.findIndex((item) => item.hash === hash);

      if (index < 0) {
        this.#showMessage("Media not found.");
        return;
      }
      this.#show(index);
    } catch (err) {
      if (this.#ctx.signal.aborted) {
        return;
      }
      this.#showMessage(`Could not load album: ${err.message}`);
    }
  }

  #show(index) {
    this.#index = index;
    const item = this.#items[index];

    // Detached videos may keep playing audio; stop explicitly.
    this.#media?.pause?.();

    this.#media = this.#buildMedia(item);
    clear(this.#stage);
    this.#stage.appendChild(this.#media);

    this.#counter.textContent = `${index + 1} / ${this.#items.length}`;
    this.#prevBtn.disabled = index === 0;
    this.#nextBtn.disabled = index === this.#items.length - 1;

    this.#renderInfo();

    this.#ctx.replace(new Route(RoutePath.VIEWER, this.#albumId, item.hash));
    this.#preload(index);
  }

  #buildMedia(item) {
    if (item.type === MediaType.VIDEO) {
      return h("video", {
        className: "viewer-media",
        src: this.#url(item, MediaKind.ORIGINAL),
        poster: this.#url(item, MediaKind.PREVIEW),
        controls: true,
        autoplay: true,
        playsinline: true,
        preload: "metadata",
      });
    }

    return h("img", {
      className: "viewer-media",
      src: this.#url(item, imageKind(item)),
      alt: "",
      draggable: "false",
    });
  }

  // Warm browser cache for neighbors so next/prev is instant.
  #preload(index) {
    for (let offset = -PRELOAD_NEIGHBORS; offset <= PRELOAD_NEIGHBORS; offset++) {
      const item = this.#items[index + offset];
      if (!offset || !item || item.type !== MediaType.IMAGE) {
        continue;
      }
      new Image().src = this.#url(item, imageKind(item));
    }
  }

  #step(step) {
    const next = this.#index + step;
    if (next < 0 || next >= this.#items.length) {
      return;
    }
    this.#show(next);
  }

  #close() {
    this.#media?.pause?.();
    this.#ctx.navigate(new Route(RoutePath.ALBUM, this.#albumId));
  }

  #toggleInfo() {
    this.#info.hidden = !this.#info.hidden;
    this.#renderInfo();
  }

  // Coords first; place name swapped in when resolved. Lookup only while panel open (third-party call).
  async #renderInfo() {
    const item = this.#items[this.#index];
    clear(this.#info);
    this.#info.appendChild(mediaInfo(item));

    if (this.#info.hidden || !item.gps) {
      return;
    }

    const place = await placeName(item.gps);

    // Navigated or closed meanwhile.
    if (!place || this.#ctx.signal.aborted || this.#items[this.#index] !== item) {
      return;
    }
    clear(this.#info);
    this.#info.appendChild(mediaInfo(item, place));
  }

  #onKey(e) {
    const actions = {
      [KEY_NAMES.ARROW_LEFT]: () => this.#step(Step.PREV),
      [KEY_NAMES.ARROW_RIGHT]: () => this.#step(Step.NEXT),
      [KEY_NAMES.ESCAPE]: () => this.#close(),
      [KEY_NAMES.I]: () => this.#toggleInfo(),
    };

    const action = actions[e.key];
    if (!action || e.altKey || e.ctrlKey || e.metaKey) {
      return;
    }

    e.preventDefault();
    action();
  }

  #showMessage(text) {
    clear(this.#stage);
    this.#stage.appendChild(h("p", { className: "viewer-message" }, text));
  }

  #url(item, kind) {
    return mediaUrl(this.#albumId, item.hash, kind);
  }
}

// Browsers can't render HEIC; use server-made JPEG preview.
function imageKind(item) {
  const ext = item.path.slice(item.path.lastIndexOf(".")).toLowerCase();
  return HEIC_EXTS.has(ext) ? MediaKind.PREVIEW : MediaKind.ORIGINAL;
}

function navButton(iconName, label, onClick) {
  return h("button", { type: "button", className: `viewer-btn viewer-${iconName}`, "aria-label": label, title: label, onClick },
    icon(iconName),
  );
}
