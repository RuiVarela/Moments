/* Swipe detector: horizontal pointer drag → callback.

   finger ◄──── (dx < 0) → onSwipeLeft   (e.g. next)
   finger ────► (dx > 0) → onSwipeRight  (e.g. prev)
   finger •     (no move) → onTap         (optional)
*/

import { SWIPE_THRESHOLD_PX, TAP_SLOP_PX } from "../constants.js";

export class SwipeDetector {
  #startX = null;
  #startY = null;
  #onSwipeLeft;
  #onSwipeRight;
  #onTap;

  constructor(el, { onSwipeLeft, onSwipeRight, onTap = () => {} }) {
    this.#onSwipeLeft = onSwipeLeft;
    this.#onSwipeRight = onSwipeRight;
    this.#onTap = onTap;

    el.addEventListener("pointerdown", (e) => this.#start(e));
    el.addEventListener("pointerup", (e) => this.#end(e));
    el.addEventListener("pointercancel", () => this.#reset());
  }

  #start(e) {
    if (!e.isPrimary) {
      return;
    }
    this.#startX = e.clientX;
    this.#startY = e.clientY;
  }

  #end(e) {
    if (this.#startX === null) {
      return;
    }

    const dx = e.clientX - this.#startX;
    const dy = e.clientY - this.#startY;
    this.#reset();

    // Barely moved: tap, not swipe.
    if (Math.abs(dx) < TAP_SLOP_PX && Math.abs(dy) < TAP_SLOP_PX) {
      this.#onTap();
      return;
    }

    if (Math.abs(dx) < SWIPE_THRESHOLD_PX) {
      return;
    }

    if (dx < 0) {
      this.#onSwipeLeft();
      return;
    }
    this.#onSwipeRight();
  }

  #reset() {
    this.#startX = null;
    this.#startY = null;
  }
}
