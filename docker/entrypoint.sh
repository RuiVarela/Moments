#!/bin/sh
# Drop root → PUID:PGID so files written to /data match the host user (NAS-friendly).
#
#   docker run -e PUID=1026 -e PGID=100 ...  → app runs as 1026:100
set -eu

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
DATA_DIR="/data"

# Top-level only: new subfolders are created by the app as PUID. No recursive chown (slow on big libraries).
if [ "$(stat -c '%u:%g' "$DATA_DIR")" != "$PUID:$PGID" ]; then
  chown "$PUID:$PGID" "$DATA_DIR"
fi

exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
