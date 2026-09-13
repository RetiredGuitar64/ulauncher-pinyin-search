#!/usr/bin/env python3
from __future__ import annotations

import logging
import os

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem

from pinyin_search.config import SearchConfig
from pinyin_search.index import FileIndex
from pinyin_search.matcher import Entry, rank


logger = logging.getLogger(__name__)
INDEX = FileIndex()


def result_item(entry: Entry) -> ExtensionResultItem:
    kind = "Folder" if entry.is_dir else "File"
    icon = "images/folder.png" if entry.is_dir else "images/file.png"
    return ExtensionResultItem(
        icon=icon,
        name=entry.name,
        description=f"{kind} · {entry.path}",
        on_enter=OpenAction(entry.path),
    )


def message_item(name: str, description: str) -> ExtensionResultItem:
    return ExtensionResultItem(
        icon="images/icon.png",
        name=name,
        description=description,
        on_enter=DoNothingAction(),
    )


class QueryListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").strip()
        config = SearchConfig.from_preferences(extension.preferences)
        INDEX.ensure(config)

        if not config.roots:
            return RenderResultListAction([
                message_item("No valid search root", "Open extension preferences and add an existing directory")
            ])
        if len(query) < config.min_query_length:
            building, count, error, backend = INDEX.status()
            state = f"{count:,} cached paths · pinyin backend: {backend}"
            if building:
                state = "Indexing in the background · " + state
            if error:
                state = error
            return RenderResultListAction([
                message_item(f"Type at least {config.min_query_length} characters", state)
            ])

        entries = INDEX.snapshot()
        if entries:
            matches = INDEX.search(query, config.max_results)
        else:
            direct = INDEX.backend.direct_search(query, config)
            matches = rank(
                query,
                (Entry.from_path(path, is_dir) for path, is_dir in direct),
                config.max_results,
            )

        if matches:
            return RenderResultListAction([result_item(entry) for entry in matches])

        building, count, error, _ = INDEX.status()
        if building:
            detail = f"The pinyin index is still building ({count:,} cached paths available)"
        elif error:
            detail = error
        else:
            detail = "Try another filename, full pinyin, or pinyin initials"
        return RenderResultListAction([message_item(f'No match for “{query}”', detail)])


class PinyinFileSearchExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, QueryListener())


if __name__ == "__main__":
    PinyinFileSearchExtension().run()
