/* Full-screen gallery viewer. */

import { h, clear } from "../dom.js";
import { RoutePath } from "../constants.js";
import { Route } from "../router.js";

export async function renderViewer(app, route, navigate) {
  clear(app);

  const viewer = h("div", { className: "viewer" },
    h("div", { className: "viewer-container" },
      h("img", { className: "viewer-media", alt: "viewing" })
    ),
    h("div", { className: "viewer-toolbar" },
      h("div", { className: "viewer-nav" },
        h("button", { onClick: () => { } }, "← Prev"),
        h("button", { onClick: () => { } }, "Next →")
      ),
      h("button", { onClick: () => navigate(new Route(RoutePath.ALBUM, route.albumId)) }, "Close")
    )
  );

  app.appendChild(viewer);
}
