"""Tests for MP3 Quran service helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mp3quran.api import Catalog, Moshaf, Reciter
from custom_components.mp3quran.const import DEFAULT_AUTO_ADVANCE
from custom_components.mp3quran.services import async_register_services
from custom_components.mp3quran.session import PlaybackSessionManager
from custom_components.mp3quran.surahs import build_fallback_surahs
from homeassistant.exceptions import HomeAssistantError


def _setup(hass):
    moshaf = Moshaf(
        id=10,
        name_en="Murattal",
        name_ar="مرتل",
        server="https://cdn.mp3quran.net/audio/demo/",
        surah_total=2,
        surah_list=[1, 2],
    )
    reciter = Reciter(id=5, name_en="Demo", name_ar="تجريبي", moshafs=[moshaf])
    catalog = Catalog(reciters={5: reciter}, surahs=build_fallback_surahs())
    coordinator = MagicMock()
    coordinator.data = catalog
    coordinator.entry = MagicMock()
    coordinator.entry.options = {"surah_repeat": 2, "display_language": "english"}
    sessions = PlaybackSessionManager(hass, coordinator)
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    async_register_services(hass, coordinator, sessions)
    play_handler = hass.services.async_register.call_args_list[0].args[2]
    stop_handler = hass.services.async_register.call_args_list[1].args[2]
    return sessions, play_handler, stop_handler


@pytest.mark.asyncio
async def test_play_defaults_auto_advance_off(hass) -> None:
    assert DEFAULT_AUTO_ADVANCE is False
    sessions, play_handler, _ = _setup(hass)
    call = SimpleNamespace(
        data={
            "entity_id": "media_player.living_room",
            "reciter_id": 5,
            "surah": 1,
        }
    )
    await play_handler(call)
    session = sessions.get_session("media_player.living_room")
    assert session is not None
    assert session.auto_advance is False
    assert session.surah_repeat == 2
    handlers = {
        call.args[1]: call.args[2] for call in hass.services.async_register.call_args_list
    }
    await handlers["next_surah"](
        SimpleNamespace(data={"entity_id": "media_player.living_room"})
    )
    assert session.surah == 2
    with pytest.raises(HomeAssistantError, match="no next"):
        await handlers["next_surah"](
            SimpleNamespace(data={"entity_id": "media_player.living_room"})
        )


@pytest.mark.asyncio
async def test_play_requires_media_player(hass) -> None:
    _, play_handler, _ = _setup(hass)
    call = SimpleNamespace(data={"reciter_id": 5, "surah": 1})
    with pytest.raises(HomeAssistantError, match="media_player"):
        await play_handler(call)


def test_schema_allows_device_id() -> None:
    from custom_components.mp3quran.services import PLAY_SCHEMA

    parsed = PLAY_SCHEMA(
        {
            "device_id": ["abc123"],
            "reciter_id": 5,
            "surah": 1,
        }
    )
    assert parsed["reciter_id"] == 5
    assert parsed["device_id"] == ["abc123"]


@pytest.mark.asyncio
async def test_device_id_expands_to_media_player(hass, monkeypatch) -> None:
    from custom_components.mp3quran.services import _media_players_from_registry

    class _Entry:
        def __init__(self, entity_id: str) -> None:
            self.entity_id = entity_id
            self.disabled_by = None

    class _Entities:
        def get_entries_for_device_id(self, device_id: str):
            assert device_id == "dev1"
            return [
                _Entry("media_player.living_room"),
                _Entry("sensor.living_room_battery"),
            ]

    class _Registry:
        entities = _Entities()

    monkeypatch.setattr(
        "custom_components.mp3quran.services.er.async_get",
        lambda _hass: _Registry(),
    )
    found = _media_players_from_registry(hass, {"device_id": "dev1"})
    assert found == {"media_player.living_room"}


@pytest.mark.asyncio
async def test_stop_handler_stops_media(hass) -> None:
    sessions, play_handler, stop_handler = _setup(hass)
    await play_handler(
        SimpleNamespace(
            data={
                "entity_id": ["media_player.living_room"],
                "reciter_id": 5,
                "surah": 1,
                "auto_advance": True,
            }
        )
    )
    hass.services.async_call.reset_mock()
    await stop_handler(
        SimpleNamespace(data={"entity_id": "media_player.living_room"})
    )
    assert sessions.get_session("media_player.living_room") is None
    assert hass.services.async_call.await_args.args[1] == "media_stop"
