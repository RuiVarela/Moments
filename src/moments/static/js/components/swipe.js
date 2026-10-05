/* Swipe detector: pointer events → left/right callbacks. */

import { SWIPE_THRESHOLD_PX } from "../constants.js";

export class SwipeDetector {
  constructor(el, { onLeft = null, onRight = null } = {}) {
    this.el = el;
    this.onLeft = onLeft;
    this.onRight = onRight;
    this.#startX = 0;
    this.#bind();
  }

  #startX;

  #bind() {
    this.el.addEventListener("pointerdown", (e) => {
      this.#startX = e.clientX;
    });

    this.el.addEventListener("pointerup", (e) => {
      const dx = e.clientX - this.#startX;
      if (Math.abs(dx) > SWIPE_THRESHOLD_PX) {
        if (dx > 0 && this.onLeft) this.onLeft();
        else if (dx < 0 && this.onRight) this.onRight();
      }
    });
  }
}
