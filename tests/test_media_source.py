"""Tests for media source browsing and identifier parsing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.mp3quran.api import Catalog, Moshaf, Reciter
from custom_components.mp3quran.const import DOMAIN, MIME_TYPE_MP3
from custom_components.mp3quran.media_source import (
    Mp3QuranMediaSource,
    _parse_identifier,
)
from custom_components.mp3quran.surahs import build_fallback_surahs
from homeassistant.components.media_source import MediaSourceItem
from homeassistant.config_entries import ConfigEntryState


def _catalog() -> Catalog:
    reciter = Reciter(
        id=102,
        name_en="Maher Al Meaqli",
        name_ar="ماهر المعيقلي",
        moshafs=[
            Moshaf(
                id=102,
                name_en="Murattal",
                name_ar="مرتل",
                server="https://cdn.mp3quran.net/audio/maher/",
                surah_total=114,
                surah_list=list(range(1, 115)),
            ),
            Moshaf(
                id=103,
                name_en="Mo'lim",
                name_ar="معلم",
                server="https://cdn.mp3quran.net/audio/maher_m/",
                surah_total=2,
                surah_list=[1, 78],
            ),
        ],
    )
    single = Reciter(
        id=1,
        name_en="Ibrahim Al-Akdar",
        name_ar="إبراهيم الأخضر",
        moshafs=[
            Moshaf(
                id=1,
                name_en="Murattal",
                name_ar="مرتل",
                server="https://cdn.mp3quran.net/audio/ibrahim/",
                surah_total=114,
                surah_list=list(range(1, 115)),
            )
        ],
    )
    return Catalog(
        reciters={1: single, 102: reciter},
        surahs=build_fallback_surahs(),
    )


def _source(catalog: Catalog, sort_language: str = "english") -> Mp3QuranMediaSource:
    entry = MagicMock()
    entry.title = "MP3 Quran"
    entry.state = ConfigEntryState.LOADED
    entry.options = {"sort_language": sort_language}
    coordinator = MagicMock()
    coordinator.data = catalog
    entry.runtime_data = SimpleNamespace(coordinator=coordinator)
    hass = MagicMock()
    return Mp3QuranMediaSource(hass, entry)


def test_parse_identifier() -> None:
    assert _parse_identifier(None) is None
    assert _parse_identifier("") is None
    assert _parse_identifier("reciter/102") == (102, None, None)
    assert _parse_identifier("reciter/102/moshaf/103") == (102, 103, None)
    assert _parse_identifier("reciter/102/moshaf/103/surah/78") == (102, 103, 78)
    assert _parse_identifier("bad/1") is None
    assert _parse_identifier("reciter/x") is None


@pytest.mark.asyncio
async def test_browse_root_sorted() -> None:
    source = _source(_catalog(), sort_language="english")
    root = await source.async_browse_media(MediaSourceItem(None))
    assert root.can_expand is True
    assert len(root.children) == 2
    titles = [child.title for child in root.children]
    assert titles == sorted(titles, key=str.casefold)
    assert "·" in titles[0]


@pytest.mark.asyncio
async def test_browse_single_moshaf_goes_to_surahs() -> None:
    source = _source(_catalog())
    page = await source.async_browse_media(MediaSourceItem("reciter/1"))
    assert page.children
    assert page.children[0].can_play is True
    assert "001" in page.children[0].title
    assert "Al-Fatihah" in page.children[0].title
    assert "الفاتحة" in page.children[0].title
    assert len(page.children) == 114


@pytest.mark.asyncio
async def test_browse_multi_moshaf_then_incomplete() -> None:
    source = _source(_catalog())
    moshafs = await source.async_browse_media(MediaSourceItem("reciter/102"))
    assert len(moshafs.children) == 2
    assert all(child.can_expand for child in moshafs.children)

    surahs = await source.async_browse_media(
        MediaSourceItem("reciter/102/moshaf/103")
    )
    assert len(surahs.children) == 2
    assert surahs.children[0].identifier.endswith("/surah/1")
    assert surahs.children[1].identifier.endswith("/surah/78")


@pytest.mark.asyncio
async def test_resolve_media() -> None:
    source = _source(_catalog())
    media = await source.async_resolve_media(
        MediaSourceItem("reciter/1/moshaf/1/surah/2")
    )
    assert media.mime_type == MIME_TYPE_MP3
    assert media.url.endswith("/002.mp3")
