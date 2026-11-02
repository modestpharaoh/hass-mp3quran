"""Shared pytest fixtures and Home Assistant stubs."""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(ROOT))


def _ensure_ha_stubs() -> None:
    """Install lightweight homeassistant stubs when HA is not installed."""
    if "homeassistant" in sys.modules and hasattr(sys.modules["homeassistant"], "core"):
        # Real or already-stubbed package present.
        try:
            import homeassistant.core  # noqa: F401

            return
        except ImportError:
            pass

    ha = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha

    # const
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.ATTR_ENTITY_ID = "entity_id"
    ha_const.STATE_IDLE = "idle"
    ha_const.STATE_OFF = "off"
    ha_const.STATE_UNAVAILABLE = "unavailable"
    ha_const.EVENT_CALL_SERVICE = "call_service"
    ha_const.SERVICE_TURN_OFF = "turn_off"
    ha_const.Platform = types.SimpleNamespace(SENSOR="sensor", BUTTON="button")
    sys.modules["homeassistant.const"] = ha_const

    # core
    ha_core = types.ModuleType("homeassistant.core")

    class HomeAssistant:
        def __init__(self) -> None:
            self.data = {}
            self.bus = MagicMock()
            self.bus.async_listen = MagicMock(return_value=MagicMock())
            self.services = MagicMock()
            self.services.has_service = MagicMock(return_value=False)
            self.services.async_register = MagicMock()
            self.services.async_remove = MagicMock()
            self.services.async_call = AsyncMock()
            self.config_entries = MagicMock()
            self.http = MagicMock()
            self.http.async_register_static_paths = AsyncMock()

    def callback(func):
        return func

    class Event:
        def __init__(self, data=None):
            self.data = data or {}

    ha_core.HomeAssistant = HomeAssistant
    ha_core.ServiceCall = type(
        "ServiceCall",
        (),
        {"__init__": lambda self, data=None: setattr(self, "data", data or {})},
    )
    ha_core.Event = Event
    ha_core.callback = callback
    sys.modules["homeassistant.core"] = ha_core

    # exceptions
    ha_exc = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    class ConfigEntryNotReady(Exception):
        pass

    ha_exc.HomeAssistantError = HomeAssistantError
    ha_exc.ConfigEntryNotReady = ConfigEntryNotReady
    sys.modules["homeassistant.exceptions"] = ha_exc

    # config_entries
    ha_ce = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        def __init__(self, **kwargs):
            self.data = kwargs.get("data", {})
            self.options = kwargs.get("options", {})
            self.title = kwargs.get("title", "MP3 Quran")
            self.entry_id = kwargs.get("entry_id", "test")
            self.runtime_data = None
            self.state = types.SimpleNamespace(value="loaded")

        def async_on_unload(self, fn):
            return fn

        def add_update_listener(self, fn):
            return MagicMock()

    class ConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            cls.domain = domain

        def async_abort(self, reason):
            return {"type": "abort", "reason": reason}

        def async_create_entry(self, title, data, options=None):
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
                "options": options or {},
            }

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors,
            }

        def _async_current_entries(self):
            return []

    class OptionsFlow:
        def __init__(self, config_entry=None):
            self.config_entry = config_entry or ConfigEntry()

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, step_id, data_schema=None):
            return {"type": "form", "step_id": step_id, "data_schema": data_schema}

    class ConfigFlowResult(dict):
        pass

    ConfigEntryState = types.SimpleNamespace(
        LOADED="loaded",
        NOT_LOADED="not_loaded",
        SETUP_ERROR="setup_error",
    )

    ha_ce.ConfigEntry = ConfigEntry
    ha_ce.ConfigFlow = ConfigFlow
    ha_ce.OptionsFlow = OptionsFlow
    ha_ce.ConfigFlowResult = ConfigFlowResult
    ha_ce.ConfigEntryState = ConfigEntryState
    sys.modules["homeassistant.config_entries"] = ha_ce

    # helpers
    ha_helpers = types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = ha_helpers

    ha_cv = types.ModuleType("homeassistant.helpers.config_validation")

    def entity_ids(value):
        if isinstance(value, str):
            return [value]
        return list(value)

    def boolean(value):
        return bool(value)

    def empty_config_schema(domain):
        return MagicMock()

    ha_cv.entity_ids = entity_ids
    ha_cv.boolean = boolean
    ha_cv.empty_config_schema = empty_config_schema
    ha_cv.cv = ha_cv
    sys.modules["homeassistant.helpers.config_validation"] = ha_cv

    ha_typing = types.ModuleType("homeassistant.helpers.typing")
    ha_typing.ConfigType = dict
    sys.modules["homeassistant.helpers.typing"] = ha_typing

    ha_aiohttp = types.ModuleType("homeassistant.helpers.aiohttp_client")
    ha_aiohttp.async_get_clientsession = MagicMock()
    sys.modules["homeassistant.helpers.aiohttp_client"] = ha_aiohttp

    ha_er = types.ModuleType("homeassistant.helpers.entity_registry")

    def _async_get_registry(_hass):
        raise RuntimeError("no registry in tests")

    ha_er.async_get = _async_get_registry
    sys.modules["homeassistant.helpers.entity_registry"] = ha_er

    ha_service = types.ModuleType("homeassistant.helpers.service")

    async def async_extract_entity_ids(hass, call):
        raw = (call.data or {}).get("entity_id")
        if not raw:
            return set()
        if isinstance(raw, str):
            return {raw}
        return set(raw)

    ha_service.async_extract_entity_ids = async_extract_entity_ids
    sys.modules["homeassistant.helpers.service"] = ha_service

    ha_uc = types.ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, name=None, config_entry=None, update_interval=None):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.config_entry = config_entry
            self.update_interval = update_interval
            self.data = None

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

    ha_uc.DataUpdateCoordinator = DataUpdateCoordinator
    ha_uc.UpdateFailed = UpdateFailed
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_uc

    ha_selector = types.ModuleType("homeassistant.helpers.selector")

    class NumberSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class NumberSelector:
        def __init__(self, config):
            self.config = config

        def __call__(self, value):
            return value

    class NumberSelectorMode:
        BOX = "box"

    class SelectSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class SelectSelector:
        def __init__(self, config):
            self.config = config

        def __call__(self, value):
            return value

    class SelectSelectorMode:
        DROPDOWN = "dropdown"

    ha_selector.NumberSelector = NumberSelector
    ha_selector.NumberSelectorConfig = NumberSelectorConfig
    ha_selector.NumberSelectorMode = NumberSelectorMode
    ha_selector.SelectSelector = SelectSelector
    ha_selector.SelectSelectorConfig = SelectSelectorConfig
    ha_selector.SelectSelectorMode = SelectSelectorMode
    sys.modules["homeassistant.helpers.selector"] = ha_selector

    # media_player
    ha_mp = types.ModuleType("homeassistant.components.media_player")
    ha_mp.ATTR_MEDIA_CONTENT_ID = "media_content_id"
    ha_mp.ATTR_MEDIA_CONTENT_TYPE = "media_content_type"
    ha_mp.ATTR_MEDIA_DURATION = "media_duration"
    ha_mp.ATTR_MEDIA_POSITION = "media_position"
    ha_mp.DOMAIN = "media_player"
    ha_mp.SERVICE_PLAY_MEDIA = "play_media"
    ha_mp.SERVICE_MEDIA_STOP = "media_stop"
    ha_mp.MediaClass = types.SimpleNamespace(
        CHANNEL="channel",
        DIRECTORY="directory",
        TRACK="track",
        MUSIC="music",
    )
    ha_mp.MediaType = types.SimpleNamespace(MUSIC="music")
    ha_mp.MediaPlayerState = types.SimpleNamespace(
        PLAYING="playing", IDLE="idle", OFF="off", PAUSED="paused"
    )

    class BrowseError(Exception):
        pass

    ha_mp.BrowseError = BrowseError
    sys.modules["homeassistant.components"] = types.ModuleType("homeassistant.components")
    sys.modules["homeassistant.components.media_player"] = ha_mp

    # device_registry helpers used by sensor/button
    ha_dr = types.ModuleType("homeassistant.helpers.device_registry")
    ha_dr.DeviceEntryType = types.SimpleNamespace(SERVICE="service")

    def DeviceInfo(**kwargs):
        return kwargs

    ha_dr.DeviceInfo = DeviceInfo
    sys.modules["homeassistant.helpers.device_registry"] = ha_dr

    ha_sensor = types.ModuleType("homeassistant.components.sensor")

    class SensorEntity:
        def async_write_ha_state(self):
            pass

    ha_sensor.SensorEntity = SensorEntity
    sys.modules["homeassistant.components.sensor"] = ha_sensor

    ha_button = types.ModuleType("homeassistant.components.button")

    class ButtonEntity:
        def async_write_ha_state(self):
            pass

    ha_button.ButtonEntity = ButtonEntity
    sys.modules["homeassistant.components.button"] = ha_button

    ha_ep = types.ModuleType("homeassistant.helpers.entity_platform")
    ha_ep.AddEntitiesCallback = object
    sys.modules["homeassistant.helpers.entity_platform"] = ha_ep

    # media_source
    ha_ms = types.ModuleType("homeassistant.components.media_source")

    class MediaSource:
        def __init__(self, domain):
            self.domain = domain

    class MediaSourceItem:
        def __init__(self, identifier=None):
            self.identifier = identifier

    class BrowseMediaSource:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class PlayMedia:
        def __init__(self, url, mime_type):
            self.url = url
            self.mime_type = mime_type

    class Unresolvable(Exception):
        pass

    ha_ms.MediaSource = MediaSource
    ha_ms.MediaSourceItem = MediaSourceItem
    ha_ms.BrowseMediaSource = BrowseMediaSource
    ha_ms.PlayMedia = PlayMedia
    ha_ms.Unresolvable = Unresolvable
    sys.modules["homeassistant.components.media_source"] = ha_ms

    ha_frontend = types.ModuleType("homeassistant.components.frontend")

    def add_extra_js_url(_hass, url):
        add_extra_js_url.calls.append(url)

    add_extra_js_url.calls = []
    ha_frontend.add_extra_js_url = add_extra_js_url
    sys.modules["homeassistant.components.frontend"] = ha_frontend

    ha_http = types.ModuleType("homeassistant.components.http")

    class StaticPathConfig:
        def __init__(self, url_path, path, cache_headers=True):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    ha_http.StaticPathConfig = StaticPathConfig
    sys.modules["homeassistant.components.http"] = ha_http


_ensure_ha_stubs()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def load_fixture():
    def _load(name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def hass():
    from homeassistant.core import HomeAssistant

    return HomeAssistant()
