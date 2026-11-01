"""Tests for PlaybackSessionManager auto-advance and repeat."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mp3quran.api import Catalog, Moshaf, Reciter
from custom_components.mp3quran.session import PlaybackSessionManager
from custom_components.mp3quran.surahs import build_fallback_surahs


def _manager(hass) -> tuple[PlaybackSessionManager, Reciter, Moshaf]:
    moshaf = Moshaf(
        id=10,
        name_en="Murattal",
        name_ar="مرتل",
        server="https://cdn.mp3quran.net/audio/demo/",
        surah_total=3,
        surah_list=[1, 2, 3],
    )
    reciter = Reciter(
        id=5,
        name_en="Demo",
        name_ar="تجريبي",
        moshafs=[moshaf],
    )
    catalog = Catalog(reciters={5: reciter}, surahs=build_fallback_surahs())
    coordinator = MagicMock()
    coordinator.data = catalog
    coordinator.entry = MagicMock()
    coordinator.entry.options = {
        "auto_advance": True,
        "surah_repeat": 1,
    }
    manager = PlaybackSessionManager(hass, coordinator)
    hass.services.async_call = AsyncMock()
    return manager, reciter, moshaf


@pytest.mark.asyncio
async def test_repeat_then_advance(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.living_room"

    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=2,
    )
    assert session.plays_remaining == 2
    assert session.expected_url.endswith("/001.mp3")
    assert hass.services.async_call.await_count == 1

    await manager._async_advance(session)
    assert session.surah == 1
    assert session.plays_remaining == 1
    assert hass.services.async_call.await_count == 2

    await manager._async_advance(session)
    assert session.surah == 2
    assert session.plays_remaining == 2
    assert session.expected_url.endswith("/002.mp3")
    assert hass.services.async_call.await_count == 3


@pytest.mark.asyncio
async def test_auto_advance_disabled_stops(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.kitchen"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=False,
        surah_repeat=1,
    )
    await manager._async_advance(session)
    assert manager.get_session(entity_id) is None


@pytest.mark.asyncio
async def test_end_of_quran_stops(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.office"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        3,
        auto_advance=True,
        surah_repeat=1,
    )
    await manager._async_advance(session)
    assert manager.get_session(entity_id) is None


@pytest.mark.asyncio
async def test_attach_from_url(hass) -> None:
    manager, _, moshaf = _manager(hass)
    url = moshaf.audio_url(2)
    session = manager.maybe_attach_from_url(
        "media_player.cast",
        url,
        auto_advance=True,
        surah_repeat=3,
    )
    assert session is not None
    assert session.surah == 2
    assert session.surah_repeat == 3


@pytest.mark.asyncio
async def test_stop_session(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    await manager.async_start(
        "media_player.x",
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    manager.stop("media_player.x")
    assert manager.get_session("media_player.x") is None
