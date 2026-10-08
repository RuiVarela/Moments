/* ZoomPan: zoom/pan state of one element centered in a viewport.

   scale 1 = fit (content as laid out; images: object-fit contain). Offset (x, y) = translate from centered.
   Zooming keeps the point under the cursor/fingers fixed:

     q = point relative to viewport center
     offset' = q - (q - offset) * scale' / scale

   Offset is clamped so zoomed content never leaves a gap at an edge it overflows:

     ┌─ viewport ─┐
   ┌─┼────────────┼─┐  max |x| = (width * scale - viewport width) / 2
   │ │  content   │ │  (0 when content is narrower than viewport → stays centered)
   └─┼────────────┼─┘
     └────────────┘
*/

import { MAX_ZOOM } from "../constants.js";

const Motion = Object.freeze({
  INSTANT: "instant",
  ANIMATE: "animate",
});

const FIT_SCALE = 1;
const ZOOM_EPSILON = 0.001;
const ANIMATE_CLASS = "zoom-animate";

export class ZoomPan {
  #el;
  #viewport;
  #scale = FIT_SCALE;
  #x = 0;
  #y = 0;

  constructor(el, viewport) {
    this.#el = el;
    this.#viewport = viewport;
  }

  get zoomed() {
    return this.#scale > FIT_SCALE + ZOOM_EPSILON;
  }

  zoomBy(ratio, clientX, clientY) {
    this.#zoomTo(this.#scale * ratio, clientX, clientY, Motion.INSTANT);
  }

  panBy(dx, dy) {
    this.#x += dx;
    this.#y += dy;
    this.#apply(Motion.INSTANT);
  }

  // Double tap: fit ↔ fill (image covers viewport), toward the tapped point.
  toggleFill(clientX, clientY) {
    if (this.zoomed) {
      this.#zoomTo(FIT_SCALE, clientX, clientY, Motion.ANIMATE);
      return;
    }
    this.#zoomTo(this.#fillScale(), clientX, clientY, Motion.ANIMATE);
  }

  #zoomTo(target, clientX, clientY, motion) {
    // Not laid out yet (image still loading).
    const content = this.#contentSize();
    if (!content.width || !content.height) {
      return;
    }

    const scale = Math.min(Math.max(target, FIT_SCALE), this.#maxScale());
    const rect = this.#viewport.getBoundingClientRect();
    const qx = clientX - (rect.left + rect.width / 2);
    const qy = clientY - (rect.top + rect.height / 2);
    const k = scale / this.#scale;

    this.#x = qx - (qx - this.#x) * k;
    this.#y = qy - (qy - this.#y) * k;
    this.#scale = scale;
    this.#apply(motion);
  }

  #apply(motion) {
    const rect = this.#viewport.getBoundingClientRect();
    const content = this.#contentSize();
    const maxX = Math.max(0, (content.width * this.#scale - rect.width) / 2);
    const maxY = Math.max(0, (content.height * this.#scale - rect.height) / 2);

    this.#x = Math.min(Math.max(this.#x, -maxX), maxX);
    this.#y = Math.min(Math.max(this.#y, -maxY), maxY);

    this.#el.classList.toggle(ANIMATE_CLASS, motion === Motion.ANIMATE);
    this.#el.style.transform = `translate(${this.#x}px, ${this.#y}px) scale(${this.#scale})`;
  }

  #fillScale() {
    const rect = this.#viewport.getBoundingClientRect();
    const content = this.#contentSize();
    return Math.max(rect.width / content.width, rect.height / content.height);
  }

  // Visible picture size at fit. Image box may be larger (letterbox from object-fit: contain).
  #contentSize() {
    const box = { width: this.#el.offsetWidth, height: this.#el.offsetHeight };
    const { naturalWidth, naturalHeight } = this.#el;
    if (!naturalWidth || !naturalHeight) {
      return box;
    }

    const k = Math.min(box.width / naturalWidth, box.height / naturalHeight);
    return { width: naturalWidth * k, height: naturalHeight * k };
  }

  // Extreme panoramas may need more than MAX_ZOOM to fill.
  #maxScale() {
    return Math.max(MAX_ZOOM, this.#fillScale());
  }
}
