"""JSON persistence with atomic writes, batch upsert, and checkpoint support."""

from __future__ import annotations

import json
import os
from datetime import datetime


def load_json(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_json(data, path: str):
    """Atomic write: write to temp file then rename to avoid corruption."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


class DataStore:
    """In-memory key-value store backed by a JSON file with batch checkpointing."""

    def __init__(self, path: str, id_key: str = "id"):
        self._path = path
        self._id_key = id_key
        self._pending = 0
        existing = load_json(path)
        self._data = {entry[id_key]: entry for entry in existing}

    @property
    def count(self) -> int:
        return len(self._data)

    def update(self, entries: list[dict]):
        now = datetime.now().isoformat()
        for entry in entries:
            if entry is None:
                continue
            eid = entry[self._id_key]
            if eid in self._data:
                entry["date_added"] = self._data[eid].get("date_added")
            else:
                entry["date_added"] = now
            self._data[eid] = entry
            self._pending += 1

    def flush(self):
        save_json(list(self._data.values()), self._path)
        self._pending = 0

    def auto_flush(self, batch_size: int) -> bool:
        if self._pending >= batch_size:
            self.flush()
            return True
        return False
