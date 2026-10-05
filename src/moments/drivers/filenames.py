"""Filename parsing: capture date encoded in file names."""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# "2006-03-03_00001.jpg" or "2006-03-03.jpg" → 2006-03-03.
_DATE_NAME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:_.*)?$")


def date_from_name(name: str) -> Optional[int]:
    """Unix timestamp (local midnight) of date in file name, or None."""
    match = _DATE_NAME.match(Path(name).stem)
    if not match:
        return None

    year, month, day = (int(part) for part in match.groups())

    try:
        return int(datetime(year, month, day).timestamp())
    except ValueError:
        return None
