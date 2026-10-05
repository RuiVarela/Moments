/* Bootstrap: initialize router and views. */

import { RoutePath } from "./constants.js";
import { Route, subscribe, navigate } from "./router.js";
import { renderAlbums } from "./views/albums.js";
import { renderAlbum } from "./views/album.js";
import { renderViewer } from "./views/viewer.js";

const app = document.getElementById("app");

function render(route) {
  while (app.firstChild) app.removeChild(app.firstChild);

  if (route.path === RoutePath.ALBUM) {
    renderAlbum(app, route, navigate);
    return;
  }

  if (route.path === RoutePath.VIEWER) {
    renderViewer(app, route, navigate);
    return;
  }

  renderAlbums(app, route, navigate);
}

subscribe(render);
render(Route.parse());
