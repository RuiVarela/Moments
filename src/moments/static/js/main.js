/* Bootstrap: route changes → view render.

   hashchange ─► router ─► render(route)
                             ├─ save scroll of previous route
                             ├─ abort previous view (polls, listeners)
                             ├─ view(app, route, { navigate, replace, signal })
                             └─ view content ready → restore scroll
*/

import { RoutePath } from "./constants.js";
import { clear } from "./dom.js";
import { Route, subscribe, navigate, replace } from "./router.js";
import { saveScroll, restoreScroll } from "./scroll.js";
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
let current = null;

async function render(route) {
  if (current) {
    saveScroll(current, app);
  }
  current = route;

  controller?.abort();
  controller = new AbortController();
  const { signal } = controller;

  clear(app);

  // Views resolve once content is in the DOM; only then is the old height back.
  const view = VIEWS[route.path] ?? renderAlbums;
  await view(app, route, { navigate, replace, signal });

  if (signal.aborted) {
    return;
  }
  restoreScroll(route, app);
}

subscribe(render);
render(Route.parse());
