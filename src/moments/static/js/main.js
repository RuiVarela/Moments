/* Bootstrap: initialize router and views. */

import { Route, subscribe, navigate } from "./router.js";
import { renderAlbums } from "./views/albums.js";
import { renderAlbum } from "./views/album.js";
import { renderViewer } from "./views/viewer.js";

const app = document.getElementById("app");

function render(route) {
  while (app.firstChild) app.removeChild(app.firstChild);

  if (route.path === "") renderAlbums(app, route, navigate);
  else if (route.path === "a") renderAlbum(app, route, navigate);
  else if (route.path === "m") renderViewer(app, route, navigate);
}

subscribe(render);
render(Route.parse());
