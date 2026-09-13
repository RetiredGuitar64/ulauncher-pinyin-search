import os
import tempfile
import unittest

from pinyin_search.config import SearchConfig


class SearchConfigTest(unittest.TestCase):
    def test_parses_and_bounds_preferences(self):
        with tempfile.TemporaryDirectory() as root:
            config = SearchConfig.from_preferences({
                "search_roots": f"{root}\n{root}\n/not/a/real/path",
                "exclude_patterns": ".git\nnode_modules",
                "max_results": "999",
                "min_query_length": "bad",
                "result_type": "invalid",
            })
        self.assertEqual(config.roots, (os.path.realpath(root),))
        self.assertEqual(config.excludes, (".git", "node_modules"))
        self.assertEqual(config.max_results, 30)
        self.assertEqual(config.min_query_length, 2)
        self.assertEqual(config.result_type, "both")

    def test_index_preferences_change_fingerprint(self):
        first = SearchConfig.from_preferences({"search_roots": "/tmp", "include_hidden": "no"})
        second = SearchConfig.from_preferences({"search_roots": "/tmp", "include_hidden": "yes"})
        self.assertNotEqual(first.fingerprint, second.fingerprint)


if __name__ == "__main__":
    unittest.main()
