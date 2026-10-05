/* Options menu: "⋯" button → dropdown of actions + status line.

   actions: [{ label, onSelect }]
   signal:  removes document listener when view unmounts.
   Returns { el, setStatus(text) }.
*/

import { h, icon } from "../dom.js";

export function optionsMenu({ actions, signal }) {
  const status = h("p", { className: "options-status" });
  const items = actions.map(({ label, onSelect }) =>
    h("button", { type: "button", role: "menuitem", onClick: () => { close(); onSelect(); } }, label),
  );

  const dropdown = h("div", { className: "options-dropdown", role: "menu", hidden: true }, items, status);
  const trigger = h("button", {
    type: "button",
    className: "options-trigger",
    "aria-label": "Album options",
    "aria-haspopup": "menu",
    "aria-expanded": "false",
    onClick: () => toggle(),
  }, icon("menu"));

  const el = h("div", { className: "options-menu" }, trigger, dropdown);

  function toggle() {
    if (dropdown.hidden) {
      open();
      return;
    }
    close();
  }

  function open() {
    dropdown.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
  }

  function close() {
    dropdown.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  // Click outside closes.
  document.addEventListener("click", (e) => {
    if (!el.contains(e.target)) {
      close();
    }
  }, { signal });

  return {
    el,
    setStatus(text) {
      status.textContent = text;
    },
  };
}
