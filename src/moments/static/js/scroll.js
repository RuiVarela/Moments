/* Scroll memory: per-route scroll of the view's section, restored once it has content.

   album (top=1200) ─open─► viewer ─close─► album (top=1200)
*/

// Views scroll inside <main class="section">, not the window.
const SCROLLER = ".section";

const positions = new Map();

export function saveScroll(route, root) {
  const el = root.querySelector(SCROLLER);
  if (!el) {
    return;
  }
  positions.set(route.toString(), el.scrollTop);
}

export function restoreScroll(route, root) {
  const el = root.querySelector(SCROLLER);
  const top = positions.get(route.toString());
  if (!el || top === undefined) {
    return;
  }
  el.scrollTop = top;
}
