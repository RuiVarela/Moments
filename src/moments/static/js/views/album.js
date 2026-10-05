/* Album view: grid, toolbar, status banner. */

import { h, clear } from "../dom.js";

export async function renderAlbum(app, route, navigate) {
  clear(app);

  const main = h("main", { className: "section album" },
    h("div", { className: "album-toolbar" },
      h("div", { className: "album-title" }, route.albumId)
    ),
    h("div", { className: "media-grid" })
  );

  app.appendChild(main);
}
