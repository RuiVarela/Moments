/* DOM helpers: h() function and icon utilities. */

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);

  for (const [key, value] of Object.entries(props)) {
    if (key === "className") {
      el.className = value;
    } else if (key === "style") {
      Object.assign(el.style, value);
    } else if (key.startsWith("on")) {
      const eventName = key.slice(2).toLowerCase();
      el.addEventListener(eventName, value);
    } else if (key === "innerHTML") {
      el.innerHTML = value;
    } else if (value !== false && value !== null && value !== undefined) {
      el.setAttribute(key, String(value));
    }
  }

  for (const child of children.flat(Infinity)) {
    if (child != null) {
      el.appendChild(
        typeof child === "string" ? document.createTextNode(child) : child
      );
    }
  }

  return el;
}

export function clear(parent) {
  while (parent.firstChild) {
    parent.removeChild(parent.firstChild);
  }
}

export function icon(name) {
  const icons = {
    play: "▶",
    close: "✕",
    prev: "❮",
    next: "❯",
    menu: "⋯",
    info: "ℹ",
    sort: "⇅",
    extract: "⟳",
    photo: "◫",
    fullscreen: "⛶",
  };
  return icons[name] || "?";
}

// "2024/trip/IMG_01.jpg" → "IMG_01.jpg"
export function fileName(path) {
  return path.split("/").pop();
}

export function duration(seconds) {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}
