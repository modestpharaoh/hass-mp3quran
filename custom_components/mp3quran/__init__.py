"""The MP3 Quran integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN
from .coordinator import Mp3QuranCoordinator
from .services import async_register_services, async_unregister_services
from .session import PlaybackSessionManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


@dataclass(slots=True)
class Mp3QuranRuntimeData:
    """Runtime data attached to the config entry."""

    coordinator: Mp3QuranCoordinator
    sessions: PlaybackSessionManager


type Mp3QuranConfigEntry = ConfigEntry[Mp3QuranRuntimeData]


_FRONTEND_READY = "frontend_ready"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (config entry only) and register the Lovelace card."""
    await _async_register_frontend(hass)
    return True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card once and load it in the frontend."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_FRONTEND_READY):
        return
    root = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig("/mp3quran", str(root / "www"), False),
            StaticPathConfig("/mp3quran_brand", str(root / "brand"), False),
        ]
    )
    add_extra_js_url(hass, CARD_URL)
    domain_data[_FRONTEND_READY] = True


async def async_setup_entry(hass: HomeAssistant, entry: Mp3QuranConfigEntry) -> bool:
    """Set up MP3 Quran from a config entry."""
    coordinator = Mp3QuranCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sessions = PlaybackSessionManager(hass, coordinator)
    entry.runtime_data = Mp3QuranRuntimeData(
        coordinator=coordinator,
        sessions=sessions,
    )

    async_register_services(hass, coordinator, sessions)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "MP3 Quran media source ready (%s reciters)",
        len(coordinator.data.reciters),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Mp3QuranConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    entry.runtime_data.sessions.async_unload()

    other_entries = [
        item
        for item in hass.config_entries.async_entries(DOMAIN)
        if item.entry_id != entry.entry_id
    ]
    if not other_entries:
        async_unregister_services(hass)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: Mp3QuranConfigEntry
) -> None:
    """Handle options updates by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
