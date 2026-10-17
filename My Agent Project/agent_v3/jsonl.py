"""JSON-lines files: append one object per line, read them back, repair a torn tail (sessions spec §4.2).

Lines are written as UTF-8 bytes with a bare `\\n`, so a crash leaves at most one torn last line.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import BinaryIO, Iterator


def append_line(file: BinaryIO, obj, *, fsync: bool = False) -> None:
    """Write `obj` as one JSON line to a binary file opened for appending, then flush (and fsync)."""
    file.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    file.flush()
    if fsync:
        os.fsync(file.fileno())


def read_jsonl(path: str | os.PathLike) -> Iterator[dict]:
    """Yield each line's object in order, skipping blank lines and lines that do not decode (a torn last line)."""
    with Path(path).open("rb") as f:
        for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:                # JSONDecodeError, or a multi-byte character torn in half
                    continue


def repair_tail(path: str | os.PathLike) -> None:
    """Truncate a file after its last `\\n`, so the next append does not join a torn fragment.

    A missing or empty file, or one that already ends with `\\n`, is left alone.
    """
    try:
        f = Path(path).open("r+b")
    except FileNotFoundError:
        return
    with f:
        end = f.seek(0, os.SEEK_END)
        pos = end
        while pos > 0:
            start = max(0, pos - 4096)
            f.seek(start)
            chunk = f.read(pos - start)
            i = chunk.rfind(b"\n")
            if i >= 0:
                cut = start + i + 1
                break
            pos = start
        else:
            cut = 0
        if cut != end:
            f.truncate(cut)
