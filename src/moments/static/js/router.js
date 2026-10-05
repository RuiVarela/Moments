/* Hash-based router with subscribers. */

import { Route } from "./constants.js";

export class Route {
  constructor(path, albumId = null, mediaHash = null) {
    this.path = path;
    this.albumId = albumId;
    this.mediaHash = mediaHash;
  }

  static parse() {
    const hash = (location.hash.slice(1) || "").split("/");
    if (!hash[0]) return new Route("");

    if (hash[0] === "a" && hash[1]) {
      const albumId = decodeURIComponent(hash[1]);
      const mediaHash = hash[2]?.slice(1) ? decodeURIComponent(hash[3]) : null;
      if (hash[2] === "m" && mediaHash) {
        return new Route("m", albumId, mediaHash);
      }
      return new Route("a", albumId);
    }

    return new Route("");
  }

  toString() {
    if (this.path === "a") return `#/a/${encodeURIComponent(this.albumId)}`;
    if (this.path === "m") {
      return `#/a/${encodeURIComponent(this.albumId)}/m/${encodeURIComponent(
        this.mediaHash
      )}`;
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

export function replace(route) {
  history.replaceState(null, "", route.toString());
  notifySubscribers();
}

function notifySubscribers() {
  const route = Route.parse();
  subscribers.forEach((fn) => fn(route));
}

window.addEventListener("hashchange", notifySubscribers);
