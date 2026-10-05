/* Swipe detector: horizontal pointer drag → callback.

   finger ◄──── (dx < 0) → onSwipeLeft   (e.g. next)
   finger ────► (dx > 0) → onSwipeRight  (e.g. prev)
*/

import { SWIPE_THRESHOLD_PX } from "../constants.js";

export class SwipeDetector {
  #startX = null;
  #onSwipeLeft;
  #onSwipeRight;

  constructor(el, { onSwipeLeft, onSwipeRight }) {
    this.#onSwipeLeft = onSwipeLeft;
    this.#onSwipeRight = onSwipeRight;

    el.addEventListener("pointerdown", (e) => this.#start(e));
    el.addEventListener("pointerup", (e) => this.#end(e));
    el.addEventListener("pointercancel", () => this.#reset());
  }

  #start(e) {
    if (!e.isPrimary) {
      return;
    }
    this.#startX = e.clientX;
  }

  #end(e) {
    if (this.#startX === null) {
      return;
    }

    const dx = e.clientX - this.#startX;
    this.#reset();

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
  }
}
