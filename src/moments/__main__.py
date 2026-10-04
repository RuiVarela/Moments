"""Entry point: load config and run server."""
import sys

import uvicorn

from moments.app import create_app
from moments.config import Config


def main() -> None:
    """Load config and run FastAPI server."""
    try:
        config = Config()
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
