/* Gestures: raw pointer/wheel input → high-level callbacks.

   1 pointer, still         → onTap()  (delayed: waits for a 2nd tap)
   1 pointer, still, twice  → onDoubleTap(x, y)
   1 pointer, moving        → onDrag(dx, dy) per move; onSwipe(Swipe.LEFT|RIGHT) on release past threshold
   2 pointers               → onPinch(ratio, x, y) + onDrag(dx, dy) of their midpoint
   wheel / trackpad pinch   → onWheel(ratio, x, y)

   Move/up listen on window: a drag released outside the element still ends.
*/

import {
  DOUBLE_TAP_MS, DOUBLE_TAP_SLOP_PX, SWIPE_THRESHOLD_PX, TAP_SLOP_PX, WHEEL_LINE_PX, WHEEL_ZOOM_RATE,
} from "../constants.js";

export const Swipe = Object.freeze({
  LEFT: "left",
  RIGHT: "right",
});

const PINCH_POINTERS = 2;

const noop = () => {};

export class Gestures {
  #pointers = new Map(); // pointerId → {x, y}
  #start = null; // first pointer's down position
  #multi = false; // gesture had 2+ pointers: no tap/swipe
  #lastTap = null; // {x, y, time}
  #tapTimer = null;
  #handlers;

  constructor(el, handlers, signal) {
    this.#handlers = {
      onTap: noop, onDoubleTap: noop, onDrag: noop, onSwipe: noop, onPinch: noop, onWheel: noop,
      ...handlers,
    };

    el.addEventListener("pointerdown", (e) => this.#down(e), { signal });
    el.addEventListener("wheel", (e) => this.#wheel(e), { passive: false, signal });
    window.addEventListener("pointermove", (e) => this.#move(e), { signal });
    window.addEventListener("pointerup", (e) => this.#up(e), { signal });
    window.addEventListener("pointercancel", (e) => this.#cancel(e), { signal });
    signal.addEventListener("abort", () => clearTimeout(this.#tapTimer));
  }

  #down(e) {
    if (!this.#pointers.size) {
      this.#start = { x: e.clientX, y: e.clientY };
      this.#multi = false;
    }

    this.#pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (this.#pointers.size >= PINCH_POINTERS) {
      this.#multi = true;
    }
  }

  // Drag = midpoint delta; pinch = spread ratio between first two pointers.
  #move(e) {
    if (!this.#pointers.has(e.pointerId)) {
      return;
    }

    const before = this.#midpoint();
    const spreadBefore = this.#spread();
    this.#pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const after = this.#midpoint();
    const spreadAfter = this.#spread();

    if (spreadBefore && spreadAfter) {
      this.#handlers.onPinch(spreadAfter / spreadBefore, after.x, after.y);
    }
    this.#handlers.onDrag(after.x - before.x, after.y - before.y);
  }

  #up(e) {
    if (!this.#pointers.delete(e.pointerId)) {
      return;
    }

    // Still pointers down, or a pinch just ended: no tap/swipe.
    if (this.#pointers.size || this.#multi) {
      return;
    }

    const dx = e.clientX - this.#start.x;
    const dy = e.clientY - this.#start.y;

    if (Math.abs(dx) < TAP_SLOP_PX && Math.abs(dy) < TAP_SLOP_PX) {
      this.#tap(e.clientX, e.clientY);
      return;
    }

    if (Math.abs(dx) < SWIPE_THRESHOLD_PX) {
      return;
    }
    this.#handlers.onSwipe(dx < 0 ? Swipe.LEFT : Swipe.RIGHT);
  }

  #cancel(e) {
    this.#pointers.delete(e.pointerId);
    this.#multi = true;
  }

  // 2nd tap soon and near → double tap; else single tap once the window passes.
  #tap(x, y) {
    const now = performance.now();
    const last = this.#lastTap;
    const isDouble = last && now - last.time < DOUBLE_TAP_MS && Math.hypot(x - last.x, y - last.y) < DOUBLE_TAP_SLOP_PX;

    clearTimeout(this.#tapTimer);

    if (isDouble) {
      this.#lastTap = null;
      this.#handlers.onDoubleTap(x, y);
      return;
    }

    this.#lastTap = { x, y, time: now };
    this.#tapTimer = setTimeout(() => {
      this.#lastTap = null;
      this.#handlers.onTap();
    }, DOUBLE_TAP_MS);
  }

  // Exponential: equal wheel steps → equal zoom ratios. Line-mode deltas (Firefox) → px.
  #wheel(e) {
    e.preventDefault();

    const delta = e.deltaMode === WheelEvent.DOM_DELTA_LINE ? e.deltaY * WHEEL_LINE_PX : e.deltaY;
    this.#handlers.onWheel(Math.exp(-delta * WHEEL_ZOOM_RATE), e.clientX, e.clientY);
  }

  #midpoint() {
    const [a, b = a] = this.#pointers.values();
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  #spread() {
    if (this.#pointers.size < PINCH_POINTERS) {
      return 0;
    }

    const [a, b] = this.#pointers.values();
    return Math.hypot(a.x - b.x, a.y - b.y);
  }
}
