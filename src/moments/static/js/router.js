/* Hash-based router with subscribers. */

import { RoutePath } from "./constants.js";

export class Route {
  constructor(path, albumId = null, mediaHash = null) {
    this.path = path;
    this.albumId = albumId;
    this.mediaHash = mediaHash;
  }

  // "#/a/<album>/m/<hash>" → ["a", album, "m", hash]
  static parse() {
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);

    if (parts[0] !== RoutePath.ALBUM || !parts[1]) {
      return new Route(RoutePath.LANDING);
    }

    const albumId = decodeURIComponent(parts[1]);

    if (parts[2] === RoutePath.VIEWER && parts[3]) {
      return new Route(RoutePath.VIEWER, albumId, decodeURIComponent(parts[3]));
    }

    return new Route(RoutePath.ALBUM, albumId);
  }

  toString() {
    const album = `#/${RoutePath.ALBUM}/${encodeURIComponent(this.albumId)}`;

    if (this.path === RoutePath.ALBUM) {
      return album;
    }

    if (this.path === RoutePath.VIEWER) {
      return `${album}/${RoutePath.VIEWER}/${encodeURIComponent(this.mediaHash)}`;
    }

    return "#/";
  }
}

const subscribers = new Set();

export function subscribe(fn) {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

export function navigate(route) {
  location.hash = route.toString();
}

// Update URL only; caller already shows the route (e.g. viewer next/prev).
export function replace(route) {
  history.replaceState(null, "", route.toString());
}

function notifySubscribers() {
  const route = Route.parse();
  subscribers.forEach((fn) => fn(route));
}

window.addEventListener("hashchange", notifySubscribers);
