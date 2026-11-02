"""Tests for PlaybackSessionManager auto-advance and repeat."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mp3quran.api import Catalog, Moshaf, Reciter
from custom_components.mp3quran.const import MIME_TYPE_MP3
from custom_components.mp3quran.session import PlaybackSessionManager
from custom_components.mp3quran.surahs import build_fallback_surahs
from homeassistant.core import Event


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
        "display_language": "english",
        "surah_repeat": 1,
    }
    manager = PlaybackSessionManager(hass, coordinator)
    hass.services.async_call = AsyncMock()
    return manager, reciter, moshaf


@pytest.mark.asyncio
async def test_skip_moves_between_surahs(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.living_room"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        2,
        auto_advance=True,
        surah_repeat=3,
        play=False,
    )
    hass.services.async_call.reset_mock()

    await manager.async_skip(entity_id, step=1)
    assert session.surah == 3
    assert session.plays_remaining == 3
    assert session.user_interrupted is False
    played = [
        call.args[2]["media_content_id"]
        for call in hass.services.async_call.await_args_list
        if call.args[1] == "play_media"
    ]
    assert played[-1].endswith("003.mp3")

    await manager.async_skip(entity_id, step=-1)
    assert session.surah == 2
    await manager.async_skip(entity_id, step=-1)
    assert session.surah == 1
    with pytest.raises(ValueError, match="no previous"):
        await manager.async_skip(entity_id, step=-1)
    with pytest.raises(ValueError, match="No active"):
        await manager.async_skip("media_player.other", step=1)


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
    assert session.title
    assert "Demo" in session.artist
    play_calls = [
        call
        for call in hass.services.async_call.await_args_list
        if call.args[1] == "play_media"
    ]
    assert play_calls, "expected play_media"
    play_data = play_calls[-1].args[2]
    assert any(call.args[1] == "clear_playlist" for call in hass.services.async_call.await_args_list)
    assert play_data["media_content_type"] == MIME_TYPE_MP3
    assert play_data["extra"]["metadata"]["metadataType"] == 3
    assert play_data["extra"]["metadata"]["title"] == session.title
    assert "title" not in play_data["extra"] or play_data["extra"].get("title") is None

    await manager._async_advance(session)
    assert session.surah == 1
    assert session.plays_remaining == 1
    assert len([c for c in hass.services.async_call.await_args_list if c.args[1] == "play_media"]) == 2

    await manager._async_advance(session)
    assert session.surah == 2
    assert session.plays_remaining == 2
    assert session.expected_url.endswith("/002.mp3")
    assert len([c for c in hass.services.async_call.await_args_list if c.args[1] == "play_media"]) == 3


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
async def test_attach_defaults_off(hass) -> None:
    manager, _, moshaf = _manager(hass)
    assert (
        manager.maybe_attach_from_url(
            "media_player.cast",
            moshaf.audio_url(1),
        )
        is None
    )


@pytest.mark.asyncio
async def test_async_stop_clears_and_media_stop(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.x"
    await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    await manager.async_stop(entity_id)
    assert manager.get_session(entity_id) is None
    assert hass.services.async_call.await_count >= 1
    stop_call = hass.services.async_call.await_args
    assert stop_call.args[1] == "media_stop"
    assert stop_call.args[2]["entity_id"] == entity_id


@pytest.mark.asyncio
async def test_mid_track_idle_clears_without_advance(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.room"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    # Simulate progress updates while playing, then idle with cleared attrs.
    playing = SimpleNamespace(
        state="playing",
        attributes={
            "media_content_id": session.expected_url,
            "media_position": 30,
            "media_duration": 300,
        },
    )
    await manager._async_on_state_changed(
        Event(
            {
                "entity_id": entity_id,
                "old_state": SimpleNamespace(state="idle", attributes={}),
                "new_state": playing,
            }
        )
    )
    assert session.last_position == 30
    idle = SimpleNamespace(state="idle", attributes={})
    await manager._async_on_state_changed(
        Event(
            {
                "entity_id": entity_id,
                "old_state": playing,
                "new_state": idle,
            }
        )
    )
    assert manager.get_session(entity_id) is None
    assert hass.services.async_call.await_count == 0


@pytest.mark.asyncio
async def test_user_stop_service_prevents_advance(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.esphome"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    await manager._async_on_call_service(
        Event(
            {
                "domain": "media_player",
                "service": "media_stop",
                "service_data": {"entity_id": entity_id},
            }
        )
    )
    assert session.user_interrupted is True
    await manager._async_on_state_changed(
        Event(
            {
                "entity_id": entity_id,
                "old_state": SimpleNamespace(
                    state="playing",
                    attributes={"media_content_id": session.expected_url},
                ),
                "new_state": SimpleNamespace(state="idle", attributes={}),
            }
        )
    )
    assert manager.get_session(entity_id) is None
    assert hass.services.async_call.await_count == 0


@pytest.mark.asyncio
async def test_resume_clears_pause_interrupt(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.cast"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    await manager._async_on_call_service(
        Event(
            {
                "domain": "media_player",
                "service": "media_pause",
                "service_data": {"entity_id": entity_id},
            }
        )
    )
    assert session.user_interrupted is True
    await manager._async_on_call_service(
        Event(
            {
                "domain": "media_player",
                "service": "media_play",
                "service_data": {"entity_id": entity_id},
            }
        )
    )
    assert session.user_interrupted is False


@pytest.mark.asyncio
async def test_near_end_idle_advances(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    entity_id = "media_player.room2"
    session = await manager.async_start(
        entity_id,
        reciter,
        moshaf,
        1,
        auto_advance=True,
        surah_repeat=1,
        play=False,
    )
    old = SimpleNamespace(
        state="playing",
        attributes={
            "media_content_id": session.expected_url,
            "media_position": 298,
            "media_duration": 300,
        },
    )
    new = SimpleNamespace(state="idle", attributes={})
    await manager._async_on_state_changed(
        Event({"entity_id": entity_id, "old_state": old, "new_state": new})
    )
    assert manager.get_session(entity_id) is not None
    assert manager.get_session(entity_id).surah == 2


@pytest.mark.asyncio
async def test_button_factory_called_on_start(hass) -> None:
    manager, reciter, moshaf = _manager(hass)
    factory = AsyncMock()
    manager.set_button_factory(factory)
    await manager.async_start(
        "media_player.speaker",
        reciter,
        moshaf,
        1,
        auto_advance=False,
        surah_repeat=1,
        play=False,
    )
    factory.assert_awaited_once_with("media_player.speaker")


def test_natural_end_helpers() -> None:
    assert (
        PlaybackSessionManager._is_natural_track_end(
            position=40, duration=100, max_position=40, user_interrupted=False
        )
        is False
    )
    assert (
        PlaybackSessionManager._is_natural_track_end(
            position=97, duration=100, max_position=97, user_interrupted=False
        )
        is True
    )
    assert (
        PlaybackSessionManager._is_natural_track_end(
            position=0, duration=400, max_position=0, user_interrupted=False
        )
        is True
    )
    assert (
        PlaybackSessionManager._is_natural_track_end(
            position=None, duration=None, user_interrupted=False
        )
        is True
    )
    assert (
        PlaybackSessionManager._is_natural_track_end(
            position=None, duration=None, user_interrupted=True
        )
        is False
    )
