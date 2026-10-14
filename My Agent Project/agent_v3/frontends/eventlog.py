"""Event log (plan §10.4): every event's `to_dict()` as one JSON line. Benchmark data source and UI replay input."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Iterator


class EventLogWriter:
    """Append-only JSONL sink. Thread-safe; flushes every line so a crash loses nothing."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, event) -> None:
        line = json.dumps(event if isinstance(event, dict) else event.to_dict(), ensure_ascii=False)
        with self._lock:
            if self._file.closed:
                return
            self._file.write(line + "\n")
            self._file.flush()

    __call__ = write

    def close(self) -> None:
        with self._lock:
            self._file.close()


def read_events(path: str | Path) -> Iterator[dict]:
    """Replay a log: yields each event dict in order, skipping a torn last line."""
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
