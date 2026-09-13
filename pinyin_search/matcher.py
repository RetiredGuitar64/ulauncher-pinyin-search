from __future__ import annotations

import heapq
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def normalize(value: str) -> str:
    return _NON_WORD.sub("", unicodedata.normalize("NFKC", value).casefold())


@dataclass(frozen=True)
class Entry:
    path: str
    name: str
    normalized_name: str
    normalized_path: str
    pinyin: str
    initials: str
    is_dir: bool

    @classmethod
    def from_path(cls, path: str, is_dir: bool, pinyin: str = "", initials: str = "") -> "Entry":
        name = os.path.basename(path) or path
        return cls(path, name, normalize(name), normalize(path), pinyin, initials, is_dir)


def _subsequence_score(query: str, target: str) -> int:
    if not query or len(query) > len(target):
        return -1
    start = target.find(query)
    if start >= 0:
        return 10_000 - start * 20 - (len(target) - len(query))

    position = -1
    first = -1
    previous = -2
    gaps = 0
    consecutive = 0
    for char in query:
        position = target.find(char, position + 1)
        if position < 0:
            return -1
        if first < 0:
            first = position
        if position == previous + 1:
            consecutive += 1
        elif previous >= 0:
            gaps += position - previous - 1
        previous = position
    return 5_000 + consecutive * 30 - first * 15 - gaps * 8 - (len(target) - len(query))


def _score_normalized(normalized_query: str, entry: Entry) -> int:
    if not normalized_query:
        return -1
    variants: Sequence[Tuple[str, int]] = (
        (entry.normalized_name, 500),
        (entry.pinyin, 420),
        (entry.initials, 360),
    )
    scored = []
    for value, bonus in variants:
        if not value:
            continue
        raw_score = _subsequence_score(normalized_query, value)
        if raw_score >= 0:
            scored.append(raw_score + bonus)
    best = max(scored, default=-1)
    if best < 0:
        return -1
    if entry.normalized_name == normalized_query or entry.pinyin == normalized_query:
        best += 2_000
    best -= min(200, entry.path.count(os.sep) * 2)
    return best


def score_entry(query: str, entry: Entry) -> int:
    return _score_normalized(normalize(query), entry)


def build_postings(entries: Sequence[Entry]) -> Dict[str, Tuple[int, ...]]:
    """Map each searchable character to entry indexes for cheap pre-filtering."""
    mutable: Dict[str, List[int]] = {}
    for index, entry in enumerate(entries):
        characters = set(entry.normalized_name)
        characters.update(entry.pinyin)
        characters.update(entry.initials)
        for character in characters:
            mutable.setdefault(character, []).append(index)
    return {character: tuple(indexes) for character, indexes in mutable.items()}


def rank(
    query: str,
    entries: Sequence[Entry],
    limit: int,
    postings: Mapping[str, Sequence[int]] | None = None,
) -> List[Entry]:
    normalized_query = normalize(query)
    if not normalized_query:
        return []
    if postings is not None:
        posting_lists = [postings.get(character, ()) for character in set(normalized_query)]
        if not posting_lists or any(not values for values in posting_lists):
            return []
        posting_lists.sort(key=len)
        matching_indexes = set(posting_lists[0])
        for values in posting_lists[1:]:
            matching_indexes.intersection_update(values)
            if not matching_indexes:
                return []
        indexes: Iterable[int] = sorted(matching_indexes)
        candidates_iterable = (entries[index] for index in indexes)
    else:
        candidates_iterable = entries

    candidates = []
    for sequence, entry in enumerate(candidates_iterable):
        score = _score_normalized(normalized_query, entry)
        if score >= 0:
            candidates.append((score, -len(entry.name), -sequence, entry))
    return [item[3] for item in heapq.nlargest(limit, candidates)]
