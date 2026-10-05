/* Landing view: grid of all albums. */

import { h } from "../dom.js";
import { listAlbums } from "../api.js";
import { RoutePath } from "../constants.js";
import { Route } from "../router.js";
import { albumCard } from "../components/album-card.js";

export async function renderAlbums(app, route, { navigate, signal }) {
  const grid = h("div", { className: "albums-grid" });

  app.appendChild(h("main", { className: "section albums" },
    h("h1", { className: "page-title" }, "Albums"),
    grid,
  ));

  try {
    const albums = await listAlbums();

    // Route changed while loading.
    if (signal.aborted) {
      return;
    }

    if (!albums.length) {
      grid.appendChild(h("p", { className: "empty-state" }, "No albums. Add folders to the source directory."));
      return;
    }

    for (const album of albums) {
      const onOpen = () => navigate(new Route(RoutePath.ALBUM, album.id));
      grid.appendChild(albumCard({ album, onOpen }));
    }
  } catch (err) {
    grid.appendChild(h("div", { className: "error-inline" },
      h("span", {}, `Could not load albums: ${err.message}`),
      h("button", { type: "button", onClick: () => location.reload() }, "Retry"),
    ));
  }
}
