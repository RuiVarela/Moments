# Frontend Implementation

Vanilla JavaScript (no build step, no framework). ES modules, CSS Grid, responsive, light/dark theme.

## Project Structure

```
src/moments/static/
├── index.html                       # Shell: <div id="app">, load /js/main.js
├── favicon.svg                      # Source icon (sunset + mountains); edit this one
├── favicon.ico                      # 16/32/48 PNGs rendered from favicon.svg
├── apple-touch-icon.png             # 180px, rendered from favicon.svg
├── css/
│   ├── tokens.css                   # Design tokens (CSS vars, light/dark)
│   ├── base.css                     # Reset, inputs, common styles
│   ├── albums.css                   # Landing page grid
│   ├── album.css                    # Album view (toolbar, grid, status)
│   └── viewer.css                   # Full-screen gallery
├── js/
│   ├── main.js                      # Bootstrap: wire router → views
│   ├── api.js                       # ONLY place that calls fetch
│   ├── router.js                    # Hash-based routing (# URLs)
│   ├── constants.js                 # Frozen enums (SortKey, Status, etc.)
│   ├── poll.js                      # Poll helper (polling with cancellation)
│   ├── prefs.js                     # localStorage: sort/order persistence
│   ├── dates.js                     # groupByMonth(): month headers for date sort
│   ├── dom.js                       # h() builder, icon helpers, duration()
│   ├── components/
│   │   ├── swipe.js                 # Pointer swipe detector (left/right callbacks)
│   │   ├── album-card.js            # (TODO) Album card for landing
│   │   ├── media-tile.js            # (TODO) Media tile + video badge
│   │   ├── sort-picker.js           # (TODO) Dropdown + order toggle
│   │   ├── options-menu.js          # (TODO) Re-extract menu
│   │   ├── status-banner.js         # (TODO) Extraction progress banner
│   │   └── month-divider.js         # Full-width "March 2006" grid header
│   └── views/
│       ├── albums.js                # Landing page (album grid)
│       ├── album.js                 # Album detail (media grid + toolbar)
│       └── viewer.js                # Full-screen gallery (viewer)
```

## Architecture & Layering (per AGENTS.md)

**Strict hierarchy**: views → components → { api, router, prefs }

- **Views** (`views/*.js`): render function(app, route, navigate); handle route state.
- **Components** (`components/*.js`): pure render functions or classes; never fetch; accept data + callbacks.
- **API** (`api.js`): ONLY place that calls `fetch()`. Throws `ApiError` on 4xx/5xx.
- **Router** (`router.js`): parse/build routes, notify subscribers on hash change.
- **Prefs** (`prefs.js`): localStorage read/write (try/catch wrapped).

Components cannot call api.js directly; views orchestrate.

## Routing

Hash-based (no server fallback needed; works from any `#` URL):

| Route | View | Purpose |
|-------|------|---------|
| `#/` | albums | Landing page: album grid |
| `#/a/<albumId>` | album | Album detail: media grid, sort, options |
| `#/a/<albumId>/m/<mediaHash>` | viewer | Full-screen gallery |

- **Open viewer** from album: `navigate()` (push state, adds to history).
- **Next/prev** in viewer: `replace()` (no history spam).
- **Close viewer**: navigate back to album route.

## Styling

### Design Tokens (css/tokens.css)

CSS variables with light/dark theme:

```css
:root {
  --color-bg, --color-fg, --color-border, --color-accent, --color-error, ...
  --space-1 to --space-8, --radius-sm/md/lg, --font-sm to --font-2xl, --z-*
}

@media (prefers-color-scheme: dark) { :root { /* override */ } }
```

Respects `prefers-reduced-motion: reduce` (no transitions/animations).

### Layout

- `#app`: flex column, height 100%.
- `main.section`: flex 1, overflow-y auto.
- `albums-grid`: CSS Grid, auto-fill columns.
- `media-grid`: CSS Grid, lazy `<img loading="lazy">`.
- `viewer`: fixed overlay (touch-action: pan-y for swipe).

## Views

### Landing (`views/albums.js`)

```js
export async function renderAlbums(app, route, navigate) { ... }
```

- Fetch `listAlbums()`.
- Grid of album cards (cover thumb or placeholder, name, count, "Extracting…" badge if running).
- Click card → `navigate(new Route("a", albumId))` → album view.
- Error: show inline error + retry button.

### Album (`views/album.js`)

```js
export async function renderAlbum(app, route, navigate) { ... }
```

- Load prefs (sort, order).
- Fetch `getAlbum(albumId, sort, order)`.
- If `status.status === "running"`: show status banner, poll every 1s, reload on idle, show error + retry on failed.
- Sorted by date → grid split by month: header ("March 2006") before each month, "Undated" last. Sorted by name → no headers.
- Grid of media tiles:
  - Images: lazy-load thumbs; click → open viewer.
  - Videos: thumb + play badge + duration overlay.
- Toolbar:
  - Title: album ID.
  - Sort picker: dropdown (date/name) + order toggle (↑/↓), save to prefs.
  - Options button → menu: "Re-extract" (POST, then poll status), current status text.

### Viewer (`views/viewer.js`)

```js
export async function renderViewer(app, route, navigate) { ... }
```

- Receive media list from album view state (passed via route or component state TODO).
- Display current media:
  - **Image**: `<img src="/api/albums/{id}/media/{hash}/original">` (except HEIC → preview).
  - **Video**: `<video controls autoplay playsinline poster="/api/albums/{id}/media/{hash}/preview">`.
- Navigation:
  - **Keyboard**: ← → (prev/next), Esc (close), i (toggle info).
  - **Swipe**: left (prev), right (next) via `SwipeDetector`.
  - **Buttons**: prev/next/close.
- Preload neighbors (±1 media item).
- **Info overlay** (toggle via `i` key or button):
  - Date (EXIF/creation date, else from file name; "—" if none).
  - Dimensions (WxH).
  - GPS: "🗺 [lat, lon]" as OSM link (no map lib).
  - Video: duration.
- **Pause video** when navigating to next/prev.

## Components (TODO)

- **album-card.js**: render album card (cover, name, count, badge).
- **media-tile.js**: render media tile (thumb, play badge + duration for video).
- **sort-picker.js**: dropdown + toggle button for sort order.
- **options-menu.js**: dropdown menu (Re-extract, status text).
- **status-banner.js**: extraction progress banner (done/total, error message, retry button).

All accept props + callbacks; no fetching.

## Utilities

### API (`api.js`)

```js
export async function listAlbums()                           // → []
export async function getAlbum(id, sort, order)             // → {id, count, items, status, cover}
export async function startExtract(id)                       // → {status: "started"}
export async function getExtractStatus(id)                  // → {status, done, total, error}
export function mediaUrl(albumId, hash, kind)               // → "/api/albums/.../media/.../thumb|preview|original"

export class ApiError extends Error {
  constructor(message, status)
}
```

Throws `ApiError` on network fail or 4xx/5xx response.

### Router (`router.js`)

```js
export class Route {
  constructor(path, albumId, mediaHash)
  static parse()                        // Parse current hash
  toString()                            // → "#/" | "#/a/id" | "#/a/id/m/hash"
}

export function subscribe(fn)            // Subscribe to route changes
export function navigate(route)          // Push new route (add to history)
export function replace(route)           // Replace current route (no history)
```

### DOM (`dom.js`)

```js
export function h(tag, props, ...children)  // h("div", {className, onClick}, "text", el)
export function clear(parent)               // Remove all children
export function icon(name)                  // → "▶" | "✕" | etc.
export function duration(seconds)           // → "1:23" | "0:45"
```

### Constants (`constants.js`)

Frozen enums:

```js
RoutePath.LANDING, RoutePath.ALBUM, RoutePath.VIEWER  // path values
SortKey.DATE, SortKey.NAME                      // sort options
SortOrder.ASC, SortOrder.DESC                   // order direction
Status.IDLE, Status.RUNNING, Status.FAILED      // extraction states
MediaType.IMAGE, MediaType.VIDEO                // media type
MediaKind.THUMB, MediaKind.PREVIEW, MediaKind.ORIGINAL
```

Plus:
- `POLL_INTERVAL_MS`: extraction status poll interval (1000 ms).
- `SWIPE_THRESHOLD_PX`: min swipe distance (50 px).
- `KEY_NAMES`: { ARROW_LEFT, ARROW_RIGHT, ESCAPE, I }.
- `HEIC_EXTS`: file extensions that need preview fallback.

### Swipe (`components/swipe.js`)

```js
export class SwipeDetector {
  constructor(el, {onLeft, onRight})   // Bind to element; callback on swipe
}
```

Uses pointer events; calls `onLeft()` on right swipe, `onRight()` on left swipe (threshold 50px).

### Prefs (`prefs.js`)

```js
export function getSort() / setSort(sort)
export function getOrder() / setOrder(order)
```

Read/write to localStorage with try/catch (silent fail if unavailable).

### Poll (`poll.js`)

```js
export async function poll(fn, until, intervalMs, signal)
// Repeatedly call fn() every intervalMs until until(result) is true
// signal?.abort() cancels polling
```

## Conventions (per AGENTS.md)

- **Constants**: all strings/numbers extracted to enums/objects in constants.js.
- **Early returns**: avoid nested ifs.
- **Functions < 30 chars**: `renderAlbums`, `startExtract`, `getPrevItem`, not `renderTheAlbumsLandingPageView`.
- **Always braces**: `if (x) { y(); }`, never bare if.
- **Comments**: one-line what/why, e.g. `// Poll status every 1s until extraction idle or fails.`
- **Private fields**: `#privateField` in ES classes.
- **Blank lines**: between logical blocks.

## Security

- **No auth**: app is trusted-network-only (per spec).
- **Path validation**: `/original`, `/thumb`, `/preview` URLs validated server-side only; frontend just passes hash + kind.
- **XSS prevention**: never use `innerHTML` except for static icon helpers; DOM via `h()`.
- **CSRF**: N/A (read-only GET, POST form action local only).

## Accessibility

- Buttons have `aria-label` where icon-only.
- Focus management in viewer (trap focus if modal-like).
- Keyboard nav: arrows, Esc, `i` all supported.
- Color contrast: tokens ensure sufficient contrast in both themes.
- `prefers-reduced-motion`: no transitions/animations.
- Semantic HTML: `<main>`, `<button>`, `<img alt="">`, `<video>`.

## Performance

- **Lazy loading**: `<img loading="lazy">` for media tiles.
- **Preload neighbors**: next/prev media in viewer (prefetch image).
- **Minimal repaint**: replace DOM nodes only on route change, not on every update.
- **No polling during idle**: stop `poll()` once extraction complete.
- **LocalStorage for prefs**: no unnecessary fetches on reload.

## Testing

`tests/test_frontend.py` (pytest, skipped without Node): `node --check` on every module; `Route.parse()`/`toString()` with stubbed browser globals.

### Manual

1. Landing page loads; albums grid renders.
2. Click album → album view loads, shows toolbar (sort picker, options button).
3. If extraction pending: status banner appears, polls until idle, reloads grid.
4. Click media tile → viewer opens, image/video displays.
5. Keyboard: ← → navigate; Esc close; i toggle info.
6. Swipe (mobile emulation): left/right navigate.
7. Options button → Re-extract starts, status updates.
8. Sort changes order; reload page → sort order persists (localStorage).
9. Dark/light mode: toggle OS setting → theme changes immediately (CSS var).
10. Deep link `#/a/x/m/<hash>` → viewer opens directly.
