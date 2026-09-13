import unittest

from pinyin_search.matcher import Entry, build_postings, rank, score_entry


class MatcherTest(unittest.TestCase):
    def setUp(self):
        self.note = Entry.from_path("/home/test/我的笔记.md", False, "wodebijimd", "wdbj")

    def test_full_pinyin_matches_chinese_name(self):
        self.assertGreater(score_entry("wodebiji", self.note), 0)

    def test_pinyin_initials_match_chinese_name(self):
        self.assertGreater(score_entry("wdbj", self.note), 0)

    def test_english_fuzzy_subsequence(self):
        readme = Entry.from_path("/home/test/MyProjectReadme.md", False)
        self.assertGreater(score_entry("mprm", readme), 0)

    def test_non_match(self):
        self.assertEqual(score_entry("totallydifferent", self.note), -1)

    def test_exact_name_ranks_first(self):
        exact = Entry.from_path("/tmp/report", False)
        longer = Entry.from_path("/tmp/annual-report-backup", False)
        self.assertEqual(rank("report", [longer, exact], 2)[0], exact)

    def test_postings_preserve_results(self):
        entries = [
            self.note,
            Entry.from_path("/tmp/annual-report-backup", False),
            Entry.from_path("/tmp/project-readme", False),
        ]
        self.assertEqual(
            rank("wdbj", entries, 3, build_postings(entries)),
            rank("wdbj", entries, 3),
        )


if __name__ == "__main__":
    unittest.main()
