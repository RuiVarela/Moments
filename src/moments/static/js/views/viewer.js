/* Full-screen gallery viewer. */

import { h, clear } from "../dom.js";

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
      h("button", { onClick: () => navigate({ path: "a", albumId: route.albumId }) }, "Close")
    )
  );

  app.appendChild(viewer);
}
