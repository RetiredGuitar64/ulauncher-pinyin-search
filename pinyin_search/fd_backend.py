from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Iterator, List, Optional, Tuple

from .config import SearchConfig


class FdBackend:
    def __init__(self) -> None:
        self.executable = shutil.which("fd") or shutil.which("fdfind")

    @property
    def available(self) -> bool:
        return self.executable is not None

    def _options(self, config: SearchConfig) -> List[str]:
        options = ["--absolute-path", "--print0", "--color", "never", "--ignore-case"]
        if config.include_hidden:
            options.append("--hidden")
        if not config.respect_gitignore:
            options.append("--no-ignore")
        if config.follow_symlinks:
            options.append("--follow")
        if config.result_type in {"both", "files"}:
            options.extend(["--type", "file"])
        if config.result_type in {"both", "folders"}:
            options.extend(["--type", "directory"])
        for pattern in config.excludes:
            options.extend(["--exclude", pattern])
        return options

    def _decode(self, output: bytes) -> Iterator[str]:
        for raw in output.split(b"\0"):
            if not raw:
                continue
            try:
                path = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if os.path.exists(path):
                yield os.path.normpath(path)

    def scan(self, config: SearchConfig) -> List[Tuple[str, bool]]:
        if not config.roots:
            return []
        if not self.executable:
            return self._walk(config)

        command = [self.executable, *self._options(config), "--max-results", str(config.max_index_entries), ".", *config.roots]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        return [(path, os.path.isdir(path)) for path in self._decode(result.stdout)]

    def direct_search(self, query: str, config: SearchConfig, limit: int = 200) -> List[Tuple[str, bool]]:
        if not self.executable or not config.roots:
            return []
        characters = [re.escape(char) for char in query.strip() if not char.isspace()]
        if not characters:
            return []
        pattern = ".*?".join(characters)
        command = [self.executable, *self._options(config), "--max-results", str(limit), pattern, *config.roots]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=0.75,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        return [(path, os.path.isdir(path)) for path in self._decode(result.stdout)]

    def _walk(self, config: SearchConfig) -> List[Tuple[str, bool]]:
        results: List[Tuple[str, bool]] = []
        excluded = set(config.excludes)
        for root in config.roots:
            for current, directories, files in os.walk(root, followlinks=config.follow_symlinks):
                directories[:] = [
                    name for name in directories
                    if name not in excluded and (config.include_hidden or not name.startswith("."))
                ]
                names = []
                if config.result_type in {"both", "folders"}:
                    names.extend((name, True) for name in directories)
                if config.result_type in {"both", "files"}:
                    names.extend(
                        (name, False) for name in files
                        if name not in excluded and (config.include_hidden or not name.startswith("."))
                    )
                for name, is_dir in names:
                    results.append((os.path.join(current, name), is_dir))
                    if len(results) >= config.max_index_entries:
                        return results
        return results
