import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pinyin_search.config import SearchConfig
from pinyin_search.index import FileIndex
from pinyin_search.matcher import rank


class FakeBackend:
    def __init__(self, paths):
        self.paths = paths

    def scan(self, _config):
        return self.paths


class FileIndexTest(unittest.TestCase):
    def test_builds_pinyin_index_and_reloads_cache(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as cache:
            path = os.path.join(root, "我的笔记.md")
            Path(path).touch()
            with patch.dict(os.environ, {"XDG_CACHE_HOME": cache}):
                config = SearchConfig.from_preferences({"search_roots": root})
                index = FileIndex(backend=FakeBackend([(path, False)]))
                index.ensure(config)
                deadline = time.monotonic() + 3
                while index.status()[0] and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertEqual(index.search("wodebiji", 5)[0].path, path)

                cached = FileIndex(backend=FakeBackend([(path, False)]))
                cached.ensure(config)
                deadline = time.monotonic() + 3
                while cached.status()[0] and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertEqual(cached.search("wdbj", 5)[0].path, path)


if __name__ == "__main__":
    unittest.main()
