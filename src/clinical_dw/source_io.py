"""Small CSV helpers shared by plain and gzip-compressed source adapters."""

import gzip
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO


@contextmanager
def open_source_text(path: Path) -> Iterator[TextIO]:
    """Open a UTF-8 CSV source whether it is plain text or gzip-compressed."""
    if path.suffix == ".gz":
        with gzip.open(path, mode="rt", newline="", encoding="utf-8-sig") as stream:
            yield stream
    else:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            yield stream
