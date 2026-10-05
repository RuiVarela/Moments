/* Album view: toolbar, extraction banner, media grid.

   load album ──► status running? ──yes──► poll status (1s) ──► reload
        │                 │                     │
        │                 no                    └─ banner: done/total
        ▼                 ▼
     grid of tiles   failed? → banner error + retry
*/

import { h, clear, icon } from "../dom.js";
import { getExtractStatus, startExtract, mediaUrl } from "../api.js";
import { loadAlbum } from "../album-store.js";
import { poll } from "../poll.js";
import { getSort, getOrder, setSort, setOrder } from "../prefs.js";
import { Route } from "../router.js";
import { CachePolicy, MediaKind, POLL_INTERVAL_MS, RoutePath, Status } from "../constants.js";
import { mediaTile } from "../components/media-tile.js";
import { sortPicker } from "../components/sort-picker.js";
import { optionsMenu } from "../components/options-menu.js";
import { statusBanner } from "../components/status-banner.js";

export function renderAlbum(app, route, ctx) {
  const view = new AlbumView(route.albumId, ctx);
  view.mount(app);
  view.refresh();
}

class AlbumView {
  #albumId;
  #ctx;
  #sort = getSort();
  #order = getOrder();
  #watching = false;
  #banner = statusBanner();
  #grid = h("div", { className: "media-grid" });
  #options;

  constructor(albumId, ctx) {
    this.#albumId = albumId;
    this.#ctx = ctx;
    this.#options = optionsMenu({
      signal: ctx.signal,
      actions: [{ label: "Re-extract album", onSelect: () => this.#reextract() }],
    });
  }

  mount(app) {
    const picker = sortPicker({
      sort: this.#sort,
      order: this.#order,
      onChange: (sort, order) => this.#resort(sort, order),
    });

    const toolbar = h("header", { className: "album-toolbar" },
      h("a", { href: new Route(RoutePath.LANDING).toString(), className: "back-link", "aria-label": "All albums" }, icon("prev")),
      h("h1", { className: "album-title" }, this.#albumId),
      picker,
      this.#options.el,
    );

    app.appendChild(h("main", { className: "section album" }, toolbar, this.#banner.el, this.#grid));
  }

  // Fetch album (starts extraction server-side if needed), render, react to status.
  async refresh() {
    try {
      const album = await loadAlbum(this.#albumId, this.#sort, this.#order, CachePolicy.REFRESH);
      if (this.#ctx.signal.aborted) {
        return;
      }

      this.#renderGrid(album.items, album.status);
      this.#applyStatus(album.status);
    } catch (err) {
      if (this.#ctx.signal.aborted) {
        return;
      }
      this.#banner.showError(`Could not load album: ${err.message}`, () => this.refresh());
    }
  }

  #renderGrid(items, status) {
    clear(this.#grid);

    if (!items.length) {
      const text = status.status === Status.RUNNING ? "" : "No photos or videos.";
      this.#grid.appendChild(h("p", { className: "empty-state" }, text));
      return;
    }

    for (const item of items) {
      this.#grid.appendChild(mediaTile({
        item,
        thumbUrl: mediaUrl(this.#albumId, item.hash, MediaKind.THUMB),
        onOpen: () => this.#ctx.navigate(new Route(RoutePath.VIEWER, this.#albumId, item.hash)),
      }));
    }
  }

  #applyStatus(status) {
    this.#options.setStatus(statusText(status));

    if (status.status === Status.RUNNING) {
      this.#banner.showProgress(status.done, status.total);
      this.#watch();
      return;
    }

    if (status.status === Status.FAILED) {
      this.#banner.showError(`Extraction failed: ${status.error ?? "unknown error"}`, () => this.#reextract());
      return;
    }

    this.#banner.hide();
  }

  // Poll until extraction stops, then reload grid. Single watcher at a time.
  async #watch() {
    if (this.#watching) {
      return;
    }
    this.#watching = true;

    try {
      await poll(() => this.#tick(), (s) => s.status !== Status.RUNNING, POLL_INTERVAL_MS, this.#ctx.signal);
      this.#watching = false;
      await this.refresh();
    } catch (err) {
      this.#watching = false;
      if (this.#ctx.signal.aborted) {
        return;
      }
      this.#banner.showError(`Lost track of extraction: ${err.message}`, () => this.refresh());
    }
  }

  async #tick() {
    const status = await getExtractStatus(this.#albumId);
    this.#options.setStatus(statusText(status));

    if (status.status === Status.RUNNING) {
      this.#banner.showProgress(status.done, status.total);
    }
    return status;
  }

  async #reextract() {
    try {
      await startExtract(this.#albumId);
      this.#banner.showProgress(0, 0);
      this.#watch();
    } catch (err) {
      this.#banner.showError(`Could not start extraction: ${err.message}`, () => this.#reextract());
    }
  }

  #resort(sort, order) {
    this.#sort = sort;
    this.#order = order;
    setSort(sort);
    setOrder(order);
    this.refresh();
  }
}

function statusText({ status, done, total, error }) {
  if (status === Status.RUNNING) {
    return `Extracting ${done} / ${total}`;
  }
  if (status === Status.FAILED) {
    return `Extraction failed: ${error ?? "unknown error"}`;
  }
  return "Extraction up to date";
}
