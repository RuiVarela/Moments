/* Sort picker: key dropdown + asc/desc toggle. */

import { h } from "../dom.js";
import { SORT_LABELS, SortOrder } from "../constants.js";

const ORDER_ICONS = Object.freeze({
  [SortOrder.ASC]: "↑",
  [SortOrder.DESC]: "↓",
});

const ORDER_LABELS = Object.freeze({
  [SortOrder.ASC]: "Ascending",
  [SortOrder.DESC]: "Descending",
});

// onChange(sort, order) fires on any change.
export function sortPicker({ sort, order, onChange }) {
  let current = { sort, order };

  const options = Object.entries(SORT_LABELS).map(([key, label]) =>
    h("option", { value: key, selected: key === sort }, label),
  );

  const select = h("select", { "aria-label": "Sort by" }, options);
  const toggle = h("button", { type: "button", className: "sort-order-toggle" });

  // Reflect current order on toggle button.
  const paint = () => {
    toggle.textContent = ORDER_ICONS[current.order];
    toggle.setAttribute("aria-label", ORDER_LABELS[current.order]);
    toggle.title = ORDER_LABELS[current.order];
  };

  select.addEventListener("change", () => {
    current = { ...current, sort: select.value };
    onChange(current.sort, current.order);
  });

  toggle.addEventListener("click", () => {
    const next = current.order === SortOrder.ASC ? SortOrder.DESC : SortOrder.ASC;
    current = { ...current, order: next };
    paint();
    onChange(current.sort, current.order);
  });

  paint();
  return h("div", { className: "sort-picker" }, h("span", { className: "select" }, select), toggle);
}
