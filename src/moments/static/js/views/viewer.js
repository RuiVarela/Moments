/* Viewer: full-screen media, one item at a time.

   ┌──────────────────────────────────┐
   │░ ✕  ℹ  ⛶ ░░ ❮  3 / 42  ❯ ░░░░░░░░░│  top bar, semi-transparent, over media
   │             [ media ]            │  stage (swipe ◄ ►, tap toggles top bar, zoom/pan)
   │░[ info panel, toggled by "i" ]░░░│  semi-transparent, over media
   └──────────────────────────────────┘
   Keys: ← → navigate, Esc close, i info.
   Images: wheel/pinch zoom, drag pans, double tap fit ↔ fill. Swipe only when not zoomed.
   Next/prev replace the URL (no history entry per photo).
*/

import { h, clear, icon } from "../dom.js";
import { mediaUrl } from "../api.js";
import { loadAlbum, saveCover } from "../album-store.js";
import { getSort, getOrder } from "../prefs.js";
import { Route } from "../router.js";
import {
  CachePolicy, CoverState, HEIC_EXTS, KEY_NAMES, MediaKind, MediaType, PRELOAD_NEIGHBORS, RoutePath,
} from "../constants.js";
import { Gestures, Swipe } from "../components/gestures.js";
import { ZoomPan } from "../components/zoom-pan.js";
import { mediaInfo } from "../components/media-info.js";
import { placeName } from "../places.js";

const Bar = Object.freeze({
  SHOWN: "shown",
  HIDDEN: "hidden",
});

const BAR_HIDDEN_CLASS = "viewer-bar--hidden";

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
  #coverHash = null;
  #coverSaving = null;
  #coverFailed = null;
  #place = null;
  #media = null;
  #zoom = null;
  #stage = h("div", { className: "viewer-stage" });
  #counter = h("span", { className: "viewer-counter" });
  #info = h("div", { className: `viewer-info-panel ${BAR_HIDDEN_CLASS}`, inert: true });
  #top;
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
    // Grid: actions | nav | empty, keeps nav centered.
    // Starts hidden; slides in once mounted.
    this.#top = h("div", { className: `viewer-top ${BAR_HIDDEN_CLASS}`, inert: true },
      h("div", { className: "viewer-actions" },
        this.#closeBtn,
        navButton("info", "Info", () => this.#toggleInfo()),
        navButton("fullscreen", "Fullscreen", () => this.#toggleFullscreen()),
      ),
      h("div", { className: "viewer-nav" }, this.#prevBtn, this.#counter, this.#nextBtn),
      h("div"),
    );

    const body = h("div", { className: "viewer-body" }, this.#stage, this.#top, this.#info);

    app.appendChild(h("div", { className: "viewer", role: "dialog", "aria-label": "Media viewer" },
      body,
    ));

    new Gestures(this.#stage, {
      onTap: () => this.#toggleTop(),
      onDoubleTap: (x, y) => this.#zoom?.toggleFill(x, y),
      onDrag: (dx, dy) => this.#zoom?.panBy(dx, dy),
      onPinch: (ratio, x, y) => this.#zoom?.zoomBy(ratio, x, y),
      onWheel: (ratio, x, y) => this.#zoom?.zoomBy(ratio, x, y),
      onSwipe: (swipe) => this.#swipe(swipe),
    }, this.#ctx.signal);

    document.addEventListener("keydown", (e) => this.#onKey(e), { signal: this.#ctx.signal });
    // Reflow commits hidden state so the slide-in animates.
    void this.#top.offsetHeight;
    setBar(this.#top, Bar.SHOWN);
  }

  // Load album items (cached when coming from album view), show requested hash.
  async open(hash) {
    try {
      const album = await loadAlbum(this.#albumId, getSort(), getOrder(), CachePolicy.USE);
      if (this.#ctx.signal.aborted) {
        return;
      }

      this.#items = album.items;
      this.#coverHash = album.cover_hash;
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

    // Zoom images only; fresh state per item (starts at fit).
    this.#zoom = item.type === MediaType.IMAGE ? new ZoomPan(this.#media, this.#stage) : null;

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

  // Zoomed: drags pan, so swipes don't navigate.
  #swipe(swipe) {
    if (this.#zoom?.zoomed) {
      return;
    }
    this.#step(swipe === Swipe.LEFT ? Step.NEXT : Step.PREV);
  }

  #close() {
    this.#media?.pause?.();
    this.#ctx.navigate(new Route(RoutePath.ALBUM, this.#albumId));
  }

  #toggleTop() {
    setBar(this.#top, isHidden(this.#top) ? Bar.SHOWN : Bar.HIDDEN);
  }

  #toggleInfo() {
    setBar(this.#info, isHidden(this.#info) ? Bar.SHOWN : Bar.HIDDEN);
    this.#renderInfo();
  }

  #toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  // Coords first; place name swapped in when resolved. Lookup only while panel open (third-party call).
  async #renderInfo() {
    const item = this.#items[this.#index];
    this.#place = null;
    this.#drawInfo(item);

    if (isHidden(this.#info) || !item.gps) {
      return;
    }

    const place = await placeName(item.gps);

    // Navigated or closed meanwhile.
    if (!place || !this.#isCurrent(item)) {
      return;
    }
    this.#place = place;
    this.#drawInfo(item);
  }

  #drawInfo(item) {
    const cover = { state: this.#coverState(item), onSet: () => this.#setCover(item) };
    clear(this.#info);
    this.#info.appendChild(mediaInfo(item, this.#place, cover));
  }

  #coverState(item) {
    const states = [
      [this.#coverSaving, CoverState.SAVING],
      [this.#coverHash, CoverState.CURRENT],
      [this.#coverFailed, CoverState.FAILED],
    ];
    return states.find(([hash]) => hash === item.hash)?.[1] ?? CoverState.OTHER;
  }

  // Saving… → "Album cover ✓", or "Failed, retry".
  async #setCover(item) {
    this.#coverSaving = item.hash;
    this.#coverFailed = null;
    this.#drawInfo(item);

    try {
      await saveCover(this.#albumId, item.hash);
      this.#coverHash = item.hash;
    } catch {
      this.#coverFailed = item.hash;
    }
    this.#coverSaving = null;

    if (this.#isCurrent(item)) {
      this.#drawInfo(item);
    }
  }

  #isCurrent(item) {
    return !this.#ctx.signal.aborted && this.#items[this.#index] === item;
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

// Slide bar out/in (direction set in CSS); inert keeps hidden buttons out of tab order.
function setBar(el, bar) {
  const hidden = bar === Bar.HIDDEN;
  el.classList.toggle(BAR_HIDDEN_CLASS, hidden);
  el.inert = hidden;
}

function isHidden(el) {
  return el.classList.contains(BAR_HIDDEN_CLASS);
}

function navButton(iconName, label, onClick) {
  return h("button", { type: "button", className: `viewer-btn viewer-${iconName}`, "aria-label": label, title: label, onClick },
    icon(iconName),
  );
}
