import unittest

from pinyin_search.transliterate import Transliterator, contains_han


class TransliteratorTest(unittest.TestCase):
    def test_detects_han(self):
        self.assertTrue(contains_han("我的笔记.md"))
        self.assertFalse(contains_han("notes.md"))

    def test_full_pinyin_and_initials(self):
        forms = Transliterator().romanize_many(["我的笔记"])["我的笔记"]
        self.assertEqual(forms, ("wodebiji", "wdbj"))

    def test_deduplicates_input(self):
        forms = Transliterator().romanize_many(["中文", "中文"])
        self.assertEqual(list(forms), ["中文"])


if __name__ == "__main__":
    unittest.main()
