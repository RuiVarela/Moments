/* Bootstrap: route changes → view render.

   hashchange ─► router ─► render(route)
                             ├─ abort previous view (polls, listeners)
                             └─ view(app, route, { navigate, replace, signal })
*/

import { RoutePath } from "./constants.js";
import { clear } from "./dom.js";
import { Route, subscribe, navigate, replace } from "./router.js";
import { renderAlbums } from "./views/albums.js";
import { renderAlbum } from "./views/album.js";
import { renderViewer } from "./views/viewer.js";

const app = document.getElementById("app");

const VIEWS = Object.freeze({
  [RoutePath.LANDING]: renderAlbums,
  [RoutePath.ALBUM]: renderAlbum,
  [RoutePath.VIEWER]: renderViewer,
});

let controller = null;

function render(route) {
  controller?.abort();
  controller = new AbortController();

  clear(app);

  const view = VIEWS[route.path] ?? renderAlbums;
  view(app, route, { navigate, replace, signal: controller.signal });
}

subscribe(render);
render(Route.parse());
