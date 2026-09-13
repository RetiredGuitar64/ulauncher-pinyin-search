from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .config import SearchConfig
from .fd_backend import FdBackend
from .matcher import Entry, build_postings, rank
from .transliterate import Transliterator


logger = logging.getLogger(__name__)


class FileIndex:
    def __init__(self, backend: Optional[FdBackend] = None, transliterator: Optional[Transliterator] = None) -> None:
        self.backend = backend or FdBackend()
        self.transliterator = transliterator or Transliterator()
        self._lock = threading.Lock()
        self._entries: Tuple[Entry, ...] = ()
        self._postings: Mapping[str, Sequence[int]] = {}
        self._fingerprint = ""
        self._generation = 0
        self._last_refresh = 0.0
        self._building = False
        self._error = ""

    def ensure(self, config: SearchConfig) -> None:
        now = time.monotonic()
        with self._lock:
            changed = config.fingerprint != self._fingerprint
            stale = now - self._last_refresh >= config.refresh_seconds
            if self._building and not changed:
                return
            if not changed and not stale:
                return
            if changed:
                self._fingerprint = config.fingerprint
                self._entries = ()
                self._postings = {}
                self._last_refresh = now
            self._generation += 1
            generation = self._generation
            self._building = True
            self._error = ""
        thread = threading.Thread(target=self._refresh, args=(config, generation), daemon=True, name="pinyin-file-index")
        thread.start()

    def snapshot(self) -> Tuple[Entry, ...]:
        with self._lock:
            return self._entries

    def search(self, query: str, limit: int) -> List[Entry]:
        with self._lock:
            entries = self._entries
            postings = self._postings
        return rank(query, entries, limit, postings)

    def status(self) -> Tuple[bool, int, str, str]:
        with self._lock:
            return self._building, len(self._entries), self._error, self.transliterator.backend

    def _refresh(self, config: SearchConfig, generation: int) -> None:
        try:
            cached, by_path, by_name = self._load_cache(config.cache_path)
            self._publish_if_current(generation, cached, building=True)
            discovered = self.backend.scan(config)
            if not discovered and cached:
                self._finish_if_current(generation, "File scan failed; using the previous cache")
                return

            missing_names = {
                Path(path).name
                for path, _ in discovered
                if path not in by_path and Path(path).name not in by_name
            }
            converted = self.transliterator.romanize_many(missing_names)
            entries: List[Entry] = []
            for path, is_dir in discovered:
                name = Path(path).name or path
                forms = by_path.get(path) or by_name.get(name) or converted.get(name, ("", ""))
                entries.append(Entry.from_path(path, is_dir, *forms))
            self._save_cache(config.cache_path, entries)
            self._publish_if_current(generation, entries, building=False)
            logger.info("Indexed %d paths using %s", len(entries), self.transliterator.backend)
        except Exception as exc:  # Keep the extension alive when an unusual path/cache fails.
            logger.exception("Could not refresh file index")
            self._finish_if_current(generation, str(exc))

    def _publish_if_current(self, generation: int, entries: List[Entry], building: bool) -> None:
        entries_tuple = tuple(entries)
        postings = build_postings(entries_tuple)
        with self._lock:
            if generation != self._generation:
                return
            self._entries = entries_tuple
            self._postings = postings
            self._building = building
            if not building:
                self._last_refresh = time.monotonic()

    def _finish_if_current(self, generation: int, error: str) -> None:
        with self._lock:
            if generation == self._generation:
                self._building = False
                self._last_refresh = time.monotonic()
                self._error = error

    def _connect(self, path: Path) -> sqlite3.Connection:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "path TEXT PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL, "
            "normalized_path TEXT NOT NULL, pinyin TEXT NOT NULL, initials TEXT NOT NULL, "
            "is_dir INTEGER NOT NULL)"
        )
        return connection

    def _load_cache(self, path: Path) -> Tuple[List[Entry], Dict[str, Tuple[str, str]], Dict[str, Tuple[str, str]]]:
        if not path.exists():
            return [], {}, {}
        connection = self._connect(path)
        try:
            rows = connection.execute(
                "SELECT path, name, normalized_name, normalized_path, pinyin, initials, is_dir FROM entries"
            ).fetchall()
        finally:
            connection.close()
        entries = [Entry(*row[:-1], bool(row[-1])) for row in rows]
        by_path = {entry.path: (entry.pinyin, entry.initials) for entry in entries}
        by_name = {entry.name: (entry.pinyin, entry.initials) for entry in entries}
        return entries, by_path, by_name

    def _save_cache(self, path: Path, entries: List[Entry]) -> None:
        connection = self._connect(path)
        try:
            connection.execute("DELETE FROM entries")
            connection.executemany(
                "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)",
                ((e.path, e.name, e.normalized_name, e.normalized_path, e.pinyin, e.initials, int(e.is_dir)) for e in entries),
            )
            connection.commit()
        finally:
            connection.close()
