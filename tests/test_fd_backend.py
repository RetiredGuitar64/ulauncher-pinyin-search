import os
import tempfile
import unittest
from pathlib import Path

from pinyin_search.config import SearchConfig
from pinyin_search.fd_backend import FdBackend


class FdBackendTest(unittest.TestCase):
    def test_scan_and_direct_fuzzy_search(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "MyProjectNotes.txt").touch()
            Path(root, "unrelated.txt").touch()
            config = SearchConfig.from_preferences({"search_roots": root})
            backend = FdBackend()
            scanned = backend.scan(config)
            self.assertIn((os.path.join(root, "MyProjectNotes.txt"), False), scanned)
            if backend.available:
                found = backend.direct_search("mpn", config)
                self.assertIn((os.path.join(root, "MyProjectNotes.txt"), False), found)


if __name__ == "__main__":
    unittest.main()
