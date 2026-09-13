from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def _lines(value: object) -> Tuple[str, ...]:
    return tuple(line.strip() for line in str(value or "").splitlines() if line.strip())


@dataclass(frozen=True)
class SearchConfig:
    roots: Tuple[str, ...]
    excludes: Tuple[str, ...]
    include_hidden: bool
    respect_gitignore: bool
    result_type: str
    follow_symlinks: bool
    max_results: int
    min_query_length: int
    refresh_seconds: int
    max_index_entries: int

    @classmethod
    def from_preferences(cls, preferences: Mapping[str, object]) -> "SearchConfig":
        roots = []
        for value in _lines(preferences.get("search_roots", "~")) or ("~",):
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(value)))
            if os.path.isdir(path) and path not in roots:
                roots.append(path)

        result_type = str(preferences.get("result_type", "both"))
        if result_type not in {"both", "files", "folders"}:
            result_type = "both"

        return cls(
            roots=tuple(roots),
            excludes=_lines(preferences.get("exclude_patterns", "")),
            include_hidden=preferences.get("include_hidden", "no") == "yes",
            respect_gitignore=preferences.get("respect_gitignore", "yes") == "yes",
            result_type=result_type,
            follow_symlinks=preferences.get("follow_symlinks", "no") == "yes",
            max_results=_bounded_int(preferences.get("max_results"), 12, 1, 30),
            min_query_length=_bounded_int(preferences.get("min_query_length"), 2, 1, 10),
            refresh_seconds=_bounded_int(preferences.get("refresh_minutes"), 10, 1, 1440) * 60,
            max_index_entries=_bounded_int(
                preferences.get("max_index_entries"), 200_000, 1_000, 2_000_000
            ),
        )

    @property
    def fingerprint(self) -> str:
        payload = {
            "roots": self.roots,
            "excludes": self.excludes,
            "include_hidden": self.include_hidden,
            "respect_gitignore": self.respect_gitignore,
            "result_type": self.result_type,
            "follow_symlinks": self.follow_symlinks,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:20]

    @property
    def cache_path(self) -> Path:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "ulauncher-pinyin-search" / f"index-{self.fingerprint}.sqlite3"
