/* Landing page view: album grid. */

import { h, clear, icon } from "../dom.js";
import { listAlbums } from "../api.js";
import { Route } from "../router.js";

export async function renderAlbums(app, route, navigate) {
  clear(app);

  const main = h("main", { className: "section albums" });
  const grid = h("div", { className: "albums-grid" });

  try {
    const albums = await listAlbums();

    for (const album of albums) {
      const card = h(
        "div",
        { className: "album-card", onClick: () => navigate(new Route("a", album.id)) },
        h("div", { className: "album-cover" },
          album.cover
            ? h("img", { src: album.cover, alt: album.id })
            : h("div", { className: "album-cover-placeholder" }, icon("extract"))
        ),
        h("div", { className: "album-info" },
          h("div", { className: "album-name" }, album.id),
          h("div", { className: "album-meta" }, `${album.count} items`),
          album.status === "running" ? h("div", { className: "album-badge" }, "Extracting…") : null
        )
      );
      grid.appendChild(card);
    }
  } catch (err) {
    grid.appendChild(h("div", { className: "error-inline" },
      err.message,
      h("button", { onClick: () => location.reload() }, "Retry")
    ));
  }

  main.appendChild(grid);
  app.appendChild(main);
}
