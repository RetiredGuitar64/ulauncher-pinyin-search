from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from typing import Dict, Iterable, List, Tuple


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A small no-dependency safety net. Normal Arch installations use ICU's `uconv`,
# which covers the complete Han repertoire. This fallback keeps common searches
# useful on systems where ICU command-line tools are absent.
_FALLBACK = {
    "我": "wo", "的": "de", "笔": "bi", "记": "ji", "文": "wen", "件": "jian",
    "中": "zhong", "国": "guo", "新": "xin", "建": "jian", "下": "xia", "载": "zai",
    "图": "tu", "片": "pian", "音": "yin", "乐": "yue", "视": "shi", "频": "pin",
    "桌": "zhuo", "面": "mian", "项": "xiang", "目": "mu", "工": "gong", "作": "zuo",
    "学": "xue", "习": "xi", "资": "zi", "料": "liao", "备": "bei", "份": "fen",
    "临": "lin", "时": "shi", "日": "ri", "志": "zhi", "照": "zhao", "相": "xiang",
    "书": "shu", "档": "dang", "案": "an", "数": "shu", "据": "ju", "库": "ku",
    "代": "dai", "码": "ma", "设": "she", "计": "ji", "报": "bao", "告": "gao",
    "会": "hui", "议": "yi", "表": "biao", "格": "ge", "合": "he", "同": "tong",
    "简": "jian", "历": "li", "收": "shou", "藏": "cang", "电": "dian", "影": "ying",
}


def contains_han(value: str) -> bool:
    return bool(_CJK_RE.search(value))


def _fallback_romanize(value: str) -> str:
    parts = []
    for char in value:
        parts.append(_FALLBACK.get(char, char))
        if char in _FALLBACK:
            parts.append(" ")
    return "".join(parts)


def _forms(value: str) -> Tuple[str, str]:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    tokens = _TOKEN_RE.findall(ascii_value.lower())
    return "".join(tokens), "".join(token[0] for token in tokens if token)


class Transliterator:
    """Batch Han-to-Latin conversion through ICU, with a built-in fallback."""

    def __init__(self) -> None:
        self.uconv = shutil.which("uconv")

    @property
    def backend(self) -> str:
        return "icu" if self.uconv else "fallback"

    def romanize_many(self, values: Iterable[str]) -> Dict[str, Tuple[str, str]]:
        unique = list(dict.fromkeys(value for value in values if contains_han(value)))
        if not unique:
            return {}

        romanized: List[str] = []
        if self.uconv:
            for offset in range(0, len(unique), 5_000):
                batch = unique[offset:offset + 5_000]
                payload = b"\0".join(value.encode("utf-8") for value in batch) + b"\0"
                try:
                    result = subprocess.run(
                        [self.uconv, "-x", "Han-Latin; Latin-ASCII; Lower()"],
                        input=payload,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                        check=True,
                    )
                    converted = result.stdout.decode("utf-8", "replace").split("\0")[:-1]
                    if len(converted) != len(batch):
                        raise ValueError("uconv returned a different number of records")
                    romanized.extend(converted)
                except (OSError, subprocess.SubprocessError, ValueError):
                    romanized.extend(_fallback_romanize(value) for value in batch)
        else:
            romanized = [_fallback_romanize(value) for value in unique]

        return {source: _forms(converted) for source, converted in zip(unique, romanized)}
